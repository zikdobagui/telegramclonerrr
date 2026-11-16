"""Read-only group visibility checks, scoped to the signed-in user's sessions."""
import asyncio
import copy
import os
import re
import threading
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flask import jsonify, request, session, Response
from data_store import atomic_write_json, load_json_file

MAX_GROUPS = 500
LINK = re.compile(r'(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/(joinchat/[\w-]+|\+[\w-]+|[A-Za-z0-9_]{4,32})(?=[/?#\s|]|$)', re.I)
HANDLE = re.compile(r'^@?([A-Za-z][A-Za-z0-9_]{3,31})$')
RESERVED = {'s', 'c', 'share', 'addstickers', 'addemoji', 'proxy', 'socks', 'login', 'iv', 'boost'}


def parse_groups(text):
    if not isinstance(text, str) or len(text) > 1_000_000:
        raise ValueError('A lista deve ser um texto com até 1 MB.')
    groups, invalid, seen = [], [], set()
    duplicates = 0
    for number, original in enumerate(text.splitlines(), 1):
        clean = original.replace('\\', '').strip().lstrip('\ufeff')
        if not clean:
            continue
        match = LINK.search(clean)
        if match:
            token = match.group(1)
        else:
            match = HANDLE.fullmatch(clean)
            token = match.group(1) if match else None
        if not token or token.lower() in RESERVED:
            invalid.append(number)
            continue
        private = token.startswith(('+', 'joinchat/'))
        key = token if private else token.lower()
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        groups.append({'link': 'https://t.me/' + token, 'token': token,
                       'original': original.strip(), 'line': number, 'private': private})
    return groups, invalid, duplicates


class SessionUnavailable(Exception):
    pass


async def inspect_group(client, group):
    """Never joins groups, sends messages, or stores participants."""
    from telethon import functions, types
    if group['private']:
        token = group['token'].removeprefix('joinchat/').removeprefix('+')
        invite = await client(functions.messages.CheckChatInviteRequest(token))
        if not isinstance(invite, types.ChatInviteAlready):
            return {'status': 'inaccessible', 'reason': 'Convite privado: a sessão ainda não participa do grupo.'}
        entity = invite.chat
    else:
        entity = await client.get_entity(group['token'])
    base = {'title': getattr(entity, 'title', group['link']), 'group_id': str(entity.id)}
    if isinstance(entity, (types.ChannelForbidden, types.ChatForbidden)):
        return dict(base, status='inaccessible', reason='Este grupo não está acessível para a sessão selecionada.')
    if isinstance(entity, types.Channel) and getattr(entity, 'megagroup', False):
        info = await client(functions.channels.GetFullChannelRequest(entity))
        full = info.full_chat
        base['members_count'] = getattr(full, 'participants_count', None)
        if getattr(full, 'participants_hidden', False):
            return dict(base, status='hidden', reason='O Telegram informa que os membros estão ocultos.')
        if getattr(full, 'can_view_participants', None) is False:
            return dict(base, status='inaccessible', reason='O Telegram não permite que esta sessão consulte a lista de membros.')
        participants = await client(functions.channels.GetParticipantsRequest(
            channel=entity, filter=types.ChannelParticipantsRecent(), offset=0, limit=1, hash=0))
        if getattr(participants, 'participants', None):
            return dict(base, status='visible', reason='Consulta da lista de membros confirmada para esta sessão.')
        return dict(base, status='inconclusive', reason='Consulta sem participantes; visibilidade não confirmada.')
    if isinstance(entity, types.Chat):
        if getattr(entity, 'migrated_to', None):
            return dict(base, status='inconclusive', reason='Grupo migrado. Use o link atual do supergrupo para confirmar.')
        info = await client(functions.messages.GetFullChatRequest(entity.id))
        members = info.full_chat.participants
        if isinstance(members, types.ChatParticipants):
            return dict(base, status='visible', members_count=len(members.participants),
                        reason='Lista do grupo básico acessível para esta sessão.')
        return dict(base, status='inaccessible', reason='A sessão não tem acesso à lista deste grupo.')
    return dict(base, status='not_group', reason='O link não aponta para um grupo de membros (pode ser um canal).')


def classify_error(error):
    from telethon import errors
    if isinstance(error, errors.FloodWaitError):
        return 'flood', f'Telegram solicitou espera de {error.seconds}s. Verificação interrompida.'
    if isinstance(error, (errors.AuthKeyUnregisteredError, errors.SessionRevokedError, errors.UserDeactivatedError, SessionUnavailable)):
        return 'session_error', 'Sessão não autorizada ou indisponível. Valide a sessão no painel.'
    if isinstance(error, (errors.ChannelPrivateError, errors.ChatAdminRequiredError, errors.UserNotParticipantError)):
        return 'inaccessible', 'Esta sessão não tem permissão para consultar os membros.'
    if isinstance(error, (errors.UsernameInvalidError, errors.UsernameNotOccupiedError, errors.InviteHashInvalidError, errors.InviteHashExpiredError)):
        return 'invalid', 'Link inválido, expirado ou grupo não encontrado.'
    if isinstance(error, (TimeoutError, ConnectionError, OSError)):
        return 'error', 'Falha de conexão ou tempo de consulta excedido.'
    return 'error', 'Não foi possível confirmar a visibilidade deste grupo.'


def register_visibility_routes(app, login_required, get_paths, get_manager, get_api, check_lock, set_lock):
    guard = threading.RLock()
    jobs, cancellations = {}, {}

    def filename(username):
        return os.path.join(get_paths(username)['data_dir'], 'group_visibility.json')

    def current(username):
        with guard:
            if username not in jobs:
                saved = load_json_file(filename(username), None)
                if isinstance(saved, dict):
                    if saved.get('status') in ('running', 'cancelling'):
                        saved.update(status='interrupted', message='Servidor reiniciado. Os resultados parciais foram preservados.')
                        atomic_write_json(filename(username), saved)
                    jobs[username] = saved
            return copy.deepcopy(jobs.get(username))

    def update(username, path, **fields):
        with guard:
            jobs[username].update(fields)
            atomic_write_json(path, jobs[username])

    def append_result(username, path, result):
        with guard:
            job = jobs[username]
            job['results'].append(result)
            job['processed'] = len(job['results'])
            atomic_write_json(path, job)

    async def run(username, path, selected, groups, api, stop, sessions_dir):
        from telethon import TelegramClient
        clients, unavailable = {}, set()
        terminal, message = 'completed', 'Verificação concluída.'
        try:
            for index, group in enumerate(groups):
                if stop.is_set():
                    terminal, message = 'cancelled', 'Verificação cancelada. Resultados parciais preservados.'
                    break
                available = [name for name in selected if name not in unavailable]
                if not available:
                    terminal, message = 'failed', 'Nenhuma sessão selecionada está disponível. Resultados parciais preservados.'
                    break
                name = available[index % len(available)]
                result = {**group, 'session': name}
                update(username, path, message=f'Verificando {index + 1}/{len(groups)}', current_link=group['link'])
                try:
                    ready = name in clients
                    if name not in clients:
                        client = TelegramClient(str(Path(sessions_dir) / name), int(api[0]), api[1],
                                                flood_sleep_threshold=0, request_retries=0, connection_retries=1)
                        clients[name] = client
                        await asyncio.wait_for(client.connect(), 25)
                        if not await asyncio.wait_for(client.is_user_authorized(), 15):
                            raise SessionUnavailable()
                        ready = True
                    result.update(await asyncio.wait_for(inspect_group(clients[name], group), 40))
                except Exception as error:
                    status, reason = classify_error(error)
                    if not ready and status not in ('flood', 'session_error'):
                        status, reason = 'session_error', 'Não foi possível conectar esta sessão. Verifique a conexão e a autorização.'
                    result.update(status=status, reason=reason)
                    if status == 'session_error':
                        unavailable.add(name)
                    if status == 'flood':
                        terminal, message = 'flood', reason
                        floods_path = get_paths(username)['floods_file']
                        floods = load_json_file(floods_path, {})
                        floods[name] = (datetime.now() + timedelta(seconds=error.seconds)).isoformat()
                        atomic_write_json(floods_path, floods)
                append_result(username, path, result)
                if terminal == 'flood':
                    break
                # Sequential queries; no parallel session rotation to evade Telegram waits.
                if index + 1 < len(groups):
                    for _ in range(20):
                        if stop.is_set():
                            break
                        await asyncio.sleep(.1)
            if stop.is_set() and terminal == 'completed':
                terminal, message = 'cancelled', 'Verificação cancelada. Resultados parciais preservados.'
        finally:
            for client in clients.values():
                try:
                    await asyncio.wait_for(client.disconnect(), 10)
                except Exception:
                    pass
        update(username, path, status=terminal, message=message, current_link=None)

    def worker(username, path, selected, groups, api, stop, sessions_dir):
        try:
            asyncio.run(run(username, path, selected, groups, api, stop, sessions_dir))
        except Exception:
            update(username, path, status='failed', message='Verificação interrompida por uma falha interna. Resultados parciais preservados.', current_link=None)
        finally:
            with guard:
                cancellations.pop(username, None)
                set_lock('group_visibility', False, username=username)

    @app.route('/api/group-visibility', methods=['GET'])
    @login_required
    def visibility_status():
        return jsonify(success=True, job=current(session['username']))

    @app.route('/api/group-visibility/preview', methods=['POST'])
    @login_required
    def visibility_preview():
        payload = request.get_json(silent=True)
        try:
            groups, invalid, duplicates = parse_groups(payload.get('groups', '') if isinstance(payload, dict) else '')
            return jsonify(success=True, valid_links=len(groups), invalid_lines=invalid, duplicates=duplicates, max_groups=MAX_GROUPS)
        except ValueError as error:
            return jsonify(success=False, error=str(error)), 400

    @app.route('/api/group-visibility/start', methods=['POST'])
    @login_required
    def visibility_start():
        username = session['username']
        payload = request.get_json(silent=True)
        try:
            if not isinstance(payload, dict):
                raise ValueError('Envie uma lista e selecione as sessões.')
            groups, invalid, duplicates = parse_groups(payload.get('groups', ''))
            amount = payload.get('limit', len(groups))
            if isinstance(amount, bool) or not isinstance(amount, int) or not 1 <= amount <= MAX_GROUPS:
                raise ValueError(f'A quantidade deve estar entre 1 e {MAX_GROUPS} grupos.')
            if not groups:
                raise ValueError('Nenhum link de grupo válido encontrado.')
            if amount > len(groups):
                raise ValueError('A quantidade ultrapassa os links únicos válidos da lista.')
            selected = payload.get('sessions')
            if not isinstance(selected, list) or not 1 <= len(selected) <= 20 or not all(isinstance(s, str) for s in selected):
                raise ValueError('Selecione entre 1 e 20 sessões.')
            selected = list(dict.fromkeys(selected))
            paths = get_paths(username)
            root = Path(paths['sessions_dir']).resolve()
            manager = get_manager(username)
            owned = {s.get('session_name'): s for s in manager.load_sessions(force_reload=True)}
            for name in selected:
                info = owned.get(name)
                if not info or not info.get('active', True) or info.get('status') in ('flood', 'disconnected', 'invalid', 'corrupted', 'banned'):
                    raise ValueError('Uma das sessões selecionadas não pertence à sua conta ou está indisponível.')
                if hasattr(manager, 'is_session_flooded') and manager.is_session_flooded(name):
                    raise ValueError('Uma das sessões selecionadas está aguardando o prazo de espera do Telegram.')
                candidate = (root / (name if name.endswith('.session') else name + '.session')).resolve()
                if candidate.parent != root or not candidate.is_file() or candidate.suffix != '.session':
                    raise ValueError('Arquivo de sessão inválido ou não encontrado.')
            api = get_api()
            if not api[0] or not api[1]:
                raise ValueError('Configure sua API do Telegram antes de verificar.')
            with guard:
                if username in cancellations:
                    return jsonify(success=False, error='Já existe uma verificação em andamento.'), 409
                allowed, message = check_lock('group_visibility', username=username)
                if not allowed:
                    return jsonify(success=False, error=message), 409
                path = filename(username)
                job = {'id': uuid.uuid4().hex, 'status': 'running', 'total': amount, 'processed': 0,
                       'results': [], 'message': 'Iniciando verificação...', 'invalid_lines': invalid,
                       'duplicates': duplicates, 'valid_links': len(groups), 'sessions': selected,
                       'created_at': datetime.now(timezone.utc).isoformat(), 'current_link': None}
                stop = threading.Event()
                atomic_write_json(path, job)
                jobs[username] = job
                cancellations[username] = stop
                set_lock('group_visibility', True, username=username)
                try:
                    threading.Thread(target=worker, args=(username, path, selected, groups[:amount], api, stop, str(root)), daemon=True).start()
                except Exception:
                    cancellations.pop(username, None)
                    set_lock('group_visibility', False, username=username)
                    update(username, path, status='failed', message='Não foi possível iniciar a verificação.')
                    raise
            return jsonify(success=True, job=copy.deepcopy(job)), 202
        except ValueError as error:
            return jsonify(success=False, error=str(error)), 400

    @app.route('/api/group-visibility/cancel', methods=['POST'])
    @login_required
    def visibility_cancel():
        username = session['username']
        with guard:
            if username not in cancellations:
                return jsonify(success=False, error='Não há verificação ativa.'), 409
            cancellations[username].set()
            update(username, filename(username), status='cancelling', message='Cancelando após a consulta atual...')
        return jsonify(success=True)

    @app.route('/api/group-visibility/export', methods=['GET'])
    @login_required
    def visibility_export():
        job = current(session['username'])
        lines = [row['original'] for row in (job or {}).get('results', []) if row['status'] == 'visible']
        return Response('\n'.join(lines), mimetype='text/plain', headers={
            'Content-Disposition': 'attachment; filename="grupos-membros-visiveis.txt"', 'Cache-Control': 'no-store'})
