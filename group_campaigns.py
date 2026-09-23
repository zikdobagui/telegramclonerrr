"""Persistent group campaigns. Telegram work is performed only after Start."""
import asyncio
import csv
import io
import json
import os
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime


def day_key():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat()


def integer(value, label, low=1, high=10000):
    try:
        result = int(value)
    except (ValueError, TypeError):
        raise ValueError(f'{label}: informe um número inteiro')
    if not low <= result <= high:
        raise ValueError(f'{label}: use um valor entre {low} e {high}')
    return result


class CampaignStore:
    def __init__(self, directory):
        os.makedirs(directory, exist_ok=True)
        self.path = os.path.join(directory, 'group_campaigns.db')
        with self.db() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS campaigns (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, settings TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'paused', error TEXT NOT NULL DEFAULT '',
                    created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
                    slot INTEGER NOT NULL, title TEXT NOT NULL, daily_limit INTEGER NOT NULL,
                    reference TEXT NOT NULL DEFAULT '', channel_id TEXT, access_hash TEXT,
                    creator TEXT NOT NULL DEFAULT '', invite TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending', current INTEGER NOT NULL DEFAULT 1,
                    warm_until REAL NOT NULL DEFAULT 0, next_message REAL NOT NULL DEFAULT 0,
                    message_index INTEGER NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '');
                CREATE UNIQUE INDEX IF NOT EXISTS current_slot ON groups(campaign_id,slot) WHERE current=1;
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY, payload TEXT NOT NULL, created REAL NOT NULL,
                    canonical_id INTEGER REFERENCES leads(id));
                CREATE TABLE IF NOT EXISTS aliases (
                    alias TEXT PRIMARY KEY, lead_id INTEGER NOT NULL REFERENCES leads(id));
                CREATE INDEX IF NOT EXISTS lead_identity ON leads(canonical_id);
                CREATE TABLE IF NOT EXISTS deliveries (
                    id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
                    group_id INTEGER NOT NULL REFERENCES groups(id), slot INTEGER NOT NULL,
                    lead_id INTEGER NOT NULL REFERENCES leads(id), scope INTEGER NOT NULL,
                    day TEXT NOT NULL, status TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', resolved_id TEXT,
                    UNIQUE(campaign_id,lead_id,scope));
                CREATE UNIQUE INDEX IF NOT EXISTS delivered_identity ON deliveries(campaign_id,scope,resolved_id) WHERE resolved_id IS NOT NULL;
                CREATE INDEX IF NOT EXISTS delivery_quota ON deliveries(campaign_id,slot,day,status);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL, message TEXT NOT NULL, created REAL NOT NULL);
            ''')

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA journal_mode=WAL')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def event(self, cid, message):
        with self.db() as conn:
            conn.execute('INSERT INTO events(campaign_id,message,created) VALUES(?,?,?)', (cid, message[:1000], time.time()))
            conn.execute('DELETE FROM events WHERE campaign_id=? AND id NOT IN (SELECT id FROM events WHERE campaign_id=? ORDER BY id DESC LIMIT 100)', (cid, cid))

    def get(self, cid):
        with self.db() as conn:
            row = conn.execute('SELECT * FROM campaigns WHERE id=?', (cid,)).fetchone()
            if not row:
                raise ValueError('Tarefa não encontrada')
            result = dict(row)
            result['settings'] = json.loads(result['settings'])
            return result

    def state(self, cid, status, error=''):
        with self.db() as conn:
            conn.execute('UPDATE campaigns SET status=?,error=? WHERE id=?', (status, error[:1000], cid))

    def prepare_start(self, cid):
        """Recover the fixed invite parsing error without retrying deliveries."""
        with self.db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            campaign = conn.execute('SELECT * FROM campaigns WHERE id=?', (cid,)).fetchone()
            if not campaign:
                raise ValueError('Tarefa não encontrada')
            settings = json.loads(campaign['settings'])
            groups = conn.execute('SELECT * FROM groups WHERE campaign_id=? AND current=1', (cid,)).fetchall()
            recovered = 0
            for group in groups:
                if group['status'] != 'error' or group['error'] != "'ChatInviteJoinResultOk' object has no attribute 'chats'":
                    continue
                if group['channel_id'] and group['access_hash'] and group['creator'] and group['invite']:
                    # These groups already exist. Resume the previous phase.
                    until = group['warm_until']
                    if settings['warming'] and not until:
                        until = time.time() + settings['warm_days'] * 86400
                    status = 'warming' if settings['warming'] and until > time.time() else 'ready'
                    conn.execute("UPDATE groups SET status=?,error='',warm_until=? WHERE id=?", (status, until, group['id']))
                elif group['reference'] and not group['channel_id']:
                    # Re-resolve the existing invite; never create a new group.
                    conn.execute("UPDATE groups SET status='pending',error='' WHERE id=?", (group['id'],))
                else:
                    continue
                recovered += 1
            runnable = conn.execute("SELECT count(*) FROM groups WHERE campaign_id=? AND current=1 AND status IN ('pending','warming','ready')", (cid,)).fetchone()[0]
            if not runnable:
                raise ValueError('Nenhum grupo disponível para iniciar. Abra os detalhes dos grupos e resolva os erros ou vincule um grupo substituto.')
            conn.execute("UPDATE campaigns SET status='running',error='' WHERE id=?", (cid,))
            if recovered:
                conn.execute('INSERT INTO events(campaign_id,message,created) VALUES(?,?,?)',
                             (cid, f'{recovered} grupo(s) recuperado(s) do erro de convite. Histórico de leads e cotas preservados.', time.time()))

    def create(self, payload, session_names):
        name = str(payload.get('name') or '').strip()[:100]
        if not name or not session_names:
            raise ValueError('Informe o nome e selecione pelo menos uma sessão')
        count = integer(payload.get('count', 10), 'Quantidade de grupos', high=30)
        limit = integer(payload.get('daily_limit', 25), 'Limite diário')
        messages = [str(line).strip()[:4000] for line in str(payload.get('messages', '')).splitlines() if line.strip()]
        warming = payload.get('warming') is True
        if warming and not messages:
            raise ValueError('Adicione frases para habilitar o aquecimento')
        settings = {
            'sessions': list(dict.fromkeys(session_names)), 'warming': warming, 'messages': messages[:1000],
            'warm_days': integer(payload.get('warm_days', 1), 'Dias de aquecimento', high=90),
            'warm_interval': integer(payload.get('warm_interval', 60), 'Intervalo de mensagens (minutos)', high=1440),
            'delay': integer(payload.get('delay', 60), 'Intervalo entre ações (segundos)', low=10, high=3600),
            'dedup': 'group' if payload.get('dedup') == 'group' else 'task',
            'limit_scope': 'task' if payload.get('limit_scope') == 'task' else 'group',
            'daily_limit': limit,
        }
        with self.db() as conn:
            cid = conn.execute('INSERT INTO campaigns(name,settings,created) VALUES(?,?,?)', (name, json.dumps(settings), time.time())).lastrowid
            for slot in range(1, count + 1):
                conn.execute('INSERT INTO groups(campaign_id,slot,title,daily_limit) VALUES(?,?,?,?)', (cid, slot, f'{name} {slot:02}', limit))
        return cid

    def groups(self, cid):
        with self.db() as conn:
            return [dict(row) for row in conn.execute('SELECT * FROM groups WHERE campaign_id=? AND current=1 ORDER BY slot', (cid,))]

    def group_update(self, gid, **values):
        allowed = {'status', 'channel_id', 'access_hash', 'creator', 'invite', 'warm_until', 'next_message', 'message_index', 'error'}
        if not values or not set(values) <= allowed:
            raise ValueError('Campos inválidos')
        with self.db() as conn:
            conn.execute('UPDATE groups SET ' + ','.join(f'{key}=?' for key in values) + ' WHERE id=?', (*values.values(), gid))

    def edit_group(self, cid, gid, payload):
        with self.db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            campaign = conn.execute('SELECT * FROM campaigns WHERE id=?', (cid,)).fetchone()
            group = conn.execute('SELECT * FROM groups WHERE id=? AND campaign_id=? AND current=1', (gid, cid)).fetchone()
            if not campaign or not group:
                raise ValueError('Grupo não encontrado nesta tarefa')
            if campaign['status'] == 'running':
                raise ValueError('Pause a tarefa antes de editar ou substituir grupos')
            limit = integer(payload.get('daily_limit', group['daily_limit']), 'Limite diário')
            if payload.get('replace'):
                title = str(payload.get('title') or group['title']).strip()[:100]
                reference = str(payload.get('reference') or '').strip()
                if reference and not re.fullmatch(r'(?:https://)?t\.me/(?:\+|joinchat/)?[\w-]+|@[\w]+', reference):
                    raise ValueError('Informe um link t.me ou @username válido')
                conn.execute('UPDATE groups SET current=0 WHERE id=?', (gid,))
                conn.execute('INSERT INTO groups(campaign_id,slot,title,daily_limit,reference) VALUES(?,?,?,?,?)', (cid, group['slot'], title, limit, reference))
            else:
                conn.execute('UPDATE groups SET daily_limit=? WHERE id=?', (limit, gid))
        self.event(cid, 'Grupo substituído; histórico de leads e cota diária preservados.' if payload.get('replace') else 'Limite diário atualizado.')

    def import_leads(self, filename, raw):
        if len(raw) > 25 * 1024 * 1024:
            raise ValueError('O arquivo deve ter até 25 MB')
        text = raw.decode('utf-8-sig')
        if filename.lower().endswith('.json'):
            data = json.loads(text)
            rows = data.get('members', data.get('leads', [])) if isinstance(data, dict) else data
            if not isinstance(rows, list):
                raise ValueError('O JSON deve conter uma lista de membros ou leads')
        elif filename.lower().endswith('.csv'):
            rows = list(csv.DictReader(io.StringIO(text)))
        elif filename.lower().endswith('.txt'):
            rows = [{'username': line.strip()} for line in text.splitlines() if line.strip()]
        else:
            raise ValueError('Use JSON, CSV ou TXT (um @username por linha)')
        stats = {'added': 0, 'duplicates': 0, 'invalid': 0}
        with self.db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            for row in rows:
                if not isinstance(row, dict):
                    stats['invalid'] += 1
                    continue
                uid = str(row.get('id') or '').strip()
                username = str(row.get('username') or '').strip().removeprefix('https://t.me/').lstrip('@').lower()
                phone = re.sub(r'\D', '', str(row.get('phone') or ''))
                aliases = []
                if uid.isdigit():
                    aliases.append('id:' + uid)
                if re.fullmatch(r'[a-z][a-z0-9_]{3,31}', username):
                    aliases.append('user:' + username)
                else:
                    username = ''
                if 7 <= len(phone) <= 15:
                    aliases.append('phone:' + phone)
                else:
                    phone = ''
                if not aliases:
                    stats['invalid'] += 1
                    continue
                known = {item['lead_id'] for item in conn.execute('SELECT lead_id FROM aliases WHERE alias IN (' + ','.join('?' * len(aliases)) + ')', aliases)}
                if known:
                    lead_id = min(known)
                    # An enriched import can connect a previous ID-only row to a
                    # username-only row. Keep both histories, but consume them as
                    # one identity in every campaign from now on.
                    if len(known) > 1:
                        placeholders = ','.join('?' * len(known))
                        conn.execute(f'UPDATE leads SET canonical_id=? WHERE (id IN ({placeholders}) OR canonical_id IN ({placeholders})) AND id<>?', (lead_id, *known, *known, lead_id))
                        conn.execute(f'UPDATE aliases SET lead_id=? WHERE lead_id IN ({placeholders})', (lead_id, *known))
                    for alias in aliases:
                        conn.execute('INSERT OR IGNORE INTO aliases VALUES(?,?)', (alias, lead_id))
                    current = json.loads(conn.execute('SELECT payload FROM leads WHERE id=?', (lead_id,)).fetchone()[0])
                    current.update({key: value for key, value in dict(row, username=username, phone=phone).items() if value not in (None, '')})
                    conn.execute('UPDATE leads SET payload=? WHERE id=?', (json.dumps(current), lead_id))
                    stats['duplicates'] += 1
                    continue
                payload = dict(row, username=username, phone=phone)
                lead_id = conn.execute('INSERT INTO leads(payload,created) VALUES(?,?)', (json.dumps(payload), time.time())).lastrowid
                for alias in aliases:
                    conn.execute('INSERT INTO aliases VALUES(?,?)', (alias, lead_id))
                stats['added'] += 1
        return stats

    def claim(self, cid, gid):
        """Reserve before network I/O: uncertain results are never resent automatically."""
        with self.db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            campaign = conn.execute('SELECT * FROM campaigns WHERE id=?', (cid,)).fetchone()
            group = conn.execute('SELECT * FROM groups WHERE id=? AND campaign_id=? AND current=1', (gid, cid)).fetchone()
            if not campaign or campaign['status'] != 'running' or not group or group['status'] != 'ready':
                return None
            settings = json.loads(campaign['settings'])
            scope = group['slot'] if settings['dedup'] == 'group' else 0
            day = day_key()
            params = [cid, day]
            slot_sql = ''
            limit = settings['daily_limit']
            if settings['limit_scope'] == 'group':
                slot_sql = ' AND slot=?'
                params.append(group['slot'])
                limit = group['daily_limit']
            used = conn.execute("SELECT count(*) FROM deliveries WHERE campaign_id=? AND day=? AND status IN ('sending','added','unknown')" + slot_sql, params).fetchone()[0]
            if used >= limit:
                return None
            lead = conn.execute('''SELECT * FROM leads l WHERE canonical_id IS NULL AND NOT EXISTS (
                SELECT 1 FROM deliveries WHERE campaign_id=? AND scope=? AND lead_id IN (
                    SELECT id FROM leads WHERE id=l.id OR canonical_id=l.id
                )) ORDER BY id LIMIT 1''', (cid, scope)).fetchone()
            if not lead:
                return None
            did = conn.execute("INSERT INTO deliveries(campaign_id,group_id,slot,lead_id,scope,day,status) VALUES(?,?,?,?,?,?,'sending')", (cid, gid, group['slot'], lead['id'], scope, day)).lastrowid
            return {'id': did, 'lead_id': lead['id'], 'payload': json.loads(lead['payload'])}

    def finish(self, did, status, error=''):
        with self.db() as conn:
            conn.execute('UPDATE deliveries SET status=?,error=? WHERE id=?', (status, error[:1000], did))

    def reserve_identity(self, did, telegram_id):
        """Final dedup check after resolving a phone/username to its Telegram ID."""
        with self.db() as conn:
            try:
                conn.execute('UPDATE deliveries SET resolved_id=? WHERE id=?', (str(telegram_id), did))
            except sqlite3.IntegrityError:
                return False
        return True

    def recover(self):
        with self.db() as conn:
            conn.execute("UPDATE campaigns SET status='paused',error='Servidor reiniciado. Clique em Iniciar para continuar.' WHERE status='running'")
            conn.execute("UPDATE deliveries SET status='unknown',error='Resultado não confirmado antes da interrupção' WHERE status='sending'")
            conn.execute("UPDATE groups SET status='error',error='Criação interrompida. Verifique o Telegram e substitua por link para evitar recriar.' WHERE status='creating'")

    def snapshot(self):
        with self.db() as conn:
            ids = [row[0] for row in conn.execute('SELECT id FROM campaigns ORDER BY id DESC')]
            result = {'total_leads': conn.execute('SELECT count(*) FROM leads WHERE canonical_id IS NULL').fetchone()[0], 'campaigns': []}
            for cid in ids:
                task = self.get(cid)
                task['groups'] = self.groups(cid)
                task['events'] = [dict(row) for row in conn.execute('SELECT message,created FROM events WHERE campaign_id=? ORDER BY id DESC LIMIT 20', (cid,))]
                task['counts'] = dict(conn.execute('SELECT status,count(*) FROM deliveries WHERE campaign_id=? GROUP BY status', (cid,)))
                for group in task['groups']:
                    group['today'] = conn.execute("SELECT count(*) FROM deliveries WHERE campaign_id=? AND slot=? AND day=? AND status IN ('added','sending','unknown')", (cid, group['slot'], day_key())).fetchone()[0]
                    group['added'] = conn.execute("SELECT count(*) FROM deliveries WHERE group_id=? AND status='added'", (group['id'],)).fetchone()[0]
                result['campaigns'].append(task)
            return result


class TelegramCampaignGateway:
    def __init__(self, paths, sessions, api):
        self.paths, self.sessions, self.api = paths, sessions, api
        self.clients = {}
        self.peers = {}

    async def client(self, name):
        if name not in self.clients:
            from telethon import TelegramClient
            info = self.sessions[name]
            client = TelegramClient(os.path.join(self.paths['sessions_dir'], name),
                                    info.get('api_id') or self.api[0], info.get('api_hash') or self.api[1],
                                    flood_sleep_threshold=0, request_retries=0)
            self.clients[name] = client
            await client.connect()
            if not await client.is_user_authorized():
                raise ValueError(f'Sessão {name} não autorizada')
        return self.clients[name]

    async def resolve(self, client, reference):
        from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
        from telethon.tl.functions.channels import JoinChannelRequest
        from telethon.tl.types import ChatInviteAlready
        match = re.search(r't\.me/(?:\+|joinchat/)([\w-]+)', reference)
        if match:
            invite = await client(CheckChatInviteRequest(match[1]))
            if isinstance(invite, ChatInviteAlready):
                return invite.chat
            result = await client(ImportChatInviteRequest(match[1]))
            updates = getattr(result, 'updates', result)
            chats = getattr(result, 'chats', None) or getattr(updates, 'chats', None)
            if chats:
                return chats[0]
            # A short update may omit entities. Confirm membership through the
            # original invite instead of repeating the join request.
            confirmed = await client(CheckChatInviteRequest(match[1]))
            if isinstance(confirmed, ChatInviteAlready):
                return confirmed.chat
            raise ValueError('Entrada no grupo ainda não confirmada. Verifique se o convite exige aprovação ou verificação no Telegram.')
        entity = await client.get_entity(reference)
        await client(JoinChannelRequest(entity))
        return entity

    async def create(self, group, name, persist):
        from telethon.tl.functions.channels import CreateChannelRequest
        from telethon.tl.functions.messages import ExportChatInviteRequest, EditChatDefaultBannedRightsRequest
        from telethon.tl.types import ChatBannedRights
        client = await self.client(name)
        if group['reference']:
            entity = await self.resolve(client, group['reference'])
            if not getattr(entity, 'megagroup', False):
                raise ValueError('O link deve apontar para um supergrupo')
        else:
            result = await client(CreateChannelRequest(title=group['title'], about=group['title'], megagroup=True))
            entity = result.chats[0]
        # Persist the identity before subsequent Telegram requests can fail.
        persist(channel_id=str(entity.id), access_hash=str(entity.access_hash), creator=name)
        self.peers[(group['id'], name)] = entity
        if not group['reference']:
            await client(EditChatDefaultBannedRightsRequest(peer=entity, banned_rights=ChatBannedRights(until_date=None, invite_users=False, change_info=True, pin_messages=True)))
        invite = await client(ExportChatInviteRequest(peer=entity))
        return {'channel_id': str(entity.id), 'access_hash': str(entity.access_hash), 'creator': name, 'invite': invite.link}

    async def peer(self, group, name):
        from telethon.tl.types import InputChannel
        key = (group['id'], name)
        client = await self.client(name)
        if key not in self.peers:
            if name == group['creator']:
                self.peers[key] = InputChannel(int(group['channel_id']), int(group['access_hash']))
            else:
                self.peers[key] = await self.resolve(client, group['invite'] or group['reference'])
        return client, self.peers[key]

    async def warm(self, group, name, phrase):
        client, peer = await self.peer(group, name)
        await client.send_message(peer, phrase)

    async def invite(self, group, name, payload, reserve_identity):
        from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantRequest
        from telethon.tl.types import InputUser
        client, peer = await self.peer(group, name)
        try:
            if payload.get('username'):
                user = await client.get_input_entity(payload['username'])
            elif payload.get('id') and payload.get('access_hash'):
                user = InputUser(int(payload['id']), int(payload['access_hash']))
            else:
                user = await client.get_input_entity(payload.get('phone') or int(payload['id']))
        except (ValueError, KeyError, TypeError) as error:
            raise LeadResolutionError(f'Lead não resolvido nesta sessão: {error}') from error
        user_id = getattr(user, 'user_id', None)
        if not user_id:
            raise LeadResolutionError('A referência não corresponde a um usuário do Telegram')
        if not reserve_identity(user_id):
            return None
        result = await client(InviteToChannelRequest(channel=peer, users=[user]))
        if getattr(result, 'missing_invitees', []):
            return False
        # Some Telegram versions return Updates even when no member was added.
        await client(GetParticipantRequest(channel=peer, participant=user))
        return True

    async def close(self):
        for client in self.clients.values():
            await client.disconnect()


class LeadResolutionError(ValueError):
    pass


async def campaign_loop(store, cid, gateway):
    settings = store.get(cid)['settings']
    names = settings['sessions']
    turn = 0

    async def wait(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end and store.get(cid)['status'] == 'running':
            await asyncio.sleep(min(1, end - time.monotonic()))

    try:
        while store.get(cid)['status'] == 'running':
            worked = False
            for group in store.groups(cid):
                if store.get(cid)['status'] != 'running':
                    break
                gid = group['id']
                if group['status'] == 'error':
                    continue
                try:
                    if group['status'] == 'pending':
                        store.group_update(gid, status='creating')
                        owner = names[(group['slot'] - 1) % len(names)]
                        created = await gateway.create(group, owner, lambda **values: store.group_update(gid, **values))
                        store.group_update(gid, **created, status='warming' if settings['warming'] else 'ready',
                                           warm_until=time.time() + settings['warm_days'] * 86400 if settings['warming'] else 0)
                        store.event(cid, f"Grupo {group['slot']}: criado/vinculado com sucesso.")
                        worked = True
                    elif group['status'] == 'warming':
                        if time.time() >= group['warm_until']:
                            store.group_update(gid, status='ready')
                        elif time.time() >= group['next_message']:
                            index = group['message_index']
                            store.group_update(gid, next_message=time.time() + settings['warm_interval'] * 60, message_index=index + 1)
                            await gateway.warm(group, names[index % len(names)], settings['messages'][index % len(settings['messages'])])
                            store.event(cid, f"Grupo {group['slot']}: frase de aquecimento enviada.")
                            worked = True
                    elif group['status'] == 'ready':
                        delivery = store.claim(cid, gid)
                        if not delivery:
                            continue
                        try:
                            added = await gateway.invite(group, names[turn % len(names)], delivery['payload'], lambda uid: store.reserve_identity(delivery['id'], uid))
                            status = 'skipped' if added is None else ('added' if added else 'failed')
                            store.finish(delivery['id'], status, 'Identidade já utilizada' if added is None else ('' if added else 'Telegram não permitiu adicionar este lead'))
                            store.event(cid, f"Grupo {group['slot']}: lead #{delivery['lead_id']} {'adicionado' if added else ('ignorado por duplicidade' if added is None else 'não adicionado pelo Telegram')}.")
                            turn += 1
                        except Exception as error:
                            # Privacy and invalid-user errors are definite failures. Others may
                            # have occurred after Telegram accepted the request: do not retry.
                            definite = type(error).__name__ in {'LeadResolutionError', 'UserPrivacyRestrictedError', 'UserNotMutualContactError', 'InputUserDeactivatedError', 'UserIdInvalidError', 'UserNotParticipantError', 'UsernameNotOccupiedError', 'UsernameInvalidError', 'UserChannelsTooMuchError', 'UserKickedError', 'UserBannedInChannelError', 'UserBotError'}
                            store.finish(delivery['id'], 'failed' if definite else 'unknown', str(error))
                            store.event(cid, f"Grupo {group['slot']}: lead #{delivery['lead_id']} não confirmado: {error}")
                            if not definite:
                                raise
                        worked = True
                except Exception as error:
                    kind = type(error).__name__
                    if kind in {'FloodWaitError', 'PeerFloodError', 'UserRestrictedError', 'AuthKeyUnregisteredError', 'SessionRevokedError'}:
                        if group['status'] == 'pending':
                            store.group_update(gid, status='error', error=str(error)[:1000])
                        raise
                    store.group_update(gid, status='error', error=str(error)[:1000])
                    store.event(cid, f"Grupo {group['slot']}: {error}. Pause e substitua o grupo ou revise a sessão.")
                    worked = True
                if worked:
                    await wait(settings['delay'])
                    worked = False
            groups = store.groups(cid)
            if groups and all(group['status'] == 'error' for group in groups):
                store.state(cid, 'paused', 'Todos os grupos precisam de revisão ou substituição.')
                break
            await wait(15)
    except Exception as error:
        store.state(cid, 'paused', str(error))
        store.event(cid, f'Tarefa pausada: {error}')
    finally:
        await gateway.close()


def register_campaign_routes(app, login_required, get_paths, get_sessions, get_api, check_lock, set_lock, get_locks):
    from flask import request, jsonify, session
    workers = {}
    initialized = set()
    guard = threading.RLock()

    def store_for(username):
        store = CampaignStore(get_paths(username)['data_dir'])
        with guard:
            if store.path not in initialized:
                store.recover()
                initialized.add(store.path)
        return store

    def endpoint(function):
        from functools import wraps
        @wraps(function)
        def wrapped(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except (ValueError, KeyError, TypeError, UnicodeError) as error:
                return jsonify(success=False, error=str(error)), 400
        return login_required(wrapped)

    @app.route('/api/group-campaigns', methods=['GET', 'POST'])
    @endpoint
    def campaigns_api():
        username = session['username']
        store = store_for(username)
        if request.method == 'GET':
            result = store.snapshot()
            with guard:
                result['worker_active'] = bool(workers.get(username) and workers[username].is_alive())
            return jsonify(success=True, **result)
        payload = request.get_json() or {}
        sessions = get_sessions(username).load_sessions()
        names = payload.get('sessions', [])
        if not isinstance(names, list) or not names or any(name not in {s['session_name'] for s in sessions if s.get('active', True) and s.get('status', 'active') == 'active'} for name in names):
            raise ValueError('Selecione sessões ativas disponíveis')
        return jsonify(success=True, id=store.create(payload, names))

    @app.route('/api/group-campaigns/leads', methods=['POST'])
    @endpoint
    def campaign_leads_api():
        file = request.files.get('file')
        if not file or not file.filename:
            raise ValueError('Selecione um arquivo de leads')
        stats = store_for(session['username']).import_leads(file.filename, file.stream.read(25 * 1024 * 1024 + 1))
        return jsonify(success=True, **stats)

    @app.route('/api/group-campaigns/<int:cid>/groups/<int:gid>', methods=['PUT'])
    @endpoint
    def campaign_group_api(cid, gid):
        username = session['username']
        with guard:
            if workers.get(username) and workers[username].is_alive():
                raise ValueError('Pause e aguarde a operação atual terminar antes de editar grupos')
            store_for(username).edit_group(cid, gid, request.get_json() or {})
        return jsonify(success=True)

    @app.route('/api/group-campaigns/<int:cid>/settings', methods=['PUT'])
    @endpoint
    def campaign_settings_api(cid):
        username = session['username']
        with guard:
            if workers.get(username) and workers[username].is_alive():
                raise ValueError('Pause e aguarde a operação atual terminar antes de editar limites')
            store = store_for(username)
            settings = store.get(cid)['settings']
            settings['daily_limit'] = integer((request.get_json() or {}).get('daily_limit'), 'Limite diário')
            with store.db() as conn:
                conn.execute('UPDATE campaigns SET settings=? WHERE id=?', (json.dumps(settings), cid))
        return jsonify(success=True)

    @app.route('/api/group-campaigns/<int:cid>/<action>', methods=['POST'])
    @endpoint
    def campaign_action_api(cid, action):
        username = session['username']
        store = store_for(username)
        task = store.get(cid)
        if action == 'pause':
            store.state(cid, 'paused')
            return jsonify(success=True)
        if action != 'start':
            raise ValueError('Ação inválida')
        with guard:
            if workers.get(username) and workers[username].is_alive():
                raise ValueError('Já existe uma tarefa de grupos em execução ou encerrando')
            allowed, message = check_lock('group_factory', username=username)
            if not allowed or get_locks(username).get('extraction'):
                raise ValueError(message if not allowed else 'Aguarde a extração terminar')
            api = get_api()
            if not all(api):
                raise ValueError('Configure sua API primeiro')
            manager = get_sessions(username)
            saved = {row['session_name']: row for row in manager.load_sessions(force_reload=True)}
            names = task['settings']['sessions']
            for name in names:
                info = saved.get(name)
                if not info or not info.get('active', True) or info.get('status', 'active') != 'active' or manager.is_session_flooded(name):
                    raise ValueError(f'Sessão indisponível: {name}')
            paths = get_paths(username)
            gateway = TelegramCampaignGateway(paths, {name: saved[name] for name in names}, api)
            store.prepare_start(cid)
            set_lock('group_campaign', True, username=username)

            def run():
                try:
                    asyncio.run(campaign_loop(store, cid, gateway))
                except Exception as error:
                    store.state(cid, 'paused', str(error))
                finally:
                    set_lock('group_campaign', False, username=username)

            worker = threading.Thread(target=run, daemon=True)
            workers[username] = worker
            try:
                worker.start()
            except Exception:
                store.state(cid, 'paused', 'Não foi possível iniciar o processo')
                set_lock('group_campaign', False, username=username)
                raise
        return jsonify(success=True)
