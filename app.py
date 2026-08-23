from flask import Flask, render_template, request, jsonify, session, redirect, url_for, has_request_context, g
from flask_socketio import SocketIO, emit, join_room
from werkzeug.local import LocalProxy
import os
import json
import threading
import tempfile
import shutil
import sys
import random
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename
from session_manager import SessionManager
from extractor import MemberExtractor
from adder import MemberAdder
from automation_manager import AutomationManager
from user_manager import UserManager
from channel_cloner import CloneManager
from session_creator import SessionCreator, get_session_creator, set_session_creator, remove_session_creator
from config import CONFIG_FILE, SESSIONS_DIR, DATA_DIR, MEMBERS_FILE
from logger import log_info, log_error, log_warning, log_debug, log_section, log_separator
from data_store import atomic_write_json, load_json_file

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

app = Flask(__name__)
app.config['SECRET_KEY'] = 'telegram-automation-secret-key-2024-multi-user'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 horas
socketio = SocketIO(app, cors_allowed_origins="*")
thread_context = threading.local()

# User Manager Global
user_manager = UserManager()

managers_by_user = {
    'sessions': {},
    'automation': {},
    'clones': {}
}
reaction_monitors = {}
processes_by_user = {}
processes_lock = threading.RLock()

def _serialize_process(process):
    return dict(process)

def get_user_processes(username=None):
    username = get_current_username(username) or '_anonymous'
    with processes_lock:
        return processes_by_user.setdefault(username, {})

def start_process(process_type, title, total=0, username=None, detail=''):
    username = get_current_username(username) or '_anonymous'
    process_id = f'{process_type}-{int(datetime.now().timestamp() * 1000)}-{random.randint(1000, 9999)}'
    process = {
        'id': process_id,
        'type': process_type,
        'title': title,
        'detail': detail,
        'status': 'running',
        'current': 0,
        'total': int(total or 0),
        'percent': 0,
        'started_at': datetime.now().isoformat(timespec='seconds'),
        'updated_at': datetime.now().isoformat(timespec='seconds'),
        'finished_at': None,
        'message': 'Iniciando...'
    }
    with processes_lock:
        processes_by_user.setdefault(username, {})[process_id] = process
    emit_to_user('process_update', _serialize_process(process), username)
    return process_id

def update_process(process_id, username=None, **updates):
    username = get_current_username(username) or '_anonymous'
    with processes_lock:
        process = processes_by_user.setdefault(username, {}).get(process_id)
        if not process:
            return None
        process.update(updates)
        process['updated_at'] = datetime.now().isoformat(timespec='seconds')
        total = int(process.get('total') or 0)
        current = int(process.get('current') or 0)
        process['percent'] = min(100, max(0, round((current / total) * 100))) if total else 0
        snapshot = _serialize_process(process)
    emit_to_user('process_update', snapshot, username)
    return snapshot

def finish_process(process_id, username=None, status='completed', message='Concluído'):
    username = get_current_username(username) or '_anonymous'
    with processes_lock:
        process = processes_by_user.setdefault(username, {}).get(process_id)
        if not process:
            return None
        process['status'] = status
        process['message'] = message
        process['finished_at'] = datetime.now().isoformat(timespec='seconds')
        process['updated_at'] = process['finished_at']
        if status == 'completed' and process.get('total'):
            process['current'] = process.get('total')
            process['percent'] = 100
        snapshot = _serialize_process(process)
    emit_to_user('process_update', snapshot, username)
    return snapshot

def list_processes(username=None):
    username = get_current_username(username) or '_anonymous'
    with processes_lock:
        processes = list(processes_by_user.setdefault(username, {}).values())
    status_order = {'running': 0, 'completed': 1, 'error': 2}
    return sorted(
        [_serialize_process(process) for process in processes],
        key=lambda item: (status_order.get(item.get('status'), 9), item.get('updated_at') or ''),
        reverse=False
    )[-20:]

def get_current_username(username=None):
    if username:
        return username
    if getattr(thread_context, 'username', None):
        return thread_context.username
    if has_request_context() and 'username' in session:
        return session['username']
    return None

def get_user_room(username=None):
    username = get_current_username(username)
    return f'user:{username}' if username else None

def emit_to_user(event_name, payload, username=None):
    room = get_user_room(username)
    if room:
        socketio.emit(event_name, payload, room=room)
    else:
        socketio.emit(event_name, payload)

class UserSocketEmitter:
    def __init__(self, socketio_instance, username, task_id=None, automation_manager=None):
        self.socketio = socketio_instance
        self.username = username
        self.task_id = task_id
        self.automation_manager = automation_manager

    def emit(self, event_name, payload=None, **kwargs):
        if self.task_id and event_name == 'log':
            payload = payload or {}
            payload['task_id'] = self.task_id
            append_task_log(
                self.task_id,
                payload.get('message', ''),
                payload.get('type', 'info'),
                self.automation_manager
            )
            event_name = 'task_log'
        kwargs.setdefault('room', get_user_room(self.username))
        return self.socketio.emit(event_name, payload, **kwargs)

@socketio.on('connect')
def handle_socket_connect():
    username = session.get('username')
    if username:
        join_room(get_user_room(username))

# ========== DECORADOR DE AUTENTICAÇÃO ==========
def login_required(f):
    """Decorator para proteger rotas que precisam de login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Não autenticado', 'login_required': True}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_paths(username=None):
    """Retorna os caminhos específicos do usuário logado"""
    username = get_current_username(username)
    if not username:
        return None

    user_manager.create_user_directories(username)
    return {
        'sessions_dir': user_manager.get_user_sessions_dir(username),
        'data_dir': user_manager.get_user_data_dir(username),
        'exports_dir': user_manager.get_user_exports_dir(username),
        'logs_dir': user_manager.get_user_logs_dir(username),
        'config_file': os.path.join(user_manager.get_user_data_dir(username), 'config.json'),
        'members_file': os.path.join(user_manager.get_user_data_dir(username), 'members.json'),
        'floods_file': os.path.join(user_manager.get_user_data_dir(username), 'session_floods.json'),
        'automation_file': os.path.join(user_manager.get_user_data_dir(username), 'automation_config.json'),
        'warming_file': os.path.join(user_manager.get_user_data_dir(username), 'warming_groups.json'),
        'reactions_file': os.path.join(user_manager.get_user_data_dir(username), 'reactions.json'),
    }

def get_session_manager_instance(username=None):
    username = get_current_username(username)
    if not username:
        raise RuntimeError('Usuário não autenticado')

    if username in managers_by_user['sessions']:
        return managers_by_user['sessions'][username]

    paths = get_user_paths(username)
    manager = SessionManager(paths['sessions_dir'], paths['config_file'])
    managers_by_user['sessions'][username] = manager

    if has_request_context():
        g.session_manager = manager

    return manager

def get_automation_manager_instance(username=None):
    username = get_current_username(username)
    if not username:
        raise RuntimeError('Usuário não autenticado')

    if username in managers_by_user['automation']:
        return managers_by_user['automation'][username]

    paths = get_user_paths(username)
    manager = AutomationManager(paths['data_dir'])
    managers_by_user['automation'][username] = manager

    if has_request_context():
        g.automation_manager = manager

    return manager

def get_clone_manager_instance(username=None):
    username = get_current_username(username)
    if not username:
        raise RuntimeError('Usuário não autenticado')

    if username in managers_by_user['clones']:
        return managers_by_user['clones'][username]

    paths = get_user_paths(username)
    manager = CloneManager(paths['data_dir'])
    managers_by_user['clones'][username] = manager

    if has_request_context():
        g.clone_manager = manager

    return manager

def get_task_members_file(task, paths=None):
    """Retorna o arquivo de membros vinculado a uma tarefa ou o arquivo padrão."""
    paths = paths or get_user_paths()
    if not paths:
        return None

    task_file = task.get('members_file')
    if task_file:
        filename = os.path.basename(task_file)
        return os.path.join(paths['data_dir'], filename)

    return paths['members_file']

def normalize_members_payload(data):
    """Aceita arquivo exportado ({members: [...]}) ou lista direta."""
    if isinstance(data, dict):
        return data.get('members') if isinstance(data.get('members'), list) else []
    if isinstance(data, list):
        return data
    return []

def load_members_from_file(file_path):
    if not file_path or not os.path.exists(file_path):
        return []
    members = normalize_members_payload(load_json_file(file_path, []))
    # Compatibilidade com exports que não gravam o marcador de processamento.
    normalized = []
    for member in members:
        if isinstance(member, dict):
            item = dict(member)
            item.setdefault('added', False)
            normalized.append(item)
    return normalized

def find_latest_pending_members_export(paths):
    """Procura o arquivo extraído mais recente que ainda tenha membros pendentes."""
    import glob
    patterns = [
        os.path.join(paths['data_dir'], 'members_export_grupo_*.json'),
        os.path.join(paths['data_dir'], 'members_export_lote_*.json'),
        os.path.join(paths['data_dir'], 'members_export.json')
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))

    for file_path in sorted(set(candidates), key=lambda path: os.path.getmtime(path), reverse=True):
        try:
            members = load_members_from_file(file_path)
            pending = [member for member in members if not member.get('added', False)]
            if pending:
                return file_path, members, pending
        except Exception:
            continue

    return None, [], []

def attach_task_members_file(task, source_file, members, paths):
    """Copia uma extração para arquivo próprio da tarefa e vincula nela."""
    from datetime import datetime
    clean_name = secure_filename(os.path.basename(source_file)) or 'members_export.json'
    task_filename = f'task_{task["id"]}_members_auto_{clean_name}'
    task_file = os.path.join(paths['data_dir'], task_filename)

    atomic_write_json(task_file, members)

    task['members_file'] = task_filename
    task['members_source_name'] = clean_name
    task['members_total'] = len(members)
    task['members_updated_at'] = datetime.now().isoformat()
    return task_file

def normalize_delay_range(min_value, max_value, default_min, default_max=None):
    default_max = default_min if default_max is None else default_max
    try:
        min_value = int(min_value)
    except Exception:
        min_value = int(default_min)
    try:
        max_value = int(max_value)
    except Exception:
        max_value = int(default_max)
    return (min(min_value, max_value), max(min_value, max_value))

def get_task_delay_range(task, prefix, fallback):
    return normalize_delay_range(
        task.get(f'{prefix}_min', task.get(prefix, fallback)),
        task.get(f'{prefix}_max', task.get(prefix, fallback)),
        fallback
    )

def pick_task_delay(task, prefix, fallback):
    delay_min, delay_max = get_task_delay_range(task, prefix, fallback)
    return random.randint(max(1, delay_min), max(1, delay_max))

def normalize_task_status(task):
    """Corrige estados inconsistentes de tarefa antes de exibir/processar."""
    target = int(task.get('target_members') or 0)
    total = int(task.get('total_added') or 0)

    if task.get('status') == 'completed' and total < target:
        task['status'] = 'paused'
        task['completion_note'] = 'Meta ainda não foi concluída; tarefa reaberta automaticamente.'
        return True

    if total >= target and target > 0 and task.get('status') != 'completed':
        task['status'] = 'completed'
        return True

    return False

def load_reactions_data(paths=None):
    paths = paths or get_user_paths()
    default_data = {
        'queue': [],
        'history': [],
        'reacted_messages': {},
        'target_cache': {},
        'settings': {
            'delay_seconds': 5,
            'disable_add_group_interactions': False,
            'custom_reactions': []
        },
        'continuous_task': {
            'enabled': False,
            'session_indexes': [],
            'post_link': '',
            'post_links': [],
            'reactions': [],
            'poll_seconds': 15,
            'started_at': None
        }
    }

    if not paths:
        return default_data

    reactions_file = paths['reactions_file']
    if not os.path.exists(reactions_file):
        save_reactions_data(default_data, paths)
        return default_data

    try:
        data = load_json_file(reactions_file, default_data)
    except Exception:
        data = default_data

    data.setdefault('queue', [])
    data.setdefault('history', [])
    data.setdefault('reacted_messages', {})
    data.setdefault('target_cache', {})
    data.setdefault('settings', {})
    data.setdefault('continuous_task', {})
    data['settings'].setdefault('delay_seconds', 5)
    data['settings'].setdefault('disable_add_group_interactions', False)
    data['settings'].setdefault('custom_reactions', [])
    data['continuous_task'].setdefault('enabled', False)
    data['continuous_task'].setdefault('session_indexes', [])
    data['continuous_task'].setdefault('post_link', '')
    data['continuous_task'].setdefault('post_links', [])
    data['continuous_task'].setdefault('reactions', [])
    data['continuous_task'].setdefault('poll_seconds', 15)
    data['continuous_task'].setdefault('started_at', None)
    if data['continuous_task'].get('post_link') and not data['continuous_task'].get('post_links'):
        data['continuous_task']['post_links'] = [data['continuous_task']['post_link']]
    return data

def normalize_reaction_links(payload):
    links = payload.get('post_links')
    if links is None:
        raw_link = payload.get('post_link') or ''
        links = str(raw_link).replace(',', '\n').splitlines()
    elif isinstance(links, str):
        links = links.replace(',', '\n').splitlines()

    normalized = []
    for link in links or []:
        link = str(link or '').strip()
        if link and link not in normalized:
            normalized.append(link)
        if len(normalized) >= 50:
            break
    return normalized

def save_reactions_data(data, paths=None):
    paths = paths or get_user_paths()
    if not paths:
        return

    atomic_write_json(paths['reactions_file'], data)

def load_api_config_for_paths(paths):
    config_file = paths['config_file']
    if not os.path.exists(config_file):
        return []

    data = load_json_file(config_file, {})

    if data.get('api_credentials'):
        return data['api_credentials']

    if data.get('api_id') and data.get('api_hash'):
        return [{
            'api_id': data['api_id'],
            'api_hash': data['api_hash'],
            'name': 'API Principal'
        }]

    return []

# ========== INICIALIZAÇÃO DO SISTEMA ==========
log_section("INICIALIZAÇÃO DO SISTEMA")

# Garante que as pastas necessárias existem
try:
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    log_info(f"✅ Pasta sessions criada/verificada: {SESSIONS_DIR}")
except Exception as e:
    log_error(f"❌ Erro ao criar pasta sessions: {e}")

try:
    os.makedirs(DATA_DIR, exist_ok=True)
    log_info(f"✅ Pasta data criada/verificada: {DATA_DIR}")
    
    # Verifica permissões
    if os.access(DATA_DIR, os.W_OK):
        log_info(f"✅ Pasta data tem permissão de escrita")
    else:
        log_warning(f"⚠️ Pasta data SEM permissão de escrita!")
        
except Exception as e:
    log_error(f"❌ Erro ao criar pasta data: {e}")

# Cria arquivo de configuração vazio se não existir
if not os.path.exists(CONFIG_FILE):
    try:
        atomic_write_json(CONFIG_FILE, {
            'sessions': [],
            'api_credentials': [],
            'warming_group': 'https://t.me/batepapoe'
        })
        log_info(f"✅ Arquivo de configuração criado: {CONFIG_FILE}")
    except Exception as e:
        log_error(f"❌ Erro ao criar arquivo de configuração: {e}")

log_separator()

session_manager = LocalProxy(get_session_manager_instance)
automation_manager = LocalProxy(get_automation_manager_instance)
clone_manager = LocalProxy(get_clone_manager_instance)

# Variáveis de aquecimento separadas por usuário
warming_states_by_user = {}

def get_warming_state(username=None):
    username = get_current_username(username) or '_anonymous'
    if username not in warming_states_by_user:
        warming_states_by_user[username] = {'active': False, 'thread': None}
    return warming_states_by_user[username]

def init_user_managers():
    """Inicializa managers com diretórios do usuário logado"""
    username = get_current_username()
    if not username:
        return False

    get_session_manager_instance(username)
    get_automation_manager_instance(username)
    get_clone_manager_instance(username)
    return True

@app.before_request
def before_request():
    """Inicializa managers antes de cada request autenticado"""
    if 'username' in session and request.endpoint not in ['login_page', 'login', 'register', 'static']:
        init_user_managers()
        try:
            automation_manager.load_config()
            session_manager.load_sessions(force_reload=True)
        except Exception as refresh_error:
            print(f'⚠️ Erro ao recarregar dados do usuário antes da request: {refresh_error}')

@app.after_request
def after_request(response):
    """Evita que o navegador reaproveite dados antigos dos endpoints JSON."""
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Funções helper para logs separados por aba
def emit_extract_log(message, log_type='info'):
    """Emite log apenas para aba Extrair"""
    emit_to_user('extract_log', {'message': message, 'type': log_type})

def emit_add_log(message, log_type='info'):
    """Emite log apenas para aba Adicionar"""
    emit_to_user('add_log', {'message': message, 'type': log_type})

def append_task_log(task_id, message, log_type='info', manager=None):
    if not task_id or not message:
        return
    manager = manager or getattr(thread_context, 'automation_manager', None)
    if not manager:
        return
    try:
        if not hasattr(manager, 'config'):
            manager.load_config()
        for task in manager.config.get('groups', []):
            if task.get('id') == task_id:
                logs = task.setdefault('logs', [])
                logs.append({
                    'time': datetime.now().isoformat(timespec='seconds'),
                    'type': log_type,
                    'message': message
                })
                task['logs'] = logs[-500:]
                break
        manager.save_config()
    except Exception as log_error:
        print(f'⚠️ Erro ao salvar log da tarefa #{task_id}: {log_error}')

def save_task_runtime_details(task_id, manager, counters=None, session_run=None, member_results=None):
    """Persiste detalhes runtime na tarefa atual do arquivo, mesmo após reloads internos."""
    if not task_id or not manager:
        return None
    try:
        manager.load_config()
        for current_task in manager.config.get('groups', []):
            if current_task.get('id') != task_id:
                continue

            if counters:
                for key in ('added_today', 'total_added'):
                    if key in counters:
                        current_task[key] = counters[key]

            if session_run:
                runs = current_task.setdefault('session_runs', [])
                runs.append(session_run)
                current_task['session_runs'] = runs[-200:]

            if member_results:
                results = current_task.setdefault('member_results', [])
                results.extend(member_results)
                current_task['member_results'] = results[-1000:]

            manager.save_config()
            return current_task
    except Exception as detail_error:
        print(f'⚠️ Erro ao salvar detalhes da tarefa #{task_id}: {detail_error}')
    return None

def is_task_fatal_group_error(last_result):
    """Retorna True quando o problema é do grupo destino, não apenas da sessão."""
    if not last_result:
        return False

    status = str(last_result.get('status') or '').strip().lower()
    reason = str(last_result.get('reason') or '').strip().lower()

    fatal_statuses = {
        'private_group',
        'admin_required',
        'write_forbidden',
        'channelprivateerror',
        'chatadminrequirederror',
        'chatwriteforbiddenerror',
    }
    if status in fatal_statuses:
        return True

    fatal_markers = (
        'não foi possível acessar grupo privado',
        'nao foi possivel acessar grupo privado',
        'não foi possível acessar o grupo',
        'nao foi possivel acessar o grupo',
        'grupo privado/inacessível',
        'grupo privado/inacessivel',
        'chatwriteforbiddenerror',
        'chatadminrequirederror',
        'channelprivateerror',
        'invitehashinvalid',
        'invitehashexpired',
    )
    return any(marker in reason for marker in fatal_markers)

def pause_task_after_fatal_group_error(task_id, manager, last_result):
    """Pausa a tarefa no arquivo quando o grupo destino caiu ou ficou bloqueado."""
    status = str((last_result or {}).get('status') or 'erro_grupo')
    reason = str((last_result or {}).get('reason') or status)
    pause_reason = f'Grupo inacessível: {reason[:180]}'

    manager.load_config()
    for current_task in manager.config.get('groups', []):
        if current_task.get('id') == task_id:
            current_task['status'] = 'paused'
            current_task['pause_requested_at'] = datetime.now().isoformat(timespec='seconds')
            current_task['pause_reason'] = pause_reason
            manager.save_config()
            return current_task, pause_reason

    return None, pause_reason

def emit_task_log(message, log_type='info', task_id=None):
    """Emite log apenas para aba Tarefas"""
    task_id = task_id or getattr(thread_context, 'task_id', None)
    payload = {'message': message, 'type': log_type}
    if task_id:
        payload['task_id'] = task_id
        append_task_log(task_id, message, log_type)
    emit_to_user('task_log', payload)

def create_session_lock_state():
    return {
        'warming': False,
        'extraction': False,
        'addition': False,
        'active_tasks': set()
    }

# Sistema de bloqueio de sessões separado por usuário
session_locks_by_user = {}

def get_user_lock_state(username=None):
    username = get_current_username(username) or '_anonymous'
    if username not in session_locks_by_user:
        session_locks_by_user[username] = create_session_lock_state()
    return session_locks_by_user[username]

def check_session_lock(operation, task_id=None, username=None):
    """Verifica se pode executar a operação"""
    session_locks = get_user_lock_state(username)
    if operation == 'task':
        if session_locks['warming']:
            return False, "Não é possível processar tarefas enquanto aquecimento está ativo. Pare o aquecimento primeiro."
        if len(session_locks['active_tasks']) > 0 and task_id not in session_locks['active_tasks']:
            active_id = next(iter(session_locks['active_tasks']))
            return False, f"Modo VPS ativo: a tarefa #{active_id} já está rodando. Pause ou aguarde terminar antes de iniciar outra."
        return True, "OK"
    elif operation == 'warming':
        if session_locks['extraction'] or session_locks['addition'] or len(session_locks['active_tasks']) > 0:
            return False, "Não é possível iniciar aquecimento enquanto extração, adição ou tarefas estão em andamento"
        return True, "OK"
    elif operation == 'extraction':
        if session_locks['warming']:
            return False, "Não é possível extrair enquanto aquecimento está ativo. Pare o aquecimento primeiro."
        if session_locks['extraction']:
            return False, "Já existe uma extração em andamento"
        return True, "OK"
    elif operation == 'addition':
        if session_locks['warming']:
            return False, "Não é possível adicionar membros enquanto aquecimento está ativo. Pare o aquecimento primeiro."
        if session_locks['addition']:
            return False, "Já existe uma adição em andamento"
        if len(session_locks['active_tasks']) > 0:
            return False, "Não é possível adicionar enquanto tarefas estão em andamento"
        return True, "OK"
    
    return True, "OK"

def set_session_lock(operation, locked, task_id=None, username=None):
    """Define o estado do lock"""
    session_locks = get_user_lock_state(username)
    
    if operation == 'task':
        if locked and task_id:
            session_locks['active_tasks'].add(task_id)
        elif not locked and task_id:
            session_locks['active_tasks'].discard(task_id)
    else:
        session_locks[operation] = locked

def load_api_config():
    """Carrega configurações da API do usuário logado"""
    if 'username' not in session:
        return []
    
    paths = get_user_paths()
    config_file = paths['config_file']
    
    if os.path.exists(config_file):
        data = load_json_file(config_file, {})

        # Suporte para múltiplas APIs
        if 'api_credentials' in data and data['api_credentials']:
            return data['api_credentials']

        # Compatibilidade com formato antigo (single API)
        if 'api_id' in data and 'api_hash' in data:
            return [{
                'api_id': data['api_id'],
                'api_hash': data['api_hash'],
                'name': 'API Principal'
            }]
    
    return []

def save_api_config(api_credentials):
    """Salva configurações das APIs do usuário logado"""
    if 'username' not in session:
        return False
    
    try:
        paths = get_user_paths()
        config_file = paths['config_file']
        data_dir = paths['data_dir']
        
        # Garante que a pasta data existe
        os.makedirs(data_dir, exist_ok=True)
        
        # Verifica permissões de escrita
        if not os.access(data_dir, os.W_OK):
            log_error(f"Sem permissão de escrita em: {data_dir}")
            raise PermissionError(f"Sem permissão de escrita em: {data_dir}")
        
        data = {}
        
        # Carrega dados existentes se o arquivo já existe
        if os.path.exists(config_file):
            try:
                data = load_json_file(config_file, {})
                log_info(f"Arquivo de configuração carregado: {config_file}")
            except Exception as read_error:
                log_warning(f"Erro ao ler config existente, criando novo: {read_error}")
                data = {}
        
        # Atualiza com novas credenciais
        data['api_credentials'] = api_credentials
        
        # Mantém compatibilidade com formato antigo
        if api_credentials:
            data['api_id'] = api_credentials[0]['api_id']
            data['api_hash'] = api_credentials[0]['api_hash']
        
        # Salva o arquivo
        atomic_write_json(config_file, data)
        
        # Verifica se salvou corretamente
        if os.path.exists(config_file):
            file_size = os.path.getsize(config_file)
            log_info(f"✅ Configuração salva com sucesso! Arquivo: {config_file} ({file_size} bytes)")
            log_info(f"✅ APIs cadastradas: {len(api_credentials)}")
            return True
        else:
            log_error(f"❌ Arquivo não foi criado: {config_file}")
            return False
            
    except PermissionError as pe:
        log_error(f"❌ Erro de permissão ao salvar config: {pe}")
        raise
    except Exception as e:
        log_error(f"❌ Erro ao salvar configuração: {e}")
        import traceback
        log_error(traceback.format_exc())
        raise

def get_next_api():
    """Retorna a próxima API na rotação"""
    api_credentials = load_api_config()
    paths = get_user_paths()
    config_file = paths['config_file'] if paths else CONFIG_FILE
    
    if not api_credentials:
        # Tenta formato antigo (compatibilidade)
        if os.path.exists(config_file):
            data = load_json_file(config_file, {})
            if 'api_id' in data and 'api_hash' in data and data['api_id'] and data['api_hash']:
                # Converte formato antigo para novo
                api_credentials = [{
                    'api_id': data['api_id'],
                    'api_hash': data['api_hash'],
                    'name': 'API Principal'
                }]
                # Salva no novo formato
                save_api_config(api_credentials)
                return data['api_id'], data['api_hash']
        
        return None, None
    
    # Se só tem uma API, retorna ela
    if len(api_credentials) == 1:
        return api_credentials[0]['api_id'], api_credentials[0]['api_hash']
    
    # Rotação: pega o índice atual e incrementa
    if os.path.exists(config_file):
        data = load_json_file(config_file, {})
        current_index = data.get('current_api_index', 0)
    else:
        data = {}
        current_index = 0
    
    # Pega a API atual
    api = api_credentials[current_index]
    
    # Incrementa o índice para próxima vez
    next_index = (current_index + 1) % len(api_credentials)
    
    # Salva o novo índice
    data['current_api_index'] = next_index
    atomic_write_json(config_file, data)
    
    log_info(f"🔄 Usando API: {api.get('name', 'Sem nome')} (ID: {api['api_id']})")
    
    return api['api_id'], api['api_hash']

# ========== ROTAS DE AUTENTICAÇÃO ==========

@app.route('/login', methods=['GET'])
def login_page():
    """Página de login"""
    if 'username' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Endpoint de login"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Preencha todos os campos'}), 400
    
    if user_manager.authenticate(username, password):
        session['username'] = username
        session.permanent = True
        log_info(f"✅ Login web bem-sucedido: {username}")
        return jsonify({'success': True, 'username': username})
    else:
        log_warning(f"❌ Tentativa de login falhou: {username}")
        return jsonify({'success': False, 'error': 'Usuário ou senha incorretos'}), 401

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Endpoint de registro"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Preencha todos os campos'}), 400
    
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Senha deve ter no mínimo 6 caracteres'}), 400
    
    success, message = user_manager.create_user(username, password)
    
    if success:
        # Confirma que o usuário foi persistido antes de responder e já inicia
        # a sessão. Isso evita uma segunda digitação da senha logo após o cadastro.
        if not user_manager.authenticate(username, password):
            log_error(f"Falha ao validar usuário recém-registrado: {username}")
            return jsonify({
                'success': False,
                'error': 'A conta não pôde ser confirmada. Tente novamente.'
            }), 500

        session['username'] = username
        session.permanent = True
        log_info(f"✅ Novo usuário registrado: {username}")
        return jsonify({
            'success': True,
            'message': message,
            'username': username,
            'authenticated': True
        })
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """Endpoint de logout"""
    username = session.get('username')
    session.clear()
    log_info(f"✅ Logout: {username}")
    return jsonify({'success': True})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Verifica se usuário está autenticado"""
    if 'username' in session:
        return jsonify({'authenticated': True, 'username': session['username']})
    return jsonify({'authenticated': False})

# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    if 'username' not in session:
        return render_template('login.html')
    return render_template('index.html', username=session.get('username'))

@app.route('/new')
def index_new():
    """Rota para testar o novo layout"""
    return render_template('index_new.html')

@app.route('/health')
def health_check():
    """Health check para monitoramento do Discloud"""
    return jsonify({
        'status': 'healthy',
        'service': 'telegram-automation',
        'version': '1.0.0',
        'domain': 'telegram-clone-site.discloud.app'
    }), 200

@app.route('/ping')
def ping():
    """Ping simples para verificar se o servidor está respondendo"""
    return 'pong', 200

@app.route('/manifest.json')
def manifest():
    """Serve o manifest PWA"""
    return app.send_static_file('manifest.json')

@app.route('/service-worker.js')
def service_worker():
    """Serve o service worker"""
    return app.send_static_file('service-worker.js')

@app.route('/api/config', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_config():
    if request.method == 'GET':
        try:
            api_credentials = load_api_config()
            
            # Verifica se a pasta data existe e tem permissão
            data_dir_info = {
                'exists': os.path.exists(DATA_DIR),
                'writable': os.access(DATA_DIR, os.W_OK) if os.path.exists(DATA_DIR) else False,
                'path': DATA_DIR
            }
            
            return jsonify({
                'configured': len(api_credentials) > 0,
                'api_credentials': api_credentials,
                'total': len(api_credentials),
                'data_dir': data_dir_info
            })
        except Exception as e:
            log_error(f"Erro ao carregar config: {e}")
            return jsonify({
                'configured': False,
                'api_credentials': [],
                'total': 0,
                'error': str(e)
            })
    
    elif request.method == 'POST':
        try:
            data = request.json
            
            log_info(f"📥 Recebida requisição para salvar API")
            log_info(f"📊 Dados recebidos: {data}")
            
            # Se for adicionar nova API
            if 'add' in data and data['add']:
                api_credentials = load_api_config()
                
                # Verifica se já existe
                for cred in api_credentials:
                    if cred['api_id'] == int(data['api_id']):
                        return jsonify({'success': False, 'error': 'API ID já cadastrada'}), 400
                
                api_credentials.append({
                    'api_id': int(data['api_id']),
                    'api_hash': data['api_hash'],
                    'name': data.get('name', f'API {len(api_credentials) + 1}')
                })
                
                log_info(f"➕ Adicionando nova API (total: {len(api_credentials)})")
                
                if save_api_config(api_credentials):
                    log_info(f"✅ API salva com sucesso!")
                    return jsonify({'success': True, 'total': len(api_credentials)})
                else:
                    log_error(f"❌ Falha ao salvar API")
                    return jsonify({'success': False, 'error': 'Falha ao salvar configuração'}), 500
            
            # Se for substituir todas
            else:
                api_credentials = [{
                    'api_id': int(data['api_id']),
                    'api_hash': data['api_hash'],
                    'name': data.get('name', 'API Principal')
                }]
                
                log_info(f"🔄 Substituindo configuração de API")
                
                if save_api_config(api_credentials):
                    log_info(f"✅ API salva com sucesso!")
                    return jsonify({'success': True})
                else:
                    log_error(f"❌ Falha ao salvar API")
                    return jsonify({'success': False, 'error': 'Falha ao salvar configuração'}), 500
                    
        except Exception as e:
            log_error(f"❌ Erro ao processar requisição POST: {e}")
            import traceback
            log_error(traceback.format_exc())
            return jsonify({'success': False, 'error': f'Erro ao salvar: {str(e)}'}), 500
    
    elif request.method == 'DELETE':
        try:
            # Remove uma API específica
            data = request.json
            api_id_to_remove = int(data['api_id'])
            
            api_credentials = load_api_config()
            api_credentials = [cred for cred in api_credentials if cred['api_id'] != api_id_to_remove]
            
            if not api_credentials:
                return jsonify({'success': False, 'error': 'Não é possível remover a última API'}), 400
            
            if save_api_config(api_credentials):
                return jsonify({'success': True, 'total': len(api_credentials)})
            else:
                return jsonify({'success': False, 'error': 'Falha ao salvar configuração'}), 500
                
        except Exception as e:
            log_error(f"❌ Erro ao deletar API: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    local_session_manager = get_session_manager_instance(session.get('username'))
    local_session_manager.invalidate_cache()
    sessions = local_session_manager.load_sessions(force_reload=True)
    
    # Adiciona informações de flood
    for session_info in sessions:
        if session_info.get('status') == 'flood':
            flood_info = local_session_manager.get_flood_info(session_info.get('session_name', ''))
            if flood_info.get('in_flood') or flood_info.get('expired'):
                session_info['flood_info'] = flood_info
    
    return jsonify({'sessions': sessions, 'total': len(sessions)})

@app.route('/api/sessions/toggle/<int:index>', methods=['POST'])
@login_required
def toggle_session(index):
    success = session_manager.toggle_session(index)
    return jsonify({'success': success})

@app.route('/api/sessions/remove/<int:index>', methods=['DELETE'])
@login_required
def remove_session(index):
    success = session_manager.remove_session(index)
    return jsonify({'success': success})

@app.route('/api/sessions/remove-all', methods=['DELETE'])
@login_required
def remove_all_sessions():
    """Remove todas as sessões de uma vez"""
    try:
        sessions = session_manager.load_sessions()
        total = len(sessions)
        
        if total == 0:
            return jsonify({'success': False, 'error': 'Nenhuma sessão para remover'}), 400
        
        log_warning(f'🗑️ Removendo TODAS as {total} sessões...')
        
        # Remove todas as sessões
        success = session_manager.remove_all_sessions()
        
        if success:
            log_info(f'✅ {total} sessão(ões) removida(s) com sucesso')
            return jsonify({'success': True, 'removed': total})
        else:
            log_error('❌ Erro ao remover sessões')
            return jsonify({'success': False, 'error': 'Erro ao remover sessões'}), 500
            
    except Exception as e:
        log_error(f'❌ Erro ao remover todas as sessões: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system/reset-locks', methods=['POST'])
@login_required
def reset_locks():
    """Reseta todos os locks do sistema"""
    username = get_current_username()
    session_locks_by_user[username] = create_session_lock_state()
    return jsonify({'success': True, 'message': 'Locks resetados com sucesso'})

@app.route('/api/processes', methods=['GET'])
@login_required
def get_processes():
    return jsonify({'success': True, 'processes': list_processes(session.get('username'))})

@app.route('/api/sessions/import', methods=['POST'])
@login_required
def import_sessions():
    """Importa múltiplas sessões de uma vez"""
    try:
        if 'sessions' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400
        
        files = request.files.getlist('sessions')
        
        if len(files) == 0:
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400
        
        # Limite alto para importação em lote grande.
        max_import_files = 500
        if len(files) > max_import_files:
            return jsonify({
                'success': False, 
                'error': f'Limite máximo: {max_import_files} sessões por vez. Você selecionou {len(files)}. Divida em múltiplas importações.'
            }), 400
        
        # Delay progressivo para lotes grandes. A validação online consulta o
        # Telegram para cada sessão, então 300+ arquivos precisam respirar mais.
        if len(files) > 300:
            import_delay = 1.5
        elif len(files) > 100:
            import_delay = 0.8
        else:
            import_delay = 0
        if len(files) > 100:
            log_warning(f'⚠️ Importando {len(files)} sessões com delay de {import_delay}s entre arquivos - isso pode demorar!')
        
        api_id, api_hash = get_next_api()
        if not api_id:
            return jsonify({'success': False, 'error': 'Configure a API primeiro'}), 400
        
        log_info(f'📦 Recebido {len(files)} arquivo(s) .session para importar')
        
        # Salva arquivos temporariamente em pasta exclusiva para permitir que a
        # resposta HTTP volte rápido enquanto a validação continua em segundo plano.
        temp_dir = tempfile.mkdtemp(prefix='session_import_')
        temp_files = []
        for file in files:
            if file.filename.endswith('.session'):
                filename = secure_filename(file.filename)
                temp_path = os.path.join(temp_dir, filename)
                if os.path.exists(temp_path):
                    name, ext = os.path.splitext(filename)
                    temp_path = os.path.join(temp_dir, f'{name}_{len(temp_files) + 1:04d}{ext}')
                file.save(temp_path)
                temp_files.append(temp_path)
        
        log_info(f'💾 {len(temp_files)} arquivos salvos temporariamente')
        
        current_username = session.get('username')
        process_id = start_process(
            'session_import',
            'Importação de sessões',
            total=len(temp_files),
            username=current_username,
            detail=f'{len(temp_files)} arquivo(s) enviados'
        )

        def import_progress(progress):
            message = (
                f"{progress.get('current')}/{progress.get('total')} processadas. "
                f"{progress.get('active')} aprovadas, {progress.get('inactive')} recusadas."
            )
            update_process(
                process_id,
                username=current_username,
                current=progress.get('current', 0),
                total=progress.get('total', len(temp_files)),
                message=message,
                detail=f"Última: {progress.get('session_name')}"
            )

        if not temp_files:
            finish_process(
                process_id,
                username=current_username,
                status='error',
                message='Nenhum arquivo .session válido foi encontrado.'
            )
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            return jsonify({'success': False, 'error': 'Nenhum arquivo .session válido foi encontrado'}), 400

        update_process(
            process_id,
            username=current_username,
            message=f'Fila criada: {len(temp_files)} sessão(ões). Delay: {import_delay}s.',
            detail='Validando em segundo plano'
        )

        def run_import_job(username, process_id, temp_files, temp_dir, api_id, api_hash, import_delay):
            try:
                user_paths = get_user_paths(username)
                manager = SessionManager(user_paths['sessions_dir'], user_paths['config_file'])
                result = manager.import_multiple_sessions(
                    temp_files,
                    api_id,
                    api_hash,
                    validate_online=True,
                    delay_between=import_delay,
                    progress_callback=import_progress
                )

                log_info(f'✅ Importação concluída: {result["active"]} aprovadas, {result["inactive"]} recusadas/puladas')
                finish_process(
                    process_id,
                    username=username,
                    status='completed',
                    message=f'Importação concluída: {result["active"]} aprovadas, {result["inactive"]} recusadas.'
                )
            except Exception as job_error:
                log_error(f'❌ Erro no processo de importação em segundo plano: {job_error}')
                import traceback
                log_error(traceback.format_exc())
                finish_process(process_id, username=username, status='error', message=f'Erro: {str(job_error)}')
            finally:
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

        socketio.start_background_task(
            run_import_job,
            current_username,
            process_id,
            temp_files,
            temp_dir,
            api_id,
            api_hash,
            import_delay
        )

        return jsonify({
            'success': True,
            'started': True,
            'process_id': process_id,
            'total': len(temp_files),
            'delay_between': import_delay,
            'message': 'Importação iniciada em segundo plano. Acompanhe o progresso em tempo real no painel.'
        })
        
    except Exception as e:
        try:
            if 'process_id' in locals():
                finish_process(process_id, username=session.get('username'), status='error', message=f'Erro: {str(e)}')
        except Exception:
            pass
        log_error(f'❌ Erro ao importar sessões: {e}')
        import traceback
        log_error(traceback.format_exc())
        
        return jsonify({
            'success': False,
            'error': f'Erro ao processar: {str(e)}. Tente importar menos sessões por vez.'
        }), 500

@app.route('/api/sessions/scan', methods=['POST'])
@login_required
def scan_sessions():
    """Escaneia a pasta de sessões e importa as que não estão cadastradas"""
    try:
        api_id, api_hash = get_next_api()
        if not api_id:
            return jsonify({'success': False, 'error': 'Configure a API primeiro'}), 400
        
        log_info('🔍 Escaneando pasta de sessões...')
        result = session_manager.scan_and_import_sessions(api_id, api_hash)
        
        return jsonify(result)
        
    except Exception as e:
        log_error(f'❌ Erro ao escanear sessões: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sessions/open-folder', methods=['POST'])
@login_required
def open_sessions_folder():
    """Abre a pasta de sessões do usuário no Explorer do Windows."""
    try:
        paths = get_user_paths()
        sessions_dir = paths['sessions_dir']
        os.makedirs(sessions_dir, exist_ok=True)

        if os.name == 'nt':
            os.startfile(sessions_dir)
        else:
            import subprocess
            subprocess.Popen(['xdg-open', sessions_dir])

        return jsonify({
            'success': True,
            'path': sessions_dir,
            'message': 'Pasta de sessões aberta'
        })
    except Exception as e:
        log_error(f'❌ Erro ao abrir pasta de sessões: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sessions/migrate-all', methods=['POST'])
@login_required
def migrate_all_sessions_route():
    """Migra todas as sessões do formato antigo para o novo"""
    try:
        from migrate_sessions import migrate_all_sessions
        
        paths = get_user_paths()
        sessions_dir = paths['sessions_dir']
        
        log_info('🔄 Iniciando migração de sessões...')
        result = migrate_all_sessions(sessions_dir)
        
        if result['success']:
            log_info(f'✅ Migração completa: {result["migrated"]} migradas, {result["already_correct"]} já corretas, {result["failed"]} falhas')
        
        return jsonify(result)
        
    except Exception as e:
        log_error(f'❌ Erro ao migrar sessões: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sessions/downgrade-all', methods=['POST'])
@login_required
def downgrade_all_sessions_route():
    """Faz downgrade de todas as sessões para funcionar com Telethon antigo"""
    try:
        from downgrade_sessions import downgrade_all_sessions
        
        paths = get_user_paths()
        sessions_dir = paths['sessions_dir']
        
        log_info('⬇️ Iniciando downgrade de sessões...')
        result = downgrade_all_sessions(sessions_dir)
        
        if result['success']:
            log_info(f'✅ Downgrade completo: {result["downgraded"]} convertidas, {result["already_old"]} já antigas, {result["failed"]} falhas')
        
        return jsonify(result)
        
    except Exception as e:
        log_error(f'❌ Erro ao fazer downgrade: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sessions/restore-backups', methods=['POST'])
@login_required
def restore_backups_route():
    """Restaura sessões dos backups criados pelo downgrade"""
    try:
        from restore_backups import restore_all_backups
        
        paths = get_user_paths()
        sessions_dir = paths['sessions_dir']
        
        log_info('🔄 Restaurando backups...')
        result = restore_all_backups(sessions_dir)
        
        if result['success']:
            log_info(f'✅ Restauração completa: {result["restored"]} restauradas, {result["failed"]} falhas')
        
        return jsonify(result)
        
    except Exception as e:
        log_error(f'❌ Erro ao restaurar backups: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sessions/upgrade-all', methods=['POST'])
@login_required
def upgrade_all_sessions_route():
    """Faz upgrade de todas as sessões para funcionar com Telethon novo (6 colunas)"""
    try:
        from migrate_sessions import migrate_all_sessions
        
        paths = get_user_paths()
        sessions_dir = paths['sessions_dir']
        
        log_info('⬆️ Iniciando upgrade de sessões...')
        result = migrate_all_sessions(sessions_dir)
        
        if result['success']:
            log_info(f'✅ Upgrade completo: {result["migrated"]} convertidas, {result["already_correct"]} já corretas, {result["failed"]} falhas')
        
        return jsonify(result)
        
    except Exception as e:
        log_error(f'❌ Erro ao fazer upgrade: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sessions/validate/<session_name>', methods=['POST'])
@login_required
def validate_session(session_name):
    """Valida se uma sessão está autorizada"""
    try:
        api_id, api_hash = get_next_api()
        if not api_id:
            return jsonify({'success': False, 'error': 'Configure a API primeiro'}), 400
        
        paths = get_user_paths()
        session_path = os.path.join(paths['sessions_dir'], session_name)
        
        log_info(f'🔍 Validando sessão: {session_name}')
        
        # Valida em thread separada
        def validate():
            import asyncio
            from telethon import TelegramClient
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def check_session():
                try:
                    client = TelegramClient(session_path, api_id, api_hash)
                    
                    # Tenta pegar informações do usuário
                    try:
                        await client.connect()
                        me = await client.get_me()
                        await client.disconnect()
                        
                        if me:
                            return {
                                'success': True,
                                'authorized': True,
                                'user_info': {
                                    'phone': me.phone if hasattr(me, 'phone') and me.phone else session_name,
                                    'username': me.username if me.username else session_name,
                                    'first_name': me.first_name if me.first_name else session_name,
                                    'user_id': me.id
                                }
                            }
                        else:
                            return {'success': True, 'authorized': False, 'error': 'Não foi possível obter informações'}
                            
                    except Exception as e:
                        error_msg = str(e)
                        try:
                            await client.disconnect()
                        except:
                            pass

                        if 'update_state has 6 columns but 5 values were supplied' in error_msg:
                            try:
                                from downgrade_sessions import downgrade_session
                                success, msg = downgrade_session(session_path + '.session')
                                if not success:
                                    return {'success': True, 'authorized': False, 'error': f'Falha ao ajustar sessão: {msg}'}

                                client = TelegramClient(session_path, api_id, api_hash)
                                await client.connect()
                                me = await client.get_me()
                                await client.disconnect()

                                if me:
                                    return {
                                        'success': True,
                                        'authorized': True,
                                        'adjusted': True,
                                        'user_info': {
                                            'phone': me.phone if hasattr(me, 'phone') and me.phone else session_name,
                                            'username': me.username if me.username else session_name,
                                            'first_name': me.first_name if me.first_name else session_name,
                                            'user_id': me.id
                                        }
                                    }
                            except Exception as adjust_error:
                                return {'success': True, 'authorized': False, 'error': f'Erro ao ajustar sessão: {adjust_error}'}

                        return {'success': True, 'authorized': False, 'error': str(e)}
                        
                except Exception as e:
                    return {'success': False, 'error': str(e)}
            
            try:
                result = loop.run_until_complete(check_session())
                return result
            finally:
                loop.close()
        
        result = validate()
        
        if result['success'] and result.get('authorized'):
            # Atualiza informações da sessão no config
            sessions = session_manager.load_sessions()
            for session in sessions:
                if session['session_name'] == session_name:
                    user_info = result['user_info']
                    session['phone'] = user_info['phone']
                    session['username'] = user_info['username']
                    session['first_name'] = user_info['first_name']
                    session['name'] = user_info['first_name']
                    session['user_id'] = user_info['user_id']
                    session['active'] = True
                    session['status'] = 'active'
                    break
            
            session_manager.sessions = sessions
            session_manager.save_sessions()
            
            log_info(f'✅ Sessão válida: {result["user_info"]["first_name"]}')
        else:
            sessions = session_manager.load_sessions()
            for session in sessions:
                if session['session_name'] == session_name:
                    session['active'] = False
                    session['status'] = 'corrupted' if result.get('corrupted') else 'invalid'
                    break
            session_manager.sessions = sessions
            session_manager.save_sessions()
            log_error(f'❌ Sessão inválida: {session_name}')
        
        return jsonify(result)
        
    except Exception as e:
        log_error(f'❌ Erro ao validar sessão: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sessions/validate-all', methods=['POST'])
@login_required
def validate_all_sessions():
    """Valida todas as sessões de uma vez"""
    try:
        api_id, api_hash = get_next_api()
        if not api_id:
            return jsonify({'success': False, 'error': 'Configure a API primeiro'}), 400
        
        sessions = session_manager.load_sessions()
        total = len(sessions)
        
        if total == 0:
            return jsonify({'success': False, 'error': 'Nenhuma sessão para validar'}), 400
        
        log_info(f'🔍 Validando {total} sessões...')
        
        paths = get_user_paths()
        valid_count = 0
        invalid_count = 0
        corrupted_count = 0
        results = []
        
        for idx, session in enumerate(sessions, 1):
            session_name = session['session_name']
            session_path = os.path.join(paths['sessions_dir'], session_name)
            
            log_info(f'⏳ [{idx}/{total}] Validando: {session_name}')
            
            # Valida
            def validate():
                import asyncio
                from telethon import TelegramClient
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def check_session():
                    client = None
                    try:
                        # Tenta carregar a sessão existente
                        try:
                            temp_client = TelegramClient(session_path, api_id, api_hash)
                            await temp_client.connect()
                            
                            # Se conectou, tenta pegar info
                            me = await temp_client.get_me()
                            await temp_client.disconnect()
                            
                            if me:
                                return {
                                    'authorized': True,
                                    'user_info': {
                                        'phone': me.phone if hasattr(me, 'phone') and me.phone else session_name,
                                        'username': me.username if me.username else session_name,
                                        'first_name': me.first_name if me.first_name else session_name,
                                        'user_id': me.id
                                    }
                                }
                            else:
                                return {'authorized': False, 'error': 'Sem informações'}
                                
                        except Exception as e:
                            error_msg = str(e)
                            
                            # Se for erro de SQLite de incompatibilidade de versão, ajusta para o formato atual.
                            if 'update_state' in error_msg and 'column' in error_msg:
                                try:
                                    # Aguarda um pouco para garantir que o banco foi liberado
                                    import time
                                    time.sleep(0.5)
                                    
                                    from downgrade_sessions import downgrade_session
                                    
                                    success, adjust_msg = downgrade_session(session_path + '.session')
                                    
                                    if success:
                                        # Aguarda um pouco após ajuste
                                        time.sleep(0.5)
                                        
                                        # Tenta conectar novamente após migração
                                        temp_client = TelegramClient(session_path, api_id, api_hash)
                                        await temp_client.connect()
                                        
                                        me = await temp_client.get_me()
                                        await temp_client.disconnect()
                                        
                                        if me:
                                            return {
                                                'authorized': True,
                                                'migrated': True,
                                                'user_info': {
                                                    'phone': me.phone if hasattr(me, 'phone') and me.phone else session_name,
                                                    'username': me.username if me.username else session_name,
                                                    'first_name': me.first_name if me.first_name else session_name,
                                                    'user_id': me.id
                                                }
                                            }
                                    
                                    return {'authorized': False, 'error': f'Falha no ajuste: {adjust_msg}', 'corrupted': True}
                                    
                                except Exception as adjust_error:
                                    return {'authorized': False, 'error': f'Erro ao ajustar: {str(adjust_error)}', 'corrupted': True}
                            
                            return {'authorized': False, 'error': error_msg}
                            
                    except Exception as e:
                        return {'authorized': False, 'error': str(e)}
                
                try:
                    result = loop.run_until_complete(check_session())
                    return result
                finally:
                    loop.close()
            
            result = validate()
            
            if result.get('authorized'):
                # Atualiza informações
                user_info = result['user_info']
                session['phone'] = user_info['phone']
                session['username'] = user_info['username']
                session['first_name'] = user_info['first_name']
                session['name'] = user_info['first_name']
                session['user_id'] = user_info['user_id']
                session['active'] = True
                session['status'] = 'active'
                valid_count += 1
                
                # Mostra se foi migrada
                if result.get('migrated'):
                    log_info(f'✅ [{idx}/{total}] Migrada e Válida: {user_info["first_name"]}')
                else:
                    log_info(f'✅ [{idx}/{total}] Válida: {user_info["first_name"]}')
                
                results.append({'session': session_name, 'valid': True, 'migrated': result.get('migrated', False), 'name': user_info['first_name']})
            else:
                # Verifica se é sessão corrompida
                if result.get('corrupted'):
                    corrupted_count += 1
                    session['active'] = False
                    session['status'] = 'corrupted'
                    log_error(f'⚠️ [{idx}/{total}] Corrompida: {session_name} - {result.get("error", "Erro desconhecido")}')
                else:
                    invalid_count += 1
                    session['active'] = False
                    session['status'] = 'invalid'
                    log_error(f'❌ [{idx}/{total}] Inválida: {session_name} - {result.get("error", "Erro desconhecido")}')
                
                results.append({'session': session_name, 'valid': False, 'corrupted': result.get('corrupted', False), 'error': result.get('error', 'Erro desconhecido')})
        
        # Salva todas as atualizações
        session_manager.sessions = sessions
        session_manager.save_sessions()
        
        log_info(f'✅ Validação completa: {valid_count} válidas, {invalid_count} inválidas, {corrupted_count} corrompidas')
        
        return jsonify({
            'success': True,
            'total': total,
            'valid': valid_count,
            'invalid': invalid_count,
            'corrupted': corrupted_count,
            'results': results
        })
        
    except Exception as e:
        log_error(f'❌ Erro ao validar sessões: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/members/stats', methods=['GET'])
@login_required
def members_stats():
    paths = get_user_paths()
    all_members = load_members_from_file(paths['members_file'])
    pending = [member for member in all_members if not member.get('added', False)]
    file_added = len(all_members) - len(pending)

    automation_manager.load_config()
    tasks = automation_manager.config.get('groups', [])
    task_added_total = 0
    task_failed_total = 0
    task_target_total = 0
    task_members_total = 0
    active_tasks = 0
    completed_tasks = 0
    paused_tasks = 0
    task_breakdown = []

    for task in tasks:
        status = task.get('status')
        if status == 'active':
            active_tasks += 1
        elif status == 'completed':
            completed_tasks += 1
        elif status == 'paused':
            paused_tasks += 1

        target_members = int(task.get('target_members') or 0)
        task_target_total += target_members

        members_total = int(task.get('members_total') or 0)
        if not members_total:
            task_file = get_task_members_file(task, paths)
            members_total = len(load_members_from_file(task_file)) if task_file and os.path.exists(task_file) else 0
        task_members_total += members_total

        session_stats = task.get('session_stats') or {}
        stats_added = sum(int(item.get('added_count') or 0) for item in session_stats.values())
        stats_failed = sum(int(item.get('failed_count') or 0) for item in session_stats.values())

        results = task.get('member_results') or []
        results_added = len([item for item in results if item.get('status') == 'adicionado'])
        results_failed = len([item for item in results if item.get('status') == 'falha'])

        task_added = max(int(task.get('total_added') or 0), stats_added, results_added)
        task_failed = max(stats_failed, results_failed)
        task_pending_goal = max(0, target_members - task_added)

        task_added_total += task_added
        task_failed_total += task_failed
        task_breakdown.append({
            'id': task.get('id'),
            'group_link': task.get('group_link'),
            'status': status,
            'target_members': target_members,
            'members_total': members_total,
            'added': task_added,
            'failed': task_failed,
            'processed': task_added + task_failed,
            'pending_goal': task_pending_goal
        })

    added = task_added_total if task_added_total else file_added
    failed = task_failed_total
    processed = added + failed
    pending_goal = max(0, task_target_total - task_added_total) if task_target_total else len(pending)
    total_reference = max(len(all_members), task_members_total, task_target_total)
    success_rate = round((added / processed) * 100, 1) if processed else 0

    return jsonify({
        'total': total_reference,
        'extracted_total': len(all_members),
        'task_members_total': task_members_total,
        'target_total': task_target_total,
        'pending': pending_goal,
        'file_pending': len(pending),
        'added': added,
        'failed': failed,
        'processed': processed,
        'success_rate': success_rate,
        'tasks_total': len(tasks),
        'tasks_active': active_tasks,
        'tasks_completed': completed_tasks,
        'tasks_paused': paused_tasks,
        'task_breakdown': task_breakdown
    })

@app.route('/api/members/import', methods=['POST'])
@login_required
def import_members():
    """Importa membros de um arquivo JSON"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400
    
    if not file.filename.endswith('.json'):
        return jsonify({'success': False, 'error': 'Apenas arquivos JSON são aceitos'}), 400
    
    try:
        data = json.load(file)
        
        if 'members' not in data:
            return jsonify({'success': False, 'error': 'Arquivo inválido - falta campo "members"'}), 400
        
        members = data['members']
        
        # Log antes de salvar
        log_info(f"IMPORTAÇÃO: Recebido arquivo com {len(members)} membros do grupo {data.get('group_name', 'Desconhecido')}")
        
        # Salva os membros (SUBSTITUI o arquivo antigo)
        api_id, api_hash = get_next_api()
        paths = get_user_paths()
        extractor = MemberExtractor(api_id, api_hash, paths['data_dir'], paths['members_file'])
        extractor.save_members(members)
        
        # Também salva o export completo
        export_file = os.path.join(paths['data_dir'], 'members_export.json')
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # Verifica se salvou corretamente
        saved_members = extractor.load_members()
        log_info(f"IMPORTAÇÃO: Arquivo salvo com sucesso! {len(saved_members)} membros confirmados no arquivo")
        
        return jsonify({
            'success': True,
            'total': len(members),
            'group_name': data.get('group_name', 'Desconhecido'),
            'saved_count': len(saved_members)
        })
        
    except Exception as e:
        log_error(f"IMPORTAÇÃO: Erro ao importar membros: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/members/export', methods=['GET'])
@login_required
def export_members():
    """Baixa o arquivo de membros exportado"""
    from flask import send_file
    paths = get_user_paths()
    export_file = os.path.join(paths['data_dir'], 'members_export.json')
    
    if os.path.exists(export_file):
        return send_file(export_file, as_attachment=True, download_name='members_export.json')
    else:
        return jsonify({'error': 'Nenhum arquivo exportado encontrado'}), 404

@app.route('/api/members/batches', methods=['GET'])
@login_required
def list_batch_files():
    """Lista todos os arquivos de lotes disponíveis"""
    import glob
    from datetime import datetime
    
    # Procura por arquivos de lotes
    paths = get_user_paths()
    batch_pattern = os.path.join(paths['data_dir'], 'members_export_lote_*.json')
    index_pattern = os.path.join(paths['data_dir'], 'members_export_index_*.json')
    list_group_pattern = os.path.join(paths['data_dir'], 'members_export_grupo_*.json')
    list_index_pattern = os.path.join(paths['data_dir'], 'members_export_lista_index_*.json')
    
    batch_files = glob.glob(batch_pattern)
    index_files = glob.glob(index_pattern)
    list_group_files = glob.glob(list_group_pattern)
    list_index_files = glob.glob(list_index_pattern)
    
    # Organiza por timestamp (mais recente primeiro)
    all_files = []
    
    # Agrupa por timestamp
    timestamps = {}
    
    for file_path in batch_files:
        filename = os.path.basename(file_path)
        # Extrai timestamp do nome: members_export_lote_1_de_10_20260201_190000.json
        parts = filename.split('_')
        if len(parts) >= 7:
            timestamp = f"{parts[-2]}_{parts[-1].replace('.json', '')}"
            
            if timestamp not in timestamps:
                timestamps[timestamp] = {
                    'timestamp': timestamp,
                    'batches': [],
                    'index_file': None
                }
            
            # Extrai informações do lote
            batch_num = int(parts[3])
            total_batches = int(parts[5])
            
            file_size = os.path.getsize(file_path)
            
            timestamps[timestamp]['batches'].append({
                'filename': filename,
                'batch_number': batch_num,
                'total_batches': total_batches,
                'size': file_size,
                'size_mb': round(file_size / 1024 / 1024, 2)
            })
    
    # Adiciona arquivos índice
    for file_path in index_files:
        filename = os.path.basename(file_path)
        parts = filename.split('_')
        if len(parts) >= 4:
            timestamp = f"{parts[-2]}_{parts[-1].replace('.json', '')}"
            
            if timestamp in timestamps:
                timestamps[timestamp]['index_file'] = filename
    
    # Ordena lotes dentro de cada timestamp
    for ts_data in timestamps.values():
        ts_data['batches'].sort(key=lambda x: x['batch_number'])
    
    # Converte para lista e ordena por timestamp (mais recente primeiro)
    result = list(timestamps.values())
    result.sort(key=lambda x: x['timestamp'], reverse=True)

    list_extractions = []
    for index_path in list_index_files:
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            filename = os.path.basename(index_path)
            timestamp = filename.replace('members_export_lista_index_', '').replace('.json', '')
            files = index_data.get('files', [])
            for item in files:
                item_path = os.path.join(paths['data_dir'], item.get('filename', ''))
                item['size_mb'] = round(os.path.getsize(item_path) / 1024 / 1024, 2) if os.path.exists(item_path) else 0
            list_extractions.append({
                'timestamp': timestamp,
                'index_file': filename,
                'total_groups': index_data.get('total_groups', len(files)),
                'total_members': index_data.get('total_members', 0),
                'files': files
            })
        except Exception:
            pass

    indexed_files = {item['filename'] for extraction in list_extractions for item in extraction.get('files', [])}
    orphan_group_files = []
    for file_path in list_group_files:
        filename = os.path.basename(file_path)
        if filename in indexed_files:
            continue
        orphan_group_files.append({
            'filename': filename,
            'group_name': filename,
            'source_group_link': '',
            'total_members': 0,
            'size_mb': round(os.path.getsize(file_path) / 1024 / 1024, 2)
        })

    if orphan_group_files:
        list_extractions.append({
            'timestamp': 'arquivos_avulsos',
            'index_file': None,
            'total_groups': len(orphan_group_files),
            'total_members': 0,
            'files': orphan_group_files
        })

    list_extractions.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify({
        'success': True,
        'extractions': result,
        'list_extractions': list_extractions,
        'total': len(result)
    })

@app.route('/api/members/batch/<filename>', methods=['GET'])
@login_required
def download_batch_file(filename):
    """Baixa um arquivo de lote específico"""
    from flask import send_file
    
    # Valida o nome do arquivo (segurança)
    allowed_prefixes = (
        'members_export_lote_',
        'members_export_index_',
        'members_export_grupo_',
        'members_export_lista_index_'
    )
    if not filename.startswith(allowed_prefixes):
        return jsonify({'error': 'Arquivo inválido'}), 400
    
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Arquivo inválido'}), 400
    
    paths = get_user_paths()
    file_path = os.path.join(paths['data_dir'], filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        return jsonify({'error': 'Arquivo não encontrado'}), 404

def make_safe_export_name(value, fallback='grupo'):
    import re
    text = str(value or fallback).strip()
    text = text.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '').replace('+', 'plus_')
    text = re.sub(r'[^A-Za-z0-9_-]+', '_', text).strip('_')
    return (text or fallback)[:60]

@socketio.on('add_session')
def handle_add_session(data):
    api_id, api_hash = get_next_api()
    if not api_id:
        emit('error', {'message': 'Configure a API primeiro!'})
        return
    
    phone = data['phone']
    emit('log', {'message': f'Iniciando autenticação para {phone}...', 'type': 'info'})
    
    # Aqui você precisaria implementar um fluxo de autenticação via WebSocket
    # Por simplicidade, vou deixar um placeholder
    emit('auth_required', {'phone': phone, 'step': 'code'})

@socketio.on('extract_members')
def handle_extract_members(data):
    api_id, api_hash = get_next_api()
    if not api_id:
        emit('error', {'message': 'Configure a API primeiro!'})
        return
    
    # Verifica se pode extrair
    can_extract, message = check_session_lock('extraction')
    if not can_extract:
        emit('error', {'message': message})
        emit_extract_log(f'❌ {message}', 'error')
        return
    
    session_index = data['session_index']
    group_link = data['group_link']
    split_batches = data.get('split_batches', 0)  # Número de lotes para dividir (0 = não dividir)
    extraction_filters = data.get('filters') or {}
    
    session_index = int(session_index)
    sessions = session_manager.load_sessions()
    if session_index >= len(sessions):
        emit('error', {'message': 'Sessão inválida'})
        return
    
    session_info = sessions[session_index]
    if not session_info.get('active', True):
        emit('error', {'message': 'Sessão indisponível para extração'})
        emit_extract_log('❌ Sessão indisponível para extração', 'error')
        return
    
    # CORRIGIDO: Adiciona o caminho completo da sessão
    current_username = session.get('username')
    paths = get_user_paths()
    if paths:
        session_info['session_path'] = os.path.join(paths['sessions_dir'], session_info['session_name'])

    process_id = start_process(
        'extraction',
        'Extração de membros',
        total=1,
        username=current_username,
        detail=group_link
    )

    def extract():
        thread_context.username = current_username
        # Bloqueia extração
        set_session_lock('extraction', True, username=current_username)
        
        try:
            extractor = MemberExtractor(api_id, api_hash, paths['data_dir'], paths['members_file'])
            
            # Define callback para progresso em tempo real - USA LOGS DE EXTRAÇÃO
            def progress_callback(log_type, message):
                emit_extract_log(message, log_type)
            
            extractor.set_progress_callback(progress_callback)
            
            emit_extract_log('🚀 Iniciando extração...', 'info')
            if extraction_filters.get('private_id_mode'):
                emit_extract_log('🔐 Modo ID privado ativo: usando a sessão selecionada para resolver o grupo nos diálogos/cache.', 'info')
                emit_extract_log('ℹ️ Se a sessão não estiver no grupo privado, o Telegram não libera access_hash dos membros.', 'warning')
            update_process(process_id, username=current_username, current=0, message='Extraindo membros...', detail=group_link)
            members = extractor.extract_members(session_info, group_link, extraction_filters)
            
            # Se deve dividir em lotes
            if split_batches > 1 and len(members) > 0:
                emit_extract_log(f'📦 Dividindo {len(members)} membros em {split_batches} lotes...', 'info')
                
                # Pega o nome do grupo do último export
                export_file = os.path.join(paths['data_dir'], 'members_export.json')
                group_name = "Grupo"
                
                if os.path.exists(export_file):
                    try:
                        with open(export_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            group_name = data.get('group_name', 'Grupo')
                    except:
                        pass
                
                # Cria os arquivos divididos
                created_files, index_file = extractor.export_batches_to_files(
                    members, 
                    group_name, 
                    split_batches,
                    group_link
                )
                
                emit_extract_log(f'✅ Criados {len(created_files)} arquivos:', 'success')
                for file_info in created_files:
                    emit_extract_log(f'   📄 {file_info["filename"]} ({file_info["size"]} membros)', 'info')
                
                emit_extract_log(f'📋 Arquivo índice: {os.path.basename(index_file)}', 'info')
                emit_extract_log(f'💾 Arquivos salvos em: data/', 'success')
                
                emit_to_user('extraction_complete', {
                    'count': len(members),
                    'split': True,
                    'batches': len(created_files),
                    'files': created_files
                }, current_username)
            else:
                emit_to_user('extraction_complete', {
                    'count': len(members),
                    'split': False
                }, current_username)
            finish_process(
                process_id,
                username=current_username,
                status='completed',
                message=f'Extração concluída: {len(members)} membro(s).'
            )
        except Exception as e:
            finish_process(process_id, username=current_username, status='error', message=f'Erro na extração: {str(e)}')
            raise
        finally:
            # Libera extração
            set_session_lock('extraction', False, username=current_username)
    
    thread = threading.Thread(target=extract)
    thread.start()

@socketio.on('extract_members_list')
def handle_extract_members_list(data):
    api_id, api_hash = get_next_api()
    if not api_id:
        emit('error', {'message': 'Configure a API primeiro!'})
        return

    can_extract, message = check_session_lock('extraction')
    if not can_extract:
        emit('error', {'message': message})
        emit_extract_log(f'❌ {message}', 'error')
        return

    session_index = data.get('session_index')
    group_links = [str(link).strip() for link in data.get('group_links', []) if str(link).strip()]
    extraction_filters = data.get('filters') or {}

    if session_index is None or not group_links:
        emit('error', {'message': 'Selecione a sessão e informe os links'})
        return

    if len(group_links) > 20:
        emit('error', {'message': 'Limite máximo: 20 links por extração'})
        emit_extract_log('❌ Limite máximo: 20 links por extração em lista', 'error')
        return

    session_index = int(session_index)
    sessions = session_manager.load_sessions()
    if session_index >= len(sessions):
        emit('error', {'message': 'Sessão inválida'})
        return

    session_info = sessions[session_index]
    if not session_info.get('active', True):
        emit('error', {'message': 'Sessão indisponível para extração'})
        emit_extract_log('❌ Sessão indisponível para extração', 'error')
        return
    current_username = session.get('username')
    paths = get_user_paths()
    if paths:
        session_info['session_path'] = os.path.join(paths['sessions_dir'], session_info['session_name'])

    process_id = start_process(
        'extraction',
        'Extração por lista',
        total=len(group_links),
        username=current_username,
        detail=f'{len(group_links)} grupo(s)'
    )

    def extract_list():
        from datetime import datetime
        thread_context.username = current_username
        set_session_lock('extraction', True, username=current_username)

        created_files = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_members_file = os.path.join(paths['data_dir'], f'members_extract_list_tmp_{current_username or "user"}.json')

        try:
            emit_extract_log(f'🚀 Iniciando extração por lista: {len(group_links)} grupo(s)', 'info')
            if extraction_filters.get('private_id_mode'):
                emit_extract_log('🔐 Modo ID privado ativo para a lista: cada ID será buscado nos diálogos da sessão selecionada.', 'info')

            for idx, group_link in enumerate(group_links, 1):
                update_process(
                    process_id,
                    username=current_username,
                    current=idx - 1,
                    total=len(group_links),
                    message=f'Extraindo grupo {idx}/{len(group_links)}',
                    detail=group_link
                )
                emit_extract_log(f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'info')
                emit_extract_log(f'📌 Grupo {idx}/{len(group_links)}: {group_link}', 'info')

                extractor = MemberExtractor(api_id, api_hash, paths['data_dir'], temp_members_file)

                def progress_callback(log_type, message):
                    emit_extract_log(message, log_type)

                extractor.set_progress_callback(progress_callback)
                members = extractor.extract_members(session_info, group_link, extraction_filters)

                export_file = os.path.join(paths['data_dir'], 'members_export.json')
                group_name = f'Grupo {idx}'
                if os.path.exists(export_file):
                    try:
                        with open(export_file, 'r', encoding='utf-8') as f:
                            export_data = json.load(f)
                            group_name = export_data.get('group_name') or group_name
                    except Exception:
                        pass

                filename = f'members_export_grupo_{idx:02d}_{make_safe_export_name(group_name)}_{timestamp}.json'
                file_path = os.path.join(paths['data_dir'], filename)
                output_data = {
                    'group_name': group_name,
                    'source_group_link': group_link,
                    'extracted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'list_batch_number': idx,
                    'total_groups_in_list': len(group_links),
                    'total_members': len(members),
                    'members': members
                }

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=4, ensure_ascii=False)

                created_files.append({
                    'filename': filename,
                    'group_name': group_name,
                    'source_group_link': group_link,
                    'total_members': len(members)
                })

                emit_extract_log(f'💾 Arquivo separado criado: {filename} ({len(members)} membros)', 'success')
                update_process(
                    process_id,
                    username=current_username,
                    current=idx,
                    total=len(group_links),
                    message=f'Grupo {idx}/{len(group_links)} concluído com {len(members)} membro(s)',
                    detail=group_name
                )

            index_filename = f'members_export_lista_index_{timestamp}.json'
            index_path = os.path.join(paths['data_dir'], index_filename)
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'extracted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'total_groups': len(group_links),
                    'total_members': sum(item['total_members'] for item in created_files),
                    'files': created_files
                }, f, indent=4, ensure_ascii=False)

            emit_extract_log(f'✅ Extração por lista finalizada: {len(created_files)} arquivo(s)', 'success')
            emit_extract_log(f'📋 Índice criado: {index_filename}', 'success')
            emit_to_user('extraction_complete', {
                'count': sum(item['total_members'] for item in created_files),
                'list': True,
                'files': created_files,
                'index_file': index_filename
            }, current_username)
            finish_process(
                process_id,
                username=current_username,
                status='completed',
                message=f'Extração concluída: {sum(item["total_members"] for item in created_files)} membro(s).'
            )
        except Exception as e:
            finish_process(process_id, username=current_username, status='error', message=f'Erro na extração: {str(e)}')
            raise
        finally:
            set_session_lock('extraction', False, username=current_username)
            try:
                if os.path.exists(temp_members_file):
                    os.remove(temp_members_file)
            except Exception:
                pass

    thread = threading.Thread(target=extract_list)
    thread.start()

@socketio.on('add_members')
def handle_add_members(data):
    api_id, api_hash = get_next_api()
    if not api_id:
        emit('error', {'message': 'Configure a API primeiro!'})
        return
    
    # Verifica se pode adicionar
    can_add, message = check_session_lock('addition')
    if not can_add:
        emit('error', {'message': message})
        emit_add_log(f'❌ {message}', 'error')
        return
    
    target_group = data['target_group']
    members_per_session = data['members_per_session']
    delay_between_adds = data['delay_between_adds']
    delay_between_sessions = data['delay_between_sessions']
    operation_mode = data.get('operation_mode', 'single')
    delay_between_rounds = data.get('delay_between_rounds', 300)
    selected_indexes = data.get('selected_sessions', [])
    
    # Verifica se alguma sessão selecionada está reservada por tarefa
    blocked_sessions = automation_manager.get_reserved_task_sessions()
    blocked_selected = [idx for idx in selected_indexes if idx in blocked_sessions]
    
    if blocked_selected:
        emit('error', {'message': f'Sessões bloqueadas por tarefas existentes: {blocked_selected}'})
        emit_add_log('❌ Algumas sessões selecionadas estão reservadas em tarefas e não podem ser usadas', 'error')
        return
    
    # Pega sessões pelo índice real do config e remove as que estão em quarentena.
    all_sessions = session_manager.load_sessions(force_reload=True)
    if selected_indexes:
        sessions = [
            all_sessions[i]
            for i in selected_indexes
            if i < len(all_sessions) and not session_manager.is_session_flooded(all_sessions[i].get('session_name', ''))
        ]
    else:
        sessions = session_manager.get_active_sessions()
    
    # CORRIGIDO: Adiciona o caminho completo para cada sessão
    current_username = session.get('username')
    paths = get_user_paths()
    if paths:
        for session in sessions:
            session['session_path'] = os.path.join(paths['sessions_dir'], session['session_name'])
    
    if not sessions:
        emit('error', {'message': 'Nenhuma sessão selecionada!'})
        return
    
    if len(sessions) == 1:
        emit_add_log('⚠️  ATENÇÃO: Apenas 1 sessão selecionada!', 'warning')
        emit_add_log('💡 Selecione múltiplas sessões para revezamento automático!', 'warning')
    
    def add_process():
        thread_context.username = current_username
        # Bloqueia adição
        set_session_lock('addition', True, username=current_username)
        
        try:
            adder = MemberAdder(api_id, api_hash, paths['data_dir'], paths['members_file'])
            extractor = MemberExtractor(api_id, api_hash, paths['data_dir'], paths['members_file'])
            total_added = 0
            round_number = 1
            
            emit_to_user('log', {
                'message': f'🚀 Iniciando com {len(sessions)} sessão(ões) selecionada(s)',
                'type': 'info'
            }, current_username)
            
            # Mostra quais sessões foram selecionadas
            for idx, sess in enumerate(sessions, 1):
                emit_to_user('log', {
                    'message': f'  {idx}. {sess["first_name"]} (@{sess["username"]})',
                    'type': 'info'
                }, current_username)
            
            while True:
                emit_to_user('log', {
                    'message': f'🔄 Rodada {round_number} iniciada...',
                    'type': 'info'
                }, current_username)
                
                added_this_round = 0
                
                for i, session_info in enumerate(sessions, 1):
                    # Verifica se ainda há membros pendentes
                    pending = extractor.get_pending_members()
                    if not pending:
                        emit_to_user('log', {
                            'message': '✅ Todos os membros foram processados!',
                            'type': 'success'
                        }, current_username)
                        emit_to_user('addition_complete', {'total_added': total_added}, current_username)
                        return
                    
                    emit_to_user('log', {
                        'message': f'[{i}/{len(sessions)}] Usando {session_info["first_name"]}...',
                        'type': 'info'
                    }, current_username)
                    
                    added = adder.add_members(
                        session_info,
                        target_group,
                        members_per_session,
                        delay_between_adds
                    )
                    
                    total_added += added
                    added_this_round += added
                    
                    # Log específico sobre o resultado da sessão
                    if added == 0:
                        emit_to_user('log', {
                            'message': f'⚠️  Sessão {session_info["first_name"]} não adicionou nenhum membro (FLOOD ou erro)',
                            'type': 'warning'
                        }, current_username)
                        emit_to_user('log', {
                            'message': f'➡️  Continuando com próxima sessão...',
                            'type': 'info'
                        }, current_username)
                    else:
                        emit_to_user('log', {
                            'message': f'✅ Sessão {session_info["first_name"]} adicionou {added} membros',
                            'type': 'success'
                        }, current_username)
                    
                    emit_to_user('progress', {
                        'session': i,
                        'total_sessions': len(sessions),
                        'added': added,
                        'total_added': total_added,
                        'round': round_number
                    }, current_username)
                    
                    # Delay entre sessões
                    if i < len(sessions):
                        emit_to_user('log', {
                            'message': f'⏳ Aguardando {delay_between_sessions}s...',
                            'type': 'warning'
                        }, current_username)
                        import time
                        time.sleep(delay_between_sessions)
                
                emit_to_user('round_complete', {
                    'round': round_number,
                    'added_this_round': added_this_round
                }, current_username)
                
                # Se modo single, para aqui
                if operation_mode == 'single':
                    emit_to_user('addition_complete', {'total_added': total_added}, current_username)
                    break
                
                # Se modo loop, verifica se ainda há membros
                pending = extractor.get_pending_members()
                if not pending:
                    emit_to_user('log', {
                        'message': '✅ Todos os membros foram processados!',
                        'type': 'success'
                    }, current_username)
                    emit_to_user('addition_complete', {'total_added': total_added}, current_username)
                    break
                
                # Delay entre rodadas
                emit_to_user('log', {
                    'message': f'⏳ Aguardando {delay_between_rounds}s antes da próxima rodada...',
                    'type': 'warning'
                }, current_username)
                import time
                time.sleep(delay_between_rounds)
                
                round_number += 1
        finally:
            # Libera adição
            set_session_lock('addition', False, username=current_username)
    
    thread = threading.Thread(target=add_process)
    thread.start()

@socketio.on('stop_adding')
def handle_stop_adding():
    # Aqui você pode implementar lógica para parar o processo
    # Por enquanto, apenas emite uma mensagem
    emit('log', {'message': '⏹️ Solicitação de parada recebida', 'type': 'warning'})

# ========== ENDPOINTS DE TAREFAS ==========

@app.route('/api/tasks', methods=['GET', 'POST'])
@login_required
def manage_tasks():
    """Gerencia tarefas de múltiplos grupos"""
    automation_manager.load_config()
    if request.method == 'GET':
        import copy
        source_tasks = automation_manager.config.get('groups', [])
        changed = False
        for task in source_tasks:
            changed = normalize_task_status(task) or changed
        if changed:
            automation_manager.save_config()

        tasks = copy.deepcopy(source_tasks)
        sessions = session_manager.load_sessions()
        active_task_sessions = set(automation_manager.get_active_task_sessions())
        reserved_sessions = set(automation_manager.get_reserved_task_sessions())

        for task in tasks:
            summary = {
                'available': 0,
                'in_use': 0,
                'flood': 0,
                'invalid': 0,
                'inactive': 0,
                'missing': 0,
                'total': len(task.get('selected_sessions', []))
            }

            details = []
            for idx in task.get('selected_sessions', []):
                if idx >= len(sessions):
                    summary['missing'] += 1
                    details.append({'index': idx, 'status': 'missing', 'label': 'Não encontrada'})
                    continue

                session_info = sessions[idx]
                status = session_info.get('status', 'active')
                active = session_info.get('active', True)
                label = 'Disponível'
                bucket = 'available'

                flood_info = session_manager.get_flood_info(session_info.get('session_name', ''))
                if flood_info.get('in_flood'):
                    label = 'Flood / quarentena'
                    bucket = 'flood'
                elif idx in active_task_sessions and task.get('status') == 'active':
                    label = 'Em uso nesta tarefa'
                    bucket = 'in_use'
                elif idx in reserved_sessions and task.get('status') in ['pending', 'paused']:
                    label = 'Reservada nesta tarefa'
                    bucket = 'in_use'
                elif status in ('invalid', 'corrupted'):
                    label = 'Inválida'
                    bucket = 'invalid'
                elif not active:
                    label = 'Inativa'
                    bucket = 'inactive'

                summary[bucket] += 1
                details.append({
                    'index': idx,
                    'status': bucket,
                    'label': label,
                    'name': session_info.get('first_name') or session_info.get('session_name'),
                    'username': session_info.get('username'),
                    'phone': session_info.get('phone')
                })

            task['session_status_summary'] = summary
            task['session_status_details'] = details
            task_members_file = get_task_members_file(task)
            task['members_source_name'] = task.get('members_source_name') or os.path.basename(task_members_file or 'members.json')
            task['members_file_exists'] = bool(task_members_file and os.path.exists(task_members_file))

        return jsonify({'success': True, 'tasks': tasks})
    
    # POST - Adicionar nova tarefa
    data = request.json
    selected_sessions = data.get('selected_sessions', [])
    
    if not selected_sessions:
        return jsonify({'success': False, 'error': 'Selecione pelo menos uma sessão disponível'}), 400

    sessions = session_manager.load_sessions()
    reserved_sessions = set(automation_manager.get_reserved_task_sessions())
    available_sessions = []
    rejected_sessions = []

    for idx in selected_sessions:
        if idx >= len(sessions):
            rejected_sessions.append({'index': idx, 'reason': 'Sessão não encontrada'})
            continue

        session_info = sessions[idx]
        flood_info = session_manager.get_flood_info(session_info.get('session_name', ''))

        if idx in reserved_sessions:
            rejected_sessions.append({'index': idx, 'reason': 'Sessão já reservada em outra tarefa'})
        elif flood_info.get('in_flood'):
            rejected_sessions.append({'index': idx, 'reason': 'Sessão em flood/quarentena'})
        elif not session_info.get('active', True):
            rejected_sessions.append({'index': idx, 'reason': 'Sessão inativa'})
        elif session_info.get('status', 'active') != 'active':
            rejected_sessions.append({'index': idx, 'reason': 'Sessão inválida ou indisponível'})
        else:
            available_sessions.append(idx)

    if not available_sessions:
        return jsonify({
            'success': False,
            'error': 'Nenhuma sessão disponível para criar tarefa',
            'rejected_sessions': rejected_sessions
        }), 400

    task_queue_limit = 200
    current_tasks = len(automation_manager.config.get('groups', []))
    if current_tasks + 1 > task_queue_limit:
        available_slots = max(task_queue_limit - current_tasks, 0)
        return jsonify({
            'success': False,
            'error': f'Limite de {task_queue_limit} tarefas na fila atingido. Há {available_slots} vaga(s) livre(s).'
        }), 400

    add_delay_min, add_delay_max = normalize_delay_range(
        data.get('delay_between_adds_min', data.get('delay_between_adds', 5)),
        data.get('delay_between_adds_max', data.get('delay_between_adds', 5)),
        5
    )
    session_delay_min, session_delay_max = normalize_delay_range(
        data.get('delay_between_sessions_min', data.get('delay_between_sessions', 90)),
        data.get('delay_between_sessions_max', data.get('delay_between_sessions', 90)),
        90
    )

    task = automation_manager.add_group_task(
        data['group_link'],
        data['target_members'],
        data.get('daily_limit', 50),
        available_sessions,
        data.get('members_per_session', 25),
        delay_between_adds=data.get('delay_between_adds', add_delay_min),
        delay_between_sessions=data.get('delay_between_sessions', session_delay_min),
        delay_between_adds_min=add_delay_min,
        delay_between_adds_max=add_delay_max,
        delay_between_sessions_min=session_delay_min,
        delay_between_sessions_max=session_delay_max,
        group_interaction_enabled=data.get('group_interaction_enabled', True)
    )

    paths = get_user_paths()
    latest_file, latest_members, latest_pending = find_latest_pending_members_export(paths)
    if latest_file:
        attach_task_members_file(task, latest_file, latest_members, paths)
        automation_manager.save_config()
        log_info(
            f'📁 Tarefa vinculada automaticamente ao arquivo extraído do usuário '
            f'{session.get("username")}: {os.path.basename(latest_file)} ({len(latest_pending)} pendentes)'
        )
    
    return jsonify({
        'success': True,
        'task': task,
        'tasks': automation_manager.config.get('groups', []),
        'created': 1,
        'sessions_linked': len(available_sessions),
        'rejected_sessions': rejected_sessions,
        'message': f'Tarefa criada com {len(available_sessions)} sessão(ões) vinculada(s)'
    })

@app.route('/api/tasks/<int:task_id>', methods=['GET', 'DELETE', 'PUT'])
@login_required
def task_operations(task_id):
    """Operações em uma tarefa específica"""
    if request.method == 'GET':
        automation_manager.load_config()
        # Retorna detalhes da tarefa
        groups = automation_manager.config.get('groups', [])
        task = next((g for g in groups if g['id'] == task_id), None)
        
        if not task:
            return jsonify({'success': False, 'error': 'Tarefa não encontrada'}), 404
        
        # Adiciona informações das sessões
        sessions = session_manager.load_sessions()
        sessions_info = []
        all_sessions_info = []
        member_results = task.get('member_results', [])
        session_stats = task.get('session_stats', {})
        for idx, s in enumerate(sessions):
            flood_info = session_manager.get_flood_info(s.get('session_name', ''))
            all_sessions_info.append({
                'index': idx,
                'first_name': s.get('first_name') or s.get('session_name', f'Sessão {idx + 1}'),
                'username': s.get('username', ''),
                'phone': s.get('phone', ''),
                'session_name': s.get('session_name', ''),
                'status': s.get('status', 'active'),
                'active': s.get('active', True),
                'flood': flood_info.get('in_flood', False),
                'flood_until': flood_info.get('flood_until')
            })

        for idx in task.get('selected_sessions', []):
            if idx < len(sessions):
                s = sessions[idx]
                flood_info = session_manager.get_flood_info(s.get('session_name', ''))
                session_name = s.get('session_name', '')
                by_session = [
                    r for r in member_results
                    if r.get('session_name') == session_name
                    or (s.get('phone') and r.get('phone') == s.get('phone'))
                ]
                added_count = len([r for r in by_session if r.get('status') == 'adicionado'])
                failed_count = len([r for r in by_session if r.get('status') == 'falha'])
                last_result = by_session[-1] if by_session else {}
                saved_stats = session_stats.get(session_name, {})
                sessions_info.append({
                    'index': idx,
                    'first_name': s.get('first_name', 'Unknown'),
                    'username': s.get('username', 'unknown'),
                    'phone': s.get('phone', ''),
                    'session_name': s.get('session_name', ''),
                    'status': s.get('status', 'active'),
                    'active': s.get('active', True),
                    'flood': flood_info.get('in_flood', False),
                    'flood_until': flood_info.get('flood_until'),
                    'added_count': saved_stats.get('added_count', added_count),
                    'failed_count': saved_stats.get('failed_count', failed_count),
                    'last_status': saved_stats.get('last_status') or last_result.get('status'),
                    'last_observation': saved_stats.get('last_observation') or last_result.get('observation'),
                    'last_seen': saved_stats.get('last_seen') or last_result.get('time')
                })
        
        task['sessions_info'] = sessions_info
        task['all_sessions_info'] = all_sessions_info
        task_members_file = get_task_members_file(task)
        task['members_source_name'] = task.get('members_source_name') or os.path.basename(task_members_file or 'members.json')
        task['members_file_exists'] = bool(task_members_file and os.path.exists(task_members_file))
        task['logs'] = task.get('logs', [])[-500:]
        task['member_results'] = task.get('member_results', [])[-1000:]
        task['session_runs'] = task.get('session_runs', [])[-200:]
        return jsonify({'success': True, 'task': task})
    
    elif request.method == 'PUT':
        # Edita tarefa
        automation_manager.load_config()
        groups = automation_manager.config.get('groups', [])
        task = next((g for g in groups if g['id'] == task_id), None)
        
        if not task:
            return jsonify({'success': False, 'error': 'Tarefa não encontrada'}), 404
        
        data = request.json
        was_active = task.get('status') == 'active'
        
        # Atualiza campos permitidos
        if 'target_members' in data:
            task['target_members'] = int(data['target_members'])
        
        if 'daily_limit' in data:
            task['daily_limit'] = int(data['daily_limit'])
        
        if 'members_per_session' in data:
            task['members_per_session'] = int(data['members_per_session'])

        if 'delay_between_adds' in data:
            task['delay_between_adds'] = int(data['delay_between_adds'])

        if 'delay_between_sessions' in data:
            task['delay_between_sessions'] = int(data['delay_between_sessions'])

        if 'delay_between_adds_min' in data:
            task['delay_between_adds_min'] = int(data['delay_between_adds_min'])

        if 'delay_between_adds_max' in data:
            task['delay_between_adds_max'] = int(data['delay_between_adds_max'])

        if 'delay_between_sessions_min' in data:
            task['delay_between_sessions_min'] = int(data['delay_between_sessions_min'])

        if 'delay_between_sessions_max' in data:
            task['delay_between_sessions_max'] = int(data['delay_between_sessions_max'])

        if 'group_interaction_enabled' in data:
            task['group_interaction_enabled'] = bool(data['group_interaction_enabled'])
        
        if 'selected_sessions' in data:
            sessions = session_manager.load_sessions(force_reload=True)
            selected_sessions = []
            for value in data.get('selected_sessions') or []:
                try:
                    idx = int(value)
                except Exception:
                    continue
                if 0 <= idx < len(sessions) and idx not in selected_sessions:
                    selected_sessions.append(idx)

            if not selected_sessions:
                return jsonify({'success': False, 'error': 'Selecione ao menos uma sessão para a tarefa'}), 400

            task['selected_sessions'] = selected_sessions
        
        if 'group_link' in data:
            task['group_link'] = data['group_link']
        
        automation_manager.save_config()

        if was_active:
            append_task_log(
                task_id,
                '🔄 Configuração da tarefa atualizada. As sessões novas serão usadas no próximo ciclo.',
                'info',
                automation_manager
            )
        
        log_info(f'✏️ Tarefa #{task_id} editada com sucesso')
        
        return jsonify({'success': True, 'task': task})
    
    # DELETE - Remove tarefa
    automation_manager.load_config()
    groups = automation_manager.config.get('groups', [])
    automation_manager.config['groups'] = [g for g in groups if g['id'] != task_id]
    automation_manager.save_config()
    
    return jsonify({'success': True})

@app.route('/api/tasks/<int:task_id>/members-file', methods=['POST'])
@login_required
def update_task_members_file(task_id):
    """Troca o arquivo de membros usado por uma tarefa sem recriar a tarefa."""
    automation_manager.load_config()
    groups = automation_manager.config.get('groups', [])
    task = next((g for g in groups if g['id'] == task_id), None)

    if not task:
        return jsonify({'success': False, 'error': 'Tarefa não encontrada'}), 404

    if task.get('status') == 'active':
        task['status'] = 'paused'
        task['pause_requested_at'] = datetime.now().isoformat(timespec='seconds')
        task['pause_reason'] = 'Pausada automaticamente para trocar arquivo de membros'
        append_task_log(
            task_id,
            '⏸️ Tarefa pausada automaticamente para trocar o arquivo de membros.',
            'warning',
            automation_manager
        )

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400

    if not file.filename.lower().endswith('.json'):
        return jsonify({'success': False, 'error': 'Apenas arquivos JSON são aceitos'}), 400

    try:
        data = json.load(file)
        members = data.get('members') if isinstance(data, dict) else data

        if not isinstance(members, list):
            return jsonify({'success': False, 'error': 'Arquivo inválido: envie um JSON com campo "members" ou uma lista de membros'}), 400

        # Exportações antigas nem sempre possuem o campo ``added``.
        # Sem esse campo elas eram tratadas como se não houvesse membros.
        normalized_members = []
        for member in members:
            if isinstance(member, dict):
                item = dict(member)
                item.setdefault('added', False)
                normalized_members.append(item)
        members = normalized_members

        clean_name = secure_filename(file.filename) or 'membros.json'
        task_filename = f'task_{task_id}_members_{clean_name}'
        paths = get_user_paths()
        task_file = os.path.join(paths['data_dir'], task_filename)

        atomic_write_json(task_file, members)

        task['members_file'] = task_filename
        task['members_source_name'] = clean_name
        task['members_total'] = len(members)
        task['members_updated_at'] = datetime.now().isoformat(timespec='seconds')
        task.pop('pause_reason', None)
        task.pop('completion_note', None)

        if task.get('status') == 'completed' and task.get('total_added', 0) < task.get('target_members', 0):
            task['status'] = 'paused'

        automation_manager.save_config()

        log_info(f'📁 Arquivo de membros da tarefa #{task_id} trocado: {clean_name} ({len(members)} membros)')

        return jsonify({
            'success': True,
            'task': task,
            'total': len(members),
            'pending': sum(1 for member in members if not member.get('added', False)),
            'filename': clean_name,
            'message': f'Arquivo trocado com {len(members)} membro(s)'
        })
    except json.JSONDecodeError:
        return jsonify({'success': False, 'error': 'JSON inválido. Verifique o arquivo enviado.'}), 400
    except Exception as e:
        log_error(f'❌ Erro ao trocar arquivo de membros da tarefa #{task_id}: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/start', methods=['POST'])
@login_required
def start_task(task_id):
    """Inicia uma tarefa"""
    log_section(f'INICIANDO TAREFA #{task_id}')
    log_info(f'Recebida requisição para iniciar tarefa #{task_id}', 'START_TASK')
    
    automation_manager.load_config()
    groups = automation_manager.config.get('groups', [])
    task = next((g for g in groups if g['id'] == task_id), None)
    
    if not task:
        log_error(f'Tarefa #{task_id} não encontrada', 'START_TASK')
        return jsonify({'success': False, 'error': 'Tarefa não encontrada'}), 404

    if normalize_task_status(task):
        automation_manager.save_config()
    
    log_info(f'Tarefa encontrada: {task["group_link"]}', 'START_TASK')
    
    if task['status'] == 'active':
        log_warning(f'Tarefa já está ativa', 'START_TASK')
        return jsonify({'success': False, 'error': 'Tarefa já está ativa'}), 400
    
    # Verifica se as sessões estão disponíveis
    selected_sessions = task.get('selected_sessions', [])
    log_info(f'Sessões selecionadas: {selected_sessions}', 'START_TASK')
    
    if not selected_sessions:
        log_error(f'Nenhuma sessão selecionada', 'START_TASK')
        return jsonify({'success': False, 'error': 'Nenhuma sessão selecionada para esta tarefa'}), 400
    
    # Verifica se pode processar tarefa
    can_process, message = check_session_lock('task', task_id)
    if not can_process:
        log_warning(f'Bloqueado: {message}', 'START_TASK')
        return jsonify({'success': False, 'error': message}), 400
    
    log_info(f'Verificações OK, iniciando processamento...', 'START_TASK')
    
    # Pega informações ANTES de iniciar a thread
    current_username = session.get('username')
    user_paths = get_user_paths()
    task_session_manager = SessionManager(user_paths['sessions_dir'], user_paths['config_file'])
    task_automation_manager = AutomationManager(user_paths['data_dir'])
    
    # Atualiza status
    task['status'] = 'active'
    task.setdefault('member_results', [])
    task.setdefault('session_runs', [])
    task.setdefault('session_stats', {})
    task['current_run_started_at'] = datetime.now().isoformat(timespec='seconds')
    task.pop('pause_requested_at', None)
    task.pop('pause_reason', None)
    task['process_id'] = start_process(
        'task',
        f'Tarefa #{task_id}',
        total=int(task.get('target_members') or 0),
        username=current_username,
        detail=task.get('group_link', '')
    )
    automation_manager.save_config()
    
    # Inicia thread de processamento
    def process_task(session_manager=task_session_manager, automation_manager=task_automation_manager, current_username=current_username):
        thread_context.username = current_username
        thread_context.task_id = task_id
        thread_context.automation_manager = automation_manager
        user_socketio = UserSocketEmitter(socketio, current_username, task_id=task_id, automation_manager=automation_manager)
        print(f'\n🔄 [PROCESS TASK] Thread iniciada para tarefa #{task_id}')
        automation_manager.load_config()
        groups = automation_manager.config.get('groups', [])
        task = next((g for g in groups if g.get('id') == task_id), None)
        if not task:
            emit_task_log(f'❌ Tarefa #{task_id} não encontrada no arquivo de configuração', 'error')
            return
        process_id = task.get('process_id')
        selected_sessions = task.get('selected_sessions', [])
        
        # Carrega API do usuário diretamente (sem usar session)
        import json
        config_file = os.path.join(user_paths['data_dir'], 'config.json')
        
        if not os.path.exists(config_file):
            print(f'❌ [PROCESS TASK] Config não encontrado')
            emit_to_user('log', {'message': '❌ Configure a API primeiro!', 'type': 'error'}, current_username)
            task['status'] = 'paused'
            automation_manager.save_config()
            if process_id:
                finish_process(process_id, username=current_username, status='error', message='API não configurada')
            return
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        api_credentials = config_data.get('api_credentials', [])
        if not api_credentials:
            print(f'❌ [PROCESS TASK] API não configurada')
            emit_to_user('log', {'message': '❌ Configure a API primeiro!', 'type': 'error'}, current_username)
            task['status'] = 'paused'
            automation_manager.save_config()
            if process_id:
                finish_process(process_id, username=current_username, status='error', message='API não configurada')
            return
        
        api_id = api_credentials[0]['api_id']
        api_hash = api_credentials[0]['api_hash']
        
        print(f'✅ [PROCESS TASK] API configurada: {api_id}')
        
        # Bloqueia esta tarefa
        set_session_lock('task', True, task_id, username=current_username)
        print(f'🔒 [PROCESS TASK] Tarefa #{task_id} bloqueada')
        
        try:
            from smart_adder import SmartAdder
            from extractor import MemberExtractor
            members_file = get_task_members_file(task, user_paths)
            
            # USA SMART ADDER com aquecimento inteligente
            adder = SmartAdder(api_id, api_hash, user_paths['data_dir'], members_file)
            
            def load_task_sessions_snapshot():
                """Recarrega as sessões da tarefa para respeitar flood/quarentena em tempo real."""
                session_manager.invalidate_cache()
                all_sessions = session_manager.load_sessions(force_reload=True)
                snapshot = []
                for selected_index in selected_sessions:
                    if selected_index >= len(all_sessions):
                        continue
                    session_copy = dict(all_sessions[selected_index])
                    session_copy['session_path'] = os.path.join(user_paths['sessions_dir'], session_copy.get('session_name', ''))
                    session_copy['_task_selected_index'] = selected_index
                    snapshot.append(session_copy)
                return snapshot

            task_sessions = load_task_sessions_snapshot()

            def get_session_cooldown(session_info):
                session_name = session_info.get('session_name')
                if not session_name:
                    return None
                try:
                    floods = load_json_file(user_paths['floods_file'], {})
                    flood_until_str = floods.get(session_name) or session_info.get('flood_until')
                    if not flood_until_str:
                        return None
                    flood_until = datetime.fromisoformat(flood_until_str)
                    now = datetime.now()
                    if now >= flood_until:
                        return None
                    remaining = flood_until - now
                    return {
                        'until': flood_until,
                        'seconds': int(remaining.total_seconds())
                    }
                except Exception:
                    return None

            def get_session_unavailable_reason(session_info):
                status = str(session_info.get('status') or 'active').lower()
                if not session_info.get('active', True):
                    return 'sessão desativada no painel'
                if status in ('invalid', 'corrupted', 'disconnected', 'banned'):
                    return f'sessão indisponível: {status}'
                if status == 'flood' and not get_session_cooldown(session_info):
                    return 'sessão marcada em flood sem prazo válido'
                return None
            
            if not task_sessions:
                emit_to_user('log', {'message': f'❌ Tarefa #{task_id}: Nenhuma sessão disponível', 'type': 'error'}, current_username)
                task['status'] = 'paused'
                automation_manager.save_config()
                if process_id:
                    finish_process(process_id, username=current_username, status='error', message='Nenhuma sessão disponível')
                return
            
            emit_task_log(f'🚀 Tarefa #{task_id} iniciada: {task["group_link"]}', 'success')
            emit_task_log(f'📊 Meta: {task["target_members"]} | Limite diário: {task["daily_limit"]}', 'info')
            emit_task_log(f'👥 Usando {len(task_sessions)} sessão(ões) dedicada(s)', 'info')
            add_delay_min, add_delay_max = get_task_delay_range(task, 'delay_between_adds', 5)
            session_delay_min, session_delay_max = get_task_delay_range(task, 'delay_between_sessions', 90)
            emit_task_log(f'⏱️ Delay entre adições: {add_delay_min}-{add_delay_max}s | Entre sessões: {session_delay_min}-{session_delay_max}s', 'info')
            emit_task_log(f'📁 Arquivo de membros: {task.get("members_source_name") or os.path.basename(members_file)}', 'info')
            reaction_settings = load_reactions_data(user_paths).get('settings', {})
            disable_add_interactions = reaction_settings.get('disable_add_group_interactions', False)
            group_interaction_enabled = task.get('group_interaction_enabled', True) and not disable_add_interactions
            emit_task_log(f'💬 Interação no grupo: {"ligada" if group_interaction_enabled else "desligada"}', 'info')
            if process_id:
                update_process(
                    process_id,
                    username=current_username,
                    current=task.get('total_added', 0),
                    total=task.get('target_members', 0),
                    message='Tarefa em execução',
                    detail=task.get('group_link', '')
                )
            
            # Carrega membros
            if not members_file or not os.path.exists(members_file):
                emit_task_log('❌ Nenhum membro para adicionar. Extraia membros primeiro!', 'error')
                task['status'] = 'paused'
                automation_manager.save_config()
                if process_id:
                    finish_process(process_id, username=current_username, status='error', message='Nenhum membro para adicionar')
                return
            
            all_members = load_members_from_file(members_file)
            
            # Filtra membros não adicionados
            members = [m for m in all_members if not m.get('added', False)]
            
            if not members:
                if task['total_added'] >= task['target_members']:
                    emit_task_log('✅ Todos os membros necessários já foram adicionados!', 'success')
                    task['status'] = 'completed'
                else:
                    emit_task_log(f'⚠️ O arquivo atual não tem membros pendentes, mas ainda faltam {task["target_members"] - task["total_added"]} para a meta.', 'warning')
                    latest_file, latest_members, latest_pending = find_latest_pending_members_export(user_paths)
                    if latest_file:
                        members_file = attach_task_members_file(task, latest_file, latest_members, user_paths)
                        automation_manager.save_config()
                        adder = SmartAdder(api_id, api_hash, user_paths['data_dir'], members_file)
                        all_members = latest_members
                        members = latest_pending
                        emit_task_log(f'📁 Usei automaticamente o último arquivo extraído: {os.path.basename(latest_file)}', 'success')
                        emit_task_log(f'📋 {len(members)} membros pendentes encontrados no novo arquivo', 'info')
                    else:
                        emit_task_log('📁 Não encontrei nenhum arquivo extraído recente com membros pendentes. Troque o arquivo na edição da tarefa.', 'info')
                        task['status'] = 'paused'
                        automation_manager.save_config()
                        if process_id:
                            finish_process(process_id, username=current_username, status='completed', message='Tarefa pausada: sem membros pendentes')
                        return
            
            emit_task_log(f'📋 {len(members)} membros disponíveis para adicionar', 'info')
            
            # Cria extractor para gerenciar membros pendentes
            extractor = MemberExtractor(api_id, api_hash, user_paths['data_dir'], members_file)
            
            # Processa enquanto tarefa está ativa e não atingiu meta
            while task['status'] == 'active' and task['total_added'] < task['target_members']:
                automation_manager.load_config()
                refreshed_task = next((g for g in automation_manager.config.get('groups', []) if g.get('id') == task_id), None)
                if not refreshed_task or refreshed_task.get('status') != 'active':
                    break
                task = refreshed_task
                selected_sessions = task.get('selected_sessions', selected_sessions)
                task_sessions = load_task_sessions_snapshot()

                # Verifica limite diário
                if task['added_today'] >= task['daily_limit']:
                    emit_task_log(f'⏸️ Limite diário atingido ({task["daily_limit"]}). Aguardando reset...', 'warning')
                    
                    # Calcula quando será o próximo reset (25 horas após o último reset)
                    from datetime import datetime, timedelta
                    last_reset = datetime.fromisoformat(task['last_reset'])
                    next_reset = last_reset + timedelta(hours=25)
                    time_until_reset = (next_reset - datetime.now()).total_seconds()
                    
                    if time_until_reset > 0:
                        hours = int(time_until_reset // 3600)
                        minutes = int((time_until_reset % 3600) // 60)
                        emit_task_log(f'⏰ Próximo reset em: {hours}h {minutes}min', 'info')
                        emit_task_log(f'💤 Tarefa continua ATIVA, aguardando reset automático...', 'info')
                        emit_task_log(f'🔄 Sistema vai verificar a cada 5 minutos', 'info')
                        
                        # Aguarda em chunks de 5 minutos para poder verificar se tarefa foi pausada manualmente
                        import time
                        wait_time = min(300, time_until_reset)  # 5 minutos ou menos
                        
                        for _ in range(int(time_until_reset // wait_time) + 1):
                            if task['status'] != 'active':
                                emit_task_log(f'⏹️ Tarefa pausada manualmente', 'warning')
                                break
                            
                            # Verifica se já pode resetar
                            now = datetime.now()
                            if (now - last_reset).total_seconds() >= 25 * 3600:
                                # Reseta o contador diário
                                task['added_today'] = 0
                                task['last_reset'] = now.isoformat()
                                automation_manager.save_config()
                                
                                emit_task_log(f'🔄 Reset automático realizado!', 'success')
                                emit_task_log(f'📊 Contador diário resetado: 0/{task["daily_limit"]}', 'success')
                                emit_task_log(f'🚀 Retomando adições...', 'success')
                                break
                            
                            # Aguarda 5 minutos
                            time.sleep(wait_time)
                            
                            # Atualiza tempo restante
                            time_until_reset = (next_reset - datetime.now()).total_seconds()
                            if time_until_reset > 0:
                                hours = int(time_until_reset // 3600)
                                minutes = int((time_until_reset % 3600) // 60)
                                emit_task_log(f'⏰ Aguardando reset... Faltam {hours}h {minutes}min', 'info')
                    else:
                        # Já passou 25h, reseta agora
                        from datetime import datetime
                        task['added_today'] = 0
                        task['last_reset'] = datetime.now().isoformat()
                        automation_manager.save_config()
                        emit_task_log(f'🔄 Reset automático realizado!', 'success')
                        emit_task_log(f'📊 Contador diário resetado: 0/{task["daily_limit"]}', 'success')
                    
                    # Continua o loop (não faz break)
                    continue
                
                # Verifica se ainda há membros pendentes
                pending = extractor.get_pending_members()
                if not pending:
                    if task['total_added'] >= task['target_members']:
                        emit_task_log('✅ Todos os membros necessários foram processados!', 'success')
                        task['status'] = 'completed'
                    else:
                        emit_task_log(f'⚠️ O arquivo atual acabou, mas ainda faltam {task["target_members"] - task["total_added"]} membros para a meta.', 'warning')
                        latest_file, latest_members, latest_pending = find_latest_pending_members_export(user_paths)
                        if latest_file:
                            members_file = attach_task_members_file(task, latest_file, latest_members, user_paths)
                            automation_manager.save_config()
                            adder = SmartAdder(api_id, api_hash, user_paths['data_dir'], members_file)
                            extractor = MemberExtractor(api_id, api_hash, user_paths['data_dir'], members_file)
                            pending = latest_pending
                            emit_task_log(f'📁 Troquei automaticamente para o último arquivo extraído: {os.path.basename(latest_file)}', 'success')
                            emit_task_log(f'📋 {len(pending)} membros pendentes encontrados no novo arquivo', 'info')
                        else:
                            emit_task_log('📁 Não encontrei nenhum arquivo extraído recente com membros pendentes. Troque o arquivo na edição da tarefa.', 'info')
                            task['status'] = 'paused'
                            automation_manager.save_config()
                            break
                    if task.get('status') == 'completed':
                        automation_manager.save_config()
                        break
                
                # Calcula quantos pode adicionar hoje
                remaining_today = task['daily_limit'] - task['added_today']
                remaining_total = task['target_members'] - task['total_added']
                to_add_today = min(remaining_today, remaining_total)
                
                if to_add_today <= 0:
                    emit_task_log(f'⏸️ Nada para adicionar hoje (limite: {task["daily_limit"]}, já adicionado: {task["added_today"]})', 'warning')
                    break
                
                emit_task_log(f'🎯 Meta de hoje: adicionar {to_add_today} membros (restante do limite diário)', 'info')
                emit_task_log(f'📊 Limite diário: {task["daily_limit"]} | Já adicionado hoje: {task["added_today"]}', 'info')
                
                members_per_session = max(1, int(task.get('members_per_session') or 1))
                emit_task_log(f'🔁 Rotação ativa: até {members_per_session} membro(s) por sessão a cada rodada', 'info')
                if members_per_session == 1:
                    emit_task_log('🔄 Modo rotação 1x1: após 1 adição a próxima sessão assume.', 'info')
                emit_task_log(f'💡 {len(task_sessions)} sessão(ões) selecionada(s) serão verificadas antes de cada uso', 'info')
                
                # Processa cada sessão
                attempted_sessions_this_round = 0
                cooldowns_this_round = []
                fatal_stop_task = False
                for session_idx, session_info in enumerate(task_sessions, 1):
                    if task['status'] != 'active':
                        break

                    cooldown = get_session_cooldown(session_info)
                    if cooldown:
                        cooldowns_this_round.append(cooldown)
                        minutes = max(1, cooldown['seconds'] // 60)
                        emit_task_log(
                            f'⏳ Sessão {session_info.get("first_name") or session_info.get("session_name")} em cooldown por flood. Libera em ~{minutes} min.',
                            'warning'
                        )
                        continue

                    unavailable_reason = get_session_unavailable_reason(session_info)
                    if unavailable_reason:
                        emit_task_log(
                            f'⏭️ Sessão {session_info.get("first_name") or session_info.get("session_name")} pulada: {unavailable_reason}.',
                            'warning'
                        )
                        continue

                    attempted_sessions_this_round += 1
                    
                    # Verifica se atingiu limite diário ANTES de processar
                    if task['added_today'] >= task['daily_limit']:
                        emit_task_log(f'🛑 Limite diário atingido! ({task["added_today"]}/{task["daily_limit"]})', 'warning')
                        emit_task_log(f'💤 Aguardando reset automático (tarefa continua ativa)...', 'info')
                        # NÃO pausa a tarefa, apenas sai do loop de sessões
                        # O loop principal vai aguardar o reset
                        break
                    
                    # Verifica se ainda há membros pendentes
                    pending = extractor.get_pending_members()
                    if not pending:
                        if task['total_added'] >= task['target_members']:
                            emit_task_log('✅ Todos os membros necessários foram processados!', 'success')
                            task['status'] = 'completed'
                        else:
                            emit_task_log(f'⚠️ O arquivo atual acabou, mas ainda faltam {task["target_members"] - task["total_added"]} membros para a meta.', 'warning')
                            latest_file, latest_members, latest_pending = find_latest_pending_members_export(user_paths)
                            if latest_file:
                                members_file = attach_task_members_file(task, latest_file, latest_members, user_paths)
                                automation_manager.save_config()
                                adder = SmartAdder(api_id, api_hash, user_paths['data_dir'], members_file)
                                extractor = MemberExtractor(api_id, api_hash, user_paths['data_dir'], members_file)
                                pending = latest_pending
                                emit_task_log(f'📁 Troquei automaticamente para o último arquivo extraído: {os.path.basename(latest_file)}', 'success')
                                emit_task_log(f'📋 {len(pending)} membros pendentes encontrados no novo arquivo', 'info')
                            else:
                                task['status'] = 'paused'
                                automation_manager.save_config()
                                break
                        if task.get('status') == 'completed':
                            automation_manager.save_config()
                            break
                    
                    # CALCULA QUANTOS MEMBROS PODE ADICIONAR (respeitando limite diário)
                    remaining_today = task['daily_limit'] - task['added_today']
                    members_to_add_now = min(members_per_session, remaining_today)
                    
                    if members_to_add_now <= 0:
                        emit_task_log(f'🛑 Limite diário atingido! ({task["added_today"]}/{task["daily_limit"]})', 'warning')
                        emit_task_log(f'⏸️ Tarefa pausada até o próximo dia', 'warning')
                        task['status'] = 'paused'
                        automation_manager.save_config()
                        break
                    
                    emit_task_log(f'👤 Sessão {session_idx}/{len(task_sessions)}: {session_info["first_name"]}', 'info')
                    emit_task_log(f'📊 Limite restante hoje: {remaining_today} membros', 'info')
                    emit_task_log(f'🎯 Esta sessão vai adicionar: {members_to_add_now} membros', 'info')
                    
                    # LOG DIRETO NO TERMINAL
                    import sys
                    sys.stdout.write(f'\n⚡ [APP.PY] ANTES DE CHAMAR add_members()\n')
                    sys.stdout.write(f'⚡ [APP.PY] Sessão: {session_info["first_name"]}\n')
                    sys.stdout.write(f'⚡ [APP.PY] Grupo: {task["group_link"]}\n')
                    sys.stdout.write(f'⚡ [APP.PY] Membros: {members_to_add_now} (limite restante: {remaining_today})\n')
                    sys.stdout.flush()
                    
                    # EMITE PROGRESSO ANTES (para mostrar que está processando)
                    emit_to_user('task_progress', {
                        'task_id': task_id,
                        'added_today': task['added_today'],
                        'total_added': task['total_added'],
                        'target_members': task['target_members'],
                        'daily_limit': task['daily_limit'],
                        'status': 'processing'
                    }, current_username)
                    
                    # USA SMART ADDER com aquecimento inteligente
                    emit_task_log(f'🔥 Iniciando adição inteligente com aquecimento...', 'info')
                    add_delay_min, add_delay_max = get_task_delay_range(task, 'delay_between_adds', 5)
                    session_delay_min, session_delay_max = get_task_delay_range(task, 'delay_between_sessions', 90)
                    emit_task_log(
                        f'⏱️ Regra atual de delay: adições {add_delay_min}-{add_delay_max}s | sessões {session_delay_min}-{session_delay_max}s',
                        'info'
                    )
                    
                    # Prepara dados da tarefa para atualização em tempo real
                    task_data = {
                        'task_id': task_id,
                        'added_today': task['added_today'],
                        'total_added': task['total_added'],
                        'target_members': task['target_members'],
                        'daily_limit': task['daily_limit'],
                        'automation_manager': automation_manager,  # Passa o automation_manager correto
                        'force_rotate_after_each_add': True,
                        'member_results': []
                    }
                    
                    session_added = adder.add_members_smart(
                        session_info,
                        task['group_link'],
                        members_to_add_now,  # USA O VALOR CALCULADO (respeitando limite)
                        task['daily_limit'],  # Passa o limite diário do grupo
                        socketio=user_socketio,  # Emite apenas para o usuário dono da tarefa
                        task_data=task_data,  # Passa dados da tarefa para atualização em tempo real
                        delay_between_adds=add_delay_min,
                        delay_between_adds_max=add_delay_max,
                        group_interaction_enabled=group_interaction_enabled
                    )
                    
                    print(f'\n🔵🔵🔵 [APP.PY] RECEBEU RETORNO 🔵🔵🔵')
                    print(f'session_added = {session_added}')
                    print(f'Tipo: {type(session_added)}')
                    print(f'🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵\n')
                    
                    sys.stdout.write(f'\n⚡ [APP.PY] DEPOIS DE CHAMAR add_members()\n')
                    sys.stdout.write(f'⚡ [APP.PY] Resultado: {session_added}\n')
                    sys.stdout.write(f'⚡ [APP.PY] Tipo: {type(session_added)}\n')
                    sys.stdout.flush()
                    
                    emit_task_log(f'📊 add_members retornou: {session_added}', 'info')
                    
                    # FORÇA CONVERSÃO PARA INT (caso esteja vindo como string ou None)
                    try:
                        session_added = int(session_added) if session_added else 0
                    except:
                        session_added = 0

                    last_result = adder.get_last_result()
                    run_entry = {
                        'time': __import__('datetime').datetime.now().isoformat(timespec='seconds'),
                        'session_name': session_info.get('session_name', ''),
                        'account': session_info.get('first_name') or session_info.get('phone') or session_info.get('session_name', ''),
                        'username': session_info.get('username', ''),
                        'phone': session_info.get('phone', ''),
                        'added': session_added,
                        'status': last_result.get('status') or ('success' if session_added > 0 else 'zero_added'),
                        'reason': last_result.get('reason') or ''
                    }
                    
                    emit_task_log(f'📊 Convertido para: {session_added}', 'info')
                    
                    # Atualiza contadores com os valores já atualizados pelo smart_adder
                    task['added_today'] = task_data['added_today']
                    task['total_added'] = task_data['total_added']
                    saved_task = save_task_runtime_details(
                        task_id,
                        automation_manager,
                        counters={
                            'added_today': task['added_today'],
                            'total_added': task['total_added']
                        },
                        session_run=run_entry,
                        member_results=[] if task_data.get('member_results_persisted') else task_data.get('member_results', [])
                    )
                    if saved_task:
                        task = saved_task

                    if process_id:
                        update_process(
                            process_id,
                            username=current_username,
                            current=task.get('total_added', 0),
                            total=task.get('target_members', 0),
                            message=f'{task.get("total_added", 0)}/{task.get("target_members", 0)} membros adicionados',
                            detail=task.get('group_link', '')
                        )

                    if is_task_fatal_group_error(last_result):
                        paused_task, pause_reason = pause_task_after_fatal_group_error(task_id, automation_manager, last_result)
                        if paused_task:
                            task = paused_task
                        emit_task_log(
                            f'🛑 Grupo destino caiu/ficou inacessível. Tarefa pausada imediatamente. {pause_reason}',
                            'error'
                        )
                        fatal_stop_task = True
                        break

                    if task.get('status') != 'active':
                        emit_task_log('⏹️ Tarefa pausada. Parando antes de usar outra sessão.', 'warning')
                        break
                    
                    # DEBUG: Print direto no console
                    print(f'\n�🔥🔥 [DEBUG TASK UPDATE] 🔥🔥🔥')
                    print(f'Task ID: {task_id}')
                    print(f'session_added: {session_added}')
                    print(f'added_today: {task["added_today"]}')
                    print(f'total_added: {task["total_added"]}')
                    print(f'🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥\n')
                    
                    emit_task_log(f'📈 Atualizado: added_today={task["added_today"]}, total_added={task["total_added"]}', 'info')
                    emit_task_log(f'🔔 Emitindo evento task_progress para task_id={task_id}', 'info')
                    
                    # VERIFICA SE ATINGIU O LIMITE DIÁRIO APÓS ADICIONAR
                    if task['added_today'] >= task['daily_limit']:
                        emit_task_log(f'🎉 Limite diário atingido! ({task["added_today"]}/{task["daily_limit"]})', 'success')
                        emit_task_log(f'💤 Aguardando reset automático (tarefa continua ativa)...', 'info')
                        # NÃO pausa a tarefa, apenas sai do loop de sessões
                        # O loop principal vai aguardar o reset
                        break
                    
                    # EMITE EVENTO PARA ATUALIZAR INTERFACE EM TEMPO REAL
                    emit_to_user('task_progress', {
                        'task_id': task_id,
                        'added_today': task['added_today'],
                        'total_added': task['total_added'],
                        'target_members': task['target_members'],
                        'daily_limit': task['daily_limit'],
                        'status': 'updated'
                    }, current_username)
                    
                    print(f'✅ Evento task_progress emitido para task_id={task_id}')
                    print(f'   Dados: added_today={task["added_today"]}, total_added={task["total_added"]}\n')
                    
                    # Salva config DEPOIS de emitir (para não bloquear)
                    try:
                        automation_manager.save_config()
                        emit_task_log(f'💾 Configuração salva', 'info')
                    except Exception as save_error:
                        emit_task_log(f'⚠️ Erro ao salvar config: {save_error}', 'warning')
                    
                    if session_added > 0:
                        emit_task_log(f'✅ Sessão adicionou {session_added} membros', 'success')
                        
                        # Verifica se atingiu limite diário (não dá delay se atingiu)
                        if task['added_today'] >= task['daily_limit']:
                            emit_task_log(f'🛑 Limite diário atingido! Não processando mais sessões.', 'warning')
                        elif session_idx < len(task_sessions):
                            # Delay entre sessões SOMENTE se adicionou alguém E não atingiu limite
                            delay_between_sessions = random.randint(max(1, session_delay_min), max(1, session_delay_max))
                            emit_task_log(
                                f'⏳ Aguardando {delay_between_sessions}s antes da próxima sessão (regra {session_delay_min}-{session_delay_max}s)...',
                                'info'
                            )
                            import time
                            slept = 0
                            while slept < delay_between_sessions:
                                chunk = min(5, delay_between_sessions - slept)
                                time.sleep(chunk)
                                slept += chunk

                                automation_manager.load_config()
                                refreshed_task = next((g for g in automation_manager.config.get('groups', []) if g.get('id') == task_id), None)
                                if not refreshed_task or refreshed_task.get('status') != 'active':
                                    task = refreshed_task or task
                                    emit_task_log('⏹️ Tarefa pausada durante o delay entre sessões.', 'warning')
                                    break
                    else:
                        reason = last_result.get('reason') or 'Sem detalhe registrado'
                        status = last_result.get('status') or 'desconhecido'
                        emit_task_log(f'⚠️ Sessão não adicionou nenhum membro', 'warning')
                        emit_task_log(f'🔎 Motivo real: {reason} [{status}]', 'warning')
                        if status in ('flood_wait', 'peer_flood', 'auth_key_duplicated', 'disconnected'):
                            emit_task_log('⏭️ Sessão bloqueada/cooldown registrado; continuando só se houver outra sessão liberada.', 'warning')
                        else:
                            emit_task_log(f'⏭️ Pulando delay, continuando com próxima sessão...', 'info')

                if fatal_stop_task:
                    break

                if attempted_sessions_this_round == 0 and task.get('status') == 'active':
                    valid_cooldowns = [c for c in cooldowns_this_round if c and c.get('seconds', 0) > 0]
                    if not valid_cooldowns:
                        emit_task_log('⚠️ Nenhuma sessão disponível agora. Aguardando 60s antes de verificar novamente.', 'warning')
                        wait_seconds = 60
                    else:
                        wait_seconds = max(1, min(c['seconds'] for c in valid_cooldowns))
                        wait_minutes = max(1, wait_seconds // 60)
                        emit_task_log(
                            f'⏳ Todas as sessões selecionadas estão em flood/cooldown. Vou aguardar ~{wait_minutes} min e tentar de novo só quando liberar.',
                            'warning'
                        )

                    import time
                    slept = 0
                    while slept < wait_seconds:
                        chunk = min(60, wait_seconds - slept)
                        time.sleep(chunk)
                        slept += chunk

                        automation_manager.load_config()
                        refreshed_task = next((g for g in automation_manager.config.get('groups', []) if g.get('id') == task_id), None)
                        if not refreshed_task or refreshed_task.get('status') != 'active':
                            task = refreshed_task or task
                            break
                        task = refreshed_task

                    continue
                
                emit_task_log(f'📊 Progresso: {task["total_added"]}/{task["target_members"]} ({task["added_today"]} hoje)', 'success')
                
                # Verifica se atingiu limite diário (vai aguardar no próximo loop)
                if task['added_today'] >= task['daily_limit']:
                    emit_task_log(f'⏰ Limite diário atingido ({task["added_today"]}/{task["daily_limit"]})', 'warning')
                    emit_task_log(f'💤 Tarefa continua ATIVA, aguardando reset automático...', 'info')
                    # NÃO faz break, deixa o loop principal tratar
                
                # Verifica se completou a meta total
                if task['total_added'] >= task['target_members']:
                    task['status'] = 'completed'
                    automation_manager.save_config()
                    emit_task_log(f'🎉 Tarefa #{task_id} COMPLETA! {task["total_added"]} membros adicionados!', 'success')
                    break
            
        except Exception as e:
            emit_task_log(f'❌ Erro na tarefa #{task_id}: {str(e)}', 'error')
            task['status'] = 'paused'
            automation_manager.save_config()
            if 'process_id' in locals() and process_id:
                finish_process(process_id, username=current_username, status='error', message=f'Erro na tarefa: {str(e)}')
                process_id = None
        finally:
            if 'process_id' in locals() and process_id:
                try:
                    automation_manager.load_config()
                    final_task = next((g for g in automation_manager.config.get('groups', []) if g.get('id') == task_id), task)
                    final_status = final_task.get('status')
                    if final_status == 'completed':
                        finish_process(
                            process_id,
                            username=current_username,
                            status='completed',
                            message=f'Tarefa concluída: {final_task.get("total_added", 0)} membros adicionados'
                        )
                    elif final_status == 'paused':
                        reason = final_task.get('pause_reason') or 'Tarefa pausada'
                        finish_process(process_id, username=current_username, status='completed', message=reason)
                except Exception as process_error:
                    log_warning(f'Não foi possível finalizar processo da tarefa #{task_id}: {process_error}', 'PROCESS')
            # Libera tarefa
            set_session_lock('task', False, task_id, username=current_username)
            thread_context.task_id = None
            thread_context.automation_manager = None
            print(f'🔓 [PROCESS TASK] Tarefa #{task_id} desbloqueada')
    
    thread = threading.Thread(target=process_task)
    thread.daemon = True
    thread.start()
    
    print(f'✅ [START TASK] Thread iniciada com sucesso!')
    print(f'📤 [START TASK] Retornando sucesso para o cliente\n')
    
    return jsonify({'success': True, 'message': 'Tarefa iniciada'})

@app.route('/api/tasks/<int:task_id>/pause', methods=['POST'])
@login_required
def pause_task(task_id):
    """Pausa uma tarefa"""
    automation_manager.load_config()
    groups = automation_manager.config.get('groups', [])
    task = next((g for g in groups if g['id'] == task_id), None)
    
    if not task:
        return jsonify({'success': False, 'error': 'Tarefa não encontrada'}), 404
    
    if task['status'] != 'active':
        task['status'] = 'paused'
        task['pause_requested_at'] = datetime.now().isoformat(timespec='seconds')
        task['pause_reason'] = 'Pausada manualmente'
        automation_manager.save_config()
        if task.get('process_id'):
            finish_process(task.get('process_id'), username=session.get('username'), status='completed', message='Tarefa pausada manualmente')
        return jsonify({'success': True, 'message': 'Tarefa já estava pausada'})
    
    # Atualiza status
    task['status'] = 'paused'
    task['pause_requested_at'] = datetime.now().isoformat(timespec='seconds')
    task['pause_reason'] = 'Pausada manualmente'
    automation_manager.save_config()
    if task.get('process_id'):
        finish_process(task.get('process_id'), username=session.get('username'), status='completed', message='Tarefa pausada manualmente')
    
    return jsonify({'success': True, 'message': 'Tarefa pausada'})

@app.route('/api/tasks/blocked-sessions', methods=['GET'])
@login_required
def get_blocked_sessions():
    """Retorna sessões em uso ou reservadas por tarefas."""
    automation_manager.load_config()
    blocked = automation_manager.get_active_task_sessions()
    reserved = automation_manager.get_reserved_task_sessions()
    session_task_map = {}
    for task in automation_manager.config.get('groups', []):
        task_status = task.get('status', 'pending')
        if task_status not in ['pending', 'active', 'paused']:
            continue
        for index in task.get('selected_sessions', []):
            session_task_map[str(index)] = {
                'task_id': task.get('id'),
                'status': task_status,
                'group_link': task.get('group_link', '')
            }
    return jsonify({
        'success': True,
        'blocked_sessions': blocked,
        'reserved_sessions': reserved,
        'session_task_map': session_task_map
    })

# ========== ENDPOINTS DE REAÇÕES MANUAIS ==========

@app.route('/api/reactions', methods=['GET'])
@login_required
def get_reactions():
    data = load_reactions_data()
    session_manager.invalidate_cache()
    sessions = session_manager.load_sessions(force_reload=True)
    available_sessions = []
    reserved_sessions = set(automation_manager.get_reserved_task_sessions())
    username = session.get('username')
    paths = get_user_paths()
    continuous_task = data.get('continuous_task', {})

    if continuous_task.get('enabled') and not reaction_monitors.get(username, {}).get('running'):
        try:
            start_reaction_monitor_for_user(
                username,
                paths,
                [int(index) for index in continuous_task.get('session_indexes', [])],
                continuous_task.get('post_links') or [continuous_task.get('post_link', '')],
                continuous_task.get('reactions', []),
                max(15, min(int(continuous_task.get('poll_seconds') or 15), 300)),
                continuous_task.get('started_at')
            )
        except Exception as e:
            continuous_task['enabled'] = False
            continuous_task['last_error'] = str(e)
            save_reactions_data(data, paths)

    monitor = reaction_monitors.get(username, {})

    for index, session_info in enumerate(sessions):
        flood_info = session_manager.get_flood_info(session_info.get('session_name', ''))
        if flood_info.get('in_flood'):
            continue
        if not session_info.get('active', True):
            continue
        if session_info.get('status', 'active') != 'active':
            continue

        available_sessions.append({
            'index': index,
            'session_name': session_info.get('session_name'),
            'first_name': session_info.get('first_name') or session_info.get('session_name'),
            'username': session_info.get('username'),
            'phone': session_info.get('phone'),
            'reserved': index in reserved_sessions
        })

    return jsonify({
        'success': True,
        'queue': data.get('queue', []),
        'history': data.get('history', []),
        'settings': data.get('settings', {}),
        'continuous_task': data.get('continuous_task', {}),
        'monitor_running': bool(monitor.get('running')),
        'monitor_started_at': monitor.get('started_at'),
        'available_sessions': available_sessions
    })

@app.route('/api/reactions/queue', methods=['POST'])
@login_required
def add_reaction_queue_item():
    payload = request.json or {}
    session_indexes = payload.get('session_indexes')
    if session_indexes is None:
        session_indexes = [payload.get('session_index')]
    elif isinstance(session_indexes, (str, int)):
        session_indexes = [session_indexes]

    try:
        session_indexes = [int(index) for index in session_indexes if index is not None and str(index).strip() != '']
    except Exception:
        return jsonify({'success': False, 'error': 'Sessões inválidas'}), 400

    session_indexes = list(dict.fromkeys(session_indexes))
    post_links = normalize_reaction_links(payload)
    reactions = payload.get('reactions')
    if reactions is None:
        reactions = [payload.get('reaction')]
    elif isinstance(reactions, str):
        reactions = [reactions]
    reactions = [
        str(reaction).strip()
        for reaction in reactions
        if str(reaction or '').strip()
    ]
    reactions = reactions[:12]

    if not session_indexes or not post_links or not reactions:
        return jsonify({'success': False, 'error': 'Selecione sessão(ões), ao menos um link/canal e ao menos uma reação'}), 400

    session_manager.invalidate_cache()
    sessions = session_manager.load_sessions(force_reload=True)
    available_sessions = []
    rejected_sessions = []
    for session_index in session_indexes:
        if session_index < 0 or session_index >= len(sessions):
            rejected_sessions.append({'index': session_index, 'reason': 'Sessão não encontrada'})
            continue

        session_info = sessions[session_index]
        flood_info = session_manager.get_flood_info(session_info.get('session_name', ''))
        if flood_info.get('in_flood') or not session_info.get('active', True) or session_info.get('status', 'active') != 'active':
            rejected_sessions.append({'index': session_index, 'reason': 'Sessão indisponível'})
            continue

        available_sessions.append((session_index, session_info))

    if not available_sessions:
        return jsonify({'success': False, 'error': 'Apenas sessões disponíveis podem entrar na fila'}), 400

    data = load_reactions_data()
    created_at = __import__('datetime').datetime.now().isoformat(timespec='seconds')
    base_id = int(__import__('time').time() * 1000)
    items = []
    offset = 0
    last_reacted = data.setdefault('reacted_messages', {})

    parsed_links = []
    for post_link in post_links:
        try:
            parsed_post_link = _parse_telegram_post_link(post_link)
        except Exception as e:
            return jsonify({'success': False, 'error': f'{post_link}: {str(e)}'}), 400
        target_key = str(parsed_post_link.get('private_channel_id') or parsed_post_link.get('peer') or parsed_post_link.get('invite_hash') or post_link).lower()
        parsed_links.append((post_link, target_key))

    def session_sort_key(target_key):
        def sort_key(session_tuple):
            _, session_info = session_tuple
            session_name = session_info.get('session_name')
            return 1 if f'{session_name}|{target_key}' in last_reacted else 0
        return sort_key

    for link_position, (post_link, target_key) in enumerate(parsed_links):
        sorted_sessions = sorted(available_sessions, key=session_sort_key(target_key))
        for position, (session_index, session_info) in enumerate(sorted_sessions):
            reaction = reactions[(position + link_position) % len(reactions)]
            item = {
                'id': base_id + offset,
                'status': 'pending',
                'session_index': int(session_index),
                'session_name': session_info.get('session_name'),
                'session_label': session_info.get('first_name') or session_info.get('username') or session_info.get('session_name'),
                'post_link': post_link,
                'reaction': reaction,
                'created_at': created_at
            }
            items.append(item)
            offset += 1

    data['queue'].extend(items)
    save_reactions_data(data)
    return jsonify({
        'success': True,
        'items': items,
        'item': items[0],
        'count': len(items),
        'targets_count': len(parsed_links),
        'rejected_sessions': rejected_sessions
    })

@app.route('/api/reactions/queue/clear', methods=['POST'])
@login_required
def clear_reaction_queue():
    data = load_reactions_data()
    removed_count = len(data.get('queue', []))
    data['queue'] = []
    save_reactions_data(data)
    emit_to_user('reaction_progress', {
        'id': 'queue-clear',
        'status': 'reacted',
        'reaction': 'OK',
        'post_link': '',
        'session_label': 'Sistema',
        'result': f'{removed_count} item(ns) pendente(s) removido(s) da fila',
        'time': __import__('datetime').datetime.now().strftime('%H:%M:%S')
    })
    return jsonify({'success': True, 'removed_count': removed_count})

def _parse_telegram_post_link(post_link):
    import re

    link = (post_link or '').strip()
    link = re.sub(r'^https?://', '', link, flags=re.IGNORECASE)
    link = link.split('?', 1)[0].split('#', 1)[0].strip('/')

    if link.startswith('@'):
        link = link[1:]
    elif link.lower().startswith('t.me/'):
        link = link[5:]
    elif link.lower().startswith('telegram.me/'):
        link = link[12:]

    parts = [part for part in link.split('/') if part]
    if len(parts) < 1:
        raise ValueError('Link inválido. Use https://t.me/canal, https://t.me/grupo, @usuario_do_chat ou https://t.me/+convite')

    if parts[0] == 's' and len(parts) >= 3:
        parts = parts[1:]

    if parts[0].startswith('+'):
        return {'invite_hash': parts[0][1:]}

    if parts[0].lower() == 'joinchat' and len(parts) >= 2:
        return {'invite_hash': parts[1]}

    if parts[0] == 'c':
        if len(parts) < 3:
            raise ValueError('Link privado inválido. Use https://t.me/c/id/123')
        return {'private_channel_id': int(parts[1]), 'message_id': int(parts[2])}

    parsed = {'peer': parts[0]}
    if len(parts) >= 2:
        parsed['message_id'] = int(parts[1])
    return parsed

def _send_telegram_reaction(item, reactions_data=None, paths=None, api_credentials=None):
    import asyncio
    from telethon import TelegramClient
    from telethon.tl.functions.messages import SendReactionRequest
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
    from telethon.tl.functions.contacts import ResolveUsernameRequest
    from telethon.tl.types import InputPeerChannel, PeerChannel, ReactionEmoji
    from telethon.errors import UserAlreadyParticipantError, UsernameInvalidError, UsernameNotOccupiedError

    if api_credentials:
        api_id = api_credentials[0].get('api_id')
        api_hash = api_credentials[0].get('api_hash')
    else:
        api_id, api_hash = get_next_api()
    if not api_id:
        return {'success': False, 'error': 'API não configurada'}

    paths = paths or get_user_paths()
    session_name = item.get('session_name')
    if not paths or not session_name:
        return {'success': False, 'error': 'Sessão inválida'}

    session_path = os.path.join(paths['sessions_dir'], session_name)
    parsed_link = _parse_telegram_post_link(item.get('post_link'))
    reactions_data = reactions_data if reactions_data is not None else load_reactions_data()
    target_key = str(parsed_link.get('private_channel_id') or parsed_link.get('peer') or parsed_link.get('invite_hash') or item.get('post_link')).lower()

    def cache_entity(entity):
        entity_id = getattr(entity, 'id', None)
        access_hash = getattr(entity, 'access_hash', None)
        if entity_id and access_hash:
            reactions_data.setdefault('target_cache', {})[target_key] = {
                'id': int(entity_id),
                'access_hash': int(access_hash)
            }

    async def resolve_cached_peer(client):
        cached = reactions_data.setdefault('target_cache', {}).get(target_key)
        if not cached:
            return None

        try:
            return await client.get_input_entity(InputPeerChannel(
                int(cached['id']),
                int(cached['access_hash'])
            ))
        except Exception:
            return None

    async def resolve_reaction_peer(client):
        if 'private_channel_id' in parsed_link:
            return await client.get_input_entity(PeerChannel(parsed_link['private_channel_id']))

        if 'invite_hash' in parsed_link:
            invite_hash = parsed_link['invite_hash']
            try:
                invite_info = await client(CheckChatInviteRequest(invite_hash))
                if hasattr(invite_info, 'chat') and invite_info.chat:
                    cache_entity(invite_info.chat)
                    return await client.get_input_entity(invite_info.chat)
            except Exception:
                pass

            try:
                updates = await client(ImportChatInviteRequest(invite_hash))
                if getattr(updates, 'chats', None):
                    cache_entity(updates.chats[0])
                    return await client.get_input_entity(updates.chats[0])
            except UserAlreadyParticipantError:
                invite_info = await client(CheckChatInviteRequest(invite_hash))
                if hasattr(invite_info, 'chat') and invite_info.chat:
                    cache_entity(invite_info.chat)
                    return await client.get_input_entity(invite_info.chat)
                raise ValueError('A sessão já participa, mas não consegui resolver o chat pelo convite.')
            except Exception as e:
                raise ValueError(f'A sessão não conseguiu entrar pelo link de convite do chat. Erro: {str(e)}')

            raise ValueError('Convite aceito, mas não consegui identificar o chat.')

        channel_username = str(parsed_link.get('peer', '')).strip().lstrip('@')
        if not channel_username:
            raise ValueError('Canal/grupo/chat inválido no link informado')

        channel_ref = f'@{channel_username}'

        entity = None
        resolve_errors = []
        for candidate in (channel_ref, channel_username, f'https://t.me/{channel_username}'):
            try:
                entity = await client.get_entity(candidate)
                break
            except Exception as e:
                resolve_errors.append(str(e))

        if entity is None:
            try:
                resolved = await client(ResolveUsernameRequest(channel_username))
                if getattr(resolved, 'chats', None):
                    entity = resolved.chats[0]
                elif getattr(resolved, 'users', None):
                    entity = resolved.users[0]
            except (UsernameInvalidError, UsernameNotOccupiedError):
                cached_peer = await resolve_cached_peer(client)
                if cached_peer:
                    return cached_peer
                raise ValueError(f'{channel_ref} não encontrado nessa sessão. Se outra sessão já acessou, tente executar de novo para usar o cache do destino.')
            except Exception as e:
                resolve_errors.append(str(e))

        if entity is None:
            cached_peer = await resolve_cached_peer(client)
            if cached_peer:
                return cached_peer
            last_error = resolve_errors[-1] if resolve_errors else 'sem detalhe do Telegram'
            raise ValueError(f'Não consegui localizar {channel_ref} como público. Erro do Telegram: {last_error}')

        try:
            await client(JoinChannelRequest(entity))
        except UserAlreadyParticipantError:
            pass
        except Exception:
            # Alguns canais não permitem entrada via API ou a conta já tem acesso indireto.
            pass

        cache_entity(entity)
        return await client.get_input_entity(entity)

    async def react():
        client = TelegramClient(session_path, api_id, api_hash)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                return {'success': False, 'error': 'Sessão não autorizada'}

            peer = await resolve_reaction_peer(client)

            message_id = parsed_link.get('message_id')
            if not message_id:
                latest_message = await client.get_messages(peer, limit=1)
                if not latest_message:
                    return {'success': False, 'error': 'Nenhuma mensagem encontrada nesse canal/grupo/chat'}
                message_id = latest_message[0].id

            channel_key = target_key
            reaction_key = f'{session_name}|{channel_key}'
            reacted_messages = reactions_data.setdefault('reacted_messages', {})
            if str(reacted_messages.get(reaction_key)) == str(message_id):
                return {
                    'success': True,
                    'skipped': True,
                    'message': f'Essa sessão já reagiu na mensagem {message_id}. Aguardando mensagem nova.',
                    'message_id': message_id,
                    'channel_key': channel_key
                }

            await client(SendReactionRequest(
                peer=peer,
                msg_id=message_id,
                reaction=[ReactionEmoji(emoticon=item.get('reaction'))],
                big=False,
                add_to_recent=True
            ))
            reacted_messages[reaction_key] = message_id
            return {
                'success': True,
                'message': f'Reação enviada automaticamente na mensagem {message_id}',
                'message_id': message_id,
                'channel_key': channel_key
            }
        finally:
            await client.disconnect()

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(react())
    finally:
        loop.close()

def _emit_reaction_progress(item, status, result=''):
    emit_to_user('reaction_progress', {
        'id': item.get('id'),
        'status': status,
        'reaction': item.get('reaction'),
        'post_link': item.get('post_link'),
        'session_label': item.get('session_label') or item.get('session_name'),
        'result': result,
        'time': __import__('datetime').datetime.now().strftime('%H:%M:%S')
    })

def _execute_reaction_item(data, paths=None, api_credentials=None):
    pending = next((item for item in data.get('queue', []) if item.get('status') == 'pending'), None)
    if not pending:
        return None

    data['queue'] = [item for item in data.get('queue', []) if item.get('id') != pending.get('id')]
    history_item = dict(pending)
    history_item['executed_at'] = __import__('datetime').datetime.now().isoformat(timespec='seconds')
    _emit_reaction_progress(pending, 'sending', 'Enviando reação...')
    try:
        result = _send_telegram_reaction(pending, data, paths=paths, api_credentials=api_credentials)
    except Exception as e:
        result = {'success': False, 'error': str(e)}

    if result.get('skipped'):
        history_item['status'] = 'waiting'
        history_item['result'] = result.get('message', 'Aguardando mensagem nova')
    elif result.get('success'):
        history_item['status'] = 'reacted'
        history_item['result'] = result.get('message', 'Reação enviada automaticamente')
    else:
        history_item['status'] = 'error'
        history_item['result'] = result.get('error', 'Erro ao enviar reação')

    _emit_reaction_progress(history_item, history_item['status'], history_item['result'])
    data.setdefault('history', []).insert(0, history_item)
    data['history'] = data['history'][:200]
    return history_item

def start_reaction_monitor_for_user(username, paths, session_indexes, post_links, reactions, poll_seconds, started_at=None):
    existing = reaction_monitors.get(username)
    if existing and existing.get('running'):
        return False, existing.get('started_at')

    if isinstance(post_links, str):
        post_links = [post_links]
    post_links = [str(link or '').strip() for link in (post_links or []) if str(link or '').strip()]
    if not post_links:
        raise ValueError('Informe ao menos um canal/link para monitorar')

    parsed_targets = []
    for post_link in post_links:
        parsed_post_link = _parse_telegram_post_link(post_link)
        target_key = str(parsed_post_link.get('private_channel_id') or parsed_post_link.get('peer') or parsed_post_link.get('invite_hash') or post_link).lower()
        parsed_targets.append((post_link, target_key))

    api_credentials = load_api_config_for_paths(paths)
    if not api_credentials:
        raise ValueError('API não configurada')

    stop_event = threading.Event()
    started_at = started_at or __import__('datetime').datetime.now().isoformat(timespec='seconds')
    reaction_monitors[username] = {'running': True, 'stop_event': stop_event, 'started_at': started_at}

    def monitor_loop():
        thread_context.username = username
        local_session_manager = SessionManager(paths['sessions_dir'], paths['config_file'])
        local_automation_manager = AutomationManager(paths['data_dir'])

        emit_to_user('reaction_progress', {
            'id': 'continuous-start',
            'status': 'sending',
            'reaction': 'AUTO',
            'post_link': ', '.join(post_links[:3]) + ('...' if len(post_links) > 3 else ''),
            'session_label': 'Sistema',
            'result': f'Monitor contínuo iniciado para {len(post_links)} alvo(s). Verificando a cada {poll_seconds}s.',
            'time': __import__('datetime').datetime.now().strftime('%H:%M:%S')
        }, username)

        while not stop_event.is_set():
            try:
                local_session_manager.invalidate_cache()
                sessions = local_session_manager.load_sessions(force_reload=True)
                available_sessions = []

                for session_index in session_indexes:
                    if session_index < 0 or session_index >= len(sessions):
                        continue
                    session_info = sessions[session_index]
                    flood_info = local_session_manager.get_flood_info(session_info.get('session_name', ''))
                    if flood_info.get('in_flood') or not session_info.get('active', True) or session_info.get('status', 'active') != 'active':
                        continue
                    available_sessions.append((session_index, session_info))

                if not available_sessions:
                    emit_to_user('reaction_progress', {
                        'id': 'continuous-empty',
                        'status': 'error',
                        'reaction': 'AUTO',
                        'post_link': ', '.join(post_links[:3]),
                        'session_label': 'Sistema',
                        'result': 'Nenhuma sessão disponível para monitorar.',
                        'time': __import__('datetime').datetime.now().strftime('%H:%M:%S')
                    }, username)
                    break

                data = load_reactions_data(paths)
                last_reacted = data.setdefault('reacted_messages', {})

                created_at = __import__('datetime').datetime.now().isoformat(timespec='seconds')
                base_id = int(__import__('time').time() * 1000)
                data['queue'] = []
                offset = 0
                for link_position, (post_link, target_key) in enumerate(parsed_targets):
                    sorted_sessions = sorted(
                        available_sessions,
                        key=lambda item: 1 if f'{item[1].get("session_name")}|{target_key}' in last_reacted else 0
                    )
                    for position, (session_index, session_info) in enumerate(sorted_sessions):
                        data['queue'].append({
                            'id': base_id + offset,
                            'status': 'pending',
                            'session_index': int(session_index),
                            'session_name': session_info.get('session_name'),
                            'session_label': session_info.get('first_name') or session_info.get('username') or session_info.get('session_name'),
                            'post_link': post_link,
                            'reaction': reactions[(position + link_position) % len(reactions)],
                            'created_at': created_at
                        })
                        offset += 1

                executed = []
                while any(item.get('status') == 'pending' for item in data.get('queue', [])) and not stop_event.is_set():
                    history_item = _execute_reaction_item(data, paths=paths, api_credentials=api_credentials)
                    if history_item:
                        executed.append(history_item)

                save_reactions_data(data, paths)
                reacted_count = len([item for item in executed if item.get('status') == 'reacted'])
                if reacted_count:
                    emit_to_user('reaction_progress', {
                        'id': f'continuous-cycle-{base_id}',
                        'status': 'reacted',
                        'reaction': 'AUTO',
                        'post_link': ', '.join(post_links[:3]),
                        'session_label': 'Sistema',
                        'result': f'{reacted_count} reação(ões) enviada(s). Continuando monitoramento.',
                        'time': __import__('datetime').datetime.now().strftime('%H:%M:%S')
                    }, username)
            except Exception as e:
                emit_to_user('reaction_progress', {
                    'id': 'continuous-error',
                    'status': 'error',
                    'reaction': 'AUTO',
                    'post_link': ', '.join(post_links[:3]),
                    'session_label': 'Sistema',
                    'result': f'Erro no monitor contínuo: {str(e)}',
                    'time': __import__('datetime').datetime.now().strftime('%H:%M:%S')
                }, username)

            stop_event.wait(poll_seconds)

        monitor = reaction_monitors.get(username, {})
        monitor['running'] = False
        reaction_monitors[username] = monitor
        emit_to_user('reaction_progress', {
            'id': 'continuous-stop',
            'status': 'waiting',
            'reaction': 'AUTO',
            'post_link': ', '.join(post_links[:3]),
            'session_label': 'Sistema',
            'result': 'Monitor contínuo parado.',
            'time': __import__('datetime').datetime.now().strftime('%H:%M:%S')
        }, username)

    thread = threading.Thread(target=monitor_loop, daemon=True)
    reaction_monitors[username]['thread'] = thread
    thread.start()
    return True, started_at

@app.route('/api/reactions/execute-next', methods=['POST'])
@login_required
def execute_next_reaction():
    data = load_reactions_data()
    history_item = _execute_reaction_item(data)
    if not history_item:
        return jsonify({'success': False, 'error': 'Nenhuma reação pendente'}), 400

    save_reactions_data(data)
    return jsonify({'success': True, 'item': history_item})

@app.route('/api/reactions/execute-all', methods=['POST'])
@login_required
def execute_all_reactions():
    payload = request.json or {}
    delay_seconds = max(1, min(int(payload.get('delay_seconds', 5)), 300))
    data = load_reactions_data()
    executed = []
    total_pending = len([item for item in data.get('queue', []) if item.get('status') == 'pending'])
    process_id = start_process(
        'reaction',
        'Execução de reações',
        total=total_pending,
        username=session.get('username'),
        detail=f'{total_pending} item(ns) pendente(s)'
    ) if total_pending else None

    try:
        while any(item.get('status') == 'pending' for item in data.get('queue', [])):
            history_item = _execute_reaction_item(data)
            if history_item:
                executed.append(history_item)
                if process_id:
                    update_process(
                        process_id,
                        username=session.get('username'),
                        current=len(executed),
                        total=total_pending,
                        message=f'{len(executed)}/{total_pending} reação(ões) processada(s)',
                        detail=history_item.get('post_link', '')
                    )
            if any(item.get('status') == 'pending' for item in data.get('queue', [])):
                __import__('time').sleep(delay_seconds)
    except Exception as e:
        if process_id:
            finish_process(process_id, username=session.get('username'), status='error', message=f'Erro nas reações: {str(e)}')
        raise

    save_reactions_data(data)
    if process_id:
        finish_process(
            process_id,
            username=session.get('username'),
            status='completed',
            message=f'Reações finalizadas: {len(executed)} item(ns) processado(s).'
        )
    return jsonify({'success': True, 'executed': executed, 'count': len(executed)})

@app.route('/api/reactions/continuous/start', methods=['POST'])
@login_required
def start_continuous_reactions():
    payload = request.json or {}
    username = session.get('username')
    if not username:
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401

    existing = reaction_monitors.get(username)
    if existing and existing.get('running'):
        return jsonify({'success': False, 'error': 'Monitor contínuo já está rodando'}), 400

    session_indexes = payload.get('session_indexes') or []
    post_links = normalize_reaction_links(payload)
    reactions = payload.get('reactions') or []
    if isinstance(reactions, str):
        reactions = [reactions]

    try:
        session_indexes = [int(index) for index in session_indexes]
    except Exception:
        return jsonify({'success': False, 'error': 'Sessões inválidas'}), 400

    reactions = [str(reaction).strip() for reaction in reactions if str(reaction or '').strip()][:12]
    if not session_indexes or not post_links or not reactions:
        return jsonify({'success': False, 'error': 'Selecione sessão(ões), ao menos um link/canal e ao menos uma reação'}), 400

    current_username = session.get('username')
    paths = get_user_paths()
    started_at = __import__('datetime').datetime.now().isoformat(timespec='seconds')
    poll_seconds = max(15, min(int(payload.get('poll_seconds') or payload.get('delay_seconds') or 15), 300))

    try:
        start_reaction_monitor_for_user(current_username, paths, session_indexes, post_links, reactions, poll_seconds, started_at)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    data = load_reactions_data(paths)
    data['continuous_task'] = {
        'enabled': True,
        'session_indexes': session_indexes,
        'post_link': post_links[0],
        'post_links': post_links,
        'reactions': reactions,
        'poll_seconds': poll_seconds,
        'started_at': started_at
    }
    data.setdefault('settings', {})['delay_seconds'] = poll_seconds
    save_reactions_data(data, paths)

    return jsonify({'success': True, 'message': 'Monitor contínuo iniciado', 'started_at': started_at})

@app.route('/api/reactions/continuous/stop', methods=['POST'])
@login_required
def stop_continuous_reactions():
    username = session.get('username')
    monitor = reaction_monitors.get(username)
    paths = get_user_paths()
    data = load_reactions_data(paths)
    data.setdefault('continuous_task', {})['enabled'] = False
    save_reactions_data(data, paths)

    if not monitor or not monitor.get('running'):
        return jsonify({'success': False, 'error': 'Monitor contínuo não está rodando'}), 400

    monitor['stop_event'].set()
    monitor['running'] = False
    return jsonify({'success': True, 'message': 'Parando monitor contínuo'})

def restore_saved_reaction_monitors():
    """Religa monitores contínuos de reações que ficaram salvos antes do restart."""
    for user in user_manager.load_users():
        username = user.get('username')
        if not username:
            continue

        try:
            user_manager.create_user_directories(username)
            paths = get_user_paths(username)
            data = load_reactions_data(paths)
            continuous_task = data.get('continuous_task', {})
            if not continuous_task.get('enabled'):
                continue
            if reaction_monitors.get(username, {}).get('running'):
                continue

            start_reaction_monitor_for_user(
                username,
                paths,
                [int(index) for index in continuous_task.get('session_indexes', [])],
                continuous_task.get('post_links') or [continuous_task.get('post_link', '')],
                continuous_task.get('reactions', []),
                max(15, min(int(continuous_task.get('poll_seconds') or 15), 300)),
                continuous_task.get('started_at')
            )
            log_info(f"Monitor contínuo de reações restaurado para {username}")
        except Exception as e:
            log_warning(f"Não foi possível restaurar monitor de reações de {username}: {e}")

def restore_saved_active_tasks():
    """Religa tarefas ativas salvas após restart do servidor."""
    for user in user_manager.load_users():
        username = user.get('username')
        if not username:
            continue

        try:
            user_manager.create_user_directories(username)
            paths = get_user_paths(username)
            manager = AutomationManager(paths['data_dir'])
            active_tasks = [
                task for task in manager.config.get('groups', [])
                if task.get('status') == 'active'
            ]

            if not active_tasks:
                continue

            for task in active_tasks:
                task_id = task.get('id')
                task['status'] = 'paused'
                task['resume_note'] = 'Tarefa religada automaticamente após reinício do servidor.'
                task['resumed_at'] = datetime.now().isoformat(timespec='seconds')
                append_task_log(
                    task_id,
                    '🔄 Servidor reiniciou; religando tarefa automaticamente em segundo plano.',
                    'info',
                    manager
                )

            manager.save_config()

            for task in active_tasks:
                task_id = task.get('id')
                if not task_id:
                    continue

                def start_saved_task(saved_username=username, saved_task_id=task_id):
                    try:
                        with app.test_client() as client:
                            with client.session_transaction() as saved_session:
                                saved_session['username'] = saved_username
                            response = client.post(f'/api/tasks/{saved_task_id}/start')
                            if response.status_code >= 400:
                                log_warning(
                                    f"Tarefa #{saved_task_id} de {saved_username} não religou: "
                                    f"HTTP {response.status_code} {response.get_data(as_text=True)}"
                                )
                            else:
                                log_info(f"Tarefa #{saved_task_id} restaurada para {saved_username}")
                    except Exception as task_error:
                        log_warning(f"Não foi possível religar tarefa #{saved_task_id} de {saved_username}: {task_error}")

                threading.Thread(target=start_saved_task, daemon=True).start()
        except Exception as e:
            log_warning(f"Não foi possível restaurar tarefas de {username}: {e}")

@app.route('/api/reactions/settings', methods=['POST'])
@login_required
def update_reaction_settings():
    payload = request.json or {}
    data = load_reactions_data()
    settings = data.setdefault('settings', {})
    if 'delay_seconds' in payload:
        settings['delay_seconds'] = max(1, min(int(payload.get('delay_seconds', 5)), 300))
    if 'disable_add_group_interactions' in payload:
        settings['disable_add_group_interactions'] = bool(payload.get('disable_add_group_interactions'))
    if 'custom_reactions' in payload:
        custom_reactions = []
        for reaction in payload.get('custom_reactions') or []:
            reaction = str(reaction or '').strip()
            if not reaction or len(reaction) > 16 or reaction in custom_reactions:
                continue
            custom_reactions.append(reaction)
            if len(custom_reactions) >= 40:
                break
        settings['custom_reactions'] = custom_reactions
    save_reactions_data(data)
    return jsonify({'success': True, 'settings': settings})

# ========== ENDPOINTS DE AQUECIMENTO ==========

def load_warming_groups(paths=None):
    """Carrega grupos de aquecimento"""
    paths = paths or get_user_paths()
    warming_groups_file = paths['warming_file'] if paths else os.path.join(DATA_DIR, 'warming_groups.json')
    if os.path.exists(warming_groups_file):
        return load_json_file(warming_groups_file, [])
    return []

def save_warming_groups(groups, paths=None):
    """Salva grupos de aquecimento"""
    paths = paths or get_user_paths()
    warming_groups_file = paths['warming_file'] if paths else os.path.join(DATA_DIR, 'warming_groups.json')
    atomic_write_json(warming_groups_file, groups)

@app.route('/api/warming/groups', methods=['GET', 'POST'])
@login_required
def manage_warming_groups():
    """Gerencia grupos de aquecimento"""
    if request.method == 'GET':
        groups = load_warming_groups()
        return jsonify({'success': True, 'groups': groups})
    
    # POST - Adicionar grupo
    data = request.json
    groups = load_warming_groups()
    
    group_link = data['group_link']
    if group_link not in groups:
        groups.append(group_link)
        save_warming_groups(groups)
    
    return jsonify({'success': True, 'groups': groups})

@app.route('/api/warming/groups/<int:index>', methods=['DELETE'])
@login_required
def remove_warming_group(index):
    """Remove grupo de aquecimento"""
    groups = load_warming_groups()
    
    if 0 <= index < len(groups):
        groups.pop(index)
        save_warming_groups(groups)
    
    return jsonify({'success': True, 'groups': groups})

@app.route('/api/warming/start', methods=['POST'])
@login_required
def start_warming():
    """Inicia aquecimento automático"""
    current_username = get_current_username()
    warming_state = get_warming_state(current_username)
    
    if warming_state.get('active'):
        return jsonify({'success': False, 'error': 'Aquecimento já está ativo'}), 400
    
    # Verifica se pode iniciar aquecimento
    can_warm, message = check_session_lock('warming')
    if not can_warm:
        return jsonify({'success': False, 'error': message}), 400
    
    data = request.json
    min_interval = data.get('min_interval', 5)
    max_interval = data.get('max_interval', 15)
    
    groups = load_warming_groups()
    if not groups:
        return jsonify({'success': False, 'error': 'Nenhum grupo configurado'}), 400
    
    sessions = session_manager.get_active_sessions()
    if not sessions:
        return jsonify({'success': False, 'error': 'Nenhuma sessão ativa'}), 400
    
    api_id, api_hash = get_next_api()
    if not api_id:
        return jsonify({'success': False, 'error': 'API não configurada'}), 400
    
    def warming_process():
        thread_context.username = current_username
        warming_state['active'] = True
        
        # Bloqueia aquecimento
        set_session_lock('warming', True, username=current_username)
        
        try:
            from warming_bot import WarmingBot
            import asyncio
            import random
            import time
            
            bot = WarmingBot(api_id, api_hash)
            
            emit_to_user('warming_log', {
                'message': f'🔥 Aquecimento iniciado com {len(sessions)} sessão(ões) em {len(groups)} grupo(s)',
                'type': 'success'
            }, current_username)
            
            # Primeiro, garante que todas as sessões estão nos grupos
            emit_to_user('warming_log', {
                'message': '📋 Verificando participação nos grupos...',
                'type': 'info'
            }, current_username)
            
            for session in sessions:
                if not warming_state.get('active'):
                    break
                    
                for group_link in groups:
                    if not warming_state.get('active'):
                        break
                        
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        success, message = loop.run_until_complete(
                            bot.ensure_in_group(session, group_link)
                        )
                        loop.close()
                        
                        if success:
                            emit_to_user('warming_log', {
                                'message': f'✅ {session["first_name"]} → {group_link}: {message}',
                                'type': 'success'
                            }, current_username)
                        else:
                            emit_to_user('warming_log', {
                                'message': f'⚠️  {session["first_name"]} → {group_link}: {message}',
                                'type': 'warning'
                            }, current_username)
                    except Exception as e:
                        emit_to_user('warming_log', {
                            'message': f'❌ Erro ao verificar {session["first_name"]}: {str(e)}',
                            'type': 'error'
                        }, current_username)
                    
                    time.sleep(2)  # Delay entre verificações
            
            emit_to_user('warming_log', {
                'message': '✅ Verificação concluída! Iniciando envio de mensagens...',
                'type': 'success'
            }, current_username)
            
            # Agora inicia o loop de aquecimento
            while warming_state.get('active'):
                for session in sessions:
                    if not warming_state.get('active'):
                        break
                    
                    if session.get('status') != 'active':
                        continue
                    
                    for group_link in groups:
                        if not warming_state.get('active'):
                            break
                        
                        try:
                            # Executa envio de mensagem
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            success = loop.run_until_complete(
                                bot.send_warming_message(session, group_link)
                            )
                            loop.close()
                            
                            if success:
                                emit_to_user('warming_log', {
                                    'message': f'✅ {session["first_name"]} → {group_link}',
                                    'type': 'success'
                                }, current_username)
                            else:
                                emit_to_user('warming_log', {
                                    'message': f'⚠️  Falha: {session["first_name"]} → {group_link}',
                                    'type': 'warning'
                                }, current_username)
                        except Exception as e:
                            emit_to_user('warming_log', {
                                'message': f'❌ Erro: {str(e)}',
                                'type': 'error'
                            }, current_username)
                        
                        # Delay aleatório entre mensagens
                        if warming_state.get('active'):
                            delay = random.randint(min_interval * 60, max_interval * 60)
                            minutes = delay // 60
                            emit_to_user('warming_log', {
                                'message': f'⏳ Aguardando {minutes} minuto(s)...',
                                'type': 'info'
                            }, current_username)
                            
                            # Sleep em chunks para poder parar mais rápido
                            for _ in range(delay):
                                if not warming_state.get('active'):
                                    break
                                time.sleep(1)
            
            emit_to_user('warming_log', {
                'message': '⏹️ Aquecimento finalizado',
                'type': 'warning'
            }, current_username)
        finally:
            # Libera aquecimento
            warming_state['active'] = False
            set_session_lock('warming', False, username=current_username)
    
    warming_state['thread'] = threading.Thread(target=warming_process, daemon=True)
    warming_state['thread'].start()
    
    return jsonify({'success': True})

@app.route('/api/warming/stop', methods=['POST'])
@login_required
def stop_warming():
    """Para aquecimento automático"""
    warming_state = get_warming_state()
    warming_state['active'] = False
    
    # Libera o lock (será liberado também no finally do thread)
    set_session_lock('warming', False)
    
    return jsonify({'success': True})

@app.route('/api/warming/logs', methods=['GET'])
@login_required
def get_warming_logs():
    """Retorna o arquivo de logs de debug"""
    from flask import send_file
    log_file = 'warming_debug.log'
    
    if os.path.exists(log_file):
        return send_file(log_file, as_attachment=True, download_name='warming_debug.log', mimetype='text/plain')
    else:
        return jsonify({'error': 'Arquivo de log não encontrado'}), 404

@app.route('/api/system/logs', methods=['GET'])
@login_required
def get_system_logs():
    """Download dos logs do sistema"""
    from flask import send_file
    log_file = os.path.join(DATA_DIR, 'system.log')
    if os.path.exists(log_file):
        return send_file(log_file, as_attachment=True, download_name='system.log', mimetype='text/plain')
    return jsonify({'error': 'Log file not found'}), 404

@app.route('/api/system/logs/view', methods=['GET'])
@login_required
def view_system_logs():
    """Visualiza os últimos logs do sistema"""
    log_file = os.path.join(DATA_DIR, 'system.log')
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Retorna últimas 500 linhas
                last_lines = lines[-500:] if len(lines) > 500 else lines
                return jsonify({
                    'success': True,
                    'logs': ''.join(last_lines),
                    'total_lines': len(lines)
                })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Log file not found'}), 404

@app.route('/api/session/locks', methods=['GET'])
@login_required
def get_session_locks():
    """Retorna o status dos locks de sessão"""
    locks = get_user_lock_state()
    warming_state = get_warming_state()
    return jsonify({
        'locks': {
            'warming': locks['warming'],
            'extraction': locks['extraction'],
            'addition': locks['addition'],
            'active_tasks': list(locks['active_tasks'])
        },
        'warming_active': warming_state.get('active', False)
    })


# ========== ENDPOINTS DE CLONAGEM DE CANAIS ==========

@app.route('/api/clones', methods=['GET', 'POST'])
@login_required
def manage_clones():
    """Gerencia clonagens de canais"""
    if request.method == 'GET':
        clones = clone_manager.load_clones()
        return jsonify({'success': True, 'clones': clones})
    
    elif request.method == 'POST':
        data = request.get_json()
        
        clone_config = {
            'name': data.get('name'),
            'session_name': data.get('session_name'),
            'source_channel': data.get('source_channel'),
            'dest_channel': data.get('dest_channel'),
            'remove_links': data.get('remove_links', False),
            'remove_mentions': data.get('remove_mentions', False),
            'prefix': data.get('prefix', ''),
            'footer': data.get('footer', ''),
            'text_replacements': data.get('text_replacements', {})
        }
        
        clone_id = clone_manager.add_clone(clone_config)
        
        return jsonify({'success': True, 'clone_id': clone_id})

@app.route('/api/clones/<clone_id>', methods=['GET', 'DELETE', 'PUT'])
@login_required
def clone_operations(clone_id):
    """Operações em uma clonagem específica"""
    clones = clone_manager.load_clones()
    clone = next((c for c in clones if c['id'] == clone_id), None)
    
    if not clone:
        return jsonify({'success': False, 'error': 'Clonagem não encontrada'}), 404
    
    if request.method == 'GET':
        return jsonify({'success': True, 'clone': clone})
    
    elif request.method == 'DELETE':
        # Para a clonagem se estiver ativa
        if clone.get('active'):
            # TODO: Parar clonagem ativa
            pass
        
        clone_manager.remove_clone(clone_id)
        return jsonify({'success': True})
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        # Atualiza configurações
        clones = clone_manager.load_clones()
        for c in clones:
            if c['id'] == clone_id:
                c['name'] = data.get('name', c['name'])
                c['source_channel'] = data.get('source_channel', c['source_channel'])
                c['dest_channel'] = data.get('dest_channel', c['dest_channel'])
                c['remove_links'] = data.get('remove_links', c.get('remove_links', False))
                c['remove_mentions'] = data.get('remove_mentions', c.get('remove_mentions', False))
                c['prefix'] = data.get('prefix', c.get('prefix', ''))
                c['footer'] = data.get('footer', c.get('footer', ''))
                c['text_replacements'] = data.get('text_replacements', c.get('text_replacements', {}))
                break
        
        clone_manager.save_clones(clones)
        return jsonify({'success': True})

@app.route('/api/clones/<clone_id>/start', methods=['POST'])
@login_required
def start_clone(clone_id):
    """Inicia uma clonagem"""
    try:
        clones = clone_manager.load_clones()
        clone = next((c for c in clones if c['id'] == clone_id), None)
        
        if not clone:
            return jsonify({'success': False, 'error': 'Clonagem não encontrada'}), 404
        
        # Pega informações da sessão
        session_name = clone['session_name']
        sessions = session_manager.load_sessions()
        session_info = next((s for s in sessions if s['session_name'] == session_name), None)
        
        if not session_info:
            return jsonify({'success': False, 'error': 'Sessão não encontrada'}), 404
        
        # Pega API credentials
        api_creds = load_api_config()
        if not api_creds:
            return jsonify({'success': False, 'error': 'API não configurada'}), 400
        
        api_id = api_creds[0]['api_id']
        api_hash = api_creds[0]['api_hash']
        
        # Pega caminho da sessão
        paths = get_user_paths()
        session_path = os.path.join(paths['sessions_dir'], session_name)
        
        # Cria cloner
        cloner = clone_manager.get_cloner(
            session_name,
            api_id,
            api_hash,
            session_info.get('phone', ''),
            session_path
        )
        
        # Prepara config de modificações
        mod_config = {
            'remove_links': clone.get('remove_links', False),
            'remove_mentions': clone.get('remove_mentions', False),
            'prefix': clone.get('prefix', ''),
            'footer': clone.get('footer', ''),
            'text_replacements': clone.get('text_replacements', {})
        }
        
        # Inicia clonagem em thread separada com loop persistente
        def run_clone():
            import asyncio
            
            # Cria loop dedicado para esta clonagem
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Armazena o loop no cloner para uso posterior
            cloner.loop = loop
            
            try:
                # Inicia a clonagem (cria a task)
                loop.run_until_complete(
                    cloner.start_clone(
                        clone_id,
                        clone['source_channel'],
                        clone['dest_channel'],
                        mod_config
                    )
                )
                
                # Mantém o loop rodando para as tasks assíncronas
                log_info(f"🔄 Loop de clonagem rodando para {clone_id}")
                loop.run_forever()
                
            except Exception as e:
                log_error(f"Erro na thread de clonagem: {e}")
                import traceback
                log_error(f"Traceback: {traceback.format_exc()}")
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_clone, daemon=True)
        thread.start()
        
        # Atualiza status
        clone_manager.update_clone_status(clone_id, True)
        
        return jsonify({'success': True, 'message': 'Clonagem iniciada'})
        
    except Exception as e:
        log_error(f"Erro ao iniciar clonagem: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clones/<clone_id>/stop', methods=['POST'])
@login_required
def stop_clone(clone_id):
    """Para uma clonagem"""
    try:
        clones = clone_manager.load_clones()
        clone = next((c for c in clones if c['id'] == clone_id), None)
        
        if not clone:
            return jsonify({'success': False, 'error': 'Clonagem não encontrada'}), 404
        
        session_name = clone['session_name']
        
        if session_name in clone_manager.cloners:
            cloner = clone_manager.cloners[session_name]
            
            # Para a clonagem
            def stop_async():
                import asyncio
                
                # Se o cloner tem um loop, usa ele
                if hasattr(cloner, 'loop') and cloner.loop:
                    # Para a task de monitoramento
                    cloner.loop.call_soon_threadsafe(
                        lambda: asyncio.ensure_future(cloner.stop_clone(clone_id), loop=cloner.loop)
                    )
                    # Para o loop após 1 segundo
                    cloner.loop.call_later(1, cloner.loop.stop)
                else:
                    # Fallback: cria novo loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(cloner.stop_clone(clone_id))
                    loop.close()
            
            thread = threading.Thread(target=stop_async, daemon=True)
            thread.start()
        
        # Atualiza status
        clone_manager.update_clone_status(clone_id, False)
        
        return jsonify({'success': True, 'message': 'Clonagem parada'})
        
    except Exception as e:
        log_error(f"Erro ao parar clonagem: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== ENDPOINTS DE CRIAÇÃO DE SESSÃO ==========

@app.route('/api/sessions/create/send-code', methods=['POST'])
@login_required
def send_session_code():
    """Envia código de verificação para criar sessão"""
    try:
        data = request.get_json()
        phone = data.get('phone', '').strip()
        
        if not phone:
            return jsonify({'success': False, 'error': 'Telefone é obrigatório'}), 400
        
        # Pega API credentials
        api_creds = load_api_config()
        if not api_creds:
            return jsonify({'success': False, 'error': 'Configure a API primeiro'}), 400
        
        api_id = api_creds[0]['api_id']
        api_hash = api_creds[0]['api_hash']
        
        # Pega diretório de sessões do usuário
        paths = get_user_paths()
        sessions_dir = paths['sessions_dir']
        
        # Cria ID único para esta sessão em criação
        import time
        session_id = f"create_{int(time.time())}"
        
        # Cria SessionCreator com loop dedicado
        creator = SessionCreator(api_id, api_hash, phone, sessions_dir)
        
        # Envia código usando o loop dedicado
        success, message = creator.run_in_loop(creator.send_code())
        
        if success:
            # Armazena creator para uso posterior
            set_session_creator(session_id, creator)
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': 'Código enviado! Verifique seu Telegram.'
            })
        else:
            return jsonify({'success': False, 'error': message}), 400
            
    except Exception as e:
        log_error(f"Erro ao enviar código: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sessions/create/verify-code', methods=['POST'])
@login_required
def verify_session_code():
    """Verifica código e cria sessão"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        code = data.get('code', '').strip()
        
        if not session_id or not code:
            return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
        # Pega creator
        creator = get_session_creator(session_id)
        if not creator:
            return jsonify({'success': False, 'error': 'Sessão expirada. Envie o código novamente.'}), 400
        
        # Verifica código usando o loop dedicado
        success, message = creator.run_in_loop(creator.verify_code(code))
        
        if success:
            # Sessão criada com sucesso!
            user_info = message
            
            # Adiciona sessão ao config
            session_info = {
                'session_name': creator.phone.replace('+', '').replace(' ', '').replace('-', ''),
                'phone': user_info['phone'],
                'name': user_info['name'],
                'username': user_info['username'],
                'user_id': user_info['user_id'],
                'active': True,
                'status': 'active'
            }
            
            # Salva no session_manager
            session_manager.sessions.append(session_info)
            session_manager.save_sessions()
            
            # Remove creator
            remove_session_creator(session_id)
            
            return jsonify({
                'success': True,
                'message': 'Sessão criada com sucesso!',
                'session': session_info
            })
        
        elif message == '2FA_REQUIRED':
            # Precisa de senha 2FA
            return jsonify({
                'success': False,
                'requires_2fa': True,
                'message': 'Esta conta tem verificação em 2 fatores. Digite sua senha.'
            })
        
        else:
            return jsonify({'success': False, 'error': message}), 400
            
    except Exception as e:
        log_error(f"Erro ao verificar código: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sessions/create/verify-password', methods=['POST'])
@login_required
def verify_session_password():
    """Verifica senha 2FA e cria sessão"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        password = data.get('password', '').strip()
        
        if not session_id or not password:
            return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
        # Pega creator
        creator = get_session_creator(session_id)
        if not creator:
            return jsonify({'success': False, 'error': 'Sessão expirada'}), 400
        
        # Verifica senha usando o loop dedicado
        success, message = creator.run_in_loop(creator.verify_password(password))
        
        if success:
            # Sessão criada com sucesso!
            user_info = message
            
            # Adiciona sessão ao config
            session_info = {
                'session_name': creator.phone.replace('+', '').replace(' ', '').replace('-', ''),
                'phone': user_info['phone'],
                'name': user_info['name'],
                'username': user_info['username'],
                'user_id': user_info['user_id'],
                'active': True,
                'status': 'active'
            }
            
            # Salva no session_manager
            session_manager.sessions.append(session_info)
            session_manager.save_sessions()
            
            # Remove creator
            remove_session_creator(session_id)
            
            return jsonify({
                'success': True,
                'message': 'Sessão criada com sucesso!',
                'session': session_info
            })
        else:
            return jsonify({'success': False, 'error': message}), 400
            
    except Exception as e:
        log_error(f"Erro ao verificar senha: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # Discloud usa porta 8080
    port = int(os.environ.get('PORT', 8080))
    restore_saved_reaction_monitors()
    restore_saved_active_tasks()
    socketio.run(app, debug=False, host='0.0.0.0', port=port)

