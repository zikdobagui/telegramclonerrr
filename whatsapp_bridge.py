"""Per-user WhatsApp linked devices and a durable clone outbox (Neonize 0.10.0)."""
import asyncio
import base64
import hashlib
import importlib.metadata
import io
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
import sys
import uuid

from flask import jsonify, request, session
from data_store import atomic_write_json, load_json_file

MAX_MEDIA = 16 * 1024 * 1024
GROUP_JID = re.compile(r'^[0-9]+(?:-[0-9]+)?@g\.us$')
_neonize_import_lock = threading.Lock()


def load_neonize_client():
    # A separate install target avoids conflicting files between Neonize's
    # python-magic dependency and the self-contained Linux fallback.
    with _neonize_import_lock:
        try:
            import magic  # noqa: F401
        except (ImportError, OSError):
            bundled = Path(__file__).resolve().parent / '.runtime' / 'libmagic'
            if not (bundled / 'magic').is_dir():
                raise ImportError('Execute o BUILD da Discloud para instalar o libmagic isolado.')
            # A failed system import can leave its incompatible loader cached.
            for name in list(sys.modules):
                if name == 'magic' or name.startswith('magic.'):
                    sys.modules.pop(name, None)
            sys.path.insert(0, str(bundled))
            try:
                import magic  # noqa: F401
            finally:
                sys.path.remove(str(bundled))
        from neonize.client import NewClient
        return NewClient


class WhatsAppError(ValueError):
    pass


class Outbox:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / 'media').mkdir(exist_ok=True)
        self.database = self.directory / 'outbox.sqlite'
        with self.db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS deliveries (
                id INTEGER PRIMARY KEY, delivery_key TEXT UNIQUE NOT NULL,
                clone_id TEXT NOT NULL, group_jid TEXT NOT NULL, text TEXT NOT NULL,
                media TEXT, kind TEXT, filename TEXT, mime TEXT,
                state TEXT NOT NULL DEFAULT 'pending', detail TEXT NOT NULL DEFAULT '',
                created REAL NOT NULL, updated REAL NOT NULL)''')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.database, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def recover(self):
        with self.db() as db:
            db.execute("UPDATE deliveries SET state='unknown', detail='Servidor reiniciado durante o envio. Confira o grupo antes de reenviar.', updated=? WHERE state='sending'", (time.time(),))

    def enqueue(self, key, clone_id, groups, text, media=None, kind=None, filename=None, mime=None):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT count(*) FROM deliveries WHERE state IN ('pending','sending')").fetchone()[0] + len(groups) > 200:
                raise WhatsAppError('Fila do WhatsApp cheia. Aguarde os envios antes de receber mais posts.')
            for group in groups:
                db.execute('''INSERT OR IGNORE INTO deliveries
                    (delivery_key,clone_id,group_jid,text,media,kind,filename,mime,created,updated)
                    VALUES (?,?,?,?,?,?,?,?,?,?)''',
                    (key + ':' + group, clone_id, group, text, media, kind, filename, mime, time.time(), time.time()))

    def claim(self):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM deliveries WHERE state='pending' ORDER BY id LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE deliveries SET state='sending',updated=? WHERE id=?", (time.time(), row['id']))
            return dict(row) if row else None

    def finish(self, delivery_id, state, detail):
        with self.db() as db:
            db.execute('UPDATE deliveries SET state=?,detail=?,updated=? WHERE id=?', (state, detail, time.time(), delivery_id))
            row = db.execute('SELECT media FROM deliveries WHERE id=?', (delivery_id,)).fetchone()
            media = row['media'] if row else None
            still_needed = media and db.execute("SELECT 1 FROM deliveries WHERE media=? AND state IN ('pending','sending') LIMIT 1", (media,)).fetchone()
        if media and not still_needed:
            Path(media).unlink(missing_ok=True)

    def summary(self):
        with self.db() as db:
            counts = dict(db.execute('SELECT state,count(*) FROM deliveries GROUP BY state').fetchall())
            recent = [dict(r) for r in db.execute('SELECT id,clone_id,group_jid,state,detail,updated FROM deliveries ORDER BY id DESC LIMIT 10')]
        return {'counts': counts, 'recent': recent}

    def cleanup(self):
        now = time.time()
        with self.db() as db:
            db.execute("UPDATE deliveries SET state='failed',detail='Post expirado após 7 dias sem envio.',updated=? WHERE state='pending' AND created<?", (now, now - 7 * 86400))
            # Once attempted, media is unnecessary; unknown sends are never retried automatically.
            retained = {r[0] for r in db.execute("SELECT media FROM deliveries WHERE state IN ('pending','sending') AND media IS NOT NULL")}
            db.execute("DELETE FROM deliveries WHERE state NOT IN ('pending','sending') AND updated<?", (now - 30 * 86400,))
        for file in (self.directory / 'media').iterdir():
            if file.is_file() and str(file) not in retained and file.stat().st_mtime < now - 3600:
                file.unlink(missing_ok=True)


class NeonizeDevice:
    """One blocking native connection, kept off the Flask and Telegram threads."""
    def __init__(self, username, directory, on_disable):
        self.username, self.directory = username, Path(directory)
        self.on_disable = on_disable
        self.guard = threading.RLock()
        self.send_guard = threading.Lock()
        self.state, self.message = 'connecting', 'Conectando ao WhatsApp...'
        self.qr, self.qr_until, self.client = None, 0, None
        self.stopping = False
        self.last_send = 0
        self.qr_sequence = 0
        self.thread = None

    def change(self, state, message, clear_qr=True):
        with self.guard:
            if self.stopping:
                return
            self.state, self.message = state, message
            if clear_qr:
                self.qr, self.qr_until = None, 0

    def snapshot(self):
        with self.guard:
            return {'status': self.state, 'message': self.message,
                    'qr': self.qr if self.qr_until > time.time() else None,
                    'qr_expires_at': self.qr_until if self.qr else None}

    def launch(self):
        self.thread = threading.Thread(target=self.run, name='whatsapp-device', daemon=True)
        self.thread.start()

    def run(self):
        try:
            NewClient = load_neonize_client()
            from neonize.events import ConnectedEv, DisconnectedEv, LoggedOutEv, StreamReplacedEv, KeepAliveTimeoutEv, KeepAliveRestoredEv
            import segno
            # The database preserves pairing. A fresh native handle prevents a
            # previous client's GC finalizer from stopping a replacement client.
            client = NewClient(str(self.directory / 'auth.sqlite'), uuid='tgauto-' + hashlib.sha256(self.username.encode()).hexdigest()[:12] + '-' + uuid.uuid4().hex)
            self.client = client

            @client.qr
            def qr_callback(_, raw):
                image = io.BytesIO()
                segno.make_qr(raw).save(image, kind='png', scale=6, border=4)
                with self.guard:
                    if self.stopping:
                        return
                    self.qr = 'data:image/png;base64,' + base64.b64encode(image.getvalue()).decode()
                    self.qr_sequence += 1
                    self.qr_until = time.time() + (55 if self.qr_sequence == 1 else 18)
                    self.state, self.message = 'qr', 'Leia o QR Code em Aparelhos conectados no WhatsApp.'

            @client.event(ConnectedEv)
            def connected(*_):
                self.change('connected', 'WhatsApp conectado. Pronto para os destinos da clonagem.')

            @client.event(DisconnectedEv)
            def disconnected(*_):
                self.change('reconnecting', 'Conexão interrompida. Aguardando reconexão...')

            @client.event(KeepAliveTimeoutEv)
            def keepalive_timeout(*_):
                self.change('reconnecting', 'Conexão instável. Aguardando o WhatsApp...')

            @client.event(KeepAliveRestoredEv)
            def keepalive_restored(*_):
                self.change('connected', 'Conexão com o WhatsApp restabelecida.')

            def disable(state, message):
                self.change(state, message)
                self.on_disable()
                threading.Thread(target=client.stop, daemon=True).start()

            @client.event(LoggedOutEv)
            def logged_out(*_):
                disable('logged_out', 'Aparelho desvinculado no WhatsApp. Conecte novamente para gerar outro QR Code.')

            @client.event(StreamReplacedEv)
            def replaced(*_):
                disable('replaced', 'Esta sessão foi aberta em outro processo. Mantenha somente uma instância conectada.')

            if self.stopping:
                return
            client.connect()
            if self.state not in ('logged_out', 'replaced'):
                self.change('disconnected', 'Conexão encerrada. Uma nova tentativa será feita automaticamente.')
        except Exception:
            self.change('error', 'Não foi possível conectar. Verifique a rede e as dependências do deploy.')

    def stop(self):
        with self.guard:
            self.stopping = True
            self.state, self.message, self.qr = 'disconnected', 'Conexão pausada. O pareamento foi preservado.', None
        if self.client:
            self.client.stop()

    def joined_groups(self):
        if self.state != 'connected' or not self.client:
            raise WhatsAppError('Conecte o WhatsApp antes de carregar os grupos.')
        groups = []
        for group in self.client.get_joined_groups():
            jid = group.JID.User + '@' + group.JID.Server
            if GROUP_JID.fullmatch(jid):
                groups.append({'id': jid, 'name': group.GroupName.Name or jid,
                               'members': len(group.Participants), 'admin_only': bool(group.GroupAnnounce.IsAnnounce)})
        return sorted(groups, key=lambda item: item['name'].casefold())

    def send(self, row):
        from neonize.utils import build_jid
        if self.state != 'connected':
            raise WhatsAppError('Conexão indisponível no momento do envio.')
        jid = build_jid(row['group_jid'].split('@')[0], 'g.us')
        if row['kind'] == 'image':
            result = self.client.send_image(jid, row['media'], caption=row['text'] or None)
        elif row['kind'] == 'video':
            result = self.client.send_video(jid, row['media'], caption=row['text'] or None)
        elif row['media']:
            result = self.client.send_document(jid, row['media'], caption=row['text'] or None,
                                               filename=row['filename'], mimetype=row['mime'])
        else:
            result = self.client.send_message(jid, row['text'])
        return result.ID


class WhatsAppService:
    def __init__(self, get_paths, list_users, device_factory=NeonizeDevice, max_devices=None):
        self.get_paths, self.list_users, self.factory = get_paths, list_users, device_factory
        self.max_devices = max_devices or max(1, int(os.environ.get('WHATSAPP_MAX_DEVICES', '3')))
        self.guard = threading.RLock()
        self.devices, self.stores, self.retry_at = {}, {}, {}
        self.thread = None
        self.stop_event = threading.Event()

    def directory(self, username):
        return Path(self.get_paths(username)['data_dir']) / 'whatsapp'

    def settings(self, username):
        return load_json_file(self.directory(username) / 'connection.json', {'enabled': False, 'groups': []})

    def save_settings(self, username, **changes):
        with self.guard:
            settings = self.settings(username)
            settings.update(changes)
            atomic_write_json(self.directory(username) / 'connection.json', settings)

    def store(self, username):
        with self.guard:
            if username not in self.stores:
                self.stores[username] = Outbox(self.directory(username))
                self.stores[username].recover()
            return self.stores[username]

    def connect(self, username):
        with self.guard:
            device = self.devices.get(username)
            if device and device.thread and device.thread.is_alive():
                if device.stopping:
                    raise WhatsAppError('Aguarde a conexão anterior encerrar para reconectar.')
                return
            alive = sum(bool(d.thread and d.thread.is_alive()) for d in self.devices.values())
            if alive >= self.max_devices:
                raise WhatsAppError('O servidor atingiu o limite de conexões WhatsApp. Tente novamente mais tarde.')
            self.store(username)
            self.save_settings(username, enabled=True)
            device = self.factory(username, self.directory(username), lambda: self.save_settings(username, enabled=False, groups=[]))
            self.devices[username] = device
            self.retry_at[username] = time.time() + 60
            device.launch()
            self.start()

    def disconnect(self, username):
        self.save_settings(username, enabled=False)
        with self.guard:
            device = self.devices.get(username)
        if device:
            with device.guard:
                device.stopping = True
                device.state, device.message, device.qr = 'disconnected', 'Conexão pausada. O pareamento foi preservado.', None
            threading.Thread(target=device.stop, daemon=True).start()

    def status(self, username):
        device = self.devices.get(username)
        info = device.snapshot() if device else {'status': 'disconnected', 'message': 'Conecte seu WhatsApp para usar na clonagem.', 'qr': None}
        try:
            info['library_version'] = importlib.metadata.version('neonize')
        except importlib.metadata.PackageNotFoundError:
            info['library_version'] = None
            info.update(status='unavailable', message='A biblioteca WhatsApp ainda não está instalada neste deploy.')
        info['outbox'] = self.store(username).summary()
        info['last_error'] = self.settings(username).get('last_error', '')
        return info

    def groups(self, username):
        device = self.devices.get(username)
        if not device:
            raise WhatsAppError('Conecte o WhatsApp primeiro.')
        groups = device.joined_groups()
        self.save_settings(username, groups=groups)
        return groups

    def validate_destinations(self, username, value):
        if not isinstance(value, list) or len(value) > 5 or not all(isinstance(jid, str) and GROUP_JID.fullmatch(jid) for jid in value):
            raise WhatsAppError('Selecione até 5 grupos válidos do seu WhatsApp.')
        selected = list(dict.fromkeys(value))
        owned = {group['id'] for group in self.settings(username).get('groups', [])}
        if any(jid not in owned for jid in selected):
            raise WhatsAppError('Carregue seus grupos do WhatsApp e selecione um destino da lista.')
        return selected

    async def enqueue_clone(self, username, clone_id, message, text, groups, telegram_client):
        if not groups:
            return
        groups = self.validate_destinations(username, groups)
        key = hashlib.sha256(f'{clone_id}:{message.chat_id}:{message.id}'.encode()).hexdigest()
        store = self.store(username)
        media, kind, filename, mime = None, None, None, None
        # WhatsApp formatting differs from Telegram's Markdown.
        text = text.replace('**', '*').replace('__', '_').replace('~~', '~')
        if len(text) > 60000:
            raise WhatsAppError('Post excede o limite de texto do envio WhatsApp.')
        if getattr(message, 'photo', None) or getattr(message, 'document', None):
            file = getattr(message, 'file', None)
            size = getattr(file, 'size', None)
            if not isinstance(size, int) or size > MAX_MEDIA:
                raise WhatsAppError('Mídia não enviada ao WhatsApp: tamanho desconhecido ou acima de 16 MB.')
            used = sum(p.stat().st_size for p in (store.directory / 'media').iterdir() if p.is_file())
            if used + size > 128 * 1024 * 1024:
                raise WhatsAppError('Armazenamento temporário do WhatsApp cheio. Aguarde a fila diminuir.')
            mime = getattr(file, 'mime_type', '') or 'application/octet-stream'
            kind = 'image' if getattr(message, 'photo', None) else ('video' if mime.startswith('video/') else 'document')
            filename = Path(getattr(file, 'name', '') or 'arquivo').name[:100]
            target = store.directory / 'media' / (key + '.bin')
            try:
                result = await asyncio.wait_for(telegram_client.download_media(message, file=str(target)), 90)
                if not result or not target.is_file() or target.stat().st_size > MAX_MEDIA:
                    raise WhatsAppError('Não foi possível preparar a mídia para o WhatsApp.')
            except BaseException:
                target.unlink(missing_ok=True)
                raise
            media = str(target)
        if not text and not media:
            return
        store.enqueue(key, clone_id, groups, text, media, kind, filename, mime)
        self.start()

    def record_error(self, username, clone_id, message):
        self.save_settings(username, last_error=f'{clone_id}: {message}')

    def send_next(self, username, device):
        if not device.send_guard.acquire(blocking=False):
            return
        try:
            if device.state != 'connected' or time.time() - device.last_send < 3:
                return
            store = self.store(username)
            row = store.claim()
            if not row:
                return
            allowed = {group['id'] for group in self.settings(username).get('groups', [])}
            if row['group_jid'] not in allowed:
                store.finish(row['id'], 'failed', 'Destino não está mais autorizado nesta conta. Carregue os grupos e revise a clonagem.')
                return
            device.last_send = time.time()
            try:
                message_id = device.send(row)
                if not message_id:
                    raise WhatsAppError('Envio sem confirmação.')
                store.finish(row['id'], 'sent', 'Envio confirmado pelo WhatsApp.')
            except Exception:
                store.finish(row['id'], 'unknown', 'Envio sem confirmação. Confira o grupo antes de reenviar; não haverá repetição automática.')
        finally:
            device.send_guard.release()

    def start(self):
        with self.guard:
            if not self.thread or not self.thread.is_alive():
                self.thread = threading.Thread(target=self.supervise, name='whatsapp-supervisor', daemon=True)
                self.thread.start()

    def supervise(self):
        last_restore = 0
        while not self.stop_event.wait(1):
            try:
                if time.time() - last_restore > 30:
                    last_restore = time.time()
                    for username in self.list_users():
                        if self.settings(username).get('enabled') and time.time() >= self.retry_at.get(username, 0):
                            try:
                                self.connect(username)
                                self.store(username).cleanup()
                            except Exception:
                                self.retry_at[username] = time.time() + 60
                with self.guard:
                    devices = list(self.devices.items())
                for username, device in devices:
                    if device.state == 'connected' and not device.send_guard.locked() and time.time() - device.last_send >= 3:
                        threading.Thread(target=self.send_next, args=(username, device), daemon=True).start()
            except Exception:
                # One user's storage/network failure must not terminate other connections.
                continue


def register_whatsapp_routes(app, login_required, service):
    @app.after_request
    def private_whatsapp_response(response):
        if request.path.startswith('/api/whatsapp'):
            response.headers['Cache-Control'] = 'no-store, private'
        return response

    @app.route('/api/whatsapp', methods=['GET'])
    @login_required
    def whatsapp_status():
        return jsonify(success=True, connection=service.status(session['username']))

    @app.route('/api/whatsapp/<action>', methods=['POST'])
    @login_required
    def whatsapp_action(action):
        username = session['username']
        try:
            if action == 'connect':
                service.connect(username)
            elif action == 'disconnect':
                service.disconnect(username)
            else:
                return jsonify(success=False, error='Ação inválida.'), 404
            return jsonify(success=True)
        except WhatsAppError as error:
            return jsonify(success=False, error=str(error)), 400

    @app.route('/api/whatsapp/groups', methods=['GET'])
    @login_required
    def whatsapp_groups():
        try:
            return jsonify(success=True, groups=service.groups(session['username']))
        except WhatsAppError as error:
            return jsonify(success=False, error=str(error)), 409
        except Exception:
            return jsonify(success=False, error='Não foi possível consultar os grupos. Confira a conexão e tente novamente.'), 502
