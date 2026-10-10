"""Persistent group campaigns with explicit controls for Telegram operations."""
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


def transient_request(error):
    return bool(re.fullmatch(r'An error occurred while communicating with DC \d+(?: \(caused by \w+\))?', str(error))) or bool(re.fullmatch(r'Request was unsuccessful \d+ time\(s\)', str(error))) or isinstance(error, (TimeoutError, ConnectionError)) or type(error).__name__ in {'ServerError', 'RpcCallFailError', 'TimedOutError', 'InterdcCallErrorError', 'InterdcCallRichErrorError'}


def admin_username(value):
    username = str(value or '').strip().removeprefix('@')
    if username and not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{3,31}', username):
        raise ValueError('Informe um @username válido para o administrador')
    return username


def admin_usernames(value):
    values = value if isinstance(value, list) else re.split(r'[\s,;]+', str(value or '').strip())
    result = []
    seen = set()
    for value in values:
        username = admin_username(value)
        if username and username.lower() not in seen:
            seen.add(username.lower())
            result.append(username)
    return result


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
                CREATE TABLE IF NOT EXISTS ownership_transfers (
                    group_id INTEGER PRIMARY KEY REFERENCES groups(id) ON DELETE CASCADE,
                    username TEXT NOT NULL, user_id TEXT NOT NULL, access_hash TEXT NOT NULL,
                    status TEXT NOT NULL, updated REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS group_deletions (
                    group_id INTEGER PRIMARY KEY REFERENCES groups(id) ON DELETE CASCADE,
                    status TEXT NOT NULL, previous_status TEXT NOT NULL,
                    previous_error TEXT NOT NULL, updated REAL NOT NULL);
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
                if group['status'] != 'error' or not (group['error'] == "'ChatInviteJoinResultOk' object has no attribute 'chats'" or transient_request(group['error'])):
                    continue
                if transient_request(group['error']) and not (group['channel_id'] and group['invite']):
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
                             (cid, f'{recovered} grupo(s) recuperado(s). Histórico de leads e cotas preservados.', time.time()))

    def validated_settings(self, payload, session_names):
        name = str(payload.get('name') or '').strip()[:100]
        if not name or not session_names:
            raise ValueError('Informe o nome e selecione pelo menos uma sessão')
        count = integer(payload.get('count', 10), 'Quantidade de grupos', high=30)
        limit = integer(payload.get('daily_limit', 25), 'Limite diário')
        messages = [str(line).strip()[:4000] for line in str(payload.get('messages', '')).splitlines() if line.strip()]
        warming = payload.get('warming') is True
        images = payload.get('images', [])
        if not isinstance(images, list) or len(images) > 30:
            raise ValueError('Selecione até 30 imagens')
        for image in images:
            if not isinstance(image, str) or not re.fullmatch(r'[a-f0-9]{32}\.(jpg|png|webp)', image) or not os.path.isfile(os.path.join(os.path.dirname(self.path), 'campaign_media', image)):
                raise ValueError('Imagem indisponível. Selecione novamente o arquivo')
        if warming and not messages and not images:
            raise ValueError('Adicione frases ou imagens para habilitar o aquecimento')
        settings = {
            'admin_usernames': admin_usernames(payload.get('admin_usernames', payload.get('admin_username'))),
            'sessions': list(dict.fromkeys(session_names)), 'warming': warming, 'messages': messages[:1000], 'images': images,
            'warm_days': integer(payload.get('warm_days', 1), 'Dias de aquecimento', high=90),
            'warm_interval': integer(payload.get('warm_interval', 60), 'Intervalo de mensagens (minutos)', high=1440),
            'delay': integer(payload.get('delay', 60), 'Intervalo entre ações (segundos)', low=10, high=3600),
            'dedup': 'group' if payload.get('dedup') == 'group' else 'task',
            'limit_scope': 'task' if payload.get('limit_scope') == 'task' else 'group',
            'daily_limit': limit,
        }
        return name, count, limit, settings

    def create(self, payload, session_names):
        name, count, limit, settings = self.validated_settings(payload, session_names)
        with self.db() as conn:
            cid = conn.execute('INSERT INTO campaigns(name,settings,created) VALUES(?,?,?)', (name, json.dumps(settings), time.time())).lastrowid
            for slot in range(1, count + 1):
                conn.execute('INSERT INTO groups(campaign_id,slot,title,daily_limit) VALUES(?,?,?,?)', (cid, slot, f'{name} {slot:02}', limit))
        return cid

    def edit(self, cid, payload, session_names):
        name, count, limit, settings = self.validated_settings(payload, session_names)
        with self.db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            task = conn.execute('SELECT * FROM campaigns WHERE id=?', (cid,)).fetchone()
            if not task:
                raise ValueError('Tarefa não encontrada')
            if task['status'] == 'running':
                raise ValueError('Pause a tarefa antes de editar')
            previous = json.loads(task['settings'])
            groups = conn.execute('SELECT * FROM groups WHERE campaign_id=? AND current=1', (cid,)).fetchall()
            if count != len(groups):
                raise ValueError('A quantidade de grupos não pode ser alterada nesta tarefa')
            if settings['dedup'] != previous['dedup'] and conn.execute('SELECT 1 FROM deliveries WHERE campaign_id=? LIMIT 1', (cid,)).fetchone():
                raise ValueError('A distribuição não pode mudar após o início das adições')
            conn.execute('UPDATE campaigns SET name=?,settings=? WHERE id=?', (name, json.dumps(settings), cid))
            if limit != previous['daily_limit']:
                conn.execute('UPDATE groups SET daily_limit=? WHERE campaign_id=? AND current=1', (limit, cid))
            if not settings['warming']:
                conn.execute("UPDATE groups SET status='ready',warm_until=0 WHERE campaign_id=? AND current=1 AND status='warming'", (cid,))
            conn.execute('INSERT INTO events(campaign_id,message,created) VALUES(?,?,?)', (cid, 'Configurações da tarefa atualizadas.', time.time()))

    def delete(self, cid):
        with self.db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            task = conn.execute('SELECT status FROM campaigns WHERE id=?', (cid,)).fetchone()
            if not task:
                raise ValueError('Tarefa não encontrada')
            if task['status'] == 'running':
                raise ValueError('Pause a tarefa antes de excluir')
            for table in ('deliveries', 'events', 'groups'):
                conn.execute(f'DELETE FROM {table} WHERE campaign_id=?', (cid,))
            conn.execute('DELETE FROM campaigns WHERE id=?', (cid,))

    def groups(self, cid):
        with self.db() as conn:
            groups = [dict(row) for row in conn.execute('SELECT * FROM groups WHERE campaign_id=? AND current=1 ORDER BY slot', (cid,))]
            for group in groups:
                row = conn.execute('SELECT username,user_id,status,updated FROM ownership_transfers WHERE group_id=?', (group['id'],)).fetchone()
                group['ownership'] = dict(row) if row else None
                row = conn.execute('SELECT status FROM group_deletions WHERE group_id=?', (group['id'],)).fetchone()
                group['deletion_status'] = row['status'] if row else None
            return groups

    def begin_group_deletion(self, cid, gid):
        with self.db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            task = conn.execute('SELECT status FROM campaigns WHERE id=?', (cid,)).fetchone()
            group = conn.execute('SELECT * FROM groups WHERE id=? AND campaign_id=? AND current=1', (gid, cid)).fetchone()
            if not group or not task or task['status'] == 'running':
                raise ValueError('Pause a tarefa e selecione um grupo disponível para excluir.')
            previous = conn.execute('SELECT * FROM group_deletions WHERE group_id=?', (gid,)).fetchone()
            if previous and previous['status'] == 'pending':
                raise ValueError('Já existe uma exclusão em andamento para este grupo.')
            status = previous['previous_status'] if previous and previous['status'] == 'unknown' else group['status']
            error = previous['previous_error'] if previous and previous['status'] == 'unknown' else group['error']
            conn.execute('INSERT OR REPLACE INTO group_deletions VALUES(?,?,?,?,?)', (gid, 'pending', status, error, time.time()))
            conn.execute("UPDATE groups SET status='error',error='Exclusão no Telegram em andamento.' WHERE id=?", (gid,))

    def finish_group_deletion(self, cid, gid, status):
        if status not in {'confirmed', 'failed', 'unknown'}:
            raise ValueError('Status de exclusão inválido')
        with self.db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            attempt = conn.execute('SELECT * FROM group_deletions WHERE group_id=?', (gid,)).fetchone()
            group = conn.execute('SELECT * FROM groups WHERE id=? AND campaign_id=?', (gid, cid)).fetchone()
            if not attempt or not group:
                raise ValueError('Exclusão não encontrada')
            conn.execute('UPDATE group_deletions SET status=?,updated=? WHERE group_id=?', (status, time.time(), gid))
            if status == 'confirmed':
                # Retain delivery history and lead reservations, but never recreate this slot.
                conn.execute("UPDATE groups SET current=0,status='deleted',error='' WHERE id=?", (gid,))
                conn.execute('INSERT INTO events(campaign_id,message,created) VALUES(?,?,?)',
                             (cid, f"Grupo {group['slot']} ({group['title']}): excluído do Telegram e removido do painel.", time.time()))
            elif status == 'failed':
                conn.execute('UPDATE groups SET status=?,error=? WHERE id=?', (attempt['previous_status'], attempt['previous_error'], gid))
            else:
                conn.execute("UPDATE groups SET status='error',error='Exclusão sem confirmação do Telegram. Confira o grupo antes de tentar excluir novamente.' WHERE id=?", (gid,))

    def ownership(self, gid):
        with self.db() as conn:
            row = conn.execute('SELECT * FROM ownership_transfers WHERE group_id=?', (gid,)).fetchone()
            return dict(row) if row else None

    def begin_ownership(self, gid, username, user_id, access_hash):
        with self.db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            previous = conn.execute('SELECT status FROM ownership_transfers WHERE group_id=?', (gid,)).fetchone()
            if previous and previous['status'] != 'failed':
                raise ValueError('Já existe uma transferência registrada. Consulte o resultado antes de continuar.')
            conn.execute('INSERT OR REPLACE INTO ownership_transfers VALUES(?,?,?,?,?,?)',
                         (gid, username, str(user_id), str(access_hash), 'pending', time.time()))

    def finish_ownership(self, gid, status):
        if status not in {'confirmed', 'failed', 'unknown'}:
            raise ValueError('Status de transferência inválido')
        with self.db() as conn:
            conn.execute('UPDATE ownership_transfers SET status=?,updated=? WHERE group_id=?', (status, time.time(), gid))

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
            deletion = conn.execute('SELECT status FROM group_deletions WHERE group_id=?', (gid,)).fetchone()
            if deletion and deletion['status'] in {'pending', 'unknown'}:
                raise ValueError('Resolva a exclusão pendente antes de editar ou substituir este grupo.')
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
            conn.execute("UPDATE ownership_transfers SET status='unknown' WHERE status='pending'")
            conn.execute("UPDATE group_deletions SET status='unknown' WHERE status='pending'")
            conn.execute("UPDATE groups SET status='error',error='Exclusão interrompida sem confirmação. Confira o grupo no Telegram.' WHERE id IN (SELECT group_id FROM group_deletions WHERE status='unknown') AND current=1")

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
                                    flood_sleep_threshold=0, request_retries=0, raise_last_call_error=True)
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

    async def warm(self, group, name, phrase, image=None):
        client, peer = await self.peer(group, name)
        if image:
            await client.send_file(peer, image)
        else:
            await client.send_message(peer, phrase)

    async def promote_admin(self, group, username):
        from telethon.tl.functions.channels import EditAdminRequest
        from telethon.tl.types import ChatAdminRights
        client, peer = await self.peer(group, group['creator'])
        user = await client.get_input_entity('@' + username)
        if not getattr(user, 'user_id', None):
            raise ValueError('O administrador deve ser um usuário do Telegram')
        await client(EditAdminRequest(channel=peer, user_id=user, admin_rights=ChatAdminRights(
            change_info=True, delete_messages=True, ban_users=True,
            invite_users=True, pin_messages=True, manage_call=True), rank='Administrador'))

    async def transfer_ownership(self, group, username, password, before_send):
        from telethon import functions, utils
        from telethon.password import compute_check
        from telethon.tl.types import User, ChannelParticipantCreator, ChannelParticipantAdmin
        client, peer = await self.peer(group, group['creator'])
        current = await client(functions.channels.GetParticipantRequest(peer, 'me'))
        if not isinstance(current.participant, ChannelParticipantCreator):
            raise OwnershipValidationError('A sessão criadora não é mais dona deste grupo no Telegram.')
        target = await client.get_entity('@' + username)
        if not isinstance(target, User) or target.bot or target.deleted:
            raise OwnershipValidationError('O novo dono deve ser uma conta de usuário ativa, não um bot.')
        if target.id == current.participant.user_id:
            raise OwnershipValidationError('Este usuário já é o dono do grupo.')
        user = utils.get_input_user(target)
        member = await client(functions.channels.GetParticipantRequest(peer, user))
        if not isinstance(member.participant, ChannelParticipantAdmin):
            raise OwnershipValidationError('Adicione o novo dono como administrador do grupo no Telegram antes de transferir.')
        password_info = await client(functions.account.GetPasswordRequest())
        if not password_info.has_password:
            raise OwnershipValidationError('Ative a verificação em duas etapas da conta criadora no Telegram antes de transferir.')
        proof = compute_check(password_info, password)
        # New Telegram layers moved this method to messages. Keep older sessions/libraries supported.
        if hasattr(functions.messages, 'EditChatCreatorRequest'):
            request = functions.messages.EditChatCreatorRequest(peer=peer, user_id=user, password=proof)
        else:
            request = functions.channels.EditCreatorRequest(channel=peer, user_id=user, password=proof)
        # Record the immutable recipient before the irreversible request. Never save the password/proof.
        before_send(user.user_id, user.access_hash)
        await client(request)

    async def check_ownership(self, group, transfer):
        from telethon.tl.functions.channels import GetParticipantRequest
        from telethon.tl.types import InputUser, ChannelParticipantCreator
        from telethon.errors import UserNotParticipantError
        client, peer = await self.peer(group, group['creator'])
        try:
            target = await client(GetParticipantRequest(peer, InputUser(int(transfer['user_id']), int(transfer['access_hash']))))
            if isinstance(target.participant, ChannelParticipantCreator):
                return 'confirmed'
        except UserNotParticipantError:
            pass
        current = await client(GetParticipantRequest(peer, 'me'))
        return 'failed' if isinstance(current.participant, ChannelParticipantCreator) else 'unknown'

    async def delete_group(self, group, before_send):
        from telethon.tl.functions.channels import GetParticipantRequest, DeleteChannelRequest
        from telethon.tl.types import ChannelParticipantCreator
        client, peer = await self.peer(group, group['creator'])
        current = await client(GetParticipantRequest(peer, 'me'))
        if not isinstance(current.participant, ChannelParticipantCreator):
            raise OwnershipValidationError('A sessão criadora não é mais dona do grupo. A exclusão precisa ser feita pelo dono atual.')
        before_send()
        await client(DeleteChannelRequest(peer))

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


class OwnershipValidationError(ValueError):
    pass


def ownership_error(error):
    """Return user-facing errors without echoing credentials or request contents."""
    kind = type(error).__name__
    messages = {
        'PasswordHashInvalidError': 'Senha de verificação em duas etapas incorreta.',
        'PasswordMissingError': 'Ative a verificação em duas etapas da conta criadora no Telegram.',
        'SrpIdInvalidError': 'A verificação de senha expirou. Consulte o resultado antes de tentar novamente.',
        'ChatAdminRequiredError': 'A sessão precisa ser dona do grupo e o destinatário deve ser administrador.',
        'UserNotParticipantError': 'Adicione o destinatário como administrador do grupo antes de transferir.',
        'UserCreatorError': 'Confira no Telegram quem é o dono atual do grupo.',
        'UsernameNotOccupiedError': 'O @username informado não foi encontrado no Telegram.',
        'UsernameInvalidError': 'Informe um @username válido para o novo dono.',
        'UserIdInvalidError': 'O Telegram não aceitou o usuário informado como novo dono.',
        'ChannelPrivateError': 'A sessão criadora não tem acesso a este grupo.',
        'AuthKeyUnregisteredError': 'A sessão criadora não está autorizada. Conecte a conta novamente.',
        'SessionRevokedError': 'A sessão criadora foi revogada. Conecte a conta novamente.',
    }
    if kind in {'PasswordTooFreshError', 'SessionTooFreshError', 'FloodWaitError'}:
        seconds = max(1, int(getattr(error, 'seconds', 0)))
        return f'O Telegram exige uma espera antes desta operação. Tente novamente em {seconds} segundos.'
    if isinstance(error, OwnershipValidationError):
        return str(error)
    return messages.get(kind, 'Não foi possível confirmar a transferência. Consulte o resultado antes de tentar novamente.')


async def campaign_loop(store, cid, gateway):
    settings = store.get(cid)['settings']
    names = settings['sessions']
    turn = 0
    warm_failures = {}

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
                        admins = admin_usernames(settings.get('admin_usernames', settings.get('admin_username')))
                        for username in admins if not group['reference'] else []:
                            try:
                                await gateway.promote_admin({**group, **created}, username)
                                store.event(cid, f"Grupo {group['slot']}: @{username} definido como administrador.")
                            except Exception as error:
                                store.event(cid, f"Grupo {group['slot']}: não foi possível promover @{username}: {error}. Verifique o administrador no Telegram.")
                        store.event(cid, f"Grupo {group['slot']}: criado/vinculado com sucesso.")
                        worked = True
                    elif group['status'] == 'warming':
                        if time.time() >= group['warm_until']:
                            store.group_update(gid, status='ready')
                        elif time.time() >= group['next_message']:
                            index = group['message_index']
                            store.group_update(gid, next_message=time.time() + settings['warm_interval'] * 60, message_index=index + 1)
                            messages = settings['messages']
                            images = settings.get('images', [])
                            content_index = index % (len(messages) + len(images))
                            if content_index < len(messages):
                                await gateway.warm(group, names[index % len(names)], messages[content_index])
                            else:
                                image = os.path.join(os.path.dirname(store.path), 'campaign_media', images[content_index - len(messages)])
                                await gateway.warm(group, names[index % len(names)], '', image=image)
                            warm_failures.pop(gid, None)
                            store.event(cid, f"Grupo {group['slot']}: conteúdo de aquecimento enviado.")
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
                    if transient_request(error) and group['status'] == 'warming':
                        warm_failures[gid] = warm_failures.get(gid, 0) + 1
                        if warm_failures[gid] < 3:
                            store.event(cid, f"Grupo {group['slot']}: comunicação temporariamente indisponível; próximo envio no intervalo configurado. Detalhe: {error}")
                            continue
                    if transient_request(error) and group['status'] in {'ready', 'warming'}:
                        message = 'Falha temporária de comunicação com o Telegram. Clique em Iniciar tarefa para retomar; leads sem confirmação permanecem reservados.'
                        store.state(cid, 'paused', message)
                        store.event(cid, f"Grupo {group['slot']}: {message} Detalhe: {kind}: {error}")
                        break
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
    group_actions_busy = set()

    def worker_busy(username):
        return username in group_actions_busy or bool(workers.get(username) and workers[username].is_alive())

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
                result['worker_active'] = worker_busy(username)
            return jsonify(success=True, **result)
        payload = request.get_json() or {}
        sessions = get_sessions(username).load_sessions()
        names = payload.get('sessions', [])
        if not isinstance(names, list) or not names or any(name not in {s['session_name'] for s in sessions if s.get('active', True) and s.get('status', 'active') == 'active'} for name in names):
            raise ValueError('Selecione sessões ativas disponíveis')
        return jsonify(success=True, id=store.create(payload, names))

    @app.route('/api/group-campaigns/<int:cid>', methods=['PUT', 'DELETE'])
    @endpoint
    def campaign_edit_api(cid):
        username = session['username']
        with guard:
            if worker_busy(username):
                raise ValueError('Pause e aguarde a operação atual terminar antes de editar ou excluir tarefas')
            store = store_for(username)
            if request.method == 'DELETE':
                store.delete(cid)
            else:
                payload = request.get_json() or {}
                payload.setdefault('images', store.get(cid)['settings'].get('images', []))
                names = payload.get('sessions', [])
                available = {s['session_name'] for s in get_sessions(username).load_sessions() if s.get('active', True) and s.get('status', 'active') == 'active'}
                if not isinstance(names, list) or not names or any(name not in available for name in names):
                    raise ValueError('Selecione sessões ativas disponíveis')
                store.edit(cid, payload, names)
        return jsonify(success=True, id=cid)

    @app.route('/api/group-campaigns/images', methods=['POST'])
    @endpoint
    def campaign_images_api():
        import uuid
        files = request.files.getlist('images')
        if not files or len(files) > 30:
            raise ValueError('Selecione entre 1 e 30 imagens')
        validated = []
        total = 0
        for file in files:
            data = file.read(10 * 1024 * 1024 + 1)
            total += len(data)
            if len(data) > 10 * 1024 * 1024 or total > 30 * 1024 * 1024:
                raise ValueError('Limite de 10 MB por imagem e 30 MB por seleção')
            extension = ('jpg' if data.startswith(b'\xff\xd8\xff') else
                         'png' if data.startswith(b'\x89PNG\r\n\x1a\n') else
                         'webp' if data.startswith(b'RIFF') and data[8:12] == b'WEBP' else None)
            if not extension:
                raise ValueError('Use imagens JPG, PNG ou WebP')
            validated.append((uuid.uuid4().hex + '.' + extension, data))
        directory = os.path.join(get_paths(session['username'])['data_dir'], 'campaign_media')
        os.makedirs(directory, exist_ok=True)
        for name, data in validated:
            with open(os.path.join(directory, name), 'wb') as output:
                output.write(data)
        return jsonify(success=True, images=[name for name, _ in validated])

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
            if worker_busy(username):
                raise ValueError('Pause e aguarde a operação atual terminar antes de editar grupos')
            store_for(username).edit_group(cid, gid, request.get_json() or {})
        return jsonify(success=True)

    @app.route('/api/group-campaigns/<int:cid>/groups/<int:gid>', methods=['DELETE'])
    @endpoint
    def campaign_delete_group_api(cid, gid):
        username = session['username']
        payload = request.get_json(silent=True) or {}
        with guard:
            if worker_busy(username):
                raise ValueError('Pause e aguarde a operação atual terminar antes de excluir o grupo.')
            store = store_for(username)
            if store.get(cid)['status'] == 'running':
                raise ValueError('Pause a tarefa antes de excluir o grupo.')
            group = next((item for item in store.groups(cid) if item['id'] == gid), None)
            if not group or not all(group.get(key) for key in ('channel_id', 'access_hash', 'creator')):
                raise ValueError('Grupo criado/vinculado não encontrado nesta tarefa.')
            if payload.get('confirmed') is not True or payload.get('title') != group['title'] or payload.get('channel_id') != group['channel_id']:
                raise ValueError('Confirme a exclusão permanente do grupo selecionado no painel e no Telegram.')
            if group['ownership'] and group['ownership']['status'] in {'pending', 'unknown'}:
                raise ValueError('Consulte o resultado da transferência de posse antes de excluir o grupo.')
            allowed, message = check_lock('group_factory', username=username)
            if not allowed or get_locks(username).get('extraction'):
                raise ValueError(message if not allowed else 'Aguarde a extração terminar.')
            manager = get_sessions(username)
            saved = {row['session_name']: row for row in manager.load_sessions(force_reload=True)}
            creator = group['creator']
            info = saved.get(creator)
            if not info or not info.get('active', True) or info.get('status', 'active') != 'active' or manager.is_session_flooded(creator):
                raise ValueError('A sessão criadora está indisponível.')
            api = get_api()
            if not all(api):
                raise ValueError('Configure sua API primeiro.')
            gateway = TelegramCampaignGateway(get_paths(username), {creator: info}, api)
            set_lock('group_campaign', True, username=username)
            group_actions_busy.add(username)

        sent = False

        def before_send():
            nonlocal sent
            store.begin_group_deletion(cid, gid)
            sent = True

        async def run():
            try:
                await asyncio.wait_for(gateway.delete_group(group, before_send), timeout=60)
            finally:
                try:
                    await asyncio.wait_for(gateway.close(), timeout=10)
                except Exception:
                    pass

        try:
            asyncio.run(run())
            store.finish_group_deletion(cid, gid, 'confirmed')
            return jsonify(success=True, message='Grupo excluído do Telegram e removido do painel. Histórico de leads preservado.')
        except Exception as error:
            if sent:
                from telethon.errors import RPCError
                definite = isinstance(error, RPCError) and getattr(error, 'code', 500) in {400, 401, 403, 404, 406, 420}
                store.finish_group_deletion(cid, gid, 'failed' if definite else 'unknown')
            messages = {
                'ChatAdminRequiredError': 'Somente o dono atual pode excluir este grupo.',
                'ChannelTooLargeError': 'O Telegram não permite excluir este grupo devido ao tamanho dele.',
                'ChannelPrivateError': 'A sessão não tem acesso ao grupo. Isso não confirma que ele foi excluído.',
                'ChannelInvalidError': 'O Telegram não reconheceu o grupo. A exclusão não foi confirmada.',
            }
            message = str(error) if isinstance(error, OwnershipValidationError) else messages.get(type(error).__name__, 'Exclusão não confirmada. O grupo foi mantido no painel; confira o Telegram antes de tentar novamente.')
            store.event(cid, f"Grupo {group['slot']}: {message}")
            return jsonify(success=False, error=message), 400
        finally:
            with guard:
                group_actions_busy.discard(username)
                set_lock('group_campaign', False, username=username)

    @app.route('/api/group-campaigns/<int:cid>/groups/<int:gid>/ownership', defaults={'check_only': False}, methods=['POST'])
    @app.route('/api/group-campaigns/<int:cid>/groups/<int:gid>/ownership/check', defaults={'check_only': True}, methods=['POST'])
    @endpoint
    def campaign_ownership_api(cid, gid, check_only):
        username = session['username']
        payload = request.get_json(silent=True) or {}
        password = payload.get('password', '')
        with guard:
            if worker_busy(username):
                raise ValueError('Pause e aguarde a operação atual terminar antes de transferir a posse.')
            store = store_for(username)
            task = store.get(cid)
            if task['status'] == 'running':
                raise ValueError('Pause a tarefa antes de transferir a posse.')
            group = next((group for group in store.groups(cid) if group['id'] == gid), None)
            if not group or not all(group.get(key) for key in ('channel_id', 'access_hash', 'creator')):
                raise ValueError('Grupo criado/vinculado não encontrado nesta tarefa.')
            if group['deletion_status'] in {'pending', 'unknown'}:
                raise ValueError('Resolva a exclusão pendente antes de transferir a posse.')
            previous = store.ownership(gid)
            target = ''
            if check_only:
                if not previous:
                    raise ValueError('Não há transferência registrada para consultar.')
            else:
                if previous and previous['status'] != 'failed':
                    raise ValueError('Já existe uma transferência registrada. Consulte o resultado antes de continuar.')
                target = admin_username(payload.get('username'))
                if not target or not isinstance(password, str) or not password:
                    raise ValueError('Informe o @username do novo dono e a senha de verificação em duas etapas da conta criadora.')
                if payload.get('confirmed') is not True:
                    raise ValueError('Confirme que deseja passar a posse deste grupo ao usuário informado.')
            allowed, message = check_lock('group_factory', username=username)
            if not allowed or get_locks(username).get('extraction'):
                raise ValueError(message if not allowed else 'Aguarde a extração terminar.')
            manager = get_sessions(username)
            saved = {row['session_name']: row for row in manager.load_sessions(force_reload=True)}
            creator = group['creator']
            info = saved.get(creator)
            if not info or not info.get('active', True) or info.get('status', 'active') != 'active' or manager.is_session_flooded(creator):
                raise ValueError('A sessão criadora está indisponível.')
            api = get_api()
            if not all(api):
                raise ValueError('Configure sua API primeiro.')
            gateway = TelegramCampaignGateway(get_paths(username), {creator: info}, api)
            set_lock('group_campaign', True, username=username)
            group_actions_busy.add(username)

        sent = False

        def before_send(user_id, access_hash):
            nonlocal sent
            store.begin_ownership(gid, target, user_id, access_hash)
            sent = True

        async def run():
            try:
                if check_only:
                    return await asyncio.wait_for(gateway.check_ownership(group, previous), timeout=60)
                await asyncio.wait_for(gateway.transfer_ownership(group, target, password, before_send), timeout=60)
                return 'confirmed'
            finally:
                # Disconnect errors must not hide a confirmed Telegram response.
                try:
                    await asyncio.wait_for(gateway.close(), timeout=10)
                except Exception:
                    pass

        try:
            status = asyncio.run(run())
            store.finish_ownership(gid, status)
            recipient = previous['username'] if check_only else target
            message = {
                'confirmed': f'Posse transferida para @{recipient}. A tarefa permanece pausada.',
                'failed': 'A sessão criadora ainda é dona do grupo. Você pode corrigir os dados e tentar novamente.',
                'unknown': 'Resultado ainda não confirmado. Confira a posse no Telegram e consulte novamente.',
            }[status]
            store.event(cid, f"Grupo {group['slot']}: {message}")
            return jsonify(success=True, status=status, message=message)
        except Exception as error:
            if sent:
                from telethon.errors import RPCError
                definite = isinstance(error, RPCError) and getattr(error, 'code', 500) in {400, 401, 403, 404, 420}
                store.finish_ownership(gid, 'failed' if definite else 'unknown')
            message = ownership_error(error)
            store.event(cid, f"Grupo {group['slot']}: transferência de posse: {message}")
            return jsonify(success=False, error=message), 400
        finally:
            password = None
            payload.clear()
            with guard:
                group_actions_busy.discard(username)
                set_lock('group_campaign', False, username=username)

    @app.route('/api/group-campaigns/<int:cid>/settings', methods=['PUT'])
    @endpoint
    def campaign_settings_api(cid):
        username = session['username']
        with guard:
            if worker_busy(username):
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
            if worker_busy(username):
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
