# Configurações do Sistema
import os
import json
from data_store import atomic_write_json

# Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, 'sessions')
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Criar diretórios se não existirem
os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Configurações do Telegram API
# Obtenha em: https://my.telegram.org/apps
API_ID = None  # Você vai configurar pelo sistema
API_HASH = None  # Você vai configurar pelo sistema

# Sistema de múltiplas APIs (rotativo)
API_CREDENTIALS = []  # Lista de dicionários com api_id e api_hash
CURRENT_API_INDEX = 0  # Índice da API atual em uso

# Configurações de adição
DEFAULT_MEMBERS_PER_SESSION = 50
DEFAULT_DELAY_BETWEEN_ADDS = 2  # segundos
DEFAULT_DELAY_BETWEEN_SESSIONS = 60  # segundos

# Arquivo de configuração
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
MEMBERS_FILE = os.path.join(DATA_DIR, 'members.json')

# Função para inicializar arquivos necessários
def init_data_files():
    """Cria arquivos de dados se não existirem"""
    
    # config.json
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            'api_credentials': [],
            'sessions': [],
            'current_api_index': 0
        }
        atomic_write_json(CONFIG_FILE, default_config)
        print(f'✅ Criado: {CONFIG_FILE}')
    
    # members.json
    if not os.path.exists(MEMBERS_FILE):
        atomic_write_json(MEMBERS_FILE, [])
        print(f'✅ Criado: {MEMBERS_FILE}')
    
    # session_floods.json
    floods_file = os.path.join(DATA_DIR, 'session_floods.json')
    if not os.path.exists(floods_file):
        atomic_write_json(floods_file, {})
        print(f'✅ Criado: {floods_file}')
    
    # automation_config.json
    automation_file = os.path.join(DATA_DIR, 'automation_config.json')
    if not os.path.exists(automation_file):
        default_automation = {
            'groups': [],
            'daily_limits': {},
            'warming_enabled': False,
            'warming_interval': 10
        }
        atomic_write_json(automation_file, default_automation)
        print(f'✅ Criado: {automation_file}')
    
    # warming_groups.json
    warming_file = os.path.join(DATA_DIR, 'warming_groups.json')
    if not os.path.exists(warming_file):
        atomic_write_json(warming_file, [])
        print(f'✅ Criado: {warming_file}')

# Inicializa arquivos ao importar o módulo
init_data_files()
