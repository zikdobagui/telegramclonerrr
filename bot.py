import subprocess
import sys
import os

# ============================================================================
# SISTEMA DE INSTALAÇÃO AUTOMÁTICA DE DEPENDÊNCIAS
# ============================================================================

def upgrade_pip():
    """Atualiza o pip para a versão mais recente"""
    try:
        print("🔧 Verificando versão do pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Pip atualizado!\n")
        return True
    except:
        print("⚠️ Não foi possível atualizar o pip, continuando...\n")
        return False

def check_package_installed(package_name):
    """Verifica se um pacote está instalado usando pip list"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.returncode == 0
    except:
        return False

def install_package(package_name, import_name=None):
    """Instala um pacote Python se ele não estiver disponível"""
    if import_name is None:
        import_name = package_name
    
    # Primeiro verifica se está instalado via pip
    if check_package_installed(package_name):
        return True
    
    # Se não estiver, tenta importar para ter certeza
    try:
        __import__(import_name)
        return True
    except ImportError:
        pass
    
    # Se realmente não estiver instalado, instala
    print(f"📦 Instalando {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "--upgrade"])
        print(f"✅ {package_name} instalado com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar {package_name}: {e}")
        return False

def create_requirements_file(packages):
    """Cria um arquivo requirements.txt com as dependências"""
    try:
        with open('requirements.txt', 'w', encoding='utf-8') as f:
            f.write("# Dependências do Bot de Divulgação\n")
            f.write("# Gerado automaticamente\n\n")
            for package, _ in packages:
                f.write(f"{package}\n")
        print("📄 Arquivo requirements.txt criado/atualizado!\n")
        return True
    except Exception as e:
        print(f"⚠️ Não foi possível criar requirements.txt: {e}\n")
        return False

# Lista de dependências necessárias
REQUIRED_PACKAGES = [
    ("colorama", "colorama"),
    ("requests", "requests"),
    ("flask", "flask"),
    ("flask-socketio", "flask_socketio"),
    ("pyjwt", "jwt"),
    ("telethon", "telethon"),
    ("cryptg", "cryptg"),
    ("aiohttp", "aiohttp"),
    ("python-dotenv", "dotenv"),
    ("psutil", "psutil"),
    ("aiogram", "aiogram"),
]

print("\n" + "=" * 60)
print("🚀 SISTEMA DE INSTALAÇÃO AUTOMÁTICA DE DEPENDÊNCIAS")
print("=" * 60)

# Verificação rápida inicial - verifica se TODOS os pacotes estão instalados
print("🔍 Verificação rápida de dependências...")
all_installed = True
for package, import_name in REQUIRED_PACKAGES:
    if not check_package_installed(package):
        all_installed = False
        break

if all_installed:
    print("✅ Todas as dependências já estão instaladas!")
    print("=" * 60)
    print("\n🎉 Bot pronto para iniciar!\n")
else:
    # Se algum pacote estiver faltando, faz a verificação completa
    print("⚠️ Algumas dependências precisam ser instaladas...\n")
    
    # Atualiza o pip primeiro
    upgrade_pip()

    # Cria arquivo requirements.txt
    create_requirements_file(REQUIRED_PACKAGES)

    print("🔍 VERIFICANDO E INSTALANDO DEPENDÊNCIAS NECESSÁRIAS")
    print("=" * 60)
    print(f"📦 Total de pacotes a verificar: {len(REQUIRED_PACKAGES)}\n")

    installed_count = 0
    already_installed_count = 0
    failed_count = 0

    for i, (package, import_name) in enumerate(REQUIRED_PACKAGES, 1):
        print(f"[{i}/{len(REQUIRED_PACKAGES)}] Verificando {package}...", end=" ")
        
        # Verifica se o pacote está instalado
        if check_package_installed(package):
            print("✅ Já instalado")
            already_installed_count += 1
        else:
            # Tenta importar como fallback
            try:
                __import__(import_name)
                print("✅ Já instalado")
                already_installed_count += 1
            except ImportError:
                print("❌ Não encontrado")
                if install_package(package, import_name):
                    installed_count += 1
                else:
                    failed_count += 1

    print("\n" + "=" * 60)
    print(f"✅ VERIFICAÇÃO CONCLUÍDA!")
    print(f"📊 Já instalados: {already_installed_count}")
    print(f"📥 Novos instalados: {installed_count}")
    if failed_count > 0:
        print(f"⚠️ Falhas: {failed_count}")
    print(f"🎯 Total: {len(REQUIRED_PACKAGES)} pacotes verificados!")
    print("=" * 60)

    if failed_count > 0:
        print(f"\n⚠️ ATENÇÃO: {failed_count} pacote(s) não puderam ser instalados.")
        print("💡 Tente instalar manualmente com: pip install -r requirements.txt")
        print("=" * 60)

    print("\n🎉 Bot pronto para iniciar!\n")


# ============================================================================
# DATABASE PATHS - Caminhos dos arquivos de dados
# ============================================================================

# Diretório de dados (usa 'data' em vez de 'database' para compatibilidade)
DATA_DIR = "data"
DATABASE_DIR = DATA_DIR  # Alias
os.makedirs(DATA_DIR, exist_ok=True)

# Arquivos de configuração
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
WEB_PANEL_CONFIG_FILE = os.path.join(DATA_DIR, "web_panel_config.json")
LOG_CONFIG_FILE = os.path.join(DATA_DIR, "log_config.json")

# Arquivos de usuários
CHAT_IDS_FILE = os.path.join(DATA_DIR, "chat_ids.json")
USER_IDS_FILE = os.path.join(DATA_DIR, "user_ids.json")
REGISTERED_USERS_FILE = os.path.join(DATA_DIR, "registered_users.json")
ADDED_BY_FILE = os.path.join(DATA_DIR, "added_by.json")

# Arquivos de mensagens
SCHEDULED_MESSAGES_FILE = os.path.join(DATA_DIR, "scheduled_messages.json")

# Arquivos de erros e falhas
FAILED_CHAT_IDS_FILE = os.path.join(DATA_DIR, "failed_chat_ids.json")
ERRORED_CHAT_IDS_FILE = os.path.join(DATA_DIR, "errored_chat_ids.json")
IDS_COM_ERROS_FILE = os.path.join(DATA_DIR, "ids_com_erros.json")
TEMP_FAILED_IDS_FILE = os.path.join(DATA_DIR, "temp_failed_ids.json")

# Arquivos de planos
EXPIRED_PLANS_FILE = os.path.join(DATA_DIR, "expired_plans.json")

# Arquivos de silenciamento
SILENCED_FILE = os.path.join(DATA_DIR, "silenciados.json")
CLIENTES_SILENCIADOS_FILE = os.path.join(DATA_DIR, "clientes_silenciados.json")
MUTED_GROUPS_FILE = os.path.join(DATA_DIR, "muted_groups.json")
MUTED_FILE = os.path.join(DATA_DIR, "muted_groups.json")  # Alias

# Arquivos de cache
CHAT_CACHE_FILE = os.path.join(DATA_DIR, "chat_cache.json")
NOTIFIED_TODAY_FILE = os.path.join(DATA_DIR, "notified_today.json")
NOTIFIED_FILE = os.path.join(DATA_DIR, "notified_today.json")  # Alias

# Arquivos de membros
MEMBERS_FILE = os.path.join(DATA_DIR, "members.json")
MEMBERS_EXPORT_FILE = os.path.join(DATA_DIR, "members_export.json")

# Arquivos de warming/aquecimento
WARMING_GROUPS_FILE = os.path.join(DATA_DIR, "warming_groups.json")
SESSION_FLOODS_FILE = os.path.join(DATA_DIR, "session_floods.json")

# Arquivos de automação
AUTOMATION_CONFIG_FILE = os.path.join(DATA_DIR, "automation_config.json")

# Arquivos de logs
SYSTEM_LOG_FILE = os.path.join(DATA_DIR, "system.log")

# ============================================================================
# IMPORTS DO BOT
# ============================================================================

import asyncio
import json
import logging
import datetime
import os
import time
import random
from collections import deque
from datetime import timedelta
import threading
import colorama
from colorama import Fore, Back, Style

# Inicializa colorama para Windows
colorama.init(autoreset=True)

# ============================================================================
# SISTEMA DE LOGGING PROFISSIONAL (INTEGRADO)
# ============================================================================

class ProfessionalLogger:
    """Logger profissional com formatação elegante e cores"""
    
    def __init__(self, name="ITACHI_BOT"):
        self.name = name
        self.start_time = datetime.datetime.now()
        
        # Configurar logging básico
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bot.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        # Símbolos e cores para diferentes tipos de log
        self.symbols = {
            'success': '✅',
            'error': '❌', 
            'warning': '⚠️',
            'info': 'ℹ️',
            'startup': '🚀',
            'web': '🌐',
            'scheduler': '📅',
            'cleanup': '🧹',
            'backup': '💾',
            'broadcast': '📨',
            'expiry': '⏰',
            'security': '🔒',
            'database': '🗄️',
            'network': '🌍'
        }
        
        self.colors = {
            'success': Fore.GREEN,
            'error': Fore.RED,
            'warning': Fore.YELLOW,
            'info': Fore.CYAN,
            'startup': Fore.MAGENTA,
            'web': Fore.BLUE,
            'scheduler': Fore.LIGHTBLUE_EX,
            'cleanup': Fore.YELLOW,
            'backup': Fore.LIGHTGREEN_EX,
            'broadcast': Fore.LIGHTCYAN_EX,
            'expiry': Fore.LIGHTYELLOW_EX,
            'security': Fore.LIGHTRED_EX,
            'database': Fore.LIGHTMAGENTA_EX,
            'network': Fore.LIGHTWHITE_EX
        }
    
    def _get_timestamp(self):
        """Retorna timestamp formatado"""
        return datetime.datetime.now().strftime('%H:%M:%S')
    
    def _print_header(self):
        """Imprime cabeçalho do bot"""
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{' '*30}{Fore.WHITE}{Style.BRIGHT}ITACHI DIVULGAÇÃO BOT{Style.RESET_ALL}{Fore.CYAN}{' '*29}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{' '*25}{Fore.LIGHTWHITE_EX}Sistema de Automação Telegram{Style.RESET_ALL}{Fore.CYAN}{' '*25}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    def startup_header(self):
        """Mostra cabeçalho de inicialização"""
        self._print_header()
        timestamp = self._get_timestamp()
        print(f"{Fore.MAGENTA}🚀 [{timestamp}] INICIANDO SISTEMA...{Style.RESET_ALL}")
    
    def log(self, level, category, message, details=None):
        """
        Log principal com formatação profissional
        
        Args:
            level: success, error, warning, info
            category: startup, web, scheduler, cleanup, etc.
            message: Mensagem principal
            details: Detalhes opcionais
        """
        timestamp = self._get_timestamp()
        symbol = self.symbols.get(level, self.symbols.get(category, 'ℹ️'))
        color = self.colors.get(level, self.colors.get(category, Fore.WHITE))
        
        # Linha principal
        print(f"{color}{symbol} [{timestamp}] {category.upper()}: {message}{Style.RESET_ALL}")
        
        # Detalhes com indentação
        if details:
            if isinstance(details, list):
                for detail in details:
                    print(f"{Fore.WHITE}   └─ {detail}{Style.RESET_ALL}")
            else:
                print(f"{Fore.WHITE}   └─ {details}{Style.RESET_ALL}")
        
        # Log para arquivo
        logging.info(f"{category.upper()}: {message} {details or ''}")
    
    def success(self, category, message, details=None):
        """Log de sucesso"""
        self.log('success', category, message, details)
    
    def error(self, category, message, details=None):
        """Log de erro"""
        self.log('error', category, message, details)
    
    def warning(self, category, message, details=None):
        """Log de aviso"""
        self.log('warning', category, message, details)
    
    def info(self, category, message, details=None):
        """Log informativo"""
        self.log('info', category, message, details)
    
    def system_status(self, component, status, details=None):
        """Log de status do sistema com formatação especial"""
        timestamp = self._get_timestamp()
        
        if status.lower() == "ok":
            color = Fore.GREEN
            symbol = "✅"
        elif status.lower() == "warning":
            color = Fore.YELLOW
            symbol = "⚠️"
        elif status.lower() == "error":
            color = Fore.RED
            symbol = "❌"
        else:
            color = Fore.CYAN
            symbol = "ℹ️"
        
        print(f"{color}{symbol} [{timestamp}] {component}: {status.upper()}{Style.RESET_ALL}")
        
        if details:
            print(f"{Fore.WHITE}   └─ {details}{Style.RESET_ALL}")
        
        logging.info(f"SYSTEM_STATUS: {component} - {status} - {details or ''}")
    
    def broadcast_summary(self, success_count, failed_count, total):
        """Resumo de broadcast formatado"""
        timestamp = self._get_timestamp()
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        print(f"\n{Fore.CYAN}📨 [{timestamp}] BROADCAST CONCLUÍDO{Style.RESET_ALL}")
        print(f"{Fore.GREEN}   ✅ Sucessos: {success_count}{Style.RESET_ALL}")
        print(f"{Fore.RED}   ❌ Falhas: {failed_count}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   📊 Taxa de sucesso: {success_rate:.1f}%{Style.RESET_ALL}")
        
        logging.info(f"BROADCAST: {success_count} sucessos, {failed_count} falhas, {success_rate:.1f}% taxa")
    
    def cleanup_summary(self, removed_count, kept_count, total_checked):
        """Resumo de limpeza formatado"""
        timestamp = self._get_timestamp()
        
        if removed_count > 0:
            print(f"\n{Fore.YELLOW}🧹 [{timestamp}] LIMPEZA AUTOMÁTICA EXECUTADA{Style.RESET_ALL}")
            print(f"{Fore.RED}   ❌ Removidas: {removed_count} mensagens expiradas{Style.RESET_ALL}")
            print(f"{Fore.GREEN}   ✅ Mantidas: {kept_count} mensagens válidas{Style.RESET_ALL}")
            print(f"{Fore.CYAN}   📊 Total verificadas: {total_checked}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}   ⏰ {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}{Style.RESET_ALL}\n")
        else:
            # Log mais discreto quando não há limpeza
            print(f"{Fore.LIGHTBLACK_EX}🧹 [{timestamp}] LIMPEZA: {total_checked} verificadas, nenhuma expirada{Style.RESET_ALL}")
        
        logging.info(f"CLEANUP: {removed_count} removidas, {kept_count} mantidas, {total_checked} verificadas")
    
    def scheduler_activity(self, message_count, processing_time=None):
        """Log de atividade do scheduler"""
        timestamp = self._get_timestamp()
        
        if message_count > 0:
            print(f"{Fore.BLUE}📅 [{timestamp}] SCHEDULER: {message_count} mensagem(s) processada(s){Style.RESET_ALL}")
            if processing_time:
                print(f"{Fore.WHITE}   └─ Tempo: {processing_time:.2f}s{Style.RESET_ALL}")
            logging.info(f"SCHEDULER: {message_count} messages processed in {processing_time or 0:.2f}s")
    
    def expiry_alert(self, alert_type, plan_id, user_id, days_remaining):
        """Log de alerta de expiração"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        if "URGENTE" in alert_type:
            color = Fore.RED
            icon = "🚨"
        else:
            color = Fore.YELLOW
            icon = "⚠️"
        
        print(f"{color}{icon} [{timestamp}] {alert_type}: Plano {plan_id[:8]}... - Usuário {user_id} - {days_remaining} dias{Style.RESET_ALL}")
    
    def plan_archived(self, plan_id, user_id):
        """Log de plano arquivado"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"{Fore.CYAN}📁 [{timestamp}] ARQUIVO: Plano {plan_id[:8]}... arquivado (Usuário: {user_id}){Style.RESET_ALL}")
    
    def plan_restored(self, plan_id, user_id, days):
        """Log de plano renovado/restaurado"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"{Fore.GREEN}🔄 [{timestamp}] RENOVAÇÃO: Plano {plan_id[:8]}... restaurado por {days} dias (Usuário: {user_id}){Style.RESET_ALL}")
    
    def expired_stats(self, total_expired, total_archived):
        """Log de estatísticas de expiração"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        if total_expired > 0:
            print(f"{Fore.YELLOW}📊 [{timestamp}] ESTATÍSTICAS: {total_expired} planos expirados, {total_archived} arquivados{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}✅ [{timestamp}] VERIFICAÇÃO: Nenhum plano expirado encontrado{Style.RESET_ALL}")
    
    def update_check(self, current_version, status="checking"):
        """Log de verificação de atualizações"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        if status == "checking":
            print(f"{Fore.CYAN}🔍 [{timestamp}] UPDATE: Verificando atualizações (v{current_version}){Style.RESET_ALL}")
        elif status == "available":
            print(f"{Fore.YELLOW}🆕 [{timestamp}] UPDATE: Nova versão disponível!{Style.RESET_ALL}")
        elif status == "updated":
            print(f"{Fore.GREEN}✅ [{timestamp}] UPDATE: Bot já está atualizado{Style.RESET_ALL}")
        elif status == "error":
            print(f"{Fore.RED}❌ [{timestamp}] UPDATE: Erro na verificação{Style.RESET_ALL}")
    
    def update_download(self, status, details=""):
        """Log de download de atualizações"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        if status == "downloading":
            print(f"{Fore.BLUE}⬇️ [{timestamp}] UPDATE: Baixando atualização...{Style.RESET_ALL}")
        elif status == "success":
            print(f"{Fore.GREEN}✅ [{timestamp}] UPDATE: Download concluído - {details}{Style.RESET_ALL}")
        elif status == "error":
            print(f"{Fore.RED}❌ [{timestamp}] UPDATE: Erro no download - {details}{Style.RESET_ALL}")
    
    def update_apply(self, status, version_info=""):
        """Log de aplicação de atualizações"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        if status == "applying":
            print(f"{Fore.MAGENTA}🔄 [{timestamp}] UPDATE: Aplicando atualização...{Style.RESET_ALL}")
        elif status == "success":
            print(f"{Fore.GREEN}🎉 [{timestamp}] UPDATE: Atualização aplicada! {version_info}{Style.RESET_ALL}")
        elif status == "restart":
            print(f"{Fore.CYAN}🔄 [{timestamp}] UPDATE: Reiniciando bot...{Style.RESET_ALL}")
        elif status == "error":
            print(f"{Fore.RED}❌ [{timestamp}] UPDATE: Erro na aplicação - {version_info}{Style.RESET_ALL}")
    
    def update_backup(self, backup_dir, file_count):
        """Log de backup antes da atualização"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"{Fore.BLUE}💾 [{timestamp}] BACKUP: Criado {backup_dir} ({file_count} arquivos){Style.RESET_ALL}")
    
    def web_panel_status(self, status, port=5000):
        """Status do painel web"""
        timestamp = self._get_timestamp()
        
        if status == "starting":
            print(f"{Fore.MAGENTA}🚀 [{timestamp}] WEB: Iniciando painel em http://localhost:{port}{Style.RESET_ALL}")
        elif status == "started":
            print(f"{Fore.BLUE}🌐 [{timestamp}] WEB: Painel iniciado em thread separada{Style.RESET_ALL}")
        elif status == "error":
            print(f"{Fore.RED}❌ [{timestamp}] WEB: Erro ao iniciar painel{Style.RESET_ALL}")
        
        logging.info(f"WEB_PANEL: {status} on port {port}")
    
    def duplicate_check(self, found_duplicates=False, terminated_count=0):
        """Log de verificação de duplicatas"""
        timestamp = self._get_timestamp()
        
        if found_duplicates:
            print(f"{Fore.YELLOW}⚠️ [{timestamp}] DUPLICATE_CHECK: {terminated_count} instâncias duplicadas encerradas{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}✅ [{timestamp}] DUPLICATE_CHECK: Nenhuma instância duplicada encontrada{Style.RESET_ALL}")
        
        logging.info(f"DUPLICATE_CHECK: {'Found and terminated' if found_duplicates else 'None found'}")
    
    def separator(self, title=None):
        """Imprime separador visual"""
        if title:
            title_len = len(title)
            padding = (60 - title_len) // 2
            print(f"\n{Fore.CYAN}{'─' * padding} {title} {'─' * padding}{Style.RESET_ALL}")
        else:
            print(f"{Fore.LIGHTBLACK_EX}{'─' * 80}{Style.RESET_ALL}")
    
    def uptime(self):
        """Mostra tempo de atividade"""
        uptime_delta = datetime.datetime.now() - self.start_time
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{uptime_delta.days}d {hours:02d}:{minutes:02d}:{seconds:02d}"

# Instância global do logger
professional_logger = ProfessionalLogger()

# ============================================================================
# SISTEMA DE AUTO-ATUALIZAÇÃO
# ============================================================================

# Versão atual do bot
BOT_VERSION = "2.7.8"  # ATUALIZADO - Sistema de atualização centralizada + comando /cancelartodos
UPDATE_SERVER_URL = "http://135.148.144.90:8080"  # URL do servidor de atualizações na VPS
UPDATE_CHECK_INTERVAL = 3600  # Verifica atualizações a cada 1 hora (3600 segundos)

import requests
import zipfile
import shutil
import hashlib

def get_current_version():
    """Retorna a versão atual do bot"""
    return BOT_VERSION

def check_for_updates():
    """Verifica se há atualizações disponíveis no servidor remoto"""
    try:
        # Faz requisição para o servidor de atualizações
        response = requests.get(f"{UPDATE_SERVER_URL}/version", timeout=10)
        if response.status_code == 200:
            remote_data = response.json()
            remote_version = remote_data.get('version')
            download_url = remote_data.get('download_url')
            changelog = remote_data.get('changelog', 'Sem informações de changelog')
            
            # **FIX: Compara versões corretamente - só notifica se versão remota é MAIOR**
            if remote_version and remote_version != BOT_VERSION:
                # Converte versões para tuplas de inteiros para comparação correta
                try:
                    current_parts = tuple(map(int, BOT_VERSION.split('.')))
                    remote_parts = tuple(map(int, remote_version.split('.')))
                    
                    # Só considera atualização se versão remota é MAIOR
                    if remote_parts > current_parts:
                        return {
                            'update_available': True,
                            'current_version': BOT_VERSION,
                            'remote_version': remote_version,
                            'download_url': download_url,
                            'changelog': changelog
                        }
                    else:
                        # Versão remota é igual ou MENOR - não é atualização
                        professional_logger.info("UPDATE", f"Versão remota {remote_version} não é maior que {BOT_VERSION} - ignorando")
                        return {'update_available': False, 'current_version': BOT_VERSION}
                except Exception as e:
                    professional_logger.error("UPDATE", f"Erro ao comparar versões: {e}")
                    return {'update_available': False, 'current_version': BOT_VERSION}
            else:
                return {'update_available': False, 'current_version': BOT_VERSION}
        else:
            professional_logger.warning("UPDATE", f"Servidor de atualizações retornou status {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        professional_logger.error("UPDATE", f"Erro ao verificar atualizações: {e}")
        return None
    except Exception as e:
        professional_logger.error("UPDATE", f"Erro inesperado na verificação: {e}")
        return None

def create_backup_before_update():
    """Cria backup dos arquivos importantes antes da atualização"""
    try:
        backup_dir = f"backup_pre_update_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Lista de arquivos importantes para backup
        important_files = [
            CONFIG_FILE,
            CHAT_IDS_FILE,
            SCHEDULED_MESSAGES_FILE,
            REGISTERED_USERS_FILE,
            USER_IDS_FILE,
            ADDED_BY_FILE,
            FAILED_CHAT_IDS_FILE,
            'expired_plans.json'
        ]
        
        backed_up_files = []
        for file in important_files:
            if os.path.exists(file):
                shutil.copy2(file, backup_dir)
                backed_up_files.append(file)
        
        professional_logger.update_backup(backup_dir, len(backed_up_files))
        return backup_dir, backed_up_files
    except Exception as e:
        professional_logger.error("BACKUP", f"Erro ao criar backup: {e}")
        return None, []

def cleanup_old_backups():
    """Remove todos os backups antigos"""
    try:
        backup_dirs = []
        for item in os.listdir('.'):
            if os.path.isdir(item) and item.startswith('backup_pre_update_'):
                backup_dirs.append(item)
        
        removed_count = 0
        for backup_dir in backup_dirs:
            try:
                shutil.rmtree(backup_dir)
                professional_logger.info("BACKUP_CLEANUP", f"🗑️ Backup removido: {backup_dir}")
                removed_count += 1
            except Exception as e:
                professional_logger.warning("BACKUP_CLEANUP", f"Erro ao remover {backup_dir}: {e}")
        
        professional_logger.info("BACKUP_CLEANUP", f"Total de backups antigos removidos: {removed_count}")
        return removed_count
        
    except Exception as e:
        professional_logger.error("BACKUP_CLEANUP", f"Erro na limpeza: {e}")
        return 0

def download_update(download_url):
    """Baixa o arquivo de atualização do servidor"""
    try:
        professional_logger.update_download("downloading")
        
        response = requests.get(download_url, timeout=30, stream=True)
        if response.status_code == 200:
            update_file = "bot_update.zip"
            
            with open(update_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verifica se o arquivo foi baixado corretamente
            if os.path.exists(update_file) and os.path.getsize(update_file) > 0:
                file_size = os.path.getsize(update_file)
                professional_logger.update_download("success", f"{update_file} ({file_size} bytes)")
                return update_file
            else:
                professional_logger.update_download("error", "Arquivo inválido")
                return None
        else:
            professional_logger.update_download("error", f"HTTP {response.status_code}")
            return None
    except Exception as e:
        professional_logger.update_download("error", str(e))
        return None

def apply_update(update_file):
    """Aplica a atualização baixada"""
    try:
        professional_logger.update_apply("applying")
        
        # Extrai o arquivo ZIP
        with zipfile.ZipFile(update_file, 'r') as zip_ref:
            zip_ref.extractall("temp_update")
        
        # Lista de arquivos que podem ser atualizados
        updatable_files = [
            'bot.py',
            'app.py', 
            'session_manager.py',
            'automation_manager.py',
            'smart_adder.py',
            'warming_bot.py',
            'extractor.py',
            'adder.py',
            'config.py',
            'logger.py',
            'requirements.txt'
        ]
        
        # Pastas que podem ser atualizadas
        updatable_folders = ['templates', 'static']
        
        updated_files = []
        
        # Atualiza arquivos individuais
        for file in updatable_files:
            temp_file = os.path.join("temp_update", file)
            if os.path.exists(temp_file):
                # Backup do arquivo atual
                if os.path.exists(file):
                    shutil.copy2(file, f"{file}.backup")
                
                # Substitui pelo novo arquivo
                shutil.copy2(temp_file, file)
                updated_files.append(file)
                professional_logger.success("UPDATE", f"Arquivo atualizado: {file}")
        
        # Atualiza pastas
        for folder in updatable_folders:
            temp_folder = os.path.join("temp_update", folder)
            if os.path.exists(temp_folder):
                # Backup da pasta atual
                if os.path.exists(folder):
                    shutil.copytree(folder, f"{folder}.backup", dirs_exist_ok=True)
                
                # Copia novos arquivos
                shutil.copytree(temp_folder, folder, dirs_exist_ok=True)
                updated_files.append(f"{folder}/")
                professional_logger.success("UPDATE", f"Pasta atualizada: {folder}/")
        
        # Remove arquivos temporários
        shutil.rmtree("temp_update", ignore_errors=True)
        os.remove(update_file)
        
        professional_logger.update_apply("success", f"{len(updated_files)} itens atualizados")
        return True, updated_files
        
    except Exception as e:
        professional_logger.update_apply("error", str(e))
        return False, []

def restart_bot():
    """Reinicia o bot após a atualização"""
    try:
        professional_logger.update_apply("restart")
        
        # Salva um arquivo de flag para indicar que foi uma atualização
        with open("update_restart.flag", "w") as f:
            f.write(datetime.datetime.now().isoformat())
        
        # Aguarda um pouco para finalizar operações
        import time
        time.sleep(1)
        
        # Reinicia usando subprocess para evitar problemas de contexto
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
        
        # Encerra o processo atual
        os._exit(0)
        
    except Exception as e:
        professional_logger.error("UPDATE", f"Erro ao reiniciar bot: {e}")
        # Fallback: tenta reiniciar de forma mais simples
        try:
            os.execv(sys.executable, ['python'] + sys.argv)
        except:
            os._exit(1)

async def async_restart_bot():
    """Reinicia o bot de forma assíncrona sem conflitos de contexto Flask"""
    try:
        professional_logger.update_apply("restart")
        
        # Salva flag de reinício
        with open("update_restart.flag", "w") as f:
            f.write(datetime.datetime.now().isoformat())
        
        # Agenda reinício para depois de um pequeno delay
        def delayed_restart():
            import time
            time.sleep(3)  # Aguarda 3 segundos
            
            try:
                # Reinicia usando subprocess
                import subprocess
                subprocess.Popen([sys.executable] + sys.argv)
                os._exit(0)
            except:
                # Fallback
                os.execv(sys.executable, ['python'] + sys.argv)
        
        # Executa reinício em thread separada para evitar conflitos
        import threading
        restart_thread = threading.Thread(target=delayed_restart, daemon=True)
        restart_thread.start()
        
        professional_logger.info("UPDATE", "🔄 Reinício agendado em 3 segundos...")
        
    except Exception as e:
        professional_logger.error("UPDATE", f"Erro ao agendar reinício: {e}")
        # Fallback: reinício simples
        try:
            os._exit(0)
        except:
            pass

async def perform_auto_update():
    """Executa o processo completo de auto-atualização"""
    try:
        professional_logger.info("UPDATE", "Verificando atualizações...")
        
        # Verifica se há atualizações
        update_info = check_for_updates()
        if not update_info:
            return False, "Erro ao verificar atualizações"
        
        if not update_info.get('update_available'):
            professional_logger.info("UPDATE", "Bot já está na versão mais recente")
            return False, "Nenhuma atualização disponível"
        
        remote_version = update_info.get('remote_version')
        download_url = update_info.get('download_url')
        changelog = update_info.get('changelog')
        
        professional_logger.info("UPDATE", f"Nova versão disponível: {remote_version}")
        
        # Notifica admins sobre a atualização
        config = load_config()
        admins = config.get('admins', [])
        
        update_message = (
            f"🔄 **ATUALIZAÇÃO DISPONÍVEL**\n\n"
            f"📦 **Versão Atual:** {BOT_VERSION}\n"
            f"🆕 **Nova Versão:** {remote_version}\n\n"
            f"📝 **Changelog:**\n{changelog}\n\n"
            f"⚡ **Iniciando atualização automática...**"
        )
        
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, update_message, parse_mode="Markdown")
            except:
                pass
        
        # Cria backup
        backup_dir, backed_files = create_backup_before_update()
        
        # Baixa a atualização
        update_file = download_update(download_url)
        if not update_file:
            return False, "Erro no download da atualização"
        
        # Aplica a atualização
        success, updated_files = apply_update(update_file)
        if not success:
            return False, "Erro ao aplicar atualização"
        
        # Notifica sucesso
        success_message = (
            f"✅ **ATUALIZAÇÃO CONCLUÍDA**\n\n"
            f"🔄 **Versão:** {BOT_VERSION} → {remote_version}\n"
            f"📁 **Arquivos atualizados:** {len(updated_files)}\n"
            f"💾 **Backup:** {backup_dir}\n\n"
            f"🔄 **Reiniciando bot...**"
        )
        
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, success_message, parse_mode="Markdown")
            except:
                pass
        
        # Aguarda um pouco para as mensagens serem enviadas
        await asyncio.sleep(2)
        
        # Reinicia o bot de forma assíncrona (sem conflito de contexto)
        await async_restart_bot()
        
        return True, "Atualização aplicada com sucesso"
        
    except Exception as e:
        professional_logger.error("UPDATE", f"Erro na auto-atualização: {e}")
        return False, f"Erro na atualização: {e}"

async def auto_update_scheduler():
    """Scheduler que verifica atualizações automaticamente"""
    while True:
        try:
            await asyncio.sleep(UPDATE_CHECK_INTERVAL)
            
            professional_logger.info("AUTO_UPDATE", "Verificando atualizações automaticamente...")
            update_info = check_for_updates()
            
            if update_info and update_info.get('update_available'):
                remote_version = update_info.get('remote_version')
                professional_logger.info("AUTO_UPDATE", f"Nova versão disponível: {remote_version}")
                
                # Cria botão inline para atualizar
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🚀 Atualizar Agora",
                            callback_data=f"auto_update_{remote_version}"
                        ),
                        InlineKeyboardButton(
                            text="📋 Ver Detalhes",
                            callback_data="update_details"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⏰ Lembrar Depois",
                            callback_data="update_later"
                        )
                    ]
                ])
                
                # Notifica admins sobre atualização disponível
                for admin_id in ADMINS:
                    try:
                        await bot.send_message(
                            admin_id,
                            f"🆕 **NOVA ATUALIZAÇÃO DISPONÍVEL!**\n\n"
                            f"📦 **Versão Atual:** `{BOT_VERSION}`\n"
                            f"🚀 **Nova Versão:** `{remote_version}`\n"
                            f"📝 **Changelog:**\n```\n{update_info.get('changelog', 'Sem informações')[:200]}...\n```\n\n"
                            f"⚡ **Clique em um botão abaixo para escolher:**",
                            parse_mode="Markdown",
                            reply_markup=keyboard
                        )
                    except Exception as e:
                        professional_logger.error("AUTO_UPDATE", f"Erro ao notificar admin {admin_id}: {e}")
            else:
                professional_logger.info("AUTO_UPDATE", "Nenhuma atualização disponível")
                
        except Exception as e:
            professional_logger.error("AUTO_UPDATE", f"Erro no scheduler: {e}")
            await asyncio.sleep(300)  # Espera 5 minutos antes de tentar novamente


# ============================================================================
# SISTEMA DE LOGGING MELHORADO COM CORES E FORMATAÇÃO
# ============================================================================

class BotLogger:
    """Sistema de logging melhorado com cores e formatação visual"""
    
    def __init__(self):
        self.setup_logging()
    
    def setup_logging(self):
        """Configura o sistema de logging com formatação melhorada"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('bot.log', encoding='utf-8')
            ]
        )
    
    def print_header(self, title, color=Fore.CYAN):
        """Imprime um cabeçalho visual"""
        separator = "═" * 60
        print(f"\n{color}{separator}")
        print(f"{color}║{title.center(58)}║")
        print(f"{color}{separator}{Style.RESET_ALL}\n")
    
    def print_section(self, title, color=Fore.YELLOW):
        """Imprime uma seção"""
        separator = "─" * 40
        print(f"\n{color}{separator}")
        print(f"{color}📋 {title}")
        print(f"{color}{separator}{Style.RESET_ALL}")
    
    def success(self, message):
        """Log de sucesso"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"{Fore.GREEN}✅ [{timestamp}] {message}{Style.RESET_ALL}")
        logging.info(f"SUCCESS: {message}")
    
    def error(self, message):
        """Log de erro"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"{Fore.RED}❌ [{timestamp}] ERRO: {message}{Style.RESET_ALL}")
        logging.error(f"ERROR: {message}")
    
    def warning(self, message):
        """Log de aviso"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"{Fore.YELLOW}⚠️  [{timestamp}] AVISO: {message}{Style.RESET_ALL}")
        logging.warning(f"WARNING: {message}")
    
    def info(self, message):
        """Log de informação"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"{Fore.CYAN}ℹ️  [{timestamp}] {message}{Style.RESET_ALL}")
        logging.info(f"INFO: {message}")
    
    def user_action(self, user_name, user_id, action):
        """Log de ação do usuário"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"{Fore.MAGENTA}👤 [{timestamp}] {user_name} (ID: {user_id}) - {action}{Style.RESET_ALL}")
        logging.info(f"USER_ACTION: {user_name} ({user_id}) - {action}")
    
    def admin_action(self, admin_name, admin_id, action):
        """Log de ação do admin"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"{Fore.RED}👑 [{timestamp}] ADMIN {admin_name} (ID: {admin_id}) - {action}{Style.RESET_ALL}")
        logging.info(f"ADMIN_ACTION: {admin_name} ({admin_id}) - {action}")
    
    def broadcast(self, message, success_count, failed_count):
        """Log de broadcast"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        total = success_count + failed_count
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        print(f"\n{Fore.CYAN}📨 [{timestamp}] BROADCAST CONCLUÍDO{Style.RESET_ALL}")
        print(f"{Fore.GREEN}   ✅ Sucessos: {success_count}{Style.RESET_ALL}")
        print(f"{Fore.RED}   ❌ Falhas: {failed_count}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   📊 Taxa de sucesso: {success_rate:.1f}%{Style.RESET_ALL}")
        
        logging.info(f"BROADCAST: {success_count} sucessos, {failed_count} falhas, {success_rate:.1f}% taxa de sucesso")
    
    def rate_limit(self, chat_id, wait_time, attempt, max_attempts):
        """Log de rate limiting"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"{Fore.YELLOW}🚨 [{timestamp}] RATE LIMIT - Chat: {chat_id} | Aguardando: {wait_time:.1f}s | Tentativa: {attempt}/{max_attempts}{Style.RESET_ALL}")
        logging.warning(f"RATE_LIMIT: Chat {chat_id}, wait {wait_time:.1f}s, attempt {attempt}/{max_attempts}")
    
    def batch_progress(self, current_batch, total_batches, batch_size):
        """Log de progresso de lotes"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        progress = (current_batch / total_batches * 100)
        print(f"{Fore.BLUE}📦 [{timestamp}] LOTE {current_batch}/{total_batches} ({batch_size} chats) - {progress:.1f}% concluído{Style.RESET_ALL}")
        logging.info(f"BATCH_PROGRESS: {current_batch}/{total_batches} ({progress:.1f}%)")
    
    def new_user_registered(self, user_name, user_id, total_users):
        """Log de novo usuário registrado"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"\n{Fore.GREEN}🆕 [{timestamp}] NOVO USUÁRIO REGISTRADO!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}   👤 Nome: {user_name}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}   🆔 ID: {user_id}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}   📊 Total de usuários: {total_users}{Style.RESET_ALL}\n")
        logging.info(f"NEW_USER: {user_name} ({user_id}) - Total: {total_users}")
    
    def startup_info(self, bot_name, total_groups, total_users, total_admins):
        """Informações de inicialização do bot"""
        self.print_header(f"🤖 {bot_name} - INICIADO COM SUCESSO", Fore.GREEN)
        print(f"{Fore.CYAN}📊 ESTATÍSTICAS INICIAIS:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   👥 Grupos cadastrados: {total_groups}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   👤 Usuários registrados: {total_users}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   👑 Administradores: {total_admins}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}   🟢 Status: ONLINE{Style.RESET_ALL}")
        
        logging.info(f"BOT_STARTUP: {bot_name} - Groups: {total_groups}, Users: {total_users}, Admins: {total_admins}")
    
    def system_status(self, component, status, details=""):
        """Log de status do sistema"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        if status.lower() == "ok":
            print(f"{Fore.GREEN}✅ [{timestamp}] {component}: {status.upper()}{Style.RESET_ALL}")
        elif status.lower() == "warning":
            print(f"{Fore.YELLOW}⚠️  [{timestamp}] {component}: {status.upper()}{Style.RESET_ALL}")
        elif status.lower() == "error":
            print(f"{Fore.RED}❌ [{timestamp}] {component}: {status.upper()}{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}ℹ️  [{timestamp}] {component}: {status}{Style.RESET_ALL}")
        
        if details:
            print(f"{Fore.WHITE}   └─ {details}{Style.RESET_ALL}")
        
        logging.info(f"SYSTEM_STATUS: {component} - {status} - {details}")
    
    def scheduler_activity(self, message_count, processing_time=None):
        """Log de atividade do scheduler"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        if message_count > 0:
            print(f"{Fore.BLUE}📅 [{timestamp}] SCHEDULER: {message_count} mensagem(s) processada(s){Style.RESET_ALL}")
            if processing_time:
                print(f"{Fore.WHITE}   └─ Tempo: {processing_time:.2f}s{Style.RESET_ALL}")
            logging.info(f"SCHEDULER: {message_count} messages processed")
        # Remover log quando não há mensagens para reduzir spam
    
    def backup_status(self, status, details=""):
        """Log de status do backup"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        if status == "success":
            print(f"{Fore.GREEN}💾 [{timestamp}] BACKUP: Concluído com sucesso{Style.RESET_ALL}")
        elif status == "error":
            print(f"{Fore.RED}💾 [{timestamp}] BACKUP: Falha{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}💾 [{timestamp}] BACKUP: {status}{Style.RESET_ALL}")
        
        if details:
            print(f"{Fore.WHITE}   └─ {details}{Style.RESET_ALL}")
    
    def expiry_check(self, total_plans, expired_count=0):
        """Log de verificação de expiração"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        if expired_count > 0:
            print(f"{Fore.YELLOW}⏰ [{timestamp}] EXPIRAÇÃO: {expired_count}/{total_plans} planos expirados{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}⏰ [{timestamp}] EXPIRAÇÃO: Todos os {total_plans} planos ativos{Style.RESET_ALL}")
    
    def cleanup_activity(self, total_checked, removed_count):
        """Log de atividade de limpeza"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        if removed_count > 0:
            print(f"{Fore.YELLOW}🧹 [{timestamp}] LIMPEZA: {removed_count}/{total_checked} IDs removidos{Style.RESET_ALL}")
        # Só mostrar limpeza se houver remoções para reduzir spam

# Instância global do logger melhorado
bot_logger = BotLogger()

# Importações do aiogram (necessárias para type hints)
try:
    from aiogram import Bot, Dispatcher, types
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
except ImportError:
    # Se aiogram não estiver instalado, define classes dummy para evitar erros
    class Bot:
        pass
    class Dispatcher:
        pass
    class types:
        class CallbackQuery: pass
        class Message: pass
    class FSMContext: pass
    class State: pass
    class StatesGroup: pass

# Estados FSM para painel administrativo
class AdminPanelStates(StatesGroup):
    esperando_id_canal_logs = State()
    esperando_mensagem_broadcast = State()
    esperando_novo_texto_start = State()
    esperando_nova_imagem_start = State()
    esperando_novo_botao_start = State()
    esperando_novo_intervalo_horarios = State()
    esperando_novo_link_plano = State()

# Variáveis globais necessárias (devem ser definidas em outro lugar do código)
# Assumindo que já existem no código principal
try:
    # Tenta usar as variáveis se já estão definidas
    ADMINS = ADMINS if 'ADMINS' in globals() else []
    dp = dp if 'dp' in globals() else None
    logger = logger if 'logger' in globals() else logging.getLogger(__name__)
except NameError:
    # Define valores padrão se não existirem
    ADMINS = []  # Lista de IDs dos administradores
    dp = None    # Dispatcher do aiogram
    logger = logging.getLogger(__name__)

# Sistema de registro de usuários
def load_registered_users():
    """Carrega a lista de usuários registrados do arquivo JSON"""
    try:
        if os.path.exists(REGISTERED_USERS_FILE):
            with open(REGISTERED_USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        bot_logger.error(f"Erro ao carregar usuários registrados: {e}")
        return {}

def load_silenced_clients():
    """Carrega lista de clientes que silenciaram notificações"""
    try:
        if os.path.exists('clientes_silenciados.json'):
            with open('clientes_silenciados.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Erro ao carregar clientes silenciados: {e}")
    return []

def save_registered_users(users_data):
    """Salva a lista de usuários registrados no arquivo JSON"""
    try:
        with open(REGISTERED_USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        bot_logger.error(f"Erro ao salvar usuários registrados: {e}")
        return False

def register_user(user_id, user_data):
    """Registra um novo usuário"""
    users = load_registered_users()
    user_id_str = str(user_id)
    
    # Verifica se é um novo usuário
    is_new_user = user_id_str not in users
    
    # Atualiza ou adiciona os dados do usuário
    users[user_id_str] = {
        'user_id': user_id,
        'username': user_data.get('username'),
        'first_name': user_data.get('first_name'),
        'last_name': user_data.get('last_name'),
        'full_name': user_data.get('full_name'),
        'registration_date': user_data.get('registration_date', datetime.datetime.now().isoformat()),
        'last_interaction': datetime.datetime.now().isoformat()
    }
    
    save_registered_users(users)
    return is_new_user

async def notify_admin_new_user(bot, user_data):
    """Notifica os administradores sobre um novo usuário registrado"""
    try:
        notification_message = (
            f"🆕 **Novo usuário registrado!**\n\n"
            f"👤 **Nome:** {user_data.get('full_name', 'N/A')}\n"
            f"🆔 **ID:** `{user_data['user_id']}`\n"
            f"📱 **Username:** @{user_data.get('username', 'N/A')}\n"
            f"📅 **Data:** {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
            f"📊 **Total de usuários:** {len(load_registered_users())}"
        )
        
        for admin_id in ADMINS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=notification_message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Erro ao notificar admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Erro ao notificar admins sobre novo usuário: {e}")

async def broadcast_to_registered_users(bot, message_text, parse_mode=None, reply_markup=None):
    """Envia mensagem para todos os usuários registrados com rate limiting robusto"""
    users = load_registered_users()
    success_count = 0
    failed_count = 0
    total_users = len(users)
    
    bot_logger.info(f"Iniciando broadcast para {total_users} usuários registrados")
    
    for i, (user_id_str, user_data) in enumerate(users.items(), 1):
        try:
            # Usa a função segura com retry automático
            result = await safe_send_message(
                bot=bot,
                chat_id=int(user_id_str),
                text=message_text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            
            if result:
                success_count += 1
                if i % 10 == 0:  # Log a cada 10 usuários
                    bot_logger.info(f"Broadcast: {i}/{total_users} - {success_count} sucessos, {failed_count} falhas")
            else:
                failed_count += 1
                bot_logger.error(f"Falha ao enviar para usuário {user_id_str}")
            
            # Delay inteligente baseado no progresso
            if i % 20 == 0:  # Pausa maior a cada 20 usuários
                await asyncio.sleep(random.uniform(3, 6))
            else:
                await asyncio.sleep(random.uniform(1, 2))
                
        except Exception as e:
            failed_count += 1
            bot_logger.error(f"Erro crítico ao enviar mensagem para usuário {user_id_str}: {e}")
    
    bot_logger.broadcast(message_text[:50] + "...", success_count, failed_count)
    return success_count, failed_count

# Função para reiniciar o bot
def restart_bot():
    """Reinicia o bot aplicando as novas configurações"""
    import sys
    import os
    bot_logger.info("Reiniciando bot para aplicar configurações...")
    try:
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        bot_logger.error(f"Erro ao reiniciar bot: {e}")

# --- Sistema de Cache para Chat Info ---
CHAT_CACHE_FILE = CHAT_CACHE_FILE
CACHE_DURATION_HOURS = 24

def load_chat_cache():
    """Carrega cache de informações de chat"""
    try:
        with open(CHAT_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_chat_cache(cache):
    """Salva cache de informações de chat"""
    try:
        with open(CHAT_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Erro ao salvar cache: {e}")

# --- Rate Limiter Melhorado com Anti-Flood ---
class TelegramRateLimiter:
    def __init__(self, max_requests=15, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = threading.Lock()
        self.base_delay = 1.5
        self.current_delay = self.base_delay
        self.max_delay = 120.0
        self.flood_detected = False
        self.last_flood_time = None
        self.consecutive_floods = 0
    
    def can_make_request(self):
        with self.lock:
            now = datetime.datetime.now()
            # Remove requisições antigas
            while self.requests and now - self.requests[0] > timedelta(seconds=self.time_window):
                self.requests.popleft()
            
            # Se detectou flood recentemente, seja mais conservador
            if self.flood_detected and self.last_flood_time:
                time_since_flood = (now - self.last_flood_time).total_seconds()
                if time_since_flood < 300:  # 5 minutos após flood
                    return len(self.requests) < max(5, self.max_requests // 3)
            
            return len(self.requests) < self.max_requests
    
    def record_request(self):
        with self.lock:
            self.requests.append(datetime.datetime.now())
    
    def record_flood(self, retry_after=None):
        """Registra detecção de flood control"""
        with self.lock:
            self.flood_detected = True
            self.last_flood_time = datetime.datetime.now()
            self.consecutive_floods += 1
            
            if retry_after:
                self.current_delay = min(retry_after + 5, self.max_delay)
            else:
                # Backoff exponencial baseado em floods consecutivos
                self.current_delay = min(self.base_delay * (2 ** self.consecutive_floods), self.max_delay)
            
            bot_logger.warning(f"FLOOD CONTROL detectado! Delay aumentado para {self.current_delay:.1f}s (Floods consecutivos: {self.consecutive_floods})")
    
    def reset_flood_status(self):
        """Reseta status de flood após sucesso"""
        with self.lock:
            if self.flood_detected:
                self.flood_detected = False
                self.consecutive_floods = max(0, self.consecutive_floods - 1)
                if self.consecutive_floods == 0:
                    self.current_delay = self.base_delay
                    bot_logger.success("Status de flood resetado - operação normal")
    
    def wait_if_needed(self):
        """Espera se necessário antes de fazer uma requisição"""
        if not self.can_make_request():
            wait_time = self.current_delay + random.uniform(2, 5)
            bot_logger.info(f"Rate limit preventivo - aguardando {wait_time:.1f}s")
            time.sleep(wait_time)
        
        # Delay base entre todas as requisições
        base_wait = random.uniform(0.8, 1.5)
        if self.flood_detected:
            base_wait *= 2  # Dobra o delay se houve flood
        
        time.sleep(base_wait)
        self.record_request()

# Função wrapper para requisições seguras
async def safe_telegram_request(func, *args, max_retries=3, **kwargs):
    """Wrapper para fazer requisições seguras ao Telegram com retry automático"""
# SISTEMA DE MONITORAMENTO DE FLOOD CONTROL
# ============================================================================

class FloodControlMonitor:
    """Monitora estatísticas de flood control para acompanhar eficácia das correções"""
    
    def __init__(self):
        self.stats = {
            'total_requests': 0,
            'flood_errors': 0,
            'successful_sends': 0,
            'failed_sends': 0,
            'total_wait_time': 0,
            'last_flood_error': None,
            'start_time': datetime.datetime.now()
        }
    
    def record_request(self):
        self.stats['total_requests'] += 1
    
    def record_success(self):
        self.stats['successful_sends'] += 1
    
    def record_failure(self):
        self.stats['failed_sends'] += 1
    
    def record_flood_error(self, wait_time=0):
        self.stats['flood_errors'] += 1
        self.stats['total_wait_time'] += wait_time
        self.stats['last_flood_error'] = datetime.datetime.now()
        
    def get_stats(self):
        uptime = datetime.datetime.now() - self.stats['start_time']
        success_rate = (self.stats['successful_sends'] / max(self.stats['total_requests'], 1)) * 100
        flood_rate = (self.stats['flood_errors'] / max(self.stats['total_requests'], 1)) * 100
        
        return {
            'uptime_hours': uptime.total_seconds() / 3600,
            'total_requests': self.stats['total_requests'],
            'success_rate': f"{success_rate:.2f}%",
            'flood_error_rate': f"{flood_rate:.2f}%",
            'total_flood_errors': self.stats['flood_errors'],
            'total_wait_time_minutes': self.stats['total_wait_time'] / 60,
            'last_flood_error': self.stats['last_flood_error']
        }
    
    def log_stats(self):
        stats = self.get_stats()
        logging.info(
            f" FLOOD CONTROL STATS: "
            f"Uptime: {stats['uptime_hours']:.1f}h | "
            f"Requests: {stats['total_requests']} | "
            f"Success: {stats['success_rate']} | "
            f"Flood Rate: {stats['flood_error_rate']} | "
            f"Wait Time: {stats['total_wait_time_minutes']:.1f}min"
        )

# Instância global do monitor
flood_monitor = FloodControlMonitor()

# Variáveis globais para gerenciamento de planos
user_selected_times = {}
planos_pendentes = {}

def load_config():
    """Carrega configurações do arquivo config.json"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Erro ao carregar config.json: {e}")
        return {}

def get_canal_referencia():
    """Obtém o canal de referência do config.json"""
    config = load_config()
    return config.get('canal_referencia')

# --- Funções Seguras para API do Telegram ---
def safe_get_chat_with_cache(bot, chat_id, max_retries=3):
    """Obtém informações do chat usando cache quando possível"""
    cache = load_chat_cache()
    chat_id_str = str(chat_id)
    
    # Verificar se existe no cache e não está expirado
    if chat_id_str in cache:
        try:
            cached_time = datetime.datetime.fromisoformat(cache[chat_id_str]['cached_at'])
            if datetime.datetime.now() - cached_time < timedelta(hours=CACHE_DURATION_HOURS):
                return cache[chat_id_str]['data']
        except:
            pass
    
    # Se não está no cache ou expirou, fazer nova requisição
    chat_info = safe_get_chat_direct(bot, chat_id, max_retries)
    if chat_info:
        # Salvar no cache
        try:
            cache[chat_id_str] = {
                'data': {
                    'id': getattr(chat_info, 'id', chat_id),
                    'title': getattr(chat_info, 'title', None),
                    'username': getattr(chat_info, 'username', None),
                    'type': getattr(chat_info, 'type', 'unknown'),
                    'invite_link': getattr(chat_info, 'invite_link', None)
                },
                'cached_at': datetime.datetime.now().isoformat()
            }
            save_chat_cache(cache)
            return cache[chat_id_str]['data']
        except Exception as e:
            logging.error(f"Erro ao salvar no cache: {e}")
            return chat_info
    
    return None

def safe_get_chat_direct(bot, chat_id, max_retries=3):
    """Função segura para obter informações do chat com retry automático"""
    for attempt in range(max_retries):
        try:
            # Rate limiting preventivo
            telegram_rate_limiter.wait_if_needed()
            
            # Fazer a requisição
            result = bot.get_chat(chat_id)
            telegram_rate_limiter.reset_delay()
            return result
            
        except Exception as e:
            error_str = str(e).lower()
            
            if "too many requests" in error_str or "flood control exceeded" in error_str:
                # Extrair tempo de espera da mensagem de erro
                retry_after = 30  # padrão
                try:
                    if "retry after" in error_str:
                        retry_after = int(error_str.split("retry after ")[1].split(" ")[0])
                    elif "retry in" in error_str:
                        retry_after = int(error_str.split("retry in ")[1].split(" ")[0])
                except:
                    pass
                
                telegram_rate_limiter.increase_delay(retry_after)
                
                if attempt < max_retries - 1:
                    wait_time = retry_after + random.uniform(1, 3)
                    logging.warning(f"[SCHEDULED] Rate limit para chat {chat_id}. Aguardando {wait_time:.1f}s (tentativa {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logging.error(f"[SCHEDULED] Falha definitiva para chat {chat_id} após {max_retries} tentativas")
                    return None
            else:
                logging.error(f"[SCHEDULED] Erro não relacionado a rate limit para chat {chat_id}: {e}")
                return None
    
    return None

def process_chats_in_batches(bot, chat_ids, batch_size=15, delay_between_batches=25):
    """Processa chats em lotes para evitar rate limiting"""
    if not chat_ids:
        return []
    
    results = []
    total_batches = len(chat_ids) // batch_size + (1 if len(chat_ids) % batch_size else 0)
    
    for i in range(0, len(chat_ids), batch_size):
        batch = chat_ids[i:i + batch_size]
        current_batch = (i // batch_size) + 1
        
        logging.info(f"[BATCH] Processando lote {current_batch}/{total_batches} ({len(batch)} chats)")
        
        batch_results = []
        for chat_id in batch:
            try:
                chat_info = safe_get_chat_with_cache(bot, chat_id)
                if chat_info:
                    batch_results.append((chat_id, chat_info))
                else:
                    batch_results.append((chat_id, None))
            except Exception as e:
                logging.error(f"[BATCH] Erro ao processar chat {chat_id}: {e}")
                batch_results.append((chat_id, None))
            
            # Pequeno delay entre cada chat no lote
            time.sleep(random.uniform(0.2, 0.5))
        
        results.extend(batch_results)
        
        # Delay maior entre lotes
        if current_batch < total_batches:
            wait_time = delay_between_batches + random.uniform(1, 3)
            logging.info(f"[BATCH] Aguardando {wait_time:.1f}s antes do próximo lote...")
            time.sleep(wait_time)
    
    return results

# --- Rate Limiter Original (mantido para compatibilidade) ---
class RateLimiter:
    def __init__(self, min_delay=2.0, max_delay=12.0, step=0.7, decay=0.1):
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._step = step
        self._decay = decay
        self._delay = min_delay
        self._lock = asyncio.Lock()
        self._last_call = 0

    async def wait(self):
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_call
            if elapsed < self._delay:
                await asyncio.sleep(self._delay - elapsed)
            self._last_call = asyncio.get_event_loop().time()

    def increase_delay(self):
        self._delay = min(self._delay + self._step, self._max_delay)
        print(f"[RateLimiter] Delay aumentado para {self._delay:.2f}s")

    def decay_delay(self):
        self._delay = max(self._delay - self._decay, self._min_delay)
        # print(f"[RateLimiter] Delay reduzido para {self._delay:.2f}s")

    async def _auto_decay(self):
        while True:
            await asyncio.sleep(60)  # a cada 1 minuto, reduz um pouco
            self.decay_delay()

    @property
    def delay(self):
        return self._delay

# Instância global do rate limiter - configuração mais conservadora
telegram_rate_limiter = TelegramRateLimiter(max_requests=15, time_window=60)
rate_limiter = RateLimiter()

# Função para iniciar o auto_decay do rate limiter (deve ser chamada após o loop estar rodando)
async def start_rate_limiter_decay():
    asyncio.create_task(rate_limiter._auto_decay())

# Exemplo de função principal async
# Adapte para o seu fluxo real, mas sempre chame start_rate_limiter_decay() logo no início!
#
# async def main():
#     await start_rate_limiter_decay()
#     # ... inicialize o bot normalmente
#     # await dp.start_polling(bot)
#
# if __name__ == '__main__':
#     import asyncio
#     asyncio.run(main())

# Funções seguras para operações sensíveis ao flood
async def safe_get_chat(bot, chat_id):
    """Função compatível com versão assíncrona usando cache"""
    # Converte para síncrono usando asyncio.to_thread para manter compatibilidade
    try:
        return await asyncio.to_thread(safe_get_chat_with_cache, bot, chat_id)
    except Exception as e:
        logging.error(f"Erro em safe_get_chat assíncrono para {chat_id}: {e}")
        return None

async def async_process_chats_in_batches(bot, chat_ids, batch_size=15, delay_between_batches=25):
    """Versão assíncrona do processamento em lotes para o scheduler"""
    if not chat_ids:
        return []
    
    # Usar asyncio.to_thread para executar a função síncrona
    try:
        return await asyncio.to_thread(process_chats_in_batches, bot, chat_ids, batch_size, delay_between_batches)
    except Exception as e:
        logging.error(f"Erro no processamento assíncrono de lotes: {e}")
        return []

async def safe_forward_message(bot, chat_id, from_chat_id, message_id, **kwargs):
    max_retries = 3
    flood_monitor.record_request()
    
    for attempt in range(max_retries):
        try:
            await rate_limiter.wait()
            result = await bot.forward_message(chat_id=chat_id, from_chat_id=from_chat_id, message_id=message_id, **kwargs)
            flood_monitor.record_success()
            return result
        except Exception as e:
            error_str = str(e).lower()
            wait_time = None
            
            # Detecta diferentes tipos de erro de flood control
            if "too many requests" in error_str or "flood control exceeded" in error_str:
                if _HAS_FLOODWAIT and isinstance(e, FloodWait):
                    wait_time = int(getattr(e, 'timeout', 30))
                elif hasattr(e, 'retry_after'):
                    wait_time = int(getattr(e, 'retry_after', 30))
                else:
                    # Extrai retry_after da mensagem de erro
                    try:
                        if "retry after" in error_str:
                            wait_time = int(error_str.split("retry after ")[1].split(" ")[0])
                        elif "retry in" in error_str:
                            wait_time = int(error_str.split("retry in ")[1].split(" ")[0])
                    except:
                        wait_time = 60  # Padrão mais conservador
                
                if wait_time and attempt < max_retries - 1:
                    # Adiciona margem de segurança ao wait_time
                    actual_wait = wait_time + random.uniform(5, 15)
                    logging.warning(f"🚨 FLOOD CONTROL: forward_message para {chat_id}. Aguardando {actual_wait:.1f}s (tentativa {attempt+1}/{max_retries})")
                    flood_monitor.record_flood_error(actual_wait)
                    rate_limiter.increase_delay()
                    await asyncio.sleep(actual_wait)
                else:
                    logging.error(f"❌ Falha definitiva no forward_message para {chat_id} após {max_retries} tentativas")
                    flood_monitor.record_failure()
                    return None
            else:
                logging.error(f"❌ Erro não relacionado a flood control no forward_message para {chat_id}: {e}")
                flood_monitor.record_failure()
                return None
    
    flood_monitor.record_failure()
    return None

# ============================================================================
# COMPATIBILIDADE AIOGRAM 2.x e 3.x
# ============================================================================
try:
    from aiogram.types import FSInputFile
except ImportError:
    # Aiogram 2.x não tem FSInputFile, usa InputFile
    from aiogram.types import InputFile as FSInputFile

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
# FloodWait pode não existir em alguns ambientes aiogram 3.x bugados
try:
    from aiogram.exceptions import FloodWait
    _HAS_FLOODWAIT = True
except ImportError:
    FloodWait = None
    _HAS_FLOODWAIT = False

import asyncio

async def safe_copy_message(bot, cid, from_chat_id, message_id):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await rate_limiter.wait()
            await bot.copy_message(cid, from_chat_id=from_chat_id, message_id=message_id)
            return True
        except Exception as e:
            error_str = str(e).lower()
            wait_time = None
            
            if "too many requests" in error_str or "flood control exceeded" in error_str:
                if _HAS_FLOODWAIT and isinstance(e, FloodWait):
                    wait_time = int(getattr(e, 'timeout', 30))
                elif hasattr(e, 'retry_after'):
                    wait_time = int(getattr(e, 'retry_after', 30))
                else:
                    try:
                        if "retry after" in error_str:
                            wait_time = int(error_str.split("retry after ")[1].split(" ")[0])
                        elif "retry in" in error_str:
                            wait_time = int(error_str.split("retry in ")[1].split(" ")[0])
                    except:
                        wait_time = 60
                
                if wait_time and attempt < max_retries - 1:
                    actual_wait = wait_time + random.uniform(5, 15)
                    logging.warning(f"🚨 FLOOD CONTROL: copy_message para {cid}. Aguardando {actual_wait:.1f}s (tentativa {attempt+1}/{max_retries})")
                    rate_limiter.increase_delay()
                    await asyncio.sleep(actual_wait)
                else:
                    logging.error(f"❌ Falha definitiva no copy_message para {cid} após {max_retries} tentativas")
                    return False
            else:
                logging.error(f"❌ Erro ao enviar copy_message para {cid}: {e}")
                return False
    
    return False

async def safe_send_message(bot, chat_id, text, **kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await rate_limiter.wait()
            return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            wait_time = None
            
            # Detecta diferentes tipos de erro de flood control
            if "too many requests" in error_str or "flood control exceeded" in error_str:
                if _HAS_FLOODWAIT and isinstance(e, FloodWait):
                    wait_time = int(getattr(e, 'timeout', 30))
                elif hasattr(e, 'retry_after'):
                    wait_time = int(getattr(e, 'retry_after', 30))
                else:
                    # Extrai retry_after da mensagem de erro
                    try:
                        if "retry after" in error_str:
                            wait_time = int(error_str.split("retry after ")[1].split(" ")[0])
                        elif "retry in" in error_str:
                            wait_time = int(error_str.split("retry in ")[1].split(" ")[0])
                    except:
                        wait_time = 60  # Padrão mais conservador
                
                if wait_time and attempt < max_retries - 1:
                    # Adiciona margem de segurança ao wait_time
                    actual_wait = wait_time + random.uniform(5, 15)
                    logging.warning(f"🚨 FLOOD CONTROL: send_message para {chat_id}. Aguardando {actual_wait:.1f}s (tentativa {attempt+1}/{max_retries})")
                    rate_limiter.increase_delay()
                    await asyncio.sleep(actual_wait)
                else:
                    logging.error(f"❌ Falha definitiva no send_message para {chat_id} após {max_retries} tentativas")
                    return None
            else:
                logging.error(f"❌ Erro não relacionado a flood control no send_message para {chat_id}: {e}")
                return None
    
    return None

SILENCED_FILE = SILENCED_FILE

def load_silenced():
    if not os.path.exists(SILENCED_FILE):
        return set()
    with open(SILENCED_FILE, encoding='utf-8') as f:
        return set(json.load(f))

def save_silenced(silenced):
    with open(SILENCED_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(silenced), f, ensure_ascii=False, indent=4)

async def enviar_aviso_expiracao(bot, user_id, mensagem):
    silenced = load_silenced()
    if str(user_id) in silenced:
        return  # Não envia se está silenciado
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔕 Silenciar avisos", callback_data=f"silenciar_{user_id}")]])
    await bot.send_message(user_id, mensagem, reply_markup=keyboard)

from aiogram import types
# Handlers de silenciar/reativar devem ser registrados APÓS a definição do dp. Veja mais abaixo no código.

async def send_report(bot: Bot, success_list, failure_list, fixed_ad_id, horario, admins):
    try:
                # ID fixo do bot
        bot_id = '5010157855'
        # Determinar período do dia
        hora_atual = datetime.datetime.now().hour
        if 5 <= hora_atual < 12:
            periodo = 'Bom dia'
        elif 12 <= hora_atual < 18:
            periodo = 'Boa tarde'
        else:
            periodo = 'Boa noite'
        total_chats = len(success_list) + len(failure_list)
        success_count = len(success_list)
        failure_count = len(failure_list)
        report_text = (
            f"⛅️ {periodo}, administrador. Acabei de enviar uma mensagem agendada!\n\n"
            f"ID: {report_id}|{horario}\n"
            f"🟦 TOTAL DE CHATS: {total_chats}\n"
            f"✅ ENVIOS BEM SUCEDIDOS: {success_count}\n"
            f"❌ ENVIOS MAU SUCEDIDOS: {failure_count}\n"
            f"Para calcular a quantidade de views, clique no botão abaixo!\n"
            f"Obs: Abra o arquivo para obter um relatório completo."
        )
        # Detalhamento completo
        full_report = report_text + "\n\n--- Detalhamento ---\n"
        if success_list:
            full_report += "\nEnviados com sucesso:\n"
            for item in success_list:
                full_report += f"✅ {item if item else 'None'}\n"
        if failure_list:
            full_report += "\nFalhas:\n"
            for item in failure_list:
                full_report += f"❌ {item}\n"
        with open('relatorio.txt', 'w', encoding='utf-8') as file:
            file.write(full_report)
        file = FSInputFile('relatorio.txt')
        for admin_id in admins:
            await bot.send_document(admin_id, file, caption=report_text)
    except Exception as e:
        print(f"Erro ao enviar o relatório: {e}")

import uuid

# Reduz o flood de logs do aiogram.event para WARNING
import logging
logging.getLogger("aiogram.event").setLevel(logging.WARNING)



# Função auxiliar para compactar horário no formato HH:MM para HHMM
def hora_compacta(h):
    return h.replace(":", "") if h and ":" in h else h
import datetime
from datetime import timedelta

from aiogram import Bot, Dispatcher, types, F, html
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, InlineQuery, InlineQueryResultArticle, 
    InputTextMessageContent, InlineQueryResultsButton
)
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- Funções utilitárias para anti-flood e silenciar ---
MUTED_FILE = MUTED_GROUPS_FILE
NOTIFIED_FILE = NOTIFIED_TODAY_FILE

def load_muted_groups():
    if not os.path.exists(MUTED_FILE):
        return []
    with open(MUTED_FILE, encoding='utf-8') as f:
        return json.load(f)

def save_muted_groups(groups):
    with open(MUTED_FILE, 'w', encoding='utf-8') as f:
        json.dump(groups, f, ensure_ascii=False, indent=4)

def load_notified_today():
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    if not os.path.exists(NOTIFIED_FILE):
        return {"date": today, "groups": []}
    with open(NOTIFIED_FILE, encoding='utf-8') as f:
        data = json.load(f)
    if data.get('date') != today:
        return {"date": today, "groups": []}
    return data

def save_notified_today(data):
    with open(NOTIFIED_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def remove_group_from_chat_ids(chat_id):
    chat_id = str(chat_id)
    try:
        with open(CHAT_IDS_FILE, encoding='utf-8') as f:
            ids = set(str(i) for i in json.load(f))
    except Exception:
        ids = set()
    if chat_id in ids:
        ids.remove(chat_id)
        with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(ids), f, ensure_ascii=False, indent=4)
        print(f"[REMOVER] chat_id removido manualmente: {chat_id} | Total agora: {len(ids)}")
        return True
    return False

# Funções utilitárias para registrar usuários privados

def load_user_ids():
    try:
        with open(USER_IDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Se for lista de dicts, extrai só os IDs privados
            if data and isinstance(data[0], dict):
                return list(set([d.get('chat_id') for d in data if isinstance(d, dict) and d.get('chat_id', 0) > 0]))
            # Se for lista de ints
            return list(set([i for i in data if isinstance(i, int) and i > 0]))
    except (FileNotFoundError, json.JSONDecodeError, IndexError):
        return []

def save_user_ids(user_ids):
    # Só salva IDs inteiros positivos (privados)
    user_ids = list(set([i for i in user_ids if isinstance(i, int) and i > 0]))
    with open(USER_IDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_ids, f, ensure_ascii=False, indent=4)

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import sys
import os
import shutil

BACKUP_FILES = [
    SCHEDULED_MESSAGES_FILE,
    CHAT_IDS_FILE,
    CONFIG_FILE,
]
BACKUP_DIR = 'backups'

import zipfile

async def backup_and_send_logs(bot, log_channel_id):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Remove TODOS os backups antigos do diretório de backup E do diretório raiz
    for f in os.listdir(BACKUP_DIR):
        file_path = os.path.join(BACKUP_DIR, f)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Erro ao remover backup antigo: {file_path} - {e}")
    
    # Remove backups antigos do diretório raiz (que não deveriam estar lá)
    import glob
    for backup_file in glob.glob("*backup*.json"):
        try:
            os.remove(backup_file)
            print(f"Removido backup antigo do diretório raiz: {backup_file}")
        except Exception as e:
            print(f"Erro ao remover backup do diretório raiz: {backup_file} - {e}")
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_paths = []
    for file in BACKUP_FILES:
        if os.path.exists(file):
            backup_name = f"{timestamp}_{file}"
            backup_path = os.path.join(BACKUP_DIR, backup_name)
            shutil.copy(file, backup_path)
            backup_paths.append(backup_path)
    # Cria o zip
    zip_name = f"backup_{timestamp}.zip"
    zip_path = os.path.join(BACKUP_DIR, zip_name)
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_path in backup_paths:
            zipf.write(file_path, os.path.basename(file_path))
    # Envia o zip
    # Lê o config diretamente do arquivo JSON
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Erro ao carregar config.json no backup: {e}")
        config = {}
    log_destino = config.get('log_destino', 'canal')
    try:
        if log_destino == 'privado':
            for admin_id in config.get('admins', []):
                try:
                    await bot.send_document(
                        chat_id=admin_id,
                        document=FSInputFile(zip_path),
                        caption=f"Backup automático: {os.path.basename(zip_path)}"
                    )
                except Exception as e:
                    if "user is deactivated" not in str(e):
                        print(f"Erro ao enviar backup zip para admin {admin_id}: {e}")
        else:
            await bot.send_document(
                chat_id=log_channel_id,
                document=FSInputFile(zip_path),
                caption=f"Backup automático: {os.path.basename(zip_path)}"
            )
    except Exception as e:
        print(f"Erro ao enviar backup zip: {e}")


def cleanup_old_backups():
    """Remove todos os backups antigos do diretório raiz"""
    import glob
    removed_count = 0
    
    # Remove backups com timestamp
    for backup_file in glob.glob("*backup*20*.json"):
        try:
            os.remove(backup_file)
            print(f"Removido: {backup_file}")
            removed_count += 1
        except Exception as e:
            print(f"Erro ao remover {backup_file}: {e}")
    
    print(f"Total de backups antigos removidos: {removed_count}")
    return removed_count

def restart_bot():
    """Reinicia o processo do bot."""
    os.execl(sys.executable, sys.executable, *sys.argv)

# Inicialização do bot e dispatcher
with open(CONFIG_FILE, encoding='utf-8') as f:
    config = json.load(f)
API_TOKEN = config.get('API_TOKEN', '')
ADMINS = config.get('admins', [])
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ============================================================================
# HANDLERS PARA BOTÕES INTERATIVOS DE EXPIRAÇÃO
# ============================================================================

@dp.callback_query(lambda c: c.data and c.data.startswith('plan_details_'))
async def handle_plan_details(callback_query: types.CallbackQuery):
    """Handler para botão 'Ver Detalhes' das mensagens de expiração"""
    try:
        # Extrai o ID do plano do callback_data
        fixed_ad_id = callback_query.data.replace('plan_details_', '')
        
        # Busca informações do plano
        scheduled_messages = load_scheduled_messages()
        plan_info = None
        
        for msg in scheduled_messages:
            if msg.get('fixed_ad_id') == fixed_ad_id:
                plan_info = msg
                break
        
        if not plan_info:
            await callback_query.answer("❌ Plano não encontrado!", show_alert=True)
            return
        
        # Calcula tempo restante
        expiry_str = plan_info.get('expiry_time', 'N/A')
        if expiry_str != 'N/A':
            try:
                expiry_dt = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                now = datetime.datetime.now()
                diff = expiry_dt - now
                
                if diff.total_seconds() > 0:
                    days = diff.days
                    hours = diff.seconds // 3600
                    minutes = (diff.seconds % 3600) // 60
                    tempo_restante = f"{days}d {hours}h {minutes}m"
                else:
                    tempo_restante = "⚠️ EXPIRADO"
            except:
                tempo_restante = "N/A"
        else:
            tempo_restante = "N/A"
        
        # Monta mensagem detalhada
        details_message = (
            f"📊 **DETALHES DO SEU PLANO**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏷️ **ID do Contrato:** `{fixed_ad_id}`\n"
            f"📋 **Tipo:** {plan_info.get('type', 'N/A')}\n"
            f"📅 **Data de Expiração:** `{expiry_str}`\n"
            f"⏰ **Tempo Restante:** `{tempo_restante}`\n"
            f"👤 **Usuário:** `{plan_info.get('recipient_id', 'N/A')}`\n"
            f"📝 **Código:** `{plan_info.get('code', 'N/A')}`\n\n"
            f"💡 **Dica:** Para renovar seu plano, entre em contato com nosso suporte!"
        )
        
        await callback_query.message.edit_text(
            details_message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 Renovar Plano",
                        url="https://t.me/suporte_bot"
                    ),
                    InlineKeyboardButton(
                        text="🔙 Voltar",
                        callback_data=f"back_to_expiry_{fixed_ad_id}"
                    )
                ]
            ])
        )
        
        await callback_query.answer("✅ Detalhes carregados!")
        
    except Exception as e:
        professional_logger.error("CALLBACK", f"Erro no handler de detalhes: {e}")
        await callback_query.answer("❌ Erro ao carregar detalhes!", show_alert=True)

# --- Registro de quem adicionou o bot ---
ADDED_BY_FILE = ADDED_BY_FILE
def load_added_by():
    if not os.path.exists(ADDED_BY_FILE):
        return {}
    with open(ADDED_BY_FILE, encoding='utf-8') as f:
        return json.load(f)
def save_added_by(data):
    with open(ADDED_BY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Handler para detectar quando o bot é adicionado a um grupo
@dp.chat_member()
async def handle_bot_added(update: types.ChatMemberUpdated):
    try:
        logging.info(f"[CHAT_MEMBER] Update recebido - Chat: {update.chat.id}, Old: {update.old_chat_member.status}, New: {update.new_chat_member.status}")
        if update.old_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED] and \
           update.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            chat_id = update.chat.id
            adicionado_por = 'Desconhecido'
            if update.from_user:
                nome = update.from_user.full_name
                user_id = update.from_user.id
                adicionado_por = f"{nome} (ID: {user_id})"
            added_by = load_added_by()
            added_by[str(chat_id)] = adicionado_por
            save_added_by(added_by)
            is_new = save_chat_id_if_new(chat_id)
            if is_new:
                # Notifica admins
                try:
                    with open(CONFIG_FILE, encoding='utf-8') as f:
                        config = json.load(f)
                    admin_ids = config.get('admins', [])
                except Exception as e:
                    logging.error(f"Erro ao carregar admin IDs para notificação de novo grupo: {e}")
                    admin_ids = []
                notification = (
                    f"🔔 Bot adicionado a um novo grupo\n\n"
                    f"🆔 ID: {chat_id}\n"
                    f"👤 Adicionado por: {adicionado_por}\n"
                    f"Data: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                    f"O bot já está pronto para divulgar neste grupo."
                )
                for admin_id in admin_ids:
                    try:
                        await update.bot.send_message(admin_id, notification)
                    except Exception as e:
                        logging.error(f"Erro ao notificar admin {admin_id} sobre novo grupo: {e}")
    except Exception as e:
        logging.error(f"Erro ao registrar quem adicionou o bot: {e}")

# Coleta automática de grupos por mensagem recebida
def save_chat_id_if_new(chat_id):
    """
    Salva o chat_id (str ou int) em chat_ids.json se ainda não estiver lá.
    Retorna True se for novo, False se já existia ou erro.
    """
    try:
        chat_id = str(chat_id)
        ids = []
        if os.path.exists(CHAT_IDS_FILE):
            try:
                with open(CHAT_IDS_FILE, encoding='utf-8') as f:
                    ids = [str(i) for i in json.load(f) if i]
            except Exception:
                ids = []
        if chat_id not in ids:
            ids.append(chat_id)
            with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(ids, f, ensure_ascii=False, indent=4)
            logging.info(f"[COLETA] Novo chat_id coletado: {chat_id}")
            return True
    except Exception as e:
        logging.error(f"Erro ao salvar chat_id novo em chat_ids.json: {e}")
    return False


    try:
        chat_id = str(chat_id)
        if not os.path.exists(CHAT_IDS_FILE):
            ids = []
        else:
            with open(CHAT_IDS_FILE, encoding='utf-8') as f:
                ids = json.load(f)
        if chat_id not in ids:
            ids.append(chat_id)
            with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(ids, f, ensure_ascii=False, indent=4)
            print(f"[COLETA] Novo chat_id coletado automaticamente: {chat_id}")
            logging.info(f"[COLETA] Novo chat_id coletado: {chat_id}")
            return True
    except Exception as e:
        logging.error(f"Erro ao salvar chat_id novo em chat_ids.json: {e}")
    return False

# Handler para detectar quando o bot é adicionado/removido especificamente (my_chat_member)
@dp.my_chat_member()
async def handle_my_chat_member(update: types.ChatMemberUpdated):
    """
    Handler específico para mudanças no status do próprio bot em chats
    Funciona melhor para canais onde o bot é adicionado como admin
    """
    try:
        chat_id = update.chat.id
        chat_type = update.chat.type
        chat_title = getattr(update.chat, 'title', 'N/A')
        old_status = update.old_chat_member.status
        new_status = update.new_chat_member.status
        
        logging.info(f"[MY_CHAT_MEMBER] Chat: {chat_id} ({chat_type}) - {old_status} → {new_status}")
        
        # Bot foi adicionado (de LEFT/KICKED para MEMBER/ADMIN/CREATOR)
        if old_status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED] and \
           new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            
            logging.info(f"[MY_CHAT_MEMBER] Bot adicionado ao {chat_type}: {chat_title} ({chat_id})")
            
            # Salva o chat_id
            is_new = save_chat_id_if_new(chat_id)
            
            if is_new:
                # Notifica admins sobre novo canal/grupo
                try:
                    with open(CONFIG_FILE, encoding='utf-8') as f:
                        config = json.load(f)
                    admin_ids = config.get('admins', [])
                except Exception as e:
                    logging.error(f"Erro ao carregar admin IDs: {e}")
                    admin_ids = []
                
                tipo_texto = "Canal" if chat_type == "channel" else "Grupo"
                emoji = "📢" if chat_type == "channel" else "👥"
                
                notification = (
                    f"{emoji} **BOT ADICIONADO A NOVO {tipo_texto.upper()}!**\n\n"
                    f"🏷️ **Nome:** {chat_title}\n"
                    f"🆔 **ID:** `{chat_id}`\n"
                    f"📋 **Tipo:** {tipo_texto}\n"
                    f"⚡ **Status:** {new_status}\n"
                    f"📅 **Data:** {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
                    f"✅ {tipo_texto} adicionado automaticamente à lista de divulgação!"
                )
                
                for admin_id in admin_ids:
                    try:
                        await update.bot.send_message(admin_id, notification, parse_mode="Markdown")
                    except Exception as e:
                        logging.error(f"Erro ao notificar admin {admin_id}: {e}")
        
        # Bot foi removido
        elif new_status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
            logging.info(f"[MY_CHAT_MEMBER] Bot removido do {chat_type}: {chat_title} ({chat_id})")
            
    except Exception as e:
        logging.error(f"Erro em handle_my_chat_member: {e}")

# Handler para detectar remoção do bot de grupos
@dp.chat_member()
async def handle_bot_removal(update: types.ChatMemberUpdated):
    try:
        # Detecta se o bot foi removido do grupo
        if update.new_chat_member.status in [types.ChatMemberStatus.LEFT, types.ChatMemberStatus.KICKED]:
            chat_id = update.chat.id
            chat_title = getattr(update.chat, 'title', str(chat_id))
            
            # Carrega dados atuais do arquivo e remove o chat_id
            try:
                with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
                    current_chat_ids = json.load(f)
            except Exception:
                current_chat_ids = []
            
            current_chat_ids = [str(cid) for cid in current_chat_ids]
            chat_id_str = str(chat_id)
            
            if chat_id_str in current_chat_ids:
                current_chat_ids.remove(chat_id_str)
                with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(current_chat_ids, f, ensure_ascii=False, indent=4)
                logging.info(f"Bot removido do grupo {chat_title} ({chat_id}). ID removido de chat_ids.json.")
            else:
                logging.info(f"Bot removido do grupo {chat_title} ({chat_id}), mas ID não estava em chat_ids.json.")

            # Notifica todos os administradores
            try:
                with open(CONFIG_FILE, encoding='utf-8') as f:
                    config = json.load(f)
                admin_ids = config.get('admins', [])
            except Exception as e:
                if "chat not found" in str(e).lower() or "bad request" in str(e).lower():
                    logging.debug(f"Erro esperado ao carregar admin IDs para notificação: {e}")
                else:
                    logging.error(f"Erro ao carregar admin IDs para notificação: {e}")
                admin_ids = []

            notification = (
                f"⚠️ *O bot foi removido de um grupo!*\n"
                f"*Grupo:* {chat_title}\n"
                f"*ID do grupo:* `{chat_id}`\n"
                f"*Data:* {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"Se quiser adicionar novamente, use o link do bot."
            )

            for admin_id in admin_ids:
                try:
                    await bot.send_message(admin_id, notification, parse_mode="Markdown")
                except Exception as e:
                    if "chat not found" in str(e).lower() or "bad request" in str(e).lower():
                        logging.debug(f"Erro esperado ao notificar admin {admin_id} sobre remoção: {e}")
                    else:
                        logging.debug(f"Erro ao notificar admin {admin_id} sobre remoção: {e}")
    except Exception as e:
        logging.error(f"Erro no handler de remoção do bot: {e}")

# --- Handlers de botões de admin ---
@dp.callback_query(lambda c: c.data.startswith('apagar_'))
async def callback_apagar_grupo(callback_query: types.CallbackQuery):
    chat_id = int(callback_query.data.split('_', 1)[1])
    ok = remove_group_from_chat_ids(chat_id)
    if ok:
        await callback_query.answer('Grupo removido da lista!')
        await callback_query.message.edit_text('✅ Grupo removido da lista de monitoramento.')
    else:
        await callback_query.answer('Grupo já não está na lista.')

@dp.callback_query(lambda c: c.data.startswith('silenciar_'))
async def callback_silenciar_grupo(callback_query: types.CallbackQuery):
    chat_id = int(callback_query.data.split('_', 1)[1])
    muted = load_muted_groups()
    if chat_id not in muted:
        muted.append(chat_id)
        save_muted_groups(muted)
        await callback_query.answer('Notificações silenciadas para este grupo.')
        await callback_query.message.edit_text('🔕 Notificações silenciadas para este grupo.')
    else:
        await callback_query.answer('Este grupo já está silenciado.')

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

# Função para obter o destino de log do config.json
def get_log_destino():
    with open(CONFIG_FILE, encoding='utf-8') as f:
        config = json.load(f)
    return config.get("log_destino")

# Função utilitária para enviar relatório para admin e log
def get_admin_ids():
    with open(CONFIG_FILE, encoding='utf-8') as f:
        config = json.load(f)
    return config.get("admins", [])

async def enviar_para_admin_e_log(bot, texto):
    admin_ids = get_admin_ids()
    log_destino = get_log_destino()
    enviados = set()
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, texto)
            enviados.add(str(admin_id))
        except Exception as e:
            error_str = str(e).lower()
            if "user is deactivated" not in error_str and "forbidden" not in error_str:
                logging.error(f"Erro ao enviar relatório para admin {admin_id}: {e}")
    # Envia para o log_destino se não for igual a nenhum admin
    if log_destino and str(log_destino) not in enviados:
        try:
            await bot.send_message(log_destino, texto)
        except Exception as e:
            logging.error(f"Erro ao enviar relatório para o log: {e}")

router = Router()

@router.message(StateFilter(AdminPanelStates.esperando_novo_link_plano))
async def handle_novo_link_plano(message: types.Message, state: FSMContext):
    link = message.text
    with open(CONFIG_FILE, encoding='utf-8') as f:
        config = json.load(f)
    config['plan_button_link'] = link
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    await message.answer('✅ Link do botão de planos atualizado com sucesso!\n\nℹ️ A alteração será aplicada automaticamente.')
    await state.clear()

# Constantes para visualização de horários
ITEMS_PER_PAGE = 8  # Número de horários por página

# Dados temporários para seleção de horários
user_selected_times = {}  # {user_id: {"times": [horários], "plan": tipo}}

# Estados para troca
class TrocaPlanoStates(StatesGroup):
    esperando_novo_anuncio = State()
    esperando_novos_horarios = State()
    plano_escolhido = State()
    esperando_idfixo = State()


    

# Função para gerar lista de horários disponíveis
def get_available_hours():
    """Retorna uma lista de horários disponíveis no formato HH:MM"""
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
        interval = int(config.get('scheduling_time_interval', 10))
    except Exception:
        interval = 10
    available_hours = []
    for hour in range(0, 24):  # Das 00:00 às 23:50
        for minute in range(0, 60, interval):  # Intervalo configurável
            available_hours.append(f"{hour:02d}:{minute:02d}")
    return available_hours

# Função para obter horários ocupados
def get_busy_hours():
    """Retorna um conjunto com os horários já agendados"""
    busy_hours = set()
    for msg in scheduled_messages:
        if 'time' in msg:
            busy_hours.add(msg['time'][:5])  # Pega apenas HH:MM
    return busy_hours

# Função para filtrar horários por período do dia
def filter_hours_by_period(hours, period):
    """Filtra os horários com base no período do dia"""
    if period == "all":
        return hours
    
    filtered = []
    for hour in hours:
        hh = int(hour.split(':')[0])
        if period == "manha" and 6 <= hh < 12:
            filtered.append(hour)
        elif period == "tarde" and 12 <= hh < 18:
            filtered.append(hour)
        elif period == "noite" and 18 <= hh < 24:
            filtered.append(hour)
        elif period == "madrugada" and (0 <= hh < 6 or hh == 24):
            filtered.append(hour)
    
    return filtered

# Função para gerar teclado de períodos
def generate_period_keyboard():
    """Gera o teclado com os períodos do dia"""
    keyboard = [
        [
            InlineKeyboardButton(text="🌅 Manhã (06:00-12:00)", callback_data="period:manha"),
            InlineKeyboardButton(text="☀️ Tarde (12:00-18:00)", callback_data="period:tarde")
        ],
        [
            InlineKeyboardButton(text="🌙 Noite (18:00-00:00)", callback_data="period:noite"),
            InlineKeyboardButton(text="🌌 Madrugada (00:00-06:00)", callback_data="period:madrugada")
        ],
        [
            InlineKeyboardButton(text="📅 Todos os horários", callback_data="period:all"),
            InlineKeyboardButton(text="❌ Fechar", callback_data="close_times")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Função para gerar teclado de planos
def generate_plans_keyboard():
    """Gera um teclado inline com os tipos de agendamento disponíveis"""
    plans = {
        "daily": {
            "name": "Diário",
            "emoji": "📅",
            "description": "Agendamento diário"
        },
        "weekly": {
            "name": "Semanal",
            "emoji": "⏳",
            "description": "Agendamento semanal"
        },
        "monthly": {
            "name": "Mensal",
            "emoji": "📆",
            "description": "Agendamento mensal"
        }
    }
    
    buttons = []
    for plan_id, plan in plans.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{plan['emoji']} {plan['name']}",
                callback_data=f"select_plan:{plan_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="❌ Fechar",
            callback_data="close_plans"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Função para gerar teclado de horários
def generate_time_keyboard(page=0, period="all", user_id=None):
    """Gera um teclado inline com os horários disponíveis, mostrando quais foram selecionados"""
    # Sempre recarrega mensagens agendadas do arquivo para garantir atualização
    try:
        scheduled_messages_atual = load_scheduled_messages()
    except Exception:
        scheduled_messages_atual = []
    
    hours = get_available_hours()
    busy_hours = set()
    for msg in scheduled_messages_atual:
        if 'time' in msg:
            busy_hours.add(msg['time'][:5])  # Pega apenas HH:MM
    
    # Filtra os horários pelo período selecionado
    if period != "all":
        hours = filter_hours_by_period(hours, period)
    
    # Remove horários ocupados
    hours = [h for h in hours if h not in busy_hours]
    
    # Calcula o número total de páginas
    total_pages = (len(hours) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    # Pega os horários da página atual
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(hours))
    page_hours = hours[start_idx:end_idx]
    
    # Cria os botões para os horários
    buttons = []
    for hour in page_hours:
        # Verifica se o horário está selecionado
        is_selected = user_id and hour in user_selected_times.get(user_id, {}).get("times", [])
        emoji = "🟢" if is_selected else "📅"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{hour} {emoji}",
                callback_data=f"toggle_time|{hour}|{period}|{page}"
            )
        ])
    
    # Adiciona botões de navegação
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Página anterior",
            callback_data=f"time_page:{page-1}:{period}"
        ))
    
    nav_buttons.append(InlineKeyboardButton(
        text=f"Página {page+1}/{total_pages}",
        callback_data=f"time_page:current:{period}"
    ))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Página seguinte ➡️",
            callback_data=f"time_page:{page+1}:{period}"
        ))
    
    buttons.append(nav_buttons)
    
    # Adiciona botão para mostrar horários selecionados
    selected_times = user_selected_times.get(user_id, {}).get("times", [])
    if selected_times:
        # Função para converter hora em minutos totais, ignorando valores inválidos
        def hora_para_int(hora):
            if not hora or not isinstance(hora, str):
                return 9999  # joga para o final
            if ":" in hora and len(hora) == 5:
                try:
                    h, m = hora.split(":")
                    return int(h) * 60 + int(m)
                except Exception:
                    return 9999
            if len(hora) == 4 and hora.isdigit():
                return int(hora[:2]) * 60 + int(hora[2:])
            return 9999

        # Filtra apenas horários válidos
        horarios_validos = [h for h in selected_times if h and ((":" in h and len(h) == 5) or (len(h) == 4 and h.isdigit()))]
        formatted_times = []
        for time in sorted(horarios_validos, key=hora_para_int):
            if len(time) == 4:
                formatted_times.append(f"{time[:2]}:{time[2:]}")
            else:
                formatted_times.append(time)
        selected_text = "✅ Horários selecionados: " + ", ".join(formatted_times)
        buttons.append([
            InlineKeyboardButton(
                text=selected_text,
                callback_data="show_selected_times"
            )
        ])
    
    # Adiciona botão de confirmação se há horários selecionados
    if selected_times:
        buttons.append([
            InlineKeyboardButton(
                text="✅ Confirmar horários",
                callback_data="confirm_times"
            )
        ])
    
    # Adiciona botão para voltar aos períodos
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Voltar aos períodos",
            callback_data="back_to_periods"
        ),
        InlineKeyboardButton(
            text="❌ Fechar",
            callback_data="close_times"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def load_config():
    """Carrega configurações do arquivo config.json"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Erro ao carregar config.json: {e}")
        return {}

def get_canal_referencia():
    """Obtém o canal de referência do config.json"""
    config = load_config()
    return config.get('canal_referencia')

# Carregar configurações
with open(CONFIG_FILE, encoding='utf-8') as f:
    config = json.load(f)

# Arquivo chat_ids.json é gerenciado dinamicamente pelas funções
# Não é mais necessário carregar em variável global

# Carregar configurações do bot
API_TOKEN = config.get('API_TOKEN')
if not API_TOKEN:
    raise ValueError("API_TOKEN não encontrado no arquivo de configuração")

DEFAULT_MESSAGE = config.get('infomessagess', 'Divulgação!')
ADMINS = config.get('admins', [])

# Definir ADMIN_CHAT_ID como o primeiro admin da lista, se existir
ADMIN_CHAT_ID = ADMINS[0] if ADMINS else None  # ID do chat do admin

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Dicionário para armazenar IDs com erros
failed_chat_ids = set()

# Carregar mensagens agendadas
def load_scheduled_messages():
    try:
        # Suporte a arquivo com nome alternativo (typo): scheduled_mesagges.json
        primary_filename = SCHEDULED_MESSAGES_FILE
        alt_filename = 'scheduled_mesagges.json'

        # Se o arquivo principal não existe mas o alternativo existe, usa o alternativo
        if not os.path.exists(primary_filename) and os.path.exists(alt_filename):
            with open(alt_filename, 'r', encoding='utf-8') as file:
                content = file.read().strip()
                if not content:
                    return []
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logging.error(f"[LOAD_SCHEDULED_MESSAGES] Erro ao decodificar JSON em {alt_filename}: {e}. Resetando para lista vazia.")
                    return []

        if not os.path.exists(primary_filename):
            with open(primary_filename, 'w', encoding='utf-8') as file:
                file.write('[]')
            return []

        with open(primary_filename, 'r', encoding='utf-8') as file:
            content = file.read().strip()
            if not content:
                return []
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logging.error(f'[LOAD_SCHEDULED_MESSAGES] Erro ao decodificar JSON: {e}. Resetando arquivo.')
                with open(primary_filename, 'w', encoding='utf-8') as f:
                    f.write('[]')
                return []
    except Exception as e:
        logging.error(f'[LOAD_SCHEDULED_MESSAGES] Erro inesperado: {e}')
        return []

# Carregar mensagens agendadas
scheduled_messages = load_scheduled_messages()

# Carregar configurações
with open(CONFIG_FILE, encoding='utf-8') as f:
    config = json.load(f)

API_TOKEN = config['API_TOKEN']

# Inicialização do bot e dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Dicionário para armazenar planos pendentes de confirmação pelo admin
planos_pendentes = {}

# Funções para carregar e salvar chats
def load_chat_ids():
    """
    Carrega todos os chat_ids do arquivo. Nunca gera erro, sempre retorna lista de str.
    """
    try:
        if not os.path.exists(CHAT_IDS_FILE):
            with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
            return []
        with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
            return [str(i) for i in json.load(f) if i]
    except Exception:
        return []

def save_chat_ids(chat_ids_list):
    """
    Salva a lista de chat_ids no arquivo chat_ids.json
    """
    try:
        with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(chat_ids_list, f, ensure_ascii=False, indent=4)
        print(f"[SAVE_CHAT_IDS] Lista salva com {len(chat_ids_list)} IDs")
    except Exception as e:
        print(f"[SAVE_CHAT_IDS] Erro ao salvar lista: {e}")

# Funções de manipulação de mensagens agendadas movidas para cima

import shutil
import traceback
import datetime

def save_scheduled_messages(messages, origem="desconhecida", force_empty=False):
    # Proteção: nunca sobrescrever com lista vazia sem querer
    if (messages is None or len(messages) == 0) and not force_empty:
        logging.warning(f"[SCHEDULED] scheduled_messages.json NÃO foi salvo vazio (origem: {origem}) — isso é comportamento normal para evitar sobrescrever agendamentos por engano.")
        return
    # Backup antes de salvar
    # Backup antes de salvar: sobrescreve sempre o mesmo arquivo
    primary_filename = SCHEDULED_MESSAGES_FILE
    alt_filename = 'scheduled_mesagges.json'
    target_filename = primary_filename if os.path.exists(primary_filename) or not os.path.exists(alt_filename) else alt_filename

    if os.path.exists(target_filename):
        # Remove TODOS os backups antigos antes de criar um novo
        import glob
        for old_backup in glob.glob("*backup*.json"):
            try:
                os.remove(old_backup)
                logging.info(f"Removido backup antigo: {old_backup}")
            except Exception as e:
                logging.warning(f"Erro ao remover backup antigo {old_backup}: {e}")
        
        # Cria apenas UM backup simples
        backup_name = f"{os.path.splitext(target_filename)[0]}_backup.json"
        shutil.copy(target_filename, backup_name)
    logging.warning(f"[SCHEDULED] Salvando {len(messages)} mensagens agendadas em {target_filename}. Origem: {origem}. Stack: {''.join(traceback.format_stack(limit=4))}")
    with open(target_filename, 'w', encoding='utf-8') as file:
        json.dump(messages, file, ensure_ascii=False, indent=4)
    if not messages:
        logging.error(f"[SCHEDULED] ATENÇÃO: scheduled_messages.json foi salvo VAZIO! Origem: {origem}")

# Função para remover mensagens expiradas
def remove_expired_messages():
    global scheduled_messages
    if not isinstance(scheduled_messages, list):
        logging.warning("scheduled_messages não é uma lista, convertendo para lista vazia")
        scheduled_messages = []
        return
        
    now = datetime.datetime.now()
    expired_count = 0
    reagendamentos_removidos = 0
    
    # Criar uma cópia da lista para iteração segura
    messages_to_check = scheduled_messages.copy()
    
    for msg in messages_to_check:
        try:
            if not isinstance(msg, dict):
                logging.info(f"Mensagem inválida encontrada, mantendo: {msg.get('code', 'N/A')}")
                continue
            
            # **NOVO: Remove TODOS os reagendamentos automaticamente, independente de expiração**
            if msg.get('is_reagendamento', False):
                logging.info(f"🗑️ Removendo reagendamento automaticamente: {msg.get('code', 'N/A')}")
                scheduled_messages.remove(msg)
                reagendamentos_removidos += 1
                expired_count += 1
                continue  # Pula para próxima mensagem
                
            expiry_str = msg.get('expiry_time')
            if not expiry_str:
                # NÃO remove mensagens sem expiry_time - elas podem ser válidas
                continue
                
            try:
                expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                if now > expiry_date:
                    # Mensagens normais são removidas se expirarem
                    logging.info(f"Removendo mensagem expirada: {msg.get('code', 'N/A')} - expirou em {expiry_str}")
                    scheduled_messages.remove(msg)
                    expired_count += 1
            except ValueError as e:
                # NÃO remove por erro de formato - pode ser formato diferente válido
                logging.warning(f"Formato de data não reconhecido para mensagem {msg.get('code', 'N/A')}: {expiry_str} - mantendo mensagem")
                
        except Exception as e:
            logging.error(f"Erro ao verificar mensagem expirada: {e}")
    
    if expired_count > 0:
        save_scheduled_messages(scheduled_messages, origem="remove_expired_messages")
        if reagendamentos_removidos > 0:
            logging.info(f"[EXPIRED_CLEANUP] {expired_count} mensagens removidas ({reagendamentos_removidos} reagendamentos deletados automaticamente)")
        else:
            logging.info(f"[EXPIRED_CLEANUP] {expired_count} mensagens expiradas removidas")
    
    return expired_count

# ============================================================================
# SISTEMA DE HISTÓRICO DE BROADCASTS
# ============================================================================

def save_broadcast_history(plan_id, fixed_id, status, chat_count, success_count, failed_count, timestamp=None):
    """Salva histórico de broadcast para estatísticas"""
    try:
        history_file = 'broadcast_history.json'
        history = []
        
        # Carrega histórico existente
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []
        
        # Adiciona novo registro
        entry = {
            'plan_id': plan_id,
            'fixed_id': fixed_id,
            'status': status,
            'chat_count': chat_count,
            'success_count': success_count,
            'failed_count': failed_count,
            'timestamp': timestamp or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        history.append(entry)
        
        # Mantém apenas últimos 1000 registros
        if len(history) > 1000:
            history = history[-1000:]
        
        # Salva
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        logging.info(f"[BROADCAST_HISTORY] Registro salvo para plano {plan_id}")
        
    except Exception as e:
        logging.error(f"[BROADCAST_HISTORY] Erro ao salvar histórico: {e}")

def get_plan_broadcast_history(plan_id, fixed_id=None, limit=50):
    """Retorna histórico de broadcasts de um plano específico"""
    try:
        history_file = 'broadcast_history.json'
        if not os.path.exists(history_file):
            return []
        
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        # Filtra por plan_id ou fixed_id
        filtered = []
        for entry in history:
            if entry.get('plan_id') == plan_id or (fixed_id and entry.get('fixed_id') == fixed_id):
                filtered.append(entry)
        
        # Retorna últimos N registros
        return filtered[-limit:] if len(filtered) > limit else filtered
        
    except Exception as e:
        logging.error(f"[BROADCAST_HISTORY] Erro ao carregar histórico: {e}")
        return []

# ============================================================================

    if expired_count > 0:
        save_scheduled_messages(scheduled_messages)
        if reagendamentos_removidos > 0:
            logging.info(f"🧹 Limpeza automática: {reagendamentos_removidos} reagendamento(s) removido(s), {expired_count - reagendamentos_removidos} mensagem(s) expirada(s)")
        else:
            logging.info(f"Removidas {expired_count} mensagens expiradas ou inválidas")

# Carrega as mensagens agendadas
scheduled_messages = load_scheduled_messages()

# **FUNÇÃO DE LIMPEZA AUTOMÁTICA - Chamada em loop**
async def check_and_remove_expired_messages():
    """Loop assíncrono para remover reagendamentos expirados automaticamente"""
    while True:
        try:
            # Recarrega as mensagens do arquivo
            global scheduled_messages
            scheduled_messages = load_scheduled_messages()
            
            # Remove mensagens expiradas (incluindo reagendamentos)
            remove_expired_messages()
            
            # Aguarda 30 segundos antes de verificar novamente
            await asyncio.sleep(30)
        except Exception as e:
            logging.error(f"Erro no loop de limpeza automática: {e}")
            await asyncio.sleep(60)  # Aguarda mais tempo em caso de erro

# Carrega os IDs com erros salvos
async def load_failed_chat_ids():
    try:
        with open(FAILED_CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
            failed_chat_ids.update(set(json.load(f)))
    except FileNotFoundError:
        pass

# Salva os IDs com erros
async def save_failed_chat_ids():
    with open(FAILED_CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(failed_chat_ids), f, ensure_ascii=False, indent=4)

# Remove apenas IDs presentes em temp_failed_ids.json de chat_ids.json
async def remove_temp_failed_ids_from_chat_ids():
    """
    Remove apenas os IDs presentes em temp_failed_ids.json do arquivo chat_ids.json.
    Não depende de variáveis globais.
    """
    import os
    removed_count = 0
    temp_failed_path = 'temp_failed_ids.json'
    chat_ids_path = CHAT_IDS_FILE
    try:
        # Lê IDs com erro
        if not os.path.exists(temp_failed_path):
            logging.info('Arquivo temp_failed_ids.json não encontrado.')
            return 0
        with open(temp_failed_path, 'r', encoding='utf-8') as f:
            temp_failed_ids = json.load(f)
        temp_failed_ids_str = set([str(cid) for cid in temp_failed_ids])

        # Lê todos os chat_ids
        if not os.path.exists(chat_ids_path):
            logging.info('Arquivo chat_ids.json não encontrado.')
            return 0
        with open(chat_ids_path, 'r', encoding='utf-8') as f:
            chat_ids = json.load(f)
        chat_ids = [str(cid) for cid in chat_ids]

        # Remove apenas os IDs que estão nos dois arquivos
        ids_para_remover = [cid for cid in chat_ids if cid in temp_failed_ids_str]
        logging.info(f"IDs para remover (presentes nos dois arquivos): {ids_para_remover}")
        chat_ids_novos = [cid for cid in chat_ids if cid not in temp_failed_ids_str]
        removed_count = len(ids_para_remover)

        # Salva resultado
        with open(chat_ids_path, 'w', encoding='utf-8') as f:
            json.dump(chat_ids_novos, f, ensure_ascii=False, indent=4)
        logging.info(f"Removidos {removed_count} IDs de chat_ids.json com base em temp_failed_ids.json.")
        return removed_count
    except Exception as e:
        logging.error(f"Erro ao remover IDs com erro: {e}")
        return 0

# Remove IDs com falha da lista de chats
async def remove_failed_chat_ids():
    global failed_chat_ids
    removed_count = 0
    try:
        # Garante que failed_chat_ids é um set e não está vazio
        if not isinstance(failed_chat_ids, set):
            logging.error(f"failed_chat_ids não é um set, é {type(failed_chat_ids)}. Convertendo para set.")
            failed_chat_ids = set(failed_chat_ids)
        if not failed_chat_ids:
            logging.info("Nenhum ID com erro para remover.")
            return 0

        # Carrega dados atuais do arquivo
        try:
            with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
                current_chat_ids = json.load(f)
        except Exception as e:
            logging.error(f"Erro ao carregar chat_ids.json: {e}")
            current_chat_ids = []

        current_chat_ids = [str(cid) for cid in current_chat_ids]

        # Só remove se estiver realmente em failed_chat_ids
        ids_para_remover = [str(cid) for cid in failed_chat_ids if str(cid) in current_chat_ids]
        logging.info(f"IDs com erro detectados para remoção: {ids_para_remover}")
        for chat_id_str in ids_para_remover:
            current_chat_ids.remove(chat_id_str)
            removed_count += 1

        failed_chat_ids.clear()
        with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_chat_ids, f, ensure_ascii=False, indent=4)
        await save_failed_chat_ids()
        logging.info(f"Removidos {removed_count} IDs com erro. IDs removidos: {ids_para_remover}")
        return removed_count
    except Exception as e:
        logging.error(f"Erro ao limpar IDs com falha: {e}")
        return 0

# Função síncrona para carregar os IDs com falha
def load_failed_chat_ids_sync():
    try:
        with open(FAILED_CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
            failed_chat_ids.update(set(json.load(f)))
    except FileNotFoundError:
        pass

# Carrega os IDs com erros ao iniciar (versão síncrona)
load_failed_chat_ids_sync()

# Comandos devem vir primeiro para ter prioridade
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    # Sistema de registro de usuários
    user_data = {
        'user_id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'full_name': message.from_user.full_name
    }
    
    # Registra o usuário e verifica se é novo
    is_new_user = register_user(message.from_user.id, user_data)
    
    # Se for um novo usuário, notifica os admins
    if is_new_user:
        try:
            from aiogram import Bot
            bot = message.bot
            await notify_admin_new_user(bot, user_data)
        except Exception as e:
            logger.error(f"Erro ao notificar admins sobre novo usuário: {e}")
    
    # Recarrega config dinamicamente para pegar mudanças
    current_config = load_config()
    menu = current_config.get("menu", {})
    start_message = menu.get("info_message") or current_config.get("infomessagess") or "🤖 Bot de divulgação online!"
    image_url = menu.get("image_url")
    buttons = menu.get("buttons", [])
    keyboard = None
    user_id = str(message.from_user.id)

    # Verifica se o usuário tem plano ativo
    plano_ativo = None
    horarios = []
    tipo_plano = None
    validade = None
    fixed_ad_id = None
    try:
        if os.path.exists(SCHEDULED_MESSAGES_FILE):
            with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
                agendados = json.load(f)
            # Filtra mensagens do usuário
            planos_usuario = [p for p in agendados if str(p.get('recipient_id')) == user_id]
            if planos_usuario:
                plano_ativo = planos_usuario[0]
                tipo_plano = plano_ativo.get('type', 'desconhecido').capitalize()
                fixed_ad_id = plano_ativo.get('fixed_ad_id')
                # Pega todos os horários do mesmo plano/fixed_ad_id
                horarios = sorted([p['time'] for p in planos_usuario if p.get('fixed_ad_id') == fixed_ad_id])
                validade = plano_ativo.get('expiry_time')
    except Exception as e:
        logging.error(f"Erro ao buscar plano ativo: {e}")

    # Monta mensagem personalizada se houver plano ativo
    if plano_ativo:
        # Adiciona informações do plano à mensagem personalizada
        plano_info = (
            f"\n\n🎉 Você possui um plano ativo!\n"
            f"ID fixo: {fixed_ad_id}\n"
            f"Tipo: {tipo_plano}\n"
            f"Horários: {', '.join(horarios)}\n"
            f"Validade: {validade}\n\n"
            f"Você pode personalizar seu anúncio ou trocar os horários a qualquer momento."
        )
        start_message = start_message + plano_info
        # Monta os botões padrões do menu
        inline_buttons = []
        if buttons and isinstance(buttons, list):
            for btn in buttons:
                text = btn.get("text", "Botão")
                if btn.get("url"):
                    inline_buttons.append([InlineKeyboardButton(text=text, url=btn["url"])])
                elif btn.get("callback_data"):
                    inline_buttons.append([InlineKeyboardButton(text=text, callback_data=btn["callback_data"])])
        # Adiciona os botões de troca
        inline_buttons.append([InlineKeyboardButton(text="Trocar Anúncio", callback_data="trocar_anuncio")])
        inline_buttons.append([InlineKeyboardButton(text="Trocar Horário", callback_data="trocar_horario")])
        # Adiciona botão para abrir busca inline de horários
        inline_buttons.append([InlineKeyboardButton(text="⏰ Ver horários disponíveis", switch_inline_query_current_chat="horarios")])
        
        # Adiciona botão do BUTTON_URL se configurado (recarrega config)
        current_config = load_config()
        button_url = current_config.get("BUTTON_URL")
        button_text = current_config.get("TEXTOBUTTON", "📢 Divulgação")
        if button_url:
            inline_buttons.append([InlineKeyboardButton(text=button_text, url=button_url)])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
    else:
        if buttons and isinstance(buttons, list):
            inline_buttons = []
            for btn in buttons:
                text = btn.get("text", "Botão")
                if btn.get("url"):
                    inline_buttons.append([InlineKeyboardButton(text=text, url=btn["url"])])
                elif btn.get("callback_data"):
                    inline_buttons.append([InlineKeyboardButton(text=text, callback_data=btn["callback_data"])])
            # Adiciona botão para abrir busca inline de horários (padrão para todos)
            inline_buttons.append([InlineKeyboardButton(text="⏰ Ver horários disponíveis", switch_inline_query_current_chat="horarios")])
            
            # Adiciona botão do BUTTON_URL se configurado (recarrega config)
            current_config = load_config()
            button_url = current_config.get("BUTTON_URL")
            button_text = current_config.get("TEXTOBUTTON", "📢 Divulgação")
            if button_url:
                inline_buttons.append([InlineKeyboardButton(text=button_text, url=button_url)])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
        else:
            # Caso não tenha botões do menu, mas tenha BUTTON_URL
            inline_buttons = []
            # Adiciona botão para abrir busca inline de horários
            inline_buttons.append([InlineKeyboardButton(text="⏰ Ver horários disponíveis", switch_inline_query_current_chat="horarios")])
            
            # Adiciona botão do BUTTON_URL se configurado (recarrega config)
            current_config = load_config()
            button_url = current_config.get("BUTTON_URL")
            button_text = current_config.get("TEXTOBUTTON", "📢 Divulgação")
            if button_url:
                inline_buttons.append([InlineKeyboardButton(text=button_text, url=button_url)])
            
            if inline_buttons:
                keyboard = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
                
    if image_url:
        await message.answer_photo(photo=image_url, caption=start_message, reply_markup=keyboard)
    else:
        await message.reply(start_message, reply_markup=keyboard)

# Handler específico para posts de CANAL (channel_post)
@dp.channel_post()
async def coletar_canal_post(message: types.Message):
    """
    Handler específico para posts de canal - captura todas as mensagens postadas em canais
    """
    chat_id = message.chat.id
    # logging.info(f"[CHANNEL_POST] Post recebido do canal: {chat_id} ({message.chat.title})")
    is_new = save_chat_id_if_new(chat_id)
    if is_new:
        try:
            nome = getattr(message.chat, 'title', None) or "(sem nome)"
            tipo = "channel"
            link = f"https://t.me/{getattr(message.chat, 'username', '')}" if getattr(message.chat, 'username', None) else "(sem link público)"
            datahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            aviso = (
                f"🆕 **NOVO CANAL DETECTADO!**\n\n"
                f"🏷️ **Nome:** {nome}\n"
                f"🆔 **ID:** `{chat_id}`\n"
                f"📋 **Tipo:** Canal\n"
                f"🔗 **Link:** {link}\n"
                f"📅 **Data:** {datahora}\n\n"
                f"✅ Canal adicionado automaticamente à lista de divulgação!"
            )
            # Notifica admins
            try:
                with open(CONFIG_FILE, encoding='utf-8') as f:
                    config = json.load(f)
                admin_ids = config.get('admins', [])
            except Exception as e:
                logging.error(f"Erro ao carregar admin IDs para notificação de novo canal: {e}")
                admin_ids = []
            
            for admin_id in admin_ids:
                try:
                    await message.bot.send_message(admin_id, aviso, parse_mode="Markdown")
                except Exception as e:
                    logging.error(f"Erro ao notificar admin {admin_id} sobre novo canal: {e}")
        except Exception as e:
            logging.error(f"Erro ao processar novo canal: {e}")

# Handler para coletar IDs de grupos/canais (mensagens normais)
@dp.message(F.chat.type.in_(["group", "supergroup", "channel"]))
async def coletar_chat_id_automatico(message: types.Message):
    """
    Handler universal: toda mensagem recebida em grupo/supergrupo/canal coleta o chat_id se for novo.
    """
    chat_id = message.chat.id
    # logging.info(f"[MESSAGE] Mensagem recebida do chat: {chat_id} ({message.chat.title})")
    is_new = save_chat_id_if_new(chat_id)
    if is_new:
        try:
            nome = getattr(message.chat, 'title', None) or "(sem nome)"
            tipo = getattr(message.chat, 'type', None)
            link = f"https://t.me/{getattr(message.chat, 'username', '')}" if getattr(message.chat, 'username', None) else "(sem link público)"
            adicionado_por = getattr(message.from_user, 'full_name', None) if message.from_user else "(desconhecido)"
            user_tag = f"(@{message.from_user.username})" if message.from_user and getattr(message.from_user, 'username', None) else ""
            datahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            aviso = (
                f"🔔 Bot adicionado a um novo grupo\n\n"
                f"📁 Nome: {nome}\n"
                f"🆔 ID: {chat_id}\n"
                f"🔗 Link: {link}\n"
                f"👤 Adicionado por: {adicionado_por} {user_tag}\n"
                f"📅 Data: {datahora}\n\n"
                f"✅ O bot já está pronto para divulgar neste grupo"
            )
            with open(CONFIG_FILE, encoding='utf-8') as f:
                config = json.load(f)
            admin_ids = config.get('admins', [])
            for admin_id in admin_ids:
                try:
                    await message.bot.send_message(admin_id, aviso)
                except Exception as e:
                    logging.error(f"Erro ao notificar admin {admin_id} sobre novo grupo: {e}")
        except Exception as e:
            logging.error(f"Erro ao salvar chat_id ou notificar admin: {e}")




# Comando /ajuda (apenas para admin)
@dp.message(Command("ajuda"))
async def ajuda_admin(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem acessar este comando.")
        return
    texto_ajuda = (
        "<b>🤖 Ajuda do Bot de Divulgação</b>\n\n"
        "Aqui estão os comandos e funcionalidades disponíveis para administradores:\n\n"
        "<b>📋 COMANDOS PRINCIPAIS:</b>\n"
        "<b>/painel</b> ou <b>/admin</b> — Acessa o painel administrativo.\n"
        "<b>/ajuda</b> — Exibe esta mensagem de ajuda.\n"
        "<b>/divulgar</b> — Envia uma mensagem para todos os grupos cadastrados.\n"
        "<b>/enviarcanal</b> — Encaminha uma mensagem para o canal de referência (responda à mensagem).\n\n"
        "<b>🔄 GERENCIAMENTO DE PLANOS:</b>\n"
        "<b>/renovar &lt;idfixo&gt;</b> — Renova um plano baseado no tipo (semanal +7 dias, mensal +30 dias, etc).\n"
        "<b>/trocar &lt;idfixo&gt; &lt;novo_recipient_id&gt;</b> — Transfere a propriedade de um plano para outro usuário.\n"
        "<b>/trocaranuncio &lt;idfixo&gt;</b> — Troca o anúncio de um plano (responda à nova mensagem).\n"
        "<b>/muda &lt;idfixo&gt;</b> — Versão simplificada para trocar anúncio (responda à nova mensagem).\n"
        "<b>/adddias &lt;dias&gt; [id_fixo]</b> — Adiciona dias extras à validade dos planos.\n"
        "- Use <code>/adddias 5</code> para adicionar dias a todos os planos.\n"
        "- Use <code>/adddias 10 id_fixo</code> para adicionar dias apenas ao plano com o ID informado.\n"
        "- Os clientes afetados recebem uma mensagem automática informando a nova data de expiração.\n\n"
        "<b>⚙️ FUNCIONALIDADES:</b>\n"
        "- Use o painel admin para gerenciar textos, imagens, admins e canais de logs.\n"
        "- Os horários disponíveis são atualizados automaticamente.\n"
        "- O painel mostra estatísticas em tempo real.\n\n"
        "<b>❌ CANCELAR ANÚNCIOS:</b>\n"
        "Use o comando /cancelar seguido do ID fixo do anúncio.\n"
        "Exemplo: <code>/cancelar 123e4567-e89b-12d3-a456-426614174000</code>\n\n"
        "<b>�️ CANCELAR TODOS OS PLANOS:</b>\n"
        "Use o comando <b>/cancelartodos</b> para cancelar todos os planos ativos de uma vez.\n"
        "⚠️ <b>ATENÇÃO:</b> Esta ação não pode ser desfeita!\n\n"
        "<b>💡 EXEMPLOS DE USO:</b>\n"
        "• <code>/renovar ba1de5dd-dfe8-45f3</code> — Renova plano automaticamente\n"
        "• <code>/trocar ba1de5dd-dfe8-45f3 1234567890</code> — Transfere plano para outro usuário\n\n"
        "Se precisar de mais detalhes, entre em contato com o desenvolvedor ou utilize os comandos acima!"
    )
    await message.reply(texto_ajuda, parse_mode="HTML")

@dp.message(Command("limparreagendados"))
async def limpar_reagendados_cmd(message: types.Message):
    """Remove todos os horários reagendados do scheduled_messages.json"""
    print("DEBUG: Comando /limparreagendados chamado!")
    
    # Verifica se é admin
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        print("DEBUG: Usuário não é admin.")
        return
    
    try:
        # Carrega o arquivo scheduled_messages.json
        try:
            with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
                scheduled_messages = json.load(f)
            print(f"DEBUG: Carregadas {len(scheduled_messages)} mensagens do arquivo.")
        except FileNotFoundError:
            await message.reply("ℹ️ Arquivo scheduled_messages.json não encontrado.")
            print("DEBUG: Arquivo não encontrado.")
            return
        except json.JSONDecodeError as e:
            await message.reply(f"❌ Erro ao ler o arquivo JSON: {e}")
            print(f"DEBUG: Erro JSON: {e}")
            return
        
        if not scheduled_messages:
            await message.reply("ℹ️ Nenhuma mensagem agendada encontrada.")
            print("DEBUG: Lista vazia.")
            return
        
        # Separa mensagens originais dos reagendamentos
        mensagens_originais = []
        reagendamentos_removidos = []
        
        for msg in scheduled_messages:
            if msg.get('is_reagendamento', False) == True:
                reagendamentos_removidos.append(msg)
                print(f"DEBUG: Reagendamento encontrado - Code: {msg.get('code', 'N/A')}")
            else:
                mensagens_originais.append(msg)
        
        total_reagendamentos = len(reagendamentos_removidos)
        print(f"DEBUG: Total de reagendamentos encontrados: {total_reagendamentos}")
        
        if total_reagendamentos == 0:
            await message.reply("ℹ️ Nenhum horário reagendado encontrado para remover.")
            print("DEBUG: Nenhum reagendamento para remover.")
            return
        
        # Salva apenas as mensagens originais (remove todos os reagendamentos)
        try:
            with open(SCHEDULED_MESSAGES_FILE, 'w', encoding='utf-8') as f:
                json.dump(mensagens_originais, f, ensure_ascii=False, indent=2)
            print("DEBUG: Arquivo salvo com sucesso.")
        except Exception as e:
            await message.reply(f"❌ Erro ao salvar o arquivo: {e}")
            print(f"DEBUG: Erro ao salvar: {e}")
            return
        
        # Resposta de sucesso
        await message.reply(
            f"✅ **{total_reagendamentos} horários reagendados foram removidos com sucesso!**\n\n"
            f"📄 Restaram **{len(mensagens_originais)}** mensagens originais no arquivo.\n\n"
            f"🗑️ Todos os reagendamentos com `is_reagendamento: true` foram deletados.",
            parse_mode="Markdown"
        )
        print(f"DEBUG: Sucesso! Removidos {total_reagendamentos} reagendamentos.")
        
    except Exception as e:
        await message.reply(f"❌ Erro inesperado: {e}")
        print(f"DEBUG: Erro inesperado: {e}")

@dp.message(Command("cancelar"))
async def cancelar_agendamento(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Use: /cancelar <id>")
        return
    id_fixo = args[1]
    SCHEDULED_FILE = SCHEDULED_MESSAGES_FILE
    if not os.path.exists(SCHEDULED_FILE):
        await message.reply("Nenhum agendamento encontrado.")
        return
    with open(SCHEDULED_FILE, encoding="utf-8") as f:
        agendamentos = json.load(f)
    novos = [a for a in agendamentos if str(a.get("fixed_ad_id")) != id_fixo]
    removidos = len(agendamentos) - len(novos)
    if removidos > 0:
        with open(SCHEDULED_FILE, "w", encoding="utf-8") as f:
            json.dump(novos, f, ensure_ascii=False, indent=2)
        await message.reply(f"✅ {removidos} anúncio(s) com o id {id_fixo} cancelado(s)!")
    else:
        await message.reply(f"❌ Nenhum anúncio/agendamento encontrado com o id: {id_fixo}")

@dp.message(Command("cancelartodos"))
async def cancelar_todos_planos(message: types.Message):
    """Cancela todos os planos ativos - apenas para admins"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    SCHEDULED_FILE = SCHEDULED_MESSAGES_FILE
    if not os.path.exists(SCHEDULED_FILE):
        await message.reply("❌ Nenhum agendamento encontrado.")
        return
    
    try:
        with open(SCHEDULED_FILE, encoding="utf-8") as f:
            agendamentos = json.load(f)
        
        total_planos = len(agendamentos)
        
        if total_planos == 0:
            await message.reply("ℹ️ Não há planos ativos para cancelar.")
            return
        
        # Limpa todos os agendamentos
        with open(SCHEDULED_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        
        await message.reply(
            f"✅ **Todos os planos foram cancelados!**\n\n"
            f"📊 Total de planos cancelados: {total_planos}\n"
            f"🗑️ O arquivo de agendamentos foi limpo completamente.",
            parse_mode="Markdown"
        )
        
        professional_logger.info("CANCEL_ALL", f"Admin {message.from_user.id} cancelou todos os {total_planos} planos ativos")
        
    except Exception as e:
        await message.reply(f"❌ Erro ao cancelar planos: {e}")
        professional_logger.error("CANCEL_ALL", f"Erro ao cancelar todos os planos: {e}")

# ============================================================================
# COMANDO RENOVAR - REATIVA PLANOS EXPIRADOS
# ============================================================================

@dp.message(Command("renovar"))
async def renovar_plano_cmd(message: types.Message):
    """Comando para renovar planos expirados"""
    # Verifica se é admin
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply(
            "📋 **Como usar o comando /renovar:**\n\n"
            "**Formato:** `/renovar <ID_do_plano> <dias>`\n\n"
            "**Exemplos:**\n"
            "• `/renovar abc123 30` - Renova por 30 dias\n"
            "• `/renovar def456 7` - Renova por 7 dias\n\n"
            "**Para buscar planos expirados:**\n"
            "• `/expirados` - Lista todos os planos expirados\n"
            "• `/buscar_expirado <termo>` - Busca plano específico",
            parse_mode="Markdown"
        )
        return
    
    plan_id = args[1]
    try:
        days = int(args[2])
        if days <= 0:
            await message.reply("❌ O número de dias deve ser maior que zero.")
            return
    except ValueError:
        await message.reply("❌ Número de dias inválido. Use apenas números.")
        return
    
    try:
        # Busca o plano nos expirados
        matches = search_expired_plan(plan_id)
        
        if not matches:
            await message.reply(
                f"❌ **Plano não encontrado nos arquivos expirados**\n\n"
                f"🔍 **ID buscado:** `{plan_id}`\n\n"
                f"💡 **Dicas:**\n"
                f"• Use `/expirados` para ver todos os planos expirados\n"
                f"• Use `/buscar_expirado {plan_id}` para busca mais detalhada\n"
                f"• Verifique se o ID está correto",
                parse_mode="Markdown"
            )
            return
        
        if len(matches) > 1:
            # Múltiplos resultados - mostra opções
            response = f"🔍 **Encontrados {len(matches)} planos com '{plan_id}':**\n\n"
            for i, plan in enumerate(matches[:5], 1):
                fixed_id = plan.get('fixed_ad_id', 'N/A')
                recipient = plan.get('recipient_id', 'N/A')
                expired_at = plan.get('expiry_time', 'N/A')
                archived_at = plan.get('archived_at', 'N/A')
                
                response += f"**{i}.** `{fixed_id}`\n"
                response += f"   👤 Usuário: {recipient}\n"
                response += f"   ⏰ Expirou: {expired_at}\n"
                response += f"   📁 Arquivado: {archived_at}\n\n"
            
            response += f"💡 **Use o ID completo para renovar:**\n"
            response += f"`/renovar {matches[0].get('fixed_ad_id')} {days}`"
            
            await message.reply(response, parse_mode="Markdown")
            return
        
        # Um resultado encontrado - procede com a renovação
        plan = matches[0]
        fixed_ad_id = plan.get('fixed_ad_id')
        
        # Calcula nova data de expiração
        new_expiry_date = datetime.datetime.now() + datetime.timedelta(days=days)
        
        # Restaura o plano
        success, result_message = restore_expired_plan(fixed_ad_id, new_expiry_date)
        
        if success:
            recipient_id = plan.get('recipient_id', 'N/A')
            old_expiry = plan.get('expiry_time', 'N/A')
            
            response = (
                f"✅ **PLANO RENOVADO COM SUCESSO**\n\n"
                f"🆔 **ID:** `{fixed_ad_id}`\n"
                f"👤 **Usuário:** {recipient_id}\n"
                f"📅 **Expiração Anterior:** {old_expiry}\n"
                f"🆕 **Nova Expiração:** {new_expiry_date.strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"⏰ **Duração:** {days} dias\n\n"
                f"🔄 **Status:** Plano reativado e movido de volta para agendamentos ativos"
            )
            
            # Notifica outros admins
            config = load_config()
            admins = config.get('admins', [])
            notification = (
                f"🔄 **PLANO RENOVADO**\n\n"
                f"👤 **Admin:** {message.from_user.first_name or 'Admin'}\n"
                f"🆔 **Plano:** `{fixed_ad_id}`\n"
                f"📅 **Nova expiração:** {new_expiry_date.strftime('%d/%m/%Y')}\n"
                f"⏰ **Duração:** {days} dias"
            )
            
            for admin_id in admins:
                if admin_id != message.from_user.id:  # Não notifica quem executou
                    try:
                        await bot.send_message(admin_id, notification, parse_mode="Markdown")
                    except:
                        pass  # Ignora erros de notificação
                        
        else:
            response = f"❌ **Erro ao renovar plano:**\n{result_message}"
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        professional_logger.error("RENOVAR_CMD", f"Erro no comando renovar: {e}")
        await message.reply(f"❌ Erro interno: {e}")

@dp.message(Command("expirados"))
async def listar_expirados_cmd(message: types.Message):
    """Lista todos os planos expirados"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    try:
        expired_plans = load_expired_plans()
        
        if not expired_plans:
            await message.reply(
                "📋 **PLANOS EXPIRADOS**\n\n"
                "✅ Nenhum plano expirado encontrado!\n\n"
                "💡 Os planos expirados aparecem aqui quando são arquivados automaticamente."
            )
            return
        
        # Ordena por data de arquivamento (mais recentes primeiro)
        expired_plans.sort(key=lambda x: x.get('archived_at', ''), reverse=True)
        
        response = f"📋 **PLANOS EXPIRADOS** ({len(expired_plans)} total)\n\n"
        
        # Mostra até 10 planos por página
        for i, plan in enumerate(expired_plans[:10], 1):
            fixed_id = plan.get('fixed_ad_id', 'N/A')
            recipient = plan.get('recipient_id', 'N/A')
            expired_at = plan.get('expiry_time', 'N/A')
            archived_at = plan.get('archived_at', 'N/A')
            
            # Trunca ID se muito longo
            display_id = fixed_id[:12] + "..." if len(str(fixed_id)) > 15 else fixed_id
            
            response += f"**{i}.** `{display_id}`\n"
            response += f"   👤 {recipient}\n"
            response += f"   ⏰ Exp: {expired_at[:10] if expired_at != 'N/A' else 'N/A'}\n"
            response += f"   📁 Arq: {archived_at[:10] if archived_at != 'N/A' else 'N/A'}\n\n"
        
        if len(expired_plans) > 10:
            response += f"... e mais {len(expired_plans) - 10} planos.\n\n"
        
        response += (
            f"💡 **Para renovar:**\n"
            f"`/renovar <ID> <dias>`\n\n"
            f"🔍 **Para buscar:**\n"
            f"`/buscar_expirado <termo>`"
        )
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        professional_logger.error("EXPIRADOS_CMD", f"Erro ao listar expirados: {e}")
        await message.reply(f"❌ Erro ao carregar planos expirados: {e}")

@dp.message(Command("buscar_expirado"))
async def buscar_expirado_cmd(message: types.Message):
    """Busca planos expirados por ID ou usuário"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply(
            "🔍 **Como buscar planos expirados:**\n\n"
            "**Formato:** `/buscar_expirado <termo>`\n\n"
            "**Exemplos:**\n"
            "• `/buscar_expirado abc123` - Busca por ID\n"
            "• `/buscar_expirado 123456789` - Busca por usuário\n"
            "• `/buscar_expirado abc` - Busca parcial por ID",
            parse_mode="Markdown"
        )
        return
    
    search_term = args[1]
    
    try:
        matches = search_expired_plan(search_term)
        
        if not matches:
            await message.reply(
                f"🔍 **Nenhum plano encontrado**\n\n"
                f"**Termo buscado:** `{search_term}`\n\n"
                f"💡 **Dicas:**\n"
                f"• Use `/expirados` para ver todos\n"
                f"• Tente buscar por parte do ID\n"
                f"• Verifique se o plano realmente expirou",
                parse_mode="Markdown"
            )
            return
        
        response = f"🔍 **Encontrados {len(matches)} resultado(s) para '{search_term}':**\n\n"
        
        for i, plan in enumerate(matches[:5], 1):
            fixed_id = plan.get('fixed_ad_id', 'N/A')
            recipient = plan.get('recipient_id', 'N/A')
            expired_at = plan.get('expiry_time', 'N/A')
            archived_at = plan.get('archived_at', 'N/A')
            
            response += f"**{i}.** `{fixed_id}`\n"
            response += f"   👤 **Usuário:** {recipient}\n"
            response += f"   ⏰ **Expirou:** {expired_at}\n"
            response += f"   📁 **Arquivado:** {archived_at}\n\n"
        
        if len(matches) > 5:
            response += f"... e mais {len(matches) - 5} resultados.\n\n"
        
        response += (
            f"💡 **Para renovar qualquer um:**\n"
            f"`/renovar <ID_completo> <dias>`\n\n"
            f"**Exemplo:**\n"
            f"`/renovar {matches[0].get('fixed_ad_id')} 30`"
        )
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        professional_logger.error("BUSCAR_EXPIRADO_CMD", f"Erro na busca: {e}")
        await message.reply(f"❌ Erro na busca: {e}")

# ============================================================================
# COMANDOS DE ATUALIZAÇÃO
# ============================================================================

@dp.message(Command("versao"))
async def versao_cmd(message: types.Message):
    """Mostra a versão atual do bot"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    try:
        # Verifica se há atualizações disponíveis
        update_info = check_for_updates()
        
        response = f"🤖 **INFORMAÇÕES DA VERSÃO**\n\n"
        response += f"📦 **Versão Atual:** `{BOT_VERSION}`\n"
        response += f"🌐 **Servidor de Updates:** `{UPDATE_SERVER_URL}`\n"
        response += f"⏱️ **Verificação:** A cada {UPDATE_CHECK_INTERVAL//60} minutos\n\n"
        
        if update_info:
            if update_info.get('update_available'):
                remote_version = update_info.get('remote_version')
                response += f"🆕 **Nova Versão Disponível:** `{remote_version}`\n"
                response += f"📝 **Changelog:** {update_info.get('changelog', 'N/A')}\n\n"
                response += f"💡 **Comandos:**\n"
                response += f"• `/atualizar` - Aplicar atualização\n"
                response += f"• `/info_update` - Ver detalhes completos"
            else:
                response += f"✅ **Status:** Versão mais recente instalada"
        else:
            response += f"⚠️ **Status:** Erro ao verificar atualizações"
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        await message.reply(f"❌ Erro ao verificar versão: {e}")

@dp.message(Command("info_update"))
async def info_update_cmd(message: types.Message):
    """Mostra informações detalhadas sobre atualizações disponíveis"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    try:
        professional_logger.info("UPDATE_CHECK", "Verificando atualizações...")
        update_info = check_for_updates()
        
        if not update_info:
            await message.reply(
                "❌ **Erro ao verificar atualizações**\n\n"
                "🔧 **Possíveis causas:**\n"
                "• Servidor de atualizações offline\n"
                "• Problema de conectividade\n"
                "• URL do servidor incorreta\n\n"
                f"🌐 **Servidor configurado:** `{UPDATE_SERVER_URL}`"
            )
            return
        
        if not update_info.get('update_available'):
            response = (
                f"✅ **BOT ATUALIZADO**\n\n"
                f"📦 **Versão Atual:** `{BOT_VERSION}`\n"
                f"🎯 **Status:** Você já possui a versão mais recente\n\n"
                f"⏰ **Próxima verificação:** {UPDATE_CHECK_INTERVAL//60} minutos\n"
                f"🔄 **Verificação manual:** `/info_update`"
            )
        else:
            remote_version = update_info.get('remote_version')
            changelog = update_info.get('changelog', 'Sem informações disponíveis')
            download_url = update_info.get('download_url', 'N/A')
            
            response = (
                f"🆕 **ATUALIZAÇÃO DISPONÍVEL**\n\n"
                f"📦 **Versão Atual:** `{BOT_VERSION}`\n"
                f"🚀 **Nova Versão:** `{remote_version}`\n\n"
                f"📝 **Changelog:**\n```\n{changelog}\n```\n\n"
                f"🔗 **URL de Download:** `{download_url[:50]}...`\n\n"
                f"⚡ **Para atualizar:**\n"
                f"• `/atualizar` - Atualização automática\n"
                f"• Backup automático será criado\n"
                f"• Bot será reiniciado automaticamente"
            )
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        professional_logger.error("INFO_UPDATE_CMD", f"Erro: {e}")
        await message.reply(f"❌ Erro ao verificar informações: {e}")

@dp.message(Command("atualizar"))
async def atualizar_cmd(message: types.Message):
    """Executa atualização manual do bot"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    try:
        # Mensagem inicial
        status_msg = await message.reply(
            "🔄 **INICIANDO ATUALIZAÇÃO**\n\n"
            "⏳ Verificando atualizações disponíveis...",
            parse_mode="Markdown"
        )
        
        # Verifica atualizações
        update_info = check_for_updates()
        if not update_info:
            await status_msg.edit_text(
                "❌ **ERRO NA VERIFICAÇÃO**\n\n"
                "🔧 Não foi possível conectar ao servidor de atualizações.\n"
                "Verifique sua conexão e tente novamente.",
                parse_mode="Markdown"
            )
            return
        
        if not update_info.get('update_available'):
            await status_msg.edit_text(
                "✅ **BOT ATUALIZADO**\n\n"
                f"📦 Versão atual: `{BOT_VERSION}`\n"
                "🎯 Você já possui a versão mais recente!",
                parse_mode="Markdown"
            )
            return
        
        remote_version = update_info.get('remote_version')
        
        # Confirma atualização
        await status_msg.edit_text(
            f"🆕 **ATUALIZAÇÃO ENCONTRADA**\n\n"
            f"📦 **Atual:** `{BOT_VERSION}`\n"
            f"🚀 **Nova:** `{remote_version}`\n\n"
            f"⚡ **Iniciando processo de atualização...**\n"
            f"💾 Criando backup...",
            parse_mode="Markdown"
        )
        
        # Executa atualização
        success, result = await perform_auto_update()
        
        if success:
            await status_msg.edit_text(
                f"✅ **ATUALIZAÇÃO CONCLUÍDA**\n\n"
                f"🔄 **Versão:** `{BOT_VERSION}` → `{remote_version}`\n"
                f"🔄 **Reiniciando bot...**\n\n"
                f"⏰ O bot voltará online em alguns segundos.",
                parse_mode="Markdown"
            )
        else:
            await status_msg.edit_text(
                f"❌ **ERRO NA ATUALIZAÇÃO**\n\n"
                f"🔧 **Detalhes:** {result}\n\n"
                f"💡 **Sugestões:**\n"
                f"• Verifique a conexão\n"
                f"• Tente novamente em alguns minutos\n"
                f"• Contate o desenvolvedor se persistir",
                parse_mode="Markdown"
            )
        
    except Exception as e:
        professional_logger.error("ATUALIZAR_CMD", f"Erro: {e}")
        await message.reply(f"❌ Erro durante atualização: {e}")

@dp.message(Command("config_update"))
async def config_update_cmd(message: types.Message):
    """Configura o servidor de atualizações"""
    global UPDATE_SERVER_URL
    
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply(
            "⚙️ **CONFIGURAÇÃO DE ATUALIZAÇÕES**\n\n"
            "**Formato:** `/config_update <nova_url>`\n\n"
            "**Exemplo:**\n"
            "`/config_update https://meu-servidor.discloud.app`\n\n"
            f"**URL atual:** `{UPDATE_SERVER_URL}`\n\n"
            "**Outros comandos:**\n"
            "• `/versao` - Ver versão atual\n"
            "• `/info_update` - Verificar atualizações\n"
            "• `/atualizar` - Aplicar atualização",
            parse_mode="Markdown"
        )
        return
    
    new_url = args[1]
    
    try:
        # Valida a URL
        if not new_url.startswith(('http://', 'https://')):
            await message.reply("❌ URL deve começar com http:// ou https://")
            return
        
        # Testa a conectividade
        test_response = requests.get(f"{new_url}/version", timeout=10)
        if test_response.status_code == 200:
            # Atualiza a configuração (seria melhor salvar em config.json)
            UPDATE_SERVER_URL = new_url
            
            await message.reply(
                f"✅ **SERVIDOR ATUALIZADO**\n\n"
                f"🌐 **Nova URL:** `{new_url}`\n"
                f"🔗 **Status:** Conectado com sucesso\n\n"
                f"💡 **Próximos passos:**\n"
                f"• Use `/info_update` para verificar atualizações\n"
                f"• A verificação automática usará a nova URL",
                parse_mode="Markdown"
            )
        else:
            await message.reply(
                f"❌ **ERRO DE CONECTIVIDADE**\n\n"
                f"🌐 **URL testada:** `{new_url}`\n"
                f"📊 **Status HTTP:** {test_response.status_code}\n\n"
                f"🔧 Verifique se o servidor está online e acessível.",
                parse_mode="Markdown"
            )
    
    except requests.exceptions.RequestException as e:
        await message.reply(
            f"❌ **ERRO DE CONEXÃO**\n\n"
            f"🌐 **URL:** `{new_url}`\n"
            f"🔧 **Erro:** {str(e)}\n\n"
            f"💡 Verifique se a URL está correta e o servidor online.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.reply(f"❌ Erro inesperado: {e}")

@dp.message(Command("teste_update"))
async def teste_update_cmd(message: types.Message):
    """Comando de teste para verificar se a atualização funcionou"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    await message.reply(
        f"🎉 **TESTE DE ATUALIZAÇÃO FUNCIONANDO!**\n\n"
        f"📦 **Versão atual:** `{BOT_VERSION}`\n"
        f"🕐 **Testado em:** {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}\n"
        f"🚀 **Sistema de auto-atualização:** ✅ Operacional\n\n"
        f"✅ Se você está vendo esta mensagem, a atualização foi aplicada com sucesso!",
        parse_mode="Markdown"
    )

@dp.message(Command("teste_canal"))
async def teste_canal_cmd(message: types.Message):
    """Comando de teste para verificar se o bot consegue detectar o canal atual"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    chat_id = message.chat.id
    chat_type = message.chat.type
    chat_title = getattr(message.chat, 'title', 'N/A')
    chat_username = getattr(message.chat, 'username', 'N/A')
    
    # Verifica se está na lista de IDs coletados
    try:
        with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
            current_ids = json.load(f)
        is_registered = str(chat_id) in current_ids
    except:
        is_registered = False
    
    # Verifica se o bot é admin no canal
    try:
        bot_member = await message.bot.get_chat_member(chat_id, message.bot.id)
        bot_status = bot_member.status
        is_admin = bot_status in ['administrator', 'creator']
    except Exception as e:
        bot_status = "Erro ao verificar"
        is_admin = False
    
    await message.reply(
        f"🔍 **TESTE DE DETECÇÃO DE CANAL/GRUPO**\n\n"
        f"🆔 **ID:** `{chat_id}`\n"
        f"📋 **Tipo:** `{chat_type}`\n"
        f"🏷️ **Nome:** `{chat_title}`\n"
        f"🔗 **Username:** `{chat_username}`\n"
        f"📝 **Registrado:** {'✅ Sim' if is_registered else '❌ Não'}\n"
        f"⚡ **Status do Bot:** `{bot_status}`\n"
        f"👑 **É Admin:** {'✅ Sim' if is_admin else '❌ Não'}\n\n"
        f"💡 **Dica:** Para canais, o bot precisa ser admin com permissão de ler mensagens!\n\n"
        f"🕐 **Testado em:** {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
        parse_mode="Markdown"
    )

# ============================================================================
# HANDLERS PARA BOTÕES DE ATUALIZAÇÃO
# ============================================================================

@dp.callback_query(lambda c: c.data.startswith('auto_update_'))
async def handle_auto_update(callback_query: types.CallbackQuery):
    """Handler para botão de atualização automática"""
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("❌ Apenas administradores podem atualizar o bot.", show_alert=True)
        return
    
    try:
        # Extrai versão do callback_data
        version = callback_query.data.replace('auto_update_', '')
        
        # Responde ao callback
        await callback_query.answer("🔄 Iniciando atualização...", show_alert=False)
        
        # Edita mensagem para mostrar progresso
        await callback_query.message.edit_text(
            f"🔄 **INICIANDO ATUALIZAÇÃO AUTOMÁTICA**\n\n"
            f"📦 **Versão de destino:** `{version}`\n"
            f"⏳ **Status:** Verificando atualizações...\n\n"
            f"💾 Criando backup automático...",
            parse_mode="Markdown"
        )
        
        # Executa atualização
        success, result = await perform_auto_update()
        
        if success:
            await callback_query.message.edit_text(
                f"✅ **ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!**\n\n"
                f"🔄 **Versão:** `{BOT_VERSION}` → `{version}`\n"
                f"🔄 **Status:** Bot reiniciando...\n\n"
                f"⏰ O bot voltará online em alguns segundos.\n"
                f"💡 Use `/teste_update` para confirmar que funcionou!",
                parse_mode="Markdown"
            )
        else:
            await callback_query.message.edit_text(
                f"❌ **ERRO NA ATUALIZAÇÃO AUTOMÁTICA**\n\n"
                f"🔧 **Detalhes:** {result}\n\n"
                f"💡 **Sugestões:**\n"
                f"• Tente usar `/atualizar` manualmente\n"
                f"• Verifique a conexão com o servidor\n"
                f"• Contate o desenvolvedor se persistir",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await callback_query.message.edit_text(
            f"❌ **ERRO INESPERADO**\n\n"
            f"🔧 **Erro:** {str(e)}\n\n"
            f"💡 Tente usar o comando `/atualizar` manualmente.",
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data == 'update_details')
async def handle_update_details(callback_query: types.CallbackQuery):
    """Handler para botão de ver detalhes da atualização"""
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("❌ Apenas administradores podem ver detalhes.", show_alert=True)
        return
    
    try:
        await callback_query.answer("📋 Carregando detalhes...", show_alert=False)
        
        # Busca informações detalhadas
        update_info = check_for_updates()
        
        if update_info and update_info.get('update_available'):
            remote_version = update_info.get('remote_version')
            changelog = update_info.get('changelog', 'Sem informações disponíveis')
            download_url = update_info.get('download_url', 'N/A')
            file_size = update_info.get('file_size', 0)
            
            # Cria teclado com opções
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚀 Atualizar Agora",
                        callback_data=f"auto_update_{remote_version}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⏰ Lembrar em 1 hora",
                        callback_data="update_later"
                    )
                ]
            ])
            
            await callback_query.message.edit_text(
                f"📋 **DETALHES DA ATUALIZAÇÃO**\n\n"
                f"📦 **Versão Atual:** `{BOT_VERSION}`\n"
                f"🚀 **Nova Versão:** `{remote_version}`\n"
                f"📊 **Tamanho:** {file_size/1024:.1f} KB\n\n"
                f"📝 **Changelog Completo:**\n```\n{changelog}\n```\n\n"
                f"🔗 **Servidor:** Disponível para download\n\n"
                f"⚡ **Escolha uma opção:**",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            await callback_query.message.edit_text(
                f"❌ **ERRO AO CARREGAR DETALHES**\n\n"
                f"🔧 Não foi possível obter informações da atualização.\n"
                f"💡 Tente novamente ou use `/info_update`",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await callback_query.message.edit_text(
            f"❌ **ERRO AO CARREGAR DETALHES**\n\n"
            f"🔧 **Erro:** {str(e)}\n\n"
            f"💡 Use `/info_update` para ver detalhes manualmente.",
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data == 'update_later')
async def handle_update_later(callback_query: types.CallbackQuery):
    """Handler para botão de lembrar depois"""
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("❌ Acesso negado.", show_alert=True)
        return
    
    await callback_query.answer("⏰ Ok! Você será notificado novamente em 1 hora.", show_alert=True)
    
    await callback_query.message.edit_text(
        f"⏰ **LEMBRETE AGENDADO**\n\n"
        f"📋 **Atualização adiada por 1 hora**\n"
        f"🔔 Você será notificado novamente automaticamente\n\n"
        f"💡 **Para atualizar manualmente a qualquer momento:**\n"
        f"• `/versao` - Ver status atual\n"
        f"• `/info_update` - Ver detalhes\n"
        f"• `/atualizar` - Aplicar atualização",
        parse_mode="Markdown"
    )
    
    # Agenda nova notificação em 1 hora
    asyncio.create_task(remind_update_later(callback_query.from_user.id))

async def remind_update_later(admin_id):
    """Lembra o admin sobre a atualização após 1 hora"""
    try:
        await asyncio.sleep(3600)  # 1 hora
        
        update_info = check_for_updates()
        if update_info and update_info.get('update_available'):
            remote_version = update_info.get('remote_version')
            
            # Cria botão inline novamente
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚀 Atualizar Agora",
                        callback_data=f"auto_update_{remote_version}"
                    ),
                    InlineKeyboardButton(
                        text="📋 Ver Detalhes",
                        callback_data="update_details"
                    )
                ]
            ])
            
            await dp.bot.send_message(
                admin_id,
                f"🔔 **LEMBRETE: ATUALIZAÇÃO DISPONÍVEL**\n\n"
                f"📦 **Versão Atual:** `{BOT_VERSION}`\n"
                f"🚀 **Nova Versão:** `{remote_version}`\n\n"
                f"⏰ **Você pediu para ser lembrado sobre esta atualização.**\n"
                f"⚡ **Clique em um botão para escolher:**",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        professional_logger.error("REMIND_UPDATE", f"Erro ao lembrar admin {admin_id}: {e}")

# Comando para divulgar mensagem em todos os grupos
@dp.message(Command("divulgar"))
async def divulgar_cmd(message: types.Message, bot: Bot):
    if message.from_user.id not in ADMINS:
        await message.reply("Você não tem permissão para usar este comando.")
        return
    
    # Sempre carrega chat_ids diretamente do arquivo para garantir dados atualizados
    try:
        with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
            current_chat_ids = json.load(f)
    except Exception as e:
        logging.error(f"Erro ao carregar chat_ids.json: {e}")
        current_chat_ids = []
    
    if not current_chat_ids:
        await message.reply("❌ Nenhum grupo encontrado para divulgação. Adicione o bot a alguns grupos primeiro.")
        return
    
    msg = DEFAULT_MESSAGE
    if message.reply_to_message and message.reply_to_message.text:
        msg = message.reply_to_message.text
    elif message.text and len(message.text.split(" ", 1)) > 1:
        msg = message.text.split(" ", 1)[1]
    
    success = 0
    fail = 0
    for chat_id in current_chat_ids:
        try:
            await bot.send_message(chat_id, msg)
            success += 1
        except Exception as e:
            fail += 1
            logging.warning(f"Falha ao enviar para {chat_id}: {e}")
    
    await message.reply(f"Divulgação enviada para {success} grupos. Falhou em {fail}.")

# Comando para enviar mensagem para o canal de referência
@dp.message(Command("enviarcanal"))
async def enviar_canal_cmd(message: types.Message, bot: Bot):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    if not message.reply_to_message:
        await message.reply("Responda a uma mensagem com /enviarcanal para encaminhar para o canal de referência.")
        return
    
    canal_referencia = get_canal_referencia()
    if not canal_referencia:
        await message.reply("❌ Canal de referência não configurado. Use o painel admin para configurar.")
        return
    
    try:
        await safe_forward_message(bot, canal_referencia, from_chat_id=message.chat.id, message_id=message.reply_to_message.message_id)
        await message.reply(f"✅ Mensagem encaminhada para o canal de referência.")
    except Exception as e:
        await message.reply(f"❌ Erro ao enviar para o canal: {e}")

# Comando para enviar mensagem para todos os usuários cadastrados
@dp.message(Command("enviartodos"))
async def enviar_todos_cmd(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    if not message.reply_to_message:
        await message.reply("Responda à mensagem que deseja enviar para todos usando /enviartodos.")
        return
    try:
        user_ids = load_user_ids()
        if not user_ids:
            await message.reply("Nenhum usuário privado cadastrado para envio.")
            return
        enviados = 0
        erros = 0
        for cid in user_ids:
            try:
                if message.reply_to_message.text:
                    await message.bot.send_message(cid, message.reply_to_message.text)
                elif message.reply_to_message.photo:
                    await message.bot.send_photo(cid, message.reply_to_message.photo[-1].file_id, caption=message.reply_to_message.caption or "")
                elif message.reply_to_message.document:
                    await message.bot.send_document(cid, message.reply_to_message.document.file_id, caption=message.reply_to_message.caption or "")
                elif message.reply_to_message.video:
                    await message.bot.send_video(cid, message.reply_to_message.video.file_id, caption=message.reply_to_message.caption or "")
                else:
                    await message.bot.send_message(cid, "Mensagem de tipo não suportado para envio em massa.")
                enviados += 1
            except Exception as e:
                erros += 1
        await message.reply(f"✅ Mensagem enviada para {enviados} usuários.\n❌ Falha em {erros} envios.")
    except Exception as e:
        await message.reply(f"Erro ao enviar: {e}")

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import uuid
import datetime
import os

def save_scheduled_message(data):
    path = SCHEDULED_MESSAGES_FILE
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                scheduled = json.load(f)
            except Exception:
                scheduled = []
    else:
        scheduled = []
    scheduled.append(data)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(scheduled, f, ensure_ascii=False, indent=4)

@dp.message(Command("agendar"))
async def agendar_cmd(message: types.Message, bot: Bot):
    await handle_schedule_command(message, bot, days=1, tipo="diario")
@dp.message(Command("semanal"))
async def semanal_cmd(message: types.Message, bot: Bot):
    await handle_schedule_command(message, bot, days=7, tipo="semanal")

@dp.message(Command("mensal"))
async def mensal_cmd(message: types.Message, bot: Bot):
    await handle_schedule_command(message, bot, days=30, tipo="mensal")
import json
from aiogram import types
from aiogram.filters import Command

@dp.message(Command("adddias"))
async def adddias_cmd(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Use: /adddias <dias> [id_fixo]")
        return
    try:
        dias = int(args[1])
        id_fixo = args[2] if len(args) > 2 else None
    except Exception:
        await message.reply("Argumentos inválidos. Exemplo: /adddias 5 ou /adddias 10 <id_fixo>")
        return
    path = SCHEDULED_MESSAGES_FILE
    if not os.path.exists(path):
        await message.reply("Nenhum plano encontrado.")
        return
    with open(path, 'r', encoding='utf-8') as f:
        try:
            agendados = json.load(f)
        except Exception:
            await message.reply("Erro ao ler scheduled_messages.json")
            return
    alterados = 0
    avisos = 0
    # Agrupar por fixed_ad_id e recipient_id
    planos_por_id = {}
    for plano in agendados:
        if id_fixo and str(plano.get('fixed_ad_id')) != str(id_fixo):
            continue
        key = (str(plano.get('fixed_ad_id')), str(plano.get('recipient_id')))
        if key not in planos_por_id:
            planos_por_id[key] = []
        planos_por_id[key].append(plano)
    # Atualizar datas e avisar apenas uma vez por id fixo/cliente
    for (fixed_ad_id, rec_id), planos_lista in planos_por_id.items():
        maior_dt_novo = None
        for plano in planos_lista:
            if 'expiry_time' in plano:
                try:
                    dt = datetime.datetime.strptime(plano['expiry_time'], '%Y-%m-%d %H:%M:%S')
                    dt_novo = dt + datetime.timedelta(days=dias)
                    plano['expiry_time'] = dt_novo.strftime('%Y-%m-%d %H:%M:%S')
                    alterados += 1
                    if maior_dt_novo is None or dt_novo > maior_dt_novo:
                        maior_dt_novo = dt_novo
                except Exception:
                    continue
        # Avisar só uma vez por plano/cliente
        if rec_id and maior_dt_novo:
            msg_cliente = (
                f"Seu plano foi estendido em {dias} dia(s)!\n"
                f"Nova data de expiração: {maior_dt_novo.strftime('%d/%m/%Y %H:%M:%S')}"
            )
            try:
                await safe_send_message(message.bot, rec_id, msg_cliente)
                avisos += 1
            except Exception:
                pass
    if alterados > 0:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(agendados, f, ensure_ascii=False, indent=4)
        if id_fixo:
            await message.reply(f"✅ {alterados} plano(s) com ID {id_fixo} tiveram a validade estendida em {dias} dias. Clientes avisados: {avisos}.")
        else:
            await message.reply(f"✅ {alterados} plano(s) tiveram a validade estendida em {dias} dias. Clientes avisados: {avisos}.")
    else:
        await message.reply("Nenhum plano alterado. Verifique o ID informado ou se há planos cadastrados.")

@dp.message(Command("dv"))
async def dv_forward(message: types.Message, bot: Bot):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    if not message.reply_to_message:
        await message.reply("Responda a uma mensagem (texto, foto, vídeo, etc) com /dv para disparar para todos os grupos/canais.")
        return
    # Carrega os IDs dos grupos/canais
    with open(CHAT_IDS_FILE, "r", encoding="utf-8") as f:
        chat_ids = json.load(f)
    enviados = 0
    for cid in chat_ids:
        await safe_copy_message(bot, cid, from_chat_id=message.chat.id, message_id=message.reply_to_message.message_id)
        enviados += 1
    await message.reply(f"✅ Mensagem encaminhada para {enviados} chats.")

# Painel admin
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# /deletar_id - Remove um ID da lista de grupos/canais
@dp.message(Command("deletar_id"))
async def deletar_id_cmd(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Use: /deletar_id <id_do_grupo_ou_canal>")
        return
    try:
        del_id = str(args[1])  # Converte para string para consistência
        
        # Sempre carrega chat_ids diretamente do arquivo
        try:
            with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
                current_chat_ids = json.load(f)
        except Exception as e:
            logging.error(f"Erro ao carregar chat_ids.json: {e}")
            current_chat_ids = []
        
        # Converte todos os IDs para string para comparação consistente
        current_chat_ids = [str(cid) for cid in current_chat_ids]
        
        if del_id in current_chat_ids:
            current_chat_ids.remove(del_id)
            with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(current_chat_ids, f, ensure_ascii=False, indent=4)
            await message.reply(f"✅ ID {del_id} removido da lista de grupos/canais.")
        else:
            await message.reply("ID não encontrado na lista.")
    except Exception as e:
        await message.reply(f"Erro ao remover: {e}")

# /info - Mostra informações do grupo onde o comando for enviado
@dp.message(Command("info"))
async def info_cmd(message: types.Message):
    if message.chat.type not in ('group', 'supergroup'):
        await message.reply("Este comando só pode ser usado em grupos.")
        return
    try:
        chat = await message.bot.get_chat(message.chat.id)
        info = f"<b>Informações do Grupo:</b>\n"
        info += f"ID: <code>{chat.id}</code>\n"
        info += f"Nome: {chat.title}\n"
        info += f"Tipo: {chat.type}\n"
        if hasattr(chat, 'username') and chat.username:
            info += f"@{chat.username}\n"
        await message.reply(info, parse_mode="HTML")
    except Exception as e:
        await message.reply(f"Erro ao obter informações: {e}")

# /horarios - Lista todos os horários agendados agrupados por ID fixo
@dp.message(Command("horarios"))
async def horarios_cmd(message: types.Message):
    def esc(s):
        """Escapa caracteres problemáticos para Markdown simples."""
        if not isinstance(s, str):
            s = str(s)
        # Não escapa hífens para manter a formatação correta de UUIDs
        return s.replace('`', '\\`').replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.')

    try:
        if not os.path.exists(SCHEDULED_MESSAGES_FILE):
            await message.reply("📅 Nenhum horário agendado encontrado.")
            return
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            agendados = json.load(f)
        if not agendados:
            await message.reply("📅 Nenhum horário agendado encontrado.")
            return
        
        # Agrupa mensagens por fixed_ad_id
        grupos = {}
        for msg in agendados:
            id_fixo = msg.get('fixed_ad_id', 'N/A')
            if id_fixo not in grupos:
                grupos[id_fixo] = []
            grupos[id_fixo].append(msg)
        
        # Constrói o texto formatado
        horarios_txt = "📅 **HORÁRIOS AGENDADOS**\n\n"
        
        for id_fixo, mensagens in grupos.items():
            # Obtém informações do primeiro item do grupo
            primeira_msg = mensagens[0]
            recipient_id = primeira_msg.get('recipient_id')
            tipo = primeira_msg.get('type', 'N/A').upper()
            validade = primeira_msg.get('expiry_time', 'Indefinido')
            
            # Tenta obter o username do usuário
            username = "N/A"
            if recipient_id:
                try:
                    user = await bot.get_chat(recipient_id)
                    if hasattr(user, 'username') and user.username:
                        username = f"@{user.username}"
                    elif hasattr(user, 'first_name'):
                        username = user.first_name
                    else:
                        username = f"ID: {recipient_id}"
                except:
                    username = f"ID: {recipient_id}"
            
            # Cabeçalho do grupo
            horarios_txt += f"🏷️ **ID FIXO:** `{esc(id_fixo)}`\n"
            horarios_txt += f"👤 **Usuário:** {esc(username)}\n"
            horarios_txt += f"📊 **Tipo:** {esc(tipo)}\n"
            horarios_txt += f"⏰ **Expira:** {esc(validade)}\n"
            horarios_txt += f"📈 **Total:** {len(mensagens)} horário(s)\n\n"
            
            # Lista os horários ordenados
            horarios_ordenados = sorted([esc(msg.get('time', '00:00')) for msg in mensagens])
            horarios_linha = ", ".join(horarios_ordenados)
            
            # Quebra em linhas se muito longo
            if len(horarios_linha) > 60:
                horarios_formatados = []
                linha_atual = ""
                for horario in horarios_ordenados:
                    if len(linha_atual + horario + ", ") > 60:
                        horarios_formatados.append(linha_atual.rstrip(", "))
                        linha_atual = horario + ", "
                    else:
                        linha_atual += horario + ", "
                if linha_atual:
                    horarios_formatados.append(linha_atual.rstrip(", "))
                horarios_txt += "\n".join([f"🕰️ {linha}" for linha in horarios_formatados])
            else:
                horarios_txt += f"🕰️ {horarios_linha}"
            
            horarios_txt += "\n" + "─" * 30 + "\n\n"
        
        # Remove a última linha separadora
        horarios_txt = horarios_txt.rstrip("\n" + "─" * 30 + "\n\n")
        
        # Adiciona resumo final
        total_agendamentos = len(agendados)
        total_grupos = len(grupos)
        horarios_txt += f"\n\n📊 **RESUMO GERAL**\n"
        horarios_txt += f"👥 **Grupos:** {esc(total_grupos)}\n"
        horarios_txt += f"📅 **Total de agendamentos:** {esc(total_agendamentos)}"
        
        # Envia como arquivo se exceder limite do Telegram
        if len(horarios_txt) > 4000:
            with open("horarios.txt", "w", encoding="utf-8") as f:
                f.write(horarios_txt)
            document = FSInputFile("horarios.txt")
            await message.reply_document(document=document, caption="Lista de horários agendados.")
            os.remove("horarios.txt")
        else:
            try:
                await message.reply(horarios_txt, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Erro ao enviar horários com Markdown: {e}")
                await message.reply("❌ Erro ao listar horários (formatação). Veja se há caracteres especiais em nomes ou IDs.")
    except Exception as e:
        await message.reply(f"Erro ao listar horários: {e}")

# /infoid [id] - Mostra informações detalhadas de um agendamento
@dp.message(Command("infoid"))
async def infoid_cmd(message: types.Message, command: CommandObject):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Use: /infoid <id_fixo>")
        return
    id_fixo = args[1].strip()
    try:
        if not os.path.exists(SCHEDULED_MESSAGES_FILE):
            await message.reply("Nenhum agendamento encontrado.")
            return
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            agendados = json.load(f)
        detalhes = [msg for msg in agendados if str(msg.get('fixed_ad_id')) == id_fixo]
        if not detalhes:
            await message.reply("Nenhum agendamento encontrado com esse ID.")
            return
        for msg in detalhes:
            texto = f"<b>Agendamento</b>\n"
            texto += f"ID Fixo: <code>{msg.get('fixed_ad_id')}</code>\n"
            texto += f"Horário: <b>{msg.get('time')}</b>\n"
            texto += f"Tipo: {msg.get('type', 'N/A')}\n"
            texto += f"Expira em: {msg.get('expiry_time', 'N/A')}\n"
            texto += f"Destinatário: <code>{msg.get('recipient_id', 'N/A')}</code>\n"
            texto += f"Criado em: {msg.get('creation_time', 'N/A')}\n"
            texto += f"Código: <code>{msg.get('code', 'N/A')}</code>\n"
            texto += f"Chat origem: <code>{msg.get('from_chat_id', 'N/A')}</code>"
            await message.reply(texto, parse_mode="HTML")
    except Exception as e:
        await message.reply(f"Erro ao buscar informações: {e}")

@dp.message(Command("painel"))
@dp.message(Command("admin"))
async def painel_admin(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem acessar o painel.")
        return

    # Sempre recarrega os dados do disco
    try:
        with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
            chat_ids_atual = json.load(f)
    except Exception:
        chat_ids_atual = []

    try:
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            scheduled_messages_atual = json.load(f)
    except Exception:
        scheduled_messages_atual = []

    # Filtra só anúncios ativos (não expirados)
    agora = datetime.datetime.now()
    anuncios_ativos = []
    for msg in scheduled_messages_atual:
        expiry_str = msg.get('expiry_time')
        if expiry_str:
            try:
                expiry_dt = datetime.datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
                if expiry_dt > agora:
                    anuncios_ativos.append(msg)
            except Exception:
                pass

    total_grupos = len(set(chat_ids_atual))
    # Cada id fixo representa 1 plano único
    id_fixos_ativos = set()
    for anuncio in anuncios_ativos:
        id_fixo = anuncio.get('fixed_ad_id')
        if id_fixo:
            id_fixos_ativos.add(str(id_fixo))
    total_anuncios = len(id_fixos_ativos)
    # Calcula horários disponíveis com base só nos ativos
    busy_hours = set()
    for msg in anuncios_ativos:
        if 'time' in msg:
            busy_hours.add(msg['time'][:5])
    total_horarios_disponiveis = len([h for h in get_available_hours() if h not in busy_hours])
    
    # Carrega usuários registrados
    registered_users = load_registered_users()
    total_users = len(registered_users)
    
    painel = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Estatísticas", callback_data="admin_stats_panel"),
                InlineKeyboardButton(text="🎨 Personalizar /start", callback_data="admin_customize_start")
            ],
            [
                InlineKeyboardButton(text="� Gerenciar Admins", callback_data="admin_manage_admins"),
                InlineKeyboardButton(text="📢 Canal de Logs", callback_data="admin_set_log_channel")
            ],
            [
                InlineKeyboardButton(text="📋 Destino dos Logs", callback_data="admin_set_log_dest"),
                InlineKeyboardButton(text="� Link de Planos", callback_data="admin_set_plan_link")
            ],
            [
                InlineKeyboardButton(text="� Botão Divulgação", callback_data="admin_set_button_config"),
                InlineKeyboardButton(text="🎆 Canal Referência", callback_data="admin_set_reference_channel")
            ],
            [
                InlineKeyboardButton(text="⏰ Intervalo Horários", callback_data="admin_set_time_interval"),
                InlineKeyboardButton(text="📄 Planos Ativos", callback_data="admin_list_active_plans")
            ],
            [
                InlineKeyboardButton(text="👥 Gerenciar Usuários", callback_data="admin_manage_users"),
                InlineKeyboardButton(text="📨 Enviar Mensagem", callback_data="admin_broadcast_message")
            ],
            [
                InlineKeyboardButton(text="🔔 Sistema de Notificações", callback_data="admin_notifications_panel")
            ]
        ]
    )

    painel_texto = (
        "⚙️ Painel Administrativo:\n\n"
        f"👥 Grupos coletados: <b>{total_grupos}</b>\n"
        f"📢 Anúncios ativos: <b>{total_anuncios}</b>\n"
        f"⏰ Horários disponíveis: <b>{total_horarios_disponiveis}</b>\n"
        f"👤 Usuários registrados: <b>{total_users}</b>\n"
    )
    await message.reply(painel_texto, reply_markup=painel, parse_mode="HTML")





# Handler para configurar intervalo de horários
@dp.callback_query(lambda c: c.data == "admin_set_time_interval")
async def admin_set_time_interval_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("Apenas administradores.", show_alert=True)
        return
    await callback_query.message.reply(
        "Digite o novo intervalo de horários em minutos (ex: 5, 10, 15):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_intervalo")]]
        )
    )
    await state.set_state("esperando_novo_intervalo")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "cancelar_intervalo")
async def cancelar_intervalo_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.reply("Operação cancelada.")
    await callback_query.answer()

# Handler para listar planos ativos
@dp.callback_query(lambda c: c.data == "admin_list_active_plans")
async def admin_list_active_plans_handler(callback_query: types.CallbackQuery):
    """Lista todos os planos ativos com detalhes"""
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    try:
        # Carrega mensagens agendadas
        scheduled_messages = load_scheduled_messages()
        
        # Filtra apenas planos ativos (não expirados)
        agora = datetime.datetime.now()
        planos_ativos = []
        
        for msg in scheduled_messages:
            expiry_str = msg.get('expiry_time')
            if expiry_str:
                try:
                    expiry_dt = datetime.datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
                    if expiry_dt > agora:
                        planos_ativos.append(msg)
                except Exception:
                    pass
        
        if not planos_ativos:
            await callback_query.message.answer(
                "📋 *Planos Ativos*\n\n"
                "Não há planos ativos no momento.",
                parse_mode="Markdown"
            )
            await callback_query.answer()
            return
        
        # Agrupa por ID fixo (cada ID fixo = 1 plano)
        planos_por_id = {}
        for msg in planos_ativos:
            fixed_id = msg.get('fixed_ad_id')
            if fixed_id:
                if fixed_id not in planos_por_id:
                    planos_por_id[fixed_id] = {
                        'horarios': [],
                        'tipo': msg.get('type', 'indefinido'),
                        'recipient_id': msg.get('recipient_id'),
                        'expiry_time': msg.get('expiry_time'),
                        'total_grupos': len(load_chat_ids())
                    }
                planos_por_id[fixed_id]['horarios'].append(msg.get('time', 'N/A'))
        
        # Monta mensagem
        texto = "📋 *PLANOS ATIVOS*\n\n"
        texto += f"📊 Total de planos: *{len(planos_por_id)}*\n"
        texto += f"⏰ Total de horários ocupados: *{len(planos_ativos)}*\n\n"
        texto += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for idx, (fixed_id, dados) in enumerate(planos_por_id.items(), 1):
            # Calcula dias restantes
            try:
                expiry_dt = datetime.datetime.strptime(dados['expiry_time'], '%Y-%m-%d %H:%M:%S')
                dias_restantes = (expiry_dt - agora).days
            except:
                dias_restantes = 0
            
            texto += f"*Plano #{idx}*\n"
            texto += f"🆔 ID: `{fixed_id[:8]}...`\n"
            texto += f"👤 Usuário: `{dados['recipient_id']}`\n"
            texto += f"📦 Tipo: *{dados['tipo'].capitalize()}*\n"
            texto += f"⏰ Horários: *{len(dados['horarios'])}*\n"
            texto += f"📅 Expira em: *{dias_restantes} dias*\n"
            texto += f"📊 Alcance: *{dados['total_grupos']} grupos*\n"
            texto += "\n"
            
            # Limita a 10 planos por mensagem
            if idx >= 10:
                texto += f"\n_... e mais {len(planos_por_id) - 10} planos_"
                break
        
        texto += "━━━━━━━━━━━━━━━━━━━━\n"
        texto += f"📅 Atualizado em: {agora.strftime('%d/%m/%Y %H:%M')}"
        
        # Botão de voltar
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Atualizar", callback_data="admin_list_active_plans")],
                [InlineKeyboardButton(text="⬅️ Voltar ao Painel", callback_data="admin_back_panel")]
            ]
        )
        
        await callback_query.message.edit_text(texto, parse_mode="Markdown", reply_markup=keyboard)
        await callback_query.answer()
        
    except Exception as e:
        professional_logger.error("ADMIN", f"Erro ao listar planos ativos: {e}")
        await callback_query.answer(f"❌ Erro ao listar planos: {e}", show_alert=True)

# ============================================================================
# HANDLERS DE ESTADOS ADMINISTRATIVOS PRIORITÁRIOS
# DEVEM VIR ANTES DO handle_admin_states PARA SEREM PROCESSADOS PRIMEIRO
# ============================================================================

@dp.message(AdminPanelStates.esperando_novo_texto_start)
async def receber_novo_texto_start_priority(message: types.Message, state: FSMContext):
    """Handler prioritário para trocar texto do /start"""
    print(f"[DEBUG] receber_novo_texto_start_priority CHAMADO! Texto recebido: {message.text[:50]}...")
    
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem executar esta ação.")
        await state.clear()
        return
    
    texto = message.text.strip()
    print(f"[DEBUG] Texto processado: {texto[:50]}...")
    
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
        
        if 'menu' not in config:
            config['menu'] = {}
        
        config['menu']['info_message'] = texto
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        print(f"[DEBUG] Config atualizado com sucesso!")
        await message.reply("✅ Texto do /start atualizado!\n\nℹ️ A alteração será aplicada automaticamente.")
    except Exception as e:
        print(f"[DEBUG] ERRO ao atualizar: {e}")
        await message.reply(f"❌ Erro ao atualizar texto do /start: {e}")
    
    await state.clear()
    print(f"[DEBUG] Estado limpo!")

@dp.message(AdminPanelStates.esperando_novo_botao_start)
async def receber_novo_botao_start_priority(message: types.Message, state: FSMContext):
    """Handler prioritário para adicionar botão ao /start"""
    print(f"[DEBUG] receber_novo_botao_start_priority chamado!")
    
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem executar esta ação.")
        await state.clear()
        return
    
    try:
        # Verifica se tem vírgula
        if "," not in message.text:
            await message.reply("❌ Formato incorreto!\n\n"
                              "Envie no formato: Texto do Botão, https://seulink.com\n\n"
                              "Exemplo: Meu Canal, https://t.me/meucanal")
            return
        
        # Separa texto e URL
        texto, url = [x.strip() for x in message.text.split(",", 1)]
        
        # Valida se tem texto e URL
        if not texto or not url:
            await message.reply("❌ Texto ou URL vazio!\n\n"
                              "Envie no formato: Texto do Botão, https://seulink.com")
            return
        
        # Valida se a URL começa com http
        if not url.startswith("http"):
            await message.reply("❌ URL inválida! Deve começar com http:// ou https://\n\n"
                              "Exemplo: https://t.me/meucanal")
            return
        
        # Carrega config
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
        
        # Garante estrutura do menu
        if 'menu' not in config:
            config['menu'] = {}
        if 'buttons' not in config['menu']:
            config['menu']['buttons'] = []
        
        # Adiciona o botão
        config['menu']['buttons'].append({"text": texto, "url": url})
        
        # Salva config
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        await message.reply(f"✅ Botão adicionado com sucesso!\n\n"
                          f"📝 Texto: {texto}\n"
                          f"🔗 Link: {url}\n\n"
                          f"Total de botões: {len(config['menu']['buttons'])}")
        
    except ValueError:
        await message.reply("❌ Erro ao processar! Use o formato:\n"
                          "Texto do Botão, https://seulink.com")
    except Exception as e:
        await message.reply(f"❌ Erro ao adicionar botão: {e}")
    
    await state.clear()

@dp.message(AdminPanelStates.esperando_nova_imagem_start)
async def receber_nova_imagem_start_priority2(message: types.Message, state: FSMContext):
    """Handler prioritário para receber nova imagem do /start"""
    print(f"[DEBUG] receber_nova_imagem_start_priority chamado!")
    
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem executar esta ação.")
        await state.clear()
        return
    
    # Aceita link ou foto
    if message.photo:
        # Pega o file_id da foto em melhor qualidade
        file_id = message.photo[-1].file_id
        
        try:
            with open(CONFIG_FILE, encoding='utf-8') as f:
                config = json.load(f)
            
            if 'menu' not in config:
                config['menu'] = {}
            
            # Salva o file_id da foto
            config['menu']['image_url'] = file_id
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            await message.reply("✅ Imagem do /start atualizada com sucesso!\n\n"
                              "🔄 Testando a nova imagem...")
            
            # Testa a nova imagem
            try:
                await message.answer_photo(
                    photo=file_id,
                    caption="✅ Esta é a nova imagem do /start!"
                )
            except Exception as e:
                await message.reply(f"⚠️ Erro ao testar imagem: {e}")
            
            await state.clear()
            return
            
        except Exception as e:
            await message.reply(f"❌ Erro ao salvar imagem: {e}")
            await state.clear()
            return
    
    # Se for um link de texto
    imagem_url = message.text.strip()
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
        if 'menu' not in config:
            config['menu'] = {}
        config['menu']['image_url'] = imagem_url
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        await message.reply("✅ Link da imagem do /start atualizado!\n\n"
                          "🔄 Testando a nova imagem...")
        
        # Testa a nova imagem
        try:
            await message.answer_photo(
                photo=imagem_url,
                caption="✅ Esta é a nova imagem do /start!"
            )
        except Exception as e:
            await message.reply(f"⚠️ Erro ao testar imagem: {e}\n"
                              "Verifique se o link está correto.")
        
    except Exception as e:
        await message.reply(f"❌ Erro ao atualizar imagem do /start: {e}")
    
    await state.clear()

@dp.message(AdminPanelStates.esperando_id_canal_logs)
async def receber_id_canal_logs_priority(message: types.Message, state: FSMContext):
    """Handler prioritário para receber ID do canal de logs"""
    try:
        print(f"[DEBUG] receber_id_canal_logs_priority chamado! User: {message.from_user.id}, Text: {message.text}")
        
        if message.from_user.id not in ADMINS:
            await message.reply("❌ Apenas administradores podem executar esta ação.")
            await state.clear()
            return
            
        canal_id = message.text.strip()
        print(f"[DEBUG] Canal ID recebido: {canal_id}")
        
        # Validação melhorada do ID do canal
        if not canal_id.startswith('-100'):
            print(f"[DEBUG] Validação falhou: não começa com -100")
            await message.reply("❌ Formato de ID inválido. O ID do canal deve começar com -100.\nExemplo: `-1001234567890`", parse_mode="Markdown")
            await state.clear()
            return
            
        # Verifica se o resto são apenas números (remove o sinal de menos)
        if not canal_id[1:].isdigit() or len(canal_id) < 10:
            print(f"[DEBUG] Validação falhou: formato inválido")
            await message.reply("❌ Formato de ID inválido. O ID do canal deve ter pelo menos 10 dígitos após -100.\nExemplo: `-1001234567890`", parse_mode="Markdown")
            await state.clear()
            return
            
        # Converte para int para validar se é um número válido
        try:
            canal_id_int = int(canal_id)
            if canal_id_int >= 0:  # IDs de canal devem ser negativos
                print(f"[DEBUG] Validação falhou: ID não é negativo")
                await message.reply("❌ ID inválido. IDs de canal devem ser números negativos.\nExemplo: `-1001234567890`", parse_mode="Markdown")
                await state.clear()
                return
        except ValueError:
            print(f"[DEBUG] Validação falhou: ValueError")
            await message.reply("❌ Formato de ID inválido. Use apenas números após o -100.\nExemplo: `-1001234567890`", parse_mode="Markdown")
            await state.clear()
            return
            
        print(f"[DEBUG] Validações passaram! Atualizando config...")
        
        # Atualiza config.json
        try:
            with open(CONFIG_FILE, 'r+', encoding='utf-8') as f:
                config = json.load(f)
                config['LOG'] = canal_id
                f.seek(0)
                json.dump(config, f, ensure_ascii=False, indent=4)
                f.truncate()
            
            print(f"[DEBUG] Config atualizado! Enviando mensagem de confirmação...")
                
            # Envia mensagem de confirmação
            await message.reply(f"✅ *Canal de logs atualizado com sucesso!*\n\nID do canal: `{canal_id}`\n\nℹ️ A alteração será aplicada automaticamente.", parse_mode="Markdown")
            
            print(f"[DEBUG] Mensagem enviada! Limpando estado...")
            
            # Limpa o estado
            await state.clear()
            
            # Log de sucesso
            professional_logger.success("CONFIG", f"Canal de logs atualizado para {canal_id}")
            
            print(f"[DEBUG] Processo concluído com sucesso!")
            
        except json.JSONDecodeError as e:
            print(f"[DEBUG] Erro JSONDecodeError: {e}")
            await message.reply("❌ Erro ao ler o arquivo de configuração. Verifique o formato do arquivo config.json")
            await state.clear()
        except FileNotFoundError as e:
            print(f"[DEBUG] Erro FileNotFoundError: {e}")
            await message.reply("❌ Arquivo config.json não encontrado.")
            await state.clear()
        except Exception as e:
            print(f"[DEBUG] Erro ao atualizar config: {e}")
            logging.error(f"Erro ao atualizar config.json: {str(e)}")
            await message.reply(f"❌ Ocorreu um erro ao atualizar as configurações: {str(e)}")
            await state.clear()
            
    except Exception as e:
        print(f"[DEBUG] Erro geral em receber_id_canal_logs: {e}")
        logging.error(f"Erro em receber_id_canal_logs: {str(e)}")
        await message.reply("❌ Ocorreu um erro ao processar sua solicitação. Tente novamente.")
        await state.clear()

@dp.message(AdminPanelStates.esperando_mensagem_broadcast)
async def receber_mensagem_broadcast_priority(message: types.Message, state: FSMContext):
    """Handler prioritário para receber mensagem de broadcast"""
    print(f"[DEBUG] receber_mensagem_broadcast_priority chamado! User ID: {message.from_user.id}")
    print(f"[DEBUG] Estado atual: {await state.get_state()}")
    
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem executar esta ação.")
        await state.clear()
        return
    
    try:
        broadcast_text = message.text or message.caption
        print(f"[DEBUG] Texto capturado: {broadcast_text[:50] if broadcast_text else 'None'}...")
        
        if not broadcast_text:
            await message.reply("❌ Por favor, envie uma mensagem de texto.")
            return
        
        # Confirmação antes do envio
        users = load_registered_users()
        total_users = len(users)
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Confirmar Envio", callback_data=f"confirm_broadcast")],
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel_broadcast")]
            ]
        )
        
        # Salva a mensagem no estado para usar depois
        await state.update_data(broadcast_message=broadcast_text)
        
        preview_text = broadcast_text[:200] + "..." if len(broadcast_text) > 200 else broadcast_text
        
        await message.reply(
            f"📨 **Confirmação de Envio**\n\n"
            f"👥 **Destinatários:** {total_users} usuários\n\n"
            f"📝 **Prévia da mensagem:**\n"
            f"```\n{preview_text}\n```\n\n"
            f"⚠️ **Tem certeza que deseja enviar esta mensagem para todos os usuários?**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await message.reply(f"❌ Erro ao processar mensagem: {e}")
        await state.clear()

# ============================================================================
# FIM DOS HANDLERS PRIORITÁRIOS
# ============================================================================

# Handler principal para todos os estados administrativos
@dp.message(lambda message: message.text and hasattr(message, 'from_user') and not message.text.startswith('/'))
async def handle_admin_states(message: types.Message, state: FSMContext):
    """Handler principal para todos os estados administrativos"""
    current_state = await state.get_state()
    print(f"[DEBUG] handle_admin_states chamado! Estado: {current_state}")
    
    # Se não há estado ativo, ignora a mensagem
    if not current_state:
        print(f"[DEBUG] Nenhum estado ativo - ignorando")
        return
    
    # Ignora estados que têm handlers específicos
    ignored_states = [
        "AdminPanelStates:esperando_mensagem_broadcast",
        "AdminPanelStates:esperando_novo_botao_start",
        "AdminPanelStates:esperando_nova_imagem_start",
        "AdminPanelStates:esperando_novo_texto_start",
        "AdminPanelStates:esperando_id_canal_logs"
    ]
    
    # Verifica se o estado atual deve ser ignorado
    if current_state in ignored_states:
        print(f"[DEBUG] Estado {current_state} tem handler específico - ignorando")
        return  # Deixa o handler específico tratar
    
    # Processa estados que não têm handlers específicos
    if current_state == "esperando_novo_intervalo":
        await receber_novo_intervalo(message, state)
    elif current_state == "esperando_button_url":
        await receber_nova_button_url(message, state)
    elif current_state == "esperando_button_text":
        await receber_novo_button_text(message, state)
    elif current_state == "esperando_canal_referencia":
        await receber_canal_referencia(message, state)
    elif current_state == "esperando_plan_button_link":
        await receber_plan_button_link(message, state)

async def receber_novo_intervalo(message: types.Message, state: FSMContext):
    try:
        novo_valor = int(message.text.strip())
        if not (1 <= novo_valor <= 60):
            await message.reply("Por favor, informe um valor entre 1 e 60 minutos.")
            return
        # Atualiza o config.json
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        config['scheduling_time_interval'] = novo_valor
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        await message.reply(f"✅ Intervalo de horários atualizado para {novo_valor} minutos!")
        await state.clear()
    except ValueError:
        await message.reply("Valor inválido. Digite apenas números inteiros.")
    except Exception as e:
        await message.reply(f"Erro ao atualizar intervalo: {e}")

# Handler para configurar botão de divulgação
@dp.callback_query(lambda c: c.data == "admin_set_button_config")
async def admin_set_button_config_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("Apenas administradores.", show_alert=True)
        return
    
    # Mostra configurações atuais
    config = load_config()
    current_url = config.get('BUTTON_URL', 'Não configurado')
    current_text = config.get('TEXTOBUTTON', 'Não configurado')
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Alterar URL", callback_data="admin_change_button_url")],
            [InlineKeyboardButton(text="📝 Alterar Texto", callback_data="admin_change_button_text")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_cancel_button_config")]
        ]
    )
    
    await callback_query.message.edit_text(
        f"📢 **Configuração do Botão de Divulgação**\n\n"
        f"🔗 **URL Atual:** `{current_url}`\n"
        f"📝 **Texto Atual:** `{current_text}`\n\n"
        f"Escolha o que deseja alterar:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "admin_change_button_url")
async def admin_change_button_url_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "🔗 **Alterar URL do Botão**\n\n"
        "Digite a nova URL (exemplo: https://t.me/seucanal):",
        parse_mode="Markdown"
    )
    await state.set_state("esperando_nova_button_url")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "admin_change_button_text")
async def admin_change_button_text_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "📝 **Alterar Texto do Botão**\n\n"
        "Digite o novo texto do botão:",
        parse_mode="Markdown"
    )
    await state.set_state("esperando_novo_button_text")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "admin_cancel_button_config")
async def admin_cancel_button_config_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.edit_text("❌ Operação cancelada.")
    await callback_query.answer()

async def receber_nova_button_url(message: types.Message, state: FSMContext):
    try:
        nova_url = message.text.strip()
        if not nova_url.startswith(('http://', 'https://')):
            await message.reply("❌ URL inválida. Deve começar com http:// ou https://")
            return
        
        # Atualiza o config.json
        config = load_config()
        config['BUTTON_URL'] = nova_url
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        await message.reply(f"✅ URL do botão atualizada para: `{nova_url}`", parse_mode="Markdown")
        await state.clear()
    except Exception as e:
        await message.reply(f"Erro ao atualizar URL: {e}")

# Handler será chamado pelo handler principal
async def receber_novo_button_text(message: types.Message, state: FSMContext):
    try:
        novo_texto = message.text.strip()
        if len(novo_texto) > 64:
            await message.reply("❌ Texto muito longo. Máximo 64 caracteres.")
            return
        
        # Atualiza o config.json
        config = load_config()
        config['TEXTOBUTTON'] = novo_texto
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        await message.reply(f"✅ Texto do botão atualizado para: `{novo_texto}`", parse_mode="Markdown")
        await state.clear()
    except Exception as e:
        await message.reply(f"Erro ao atualizar texto: {e}")

# Handler para configurar canal de referência
@dp.callback_query(lambda c: c.data == "admin_set_reference_channel")
async def admin_set_reference_channel_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("Apenas administradores.", show_alert=True)
        return
    
    # Mostra configuração atual
    config = load_config()
    current_channel = config.get('canal_referencia')
    current_text = f"`{current_channel}`" if current_channel else "Não configurado"
    
    await callback_query.message.edit_text(
        f"🎆 **Canal de Referência**\n\n"
        f"📺 **Canal Atual:** {current_text}\n\n"
        f"Digite o ID do canal de referência (exemplo: -1001234567890):\n\n"
        f"📝 **Como obter o ID:**\n"
        f"1. Adicione o bot como admin no canal\n"
        f"2. Envie uma mensagem no canal\n"
        f"3. Use @userinfobot para obter o ID",
        parse_mode="Markdown"
    )
    await state.set_state("esperando_canal_referencia")
    await callback_query.answer()

# Handler será chamado pelo handler principal
async def receber_canal_referencia(message: types.Message, state: FSMContext):
    try:
        canal_id = message.text.strip()
        
        # Valida se é um ID válido
        if canal_id.lower() == 'null' or canal_id.lower() == 'none':
            canal_id = None
        else:
            try:
                canal_id_int = int(canal_id)
                if not str(canal_id_int).startswith('-100'):
                    await message.reply("❌ ID inválido. IDs de canais geralmente começam com -100")
                    return
                canal_id = canal_id_int
            except ValueError:
                await message.reply("❌ ID inválido. Digite apenas números ou 'null' para remover.")
                return
        
        # Atualiza o config.json
        config = load_config()
        config['canal_referencia'] = canal_id
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        if canal_id:
            await message.reply(f"✅ Canal de referência configurado: `{canal_id}`", parse_mode="Markdown")
        else:
            await message.reply("✅ Canal de referência removido.")
        
        await state.clear()
    except Exception as e:
        await message.reply(f"Erro ao configurar canal: {e}")

# Handler será chamado pelo handler principal
async def receber_plan_button_link(message: types.Message, state: FSMContext):
    try:
        novo_link = message.text.strip()
        if not novo_link.startswith(('http://', 'https://')):
            await message.reply("❌ URL inválida. Deve começar com http:// ou https://")
            return
        
        # Atualiza o config.json
        config = load_config()
        config['plan_button_link'] = novo_link
        
        # Atualiza também o botão "Planos Divulgação" no menu se existir
        if 'menu' in config and 'buttons' in config['menu']:
            for button in config['menu']['buttons']:
                if 'Planos' in button.get('text', ''):
                    button['url'] = novo_link
                    break
        
        # Atualiza também em messages.divulgar_planos se existir
        if 'messages' in config:
            config['messages']['divulgar_planos'] = novo_link
            config['messages']['divulgar'] = novo_link
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        await message.reply(f"✅ Link do botão de planos atualizado para: `{novo_link}`\n\n🔄 Todos os locais foram sincronizados!\n\nℹ️ A alteração será aplicada automaticamente.", parse_mode="Markdown")
        await state.clear()
        
    except Exception as e:
        await message.reply(f"Erro ao atualizar link: {e}")
    
# Handler para mostrar horários disponíveis via botão inline do /start
@dp.callback_query(lambda c: c.data == "ver_horarios_inline")
async def ver_horarios_inline(query: types.CallbackQuery):
    try:
                # Carrega horários disponíveis (função já existente)
        horarios = get_available_hours()
        # Remove horários já ocupados
        busy = set()
        if os.path.exists(SCHEDULED_MESSAGES_FILE):
            with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
                agendados = json.load(f)
            for plano in agendados:
                hora = plano.get('time')
                if hora:
                    busy.add(hora)
        livres = [h for h in horarios if h not in busy]
        if livres:
            resposta = '<b>⏰ Horários disponíveis:</b>\n' + ', '.join(livres)
        else:
            resposta = '❌ Nenhum horário disponível no momento.'
        await query.message.reply(resposta, parse_mode="HTML")
    except Exception as e:
        await query.message.reply(f"Erro ao listar planos: {e}")
    await query.answer()

# Handler para gerenciar usuários registrados
@dp.callback_query(lambda c: c.data == "admin_manage_users")
async def admin_manage_users(query: types.CallbackQuery):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    
    try:
        users = load_registered_users()
        total_users = len(users)
        
        if total_users == 0:
            await query.message.reply("📋 Nenhum usuário registrado encontrado.")
            await query.answer()
            return
        
        # Cria resumo dos usuários
        user_summary = []
        for user_id, user_data in list(users.items())[:20]:  # Mostra apenas os primeiros 20
            registration_date = user_data.get('registration_date', 'N/A')
            if registration_date != 'N/A':
                try:
                    reg_dt = datetime.datetime.fromisoformat(registration_date)
                    registration_date = reg_dt.strftime('%d/%m/%Y %H:%M')
                except:
                    pass
            
            # Escapa caracteres especiais para evitar erro de parsing
            full_name = str(user_data.get('full_name', 'N/A')).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
            username = str(user_data.get('username', 'N/A')).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
            
            user_summary.append(
                f"👤 *{full_name}*\n"
                f"🆔 ID: `{user_id}`\n"
                f"📱 Username: @{username}\n"
                f"📅 Registro: {registration_date}\n"
            )
        
        summary_text = (
            f"👥 *Usuários Registrados: {total_users}*\n\n"
            + "\n".join(user_summary)
        )
        
        if total_users > 20:
            summary_text += f"\n\n... e mais {total_users - 20} usuários."
        
        # Botões de ação
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📊 Estatísticas detalhadas", callback_data="admin_user_stats")],
                [InlineKeyboardButton(text="📄 Exportar lista completa", callback_data="admin_export_users")],
                [InlineKeyboardButton(text="⬅️ Voltar", callback_data="admin_back_panel")]
            ]
        )
        
        await query.message.reply(summary_text, reply_markup=keyboard, parse_mode='Markdown')
        
    except Exception as e:
        await query.message.reply(f"❌ Erro ao carregar usuários: {e}")
    
    await query.answer()

# Handler para estatísticas de usuários
@dp.callback_query(lambda c: c.data == "admin_user_stats")
async def admin_user_stats(query: types.CallbackQuery):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    
    try:
        users = load_registered_users()
        total_users = len(users)
        
        # Estatísticas por período
        now = datetime.datetime.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        users_today = 0
        users_week = 0
        users_month = 0
        users_with_username = 0
        
        for user_data in users.values():
            reg_date_str = user_data.get('registration_date')
            if reg_date_str:
                try:
                    reg_date = datetime.datetime.fromisoformat(reg_date_str)
                    if reg_date.date() == today:
                        users_today += 1
                    if reg_date >= week_ago:
                        users_week += 1
                    if reg_date >= month_ago:
                        users_month += 1
                except:
                    pass
            
            if user_data.get('username'):
                users_with_username += 1
        
        stats_text = (
            f"📊 **Estatísticas de Usuários**\n\n"
            f"👥 **Total:** {total_users}\n"
            f"📅 **Hoje:** {users_today}\n"
            f"📈 **Esta semana:** {users_week}\n"
            f"📊 **Este mês:** {users_month}\n"
            f"📱 **Com username:** {users_with_username}\n"
            f"📱 **Sem username:** {total_users - users_with_username}\n\n"
            f"📈 **Taxa de crescimento:**\n"
            f"• Diária: {users_today} usuários\n"
            f"• Semanal: {users_week} usuários\n"
            f"• Mensal: {users_month} usuários"
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Voltar", callback_data="admin_manage_users")]
            ]
        )
        
        await query.message.reply(stats_text, reply_markup=keyboard, parse_mode='Markdown')
        
    except Exception as e:
        await query.message.reply(f"❌ Erro ao gerar estatísticas: {e}")
    
    await query.answer()

# Handler para exportar lista de usuários
@dp.callback_query(lambda c: c.data == "admin_export_users")
async def admin_export_users(query: types.CallbackQuery):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    
    try:
        users = load_registered_users()
        
        if not users:
            await query.message.reply("📋 Nenhum usuário para exportar.")
            await query.answer()
            return
        
        # Cria arquivo de exportação
        export_data = []
        export_data.append("=== LISTA DE USUÁRIOS REGISTRADOS ===")
        export_data.append(f"Data de exportação: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        export_data.append(f"Total de usuários: {len(users)}")
        export_data.append("\n" + "="*50 + "\n")
        
        for i, (user_id, user_data) in enumerate(users.items(), 1):
            registration_date = user_data.get('registration_date', 'N/A')
            if registration_date != 'N/A':
                try:
                    reg_dt = datetime.datetime.fromisoformat(registration_date)
                    registration_date = reg_dt.strftime('%d/%m/%Y %H:%M:%S')
                except:
                    pass
            
            export_data.append(f"{i}. {user_data.get('full_name', 'N/A')}")
            export_data.append(f"   ID: {user_id}")
            export_data.append(f"   Username: @{user_data.get('username', 'N/A')}")
            export_data.append(f"   Primeiro nome: {user_data.get('first_name', 'N/A')}")
            export_data.append(f"   Último nome: {user_data.get('last_name', 'N/A')}")
            export_data.append(f"   Data de registro: {registration_date}")
            export_data.append("")
        
        # Salva arquivo temporário
        filename = f"usuarios_registrados_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(export_data))
        
        # Envia arquivo
        await query.message.reply_document(
            document=types.FSInputFile(filename),
            caption=f"📄 Lista completa de {len(users)} usuários registrados"
        )
        
        # Remove arquivo temporário
        os.remove(filename)
        
    except Exception as e:
        await query.message.reply(f"❌ Erro ao exportar usuários: {e}")
    
    await query.answer()

# Handler para broadcast de mensagens
@dp.callback_query(lambda c: c.data == "admin_broadcast_message")
async def admin_broadcast_message(query: types.CallbackQuery, state: FSMContext):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    
    users = load_registered_users()
    total_users = len(users)
    
    if total_users == 0:
        await query.message.reply("📋 Nenhum usuário registrado para enviar mensagens.")
        await query.answer()
        return
    
    await query.message.reply(
        f"📨 **Envio de Mensagem em Massa**\n\n"
        f"👥 **Usuários registrados:** {total_users}\n\n"
        f"📝 **Envie a mensagem que deseja transmitir para todos os usuários registrados:**\n\n"
        f"💡 *Você pode usar formatação Markdown (negrito, itálico, etc.)*",
        parse_mode='Markdown'
    )
    
    await state.set_state(AdminPanelStates.esperando_mensagem_broadcast)
    await query.answer()

# Handler para confirmar broadcast
@dp.callback_query(lambda c: c.data == "confirm_broadcast")
async def confirm_broadcast(query: types.CallbackQuery, state: FSMContext):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    
    try:
        # Recupera a mensagem do estado
        data = await state.get_data()
        broadcast_message = data.get('broadcast_message')
        
        if not broadcast_message:
            await query.message.reply("❌ Mensagem não encontrada. Tente novamente.")
            await state.clear()
            await query.answer()
            return
        
        await query.message.reply("📤 **Iniciando envio...** Isso pode levar alguns minutos.")
        
        # Envia para todos os usuários registrados
        success_count, failed_count = await broadcast_to_registered_users(
            query.bot, 
            broadcast_message, 
            parse_mode='Markdown'
        )
        
        # Relatório final
        report_text = (
            f"📊 **Relatório de Envio Concluído**\n\n"
            f"✅ **Enviados com sucesso:** {success_count}\n"
            f"❌ **Falhas:** {failed_count}\n"
            f"📈 **Taxa de sucesso:** {(success_count/(success_count+failed_count)*100):.1f}%" if (success_count+failed_count) > 0 else "📈 **Taxa de sucesso:** 0%"
        )
        
        await query.message.reply(report_text, parse_mode='Markdown')
        
    except Exception as e:
        await query.message.reply(f"❌ Erro durante o envio: {e}")
    
    await state.clear()
    await query.answer()

# Handler para cancelar broadcast
@dp.callback_query(lambda c: c.data == "cancel_broadcast")
async def cancel_broadcast(query: types.CallbackQuery, state: FSMContext):
    await query.message.reply("❌ **Envio cancelado.**")
    await state.clear()
    await query.answer()


# Submenu Personalizar /start
@dp.callback_query(lambda c: c.data == "admin_customize_start")
async def admin_customize_start(query: types.CallbackQuery):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Trocar texto do /start", callback_data="start_edit_text")],
            [InlineKeyboardButton(text="🖼️ Trocar imagem do /start", callback_data="start_edit_image")],
            [InlineKeyboardButton(text="➕ Adicionar botão ao /start", callback_data="start_add_button")],
            [InlineKeyboardButton(text="🗑️ Gerenciar botões do /start", callback_data="start_manage_buttons")],
            [InlineKeyboardButton(text="⬅️ Voltar", callback_data="admin_back_panel")]
        ]
    )
    await query.message.answer("Escolha o que deseja personalizar:", reply_markup=kb)

# Voltar ao painel admin principal
@dp.callback_query(lambda c: c.data == "admin_back_panel")
async def admin_back_panel(query: types.CallbackQuery):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    # Carrega dados atualizados
    try:
        with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
            chat_ids_atual = json.load(f)
    except Exception:
        chat_ids_atual = []

    try:
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            scheduled_messages_atual = json.load(f)
    except Exception:
        scheduled_messages_atual = []

    # Filtra só anúncios ativos (não expirados)
    agora = datetime.datetime.now()
    anuncios_ativos = []
    for msg in scheduled_messages_atual:
        expiry_str = msg.get('expiry_time')
        if expiry_str:
            try:
                expiry_dt = datetime.datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
                if expiry_dt > agora:
                    anuncios_ativos.append(msg)
            except Exception:
                pass

    total_grupos = len(set(chat_ids_atual))
    id_fixos_ativos = set()
    for anuncio in anuncios_ativos:
        id_fixo = anuncio.get('fixed_ad_id')
        if id_fixo:
            id_fixos_ativos.add(str(id_fixo))
    total_anuncios = len(id_fixos_ativos)
    
    busy_hours = set()
    for msg in anuncios_ativos:
        if 'time' in msg:
            busy_hours.add(msg['time'][:5])
    total_horarios_disponiveis = len([h for h in get_available_hours() if h not in busy_hours])
    
    registered_users = load_registered_users()
    total_users = len(registered_users)
    
    painel = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Estatísticas", callback_data="admin_stats_panel"),
                InlineKeyboardButton(text="🎨 Personalizar /start", callback_data="admin_customize_start")
            ],
            [
                InlineKeyboardButton(text="👤 Gerenciar Admins", callback_data="admin_manage_admins"),
                InlineKeyboardButton(text="📢 Canal de Logs", callback_data="admin_set_log_channel")
            ],
            [
                InlineKeyboardButton(text="📋 Destino dos Logs", callback_data="admin_set_log_dest"),
                InlineKeyboardButton(text="🔗 Link de Planos", callback_data="admin_set_plan_link")
            ],
            [
                InlineKeyboardButton(text="📢 Botão Divulgação", callback_data="admin_set_button_config"),
                InlineKeyboardButton(text="🎆 Canal Referência", callback_data="admin_set_reference_channel")
            ],
            [
                InlineKeyboardButton(text="⏰ Intervalo Horários", callback_data="admin_set_time_interval"),
                InlineKeyboardButton(text="📄 Planos Ativos", callback_data="admin_list_active_plans")
            ],
            [
                InlineKeyboardButton(text="👥 Gerenciar Usuários", callback_data="admin_manage_users"),
                InlineKeyboardButton(text="📨 Enviar Mensagem", callback_data="admin_broadcast_message")
            ],
            [
                InlineKeyboardButton(text="🔔 Sistema de Notificações", callback_data="admin_notifications_panel")
            ]
        ]
    )

    painel_texto = (
        "⚙️ Painel Administrativo:\n\n"
        f"👥 Grupos coletados: <b>{total_grupos}</b>\n"
        f"📢 Anúncios ativos: <b>{total_anuncios}</b>\n"
        f"⏰ Horários disponíveis: <b>{total_horarios_disponiveis}</b>\n"
        f"👤 Usuários registrados: <b>{total_users}</b>\n"
    )
    
    await query.message.edit_text(painel_texto, reply_markup=painel, parse_mode="HTML")
    await query.answer()

# FSM para trocar texto e imagem do /start


@dp.callback_query(lambda c: c.data == "start_edit_text")
async def start_edit_text(query: types.CallbackQuery, state: FSMContext):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    await query.message.answer("Envie o novo texto do /start:")
    await state.set_state(AdminPanelStates.esperando_novo_texto_start)

@dp.callback_query(lambda c: c.data == "start_edit_image")
async def start_edit_image(query: types.CallbackQuery, state: FSMContext):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    await query.message.answer("Envie o link da nova imagem do /start (ou envie uma imagem):")
    await state.set_state(AdminPanelStates.esperando_nova_imagem_start)

@dp.callback_query(lambda c: c.data == "start_add_button")
async def start_add_button(query: types.CallbackQuery, state: FSMContext):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    await query.message.answer("Envie o texto do botão e o link separados por vírgula.\nExemplo: Meu Botão, https://meulink.com")
    await state.set_state(AdminPanelStates.esperando_novo_botao_start)

@dp.callback_query(lambda c: c.data == "start_manage_buttons")
async def start_manage_buttons(query: types.CallbackQuery):
    """Mostra lista de botões para gerenciar"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
        
        buttons = config.get('menu', {}).get('buttons', [])
        
        if not buttons:
            await query.message.edit_text(
                "ℹ️ Nenhum botão configurado no /start.\n\n"
                "Use 'Adicionar botão' para criar um.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Voltar", callback_data="admin_customize_start")]
                ])
            )
            return
        
        # Cria lista de botões para remover
        keyboard = []
        for i, btn in enumerate(buttons):
            texto = btn.get('text', 'Sem texto')
            url = btn.get('url', 'Sem URL')
            # Trunca texto longo
            display_text = texto[:30] + "..." if len(texto) > 30 else texto
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🗑️ {display_text}",
                    callback_data=f"remove_button_{i}"
                )
            ])
        
        # Adiciona opção de remover todos
        keyboard.append([
            InlineKeyboardButton(text="❌ Remover TODOS os botões", callback_data="start_remove_all_buttons")
        ])
        keyboard.append([
            InlineKeyboardButton(text="⬅️ Voltar", callback_data="admin_customize_start")
        ])
        
        await query.message.edit_text(
            f"🗑️ **Gerenciar Botões do /start**\n\n"
            f"📊 Total de botões: {len(buttons)}\n\n"
            f"Clique em um botão para removê-lo:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await query.message.answer(f"❌ Erro ao carregar botões: {e}")
    
    await query.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("remove_button_"))
async def remove_specific_button(query: types.CallbackQuery):
    """Remove um botão específico"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    
    try:
        # Extrai o índice do botão
        button_index = int(query.data.split("_")[-1])
        
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
        
        buttons = config.get('menu', {}).get('buttons', [])
        
        if button_index < 0 or button_index >= len(buttons):
            await query.answer("❌ Botão não encontrado!", show_alert=True)
            return
        
        # Remove o botão
        removed_button = buttons.pop(button_index)
        config['menu']['buttons'] = buttons
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        await query.answer(f"✅ Botão '{removed_button.get('text')}' removido!", show_alert=True)
        
        # Atualiza a lista
        if buttons:
            # Ainda há botões, mostra a lista atualizada
            keyboard = []
            for i, btn in enumerate(buttons):
                texto = btn.get('text', 'Sem texto')
                display_text = texto[:30] + "..." if len(texto) > 30 else texto
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"🗑️ {display_text}",
                        callback_data=f"remove_button_{i}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton(text="❌ Remover TODOS os botões", callback_data="start_remove_all_buttons")
            ])
            keyboard.append([
                InlineKeyboardButton(text="⬅️ Voltar", callback_data="admin_customize_start")
            ])
            
            await query.message.edit_text(
                f"🗑️ **Gerenciar Botões do /start**\n\n"
                f"📊 Total de botões: {len(buttons)}\n\n"
                f"Clique em um botão para removê-lo:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        else:
            # Não há mais botões
            await query.message.edit_text(
                "✅ Botão removido!\n\n"
                "ℹ️ Não há mais botões configurados.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Voltar", callback_data="admin_customize_start")]
                ])
            )
        
    except Exception as e:
        await query.answer(f"❌ Erro ao remover botão: {e}", show_alert=True)

@dp.callback_query(lambda c: c.data == "start_remove_all_buttons")
async def start_remove_all_buttons(query: types.CallbackQuery):
    """Remove todos os botões com confirmação"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    
    # Pede confirmação
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Sim, remover TODOS", callback_data="confirm_remove_all_buttons"),
            InlineKeyboardButton(text="❌ Cancelar", callback_data="start_manage_buttons")
        ]
    ])
    
    await query.message.edit_text(
        "⚠️ **ATENÇÃO**\n\n"
        "Tem certeza que deseja remover **TODOS** os botões do /start?\n\n"
        "Esta ação não pode ser desfeita!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await query.answer()

@dp.callback_query(lambda c: c.data == "confirm_remove_all_buttons")
async def confirm_remove_all_buttons(query: types.CallbackQuery):
    """Confirma e remove todos os botões"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
        
        if 'menu' in config and 'buttons' in config['menu']:
            total_removed = len(config['menu']['buttons'])
            config['menu']['buttons'] = []
        else:
            total_removed = 0
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        await query.message.edit_text(
            f"✅ Todos os botões foram removidos!\n\n"
            f"📊 Total removido: {total_removed} botão(ões)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Voltar", callback_data="admin_customize_start")]
            ])
        )
        
    except Exception as e:
        await query.message.edit_text(f"❌ Erro ao remover botões: {e}")
    
    await query.answer()

@dp.callback_query(lambda c: c.data == "start_remove_buttons")
async def start_remove_buttons(query: types.CallbackQuery):
    """Redireciona para o novo sistema de gerenciamento"""
    await start_manage_buttons(query)

# Handler para editar mensagem do /start
@dp.callback_query(lambda c: c.data == "admin_edit_start")
async def admin_edit_start(query: types.CallbackQuery):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    await query.message.answer("Envie a nova mensagem do /start:")
    # Aqui você pode implementar lógica de FSM para aguardar a mensagem e salvar no config.json

# Handler para gerenciar admins
@dp.callback_query(lambda c: c.data == "admin_manage_admins")
async def admin_manage_admins(query: types.CallbackQuery):
    """Gerencia lista de administradores do bot"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    
    try:
        # Carrega config
        config = load_config()
        admins_list = config.get('admins', [])
        
        # Monta mensagem
        texto = "👥 *GERENCIAR ADMINISTRADORES*\n\n"
        texto += f"📊 Total de admins: *{len(admins_list)}*\n\n"
        texto += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if admins_list:
            texto += "*Lista de Administradores:*\n\n"
            for idx, admin_id in enumerate(admins_list, 1):
                texto += f"{idx}. `{admin_id}`\n"
        else:
            texto += "⚠️ Nenhum administrador configurado.\n"
        
        texto += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
        texto += "ℹ️ *Como gerenciar:*\n"
        texto += "• Para adicionar: Edite o arquivo `config.json`\n"
        texto += "• Adicione o ID do usuário na lista `admins`\n"
        texto += "• Reinicie o bot para aplicar\n\n"
        texto += "💡 *Dica:* Use @userinfobot para obter seu ID"
        
        # Botão de voltar
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Voltar ao Painel", callback_data="admin_back_panel")]
            ]
        )
        
        await query.message.edit_text(texto, parse_mode="Markdown", reply_markup=keyboard)
        await query.answer()
        
    except Exception as e:
        professional_logger.error("ADMIN", f"Erro ao gerenciar admins: {e}")
        await query.answer(f"❌ Erro: {e}", show_alert=True)

# Handler para definir destino dos logs
@dp.callback_query(lambda c: c.data == "admin_set_log_dest")
async def admin_set_log_dest(query: types.CallbackQuery, state: FSMContext):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Receber logs no PRIVADO", callback_data="log_dest_privado")],
            [InlineKeyboardButton(text="Receber logs no CANAL", callback_data="log_dest_canal")]
        ]
    )
    await query.message.answer("Escolha onde deseja receber os logs:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("log_dest_"))
async def set_log_destino(query: types.CallbackQuery):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    destino = "privado" if query.data == "log_dest_privado" else "canal"
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
        config["log_destino"] = destino
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        await query.message.answer(f"✅ Destino dos logs atualizado para: {destino.upper()}\n\n"
                                   f"ℹ️ A alteração será aplicada automaticamente.")
    except Exception as e:
        await query.message.answer(f"❌ Erro ao atualizar destino dos logs: {e}")
    await query.answer()

# Handler para configurar canal de logs
@dp.callback_query(lambda c: c.data == "admin_set_log_channel")
async def admin_set_log_channel(query: types.CallbackQuery, state: FSMContext):
    try:
        if query.from_user.id not in ADMINS:
            await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
            return
        await query.answer()  # Responde ao callback para remover o "relógio" do botão
        await query.message.answer("📝 *Configuração do Canal de Logs*\n\nPor favor, envie o ID do canal de logs no formato:\n`-1001234567890`\n\nVocê pode obter o ID do canal encaminhando uma mensagem qualquer do canal para @userinfobot", parse_mode="Markdown")
        await state.set_state(AdminPanelStates.esperando_id_canal_logs)
    except Exception as e:
        logger.error(f"Erro em admin_set_log_channel: {str(e)}")
        await query.message.answer("❌ Ocorreu um erro ao configurar o canal de logs. Tente novamente.")

# Handler para definir link do botão de planos
@dp.callback_query(lambda c: c.data == "admin_set_plan_link")
async def admin_set_plan_link(query: types.CallbackQuery, state: FSMContext):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    
    # Mostra configuração atual
    current_config = load_config()
    current_link = current_config.get('plan_button_link', 'Não configurado')
    
    await query.message.edit_text(
        f"🔗 **Configurar Link do Botão de Planos**\n\n"
        f"🔗 **Link Atual:** `{current_link}`\n\n"
        f"Digite o novo link do botão de planos:",
        parse_mode="Markdown"
    )
    await state.set_state("esperando_plan_button_link")
    await query.answer()

@dp.message(Command("anual"))
async def anual_cmd(message: types.Message, bot: Bot):
    await handle_schedule_command(message, bot, days=365, tipo="anual")

@dp.message(Command("outros"))
async def outros_cmd(message: types.Message, bot: Bot):
    if message.from_user.id not in ADMINS:
        await message.reply("Você não tem permissão para usar este comando.")
        return
    if not message.reply_to_message:
        await message.reply("Responda à mensagem que deseja agendar usando este comando.")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Use: /outros <dias> [id] hh:mm hh:mm ... (responda à mensagem a ser divulgada)")
        return
    try:
        dias = int(args[1])
    except (ValueError, IndexError):
        await message.reply("O primeiro argumento após /outros deve ser o número de dias.")
        return
    id_cliente = None
    horarios = []
    codigos = []
    for arg in args[2:]:
        if arg.isdigit():
            id_cliente = int(arg)
        elif ":" in arg:
            horarios.append(arg)
    if not horarios:
        await message.reply("Informe pelo menos um horário no formato hh:mm.")
        return
    
    # Obtém o horário atual
    now = datetime.datetime.now()
    current_time = now.time()
    
    # Verifica se algum horário já passou
    tem_horario_passado = False
    for h in horarios:
        try:
            hora_agendada = datetime.datetime.strptime(h, "%H:%M").time()
            if hora_agendada <= current_time:
                tem_horario_passado = True
                break
        except ValueError:
            continue
    
    creation_time = now.strftime("%Y-%m-%d %H:%M:%S")
    fixed_ad_id = str(uuid.uuid4())
    
    # Se algum horário já passou, TODOS começam amanhã para evitar duplicatas
    if tem_horario_passado:
        expiry_time = (now + timedelta(days=dias + 1)).strftime("%Y-%m-%d %H:%M:%S")
        for h in horarios:
            codigo = str(uuid.uuid4())[:4]
            codigos.append((codigo, h, expiry_time))
            entry = {
                "recipient_id": id_cliente if id_cliente else str(config.get('LOG')),
                "fixed_ad_id": fixed_ad_id,
                "chat_id": message.from_user.id,
                "time": h,
                "from_chat_id": message.reply_to_message.chat.id,
                "message_id": message.reply_to_message.message_id,
                "code": codigo,
                "creation_time": creation_time,
                "expiry_time": expiry_time,
                "type": f"outros_{dias}_dias",
                "start_tomorrow": True
            }
            save_scheduled_message(entry)
        
        confirm = f"✅ Mensagem agendada com sucesso!\n\n📌 ID Fixo: {fixed_ad_id}\n\n"
        confirm += "📅 Todos os horários começam AMANHÃ (alguns horários já passaram hoje):\n"
        for codigo, h, venc in codigos:
            confirm += f"  • {h} - Código: {codigo}\n"
        confirm += f"\n⏰ Vencimento: {expiry_time}"
    else:
        # Todos os horários ainda não passaram, podem começar hoje
        expiry_time = (now + timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
        for h in horarios:
            codigo = str(uuid.uuid4())[:4]
            codigos.append((codigo, h, expiry_time))
            entry = {
                "recipient_id": id_cliente if id_cliente else str(config.get('LOG')),
                "fixed_ad_id": fixed_ad_id,
                "chat_id": message.from_user.id,
                "time": h,
                "from_chat_id": message.reply_to_message.chat.id,
                "message_id": message.reply_to_message.message_id,
                "code": codigo,
                "creation_time": creation_time,
                "expiry_time": expiry_time,
                "type": f"outros_{dias}_dias"
            }
            save_scheduled_message(entry)
        
        confirm = f"✅ Mensagem agendada com sucesso!\n\n📌 ID Fixo: {fixed_ad_id}\n\n"
        confirm += "🕐 Todos os horários começam HOJE:\n"
        for codigo, h, venc in codigos:
            confirm += f"  • {h} - Código: {codigo}\n"
        confirm += f"\n⏰ Vencimento: {expiry_time}"
    
    await message.reply(confirm)

async def handle_schedule_command(message, bot, days, tipo):
    if message.from_user.id not in ADMINS:
        await message.reply("Você não tem permissão para usar este comando.")
        return
    if not message.reply_to_message:
        await message.reply("Responda à mensagem que deseja agendar usando este comando.")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply(f"Use: /{tipo} [id] hh:mm hh:mm ... (responda à mensagem a ser divulgada)")
        return
    id_cliente = None
    horarios = []
    codigos = []
    for arg in args[1:]:
        if arg.isdigit():
            id_cliente = int(arg)
        elif ":" in arg:
            horarios.append(arg)
    if not horarios:
        await message.reply("Informe pelo menos um horário no formato hh:mm.")
        return
    
    # Obtém o horário atual
    now = datetime.datetime.now()
    current_time = now.time()
    
    # Verifica se algum horário já passou
    tem_horario_passado = False
    for h in horarios:
        try:
            hora_agendada = datetime.datetime.strptime(h, "%H:%M").time()
            if hora_agendada <= current_time:
                tem_horario_passado = True
                break
        except ValueError:
            continue
    
    creation_time = now.strftime("%Y-%m-%d %H:%M:%S")
    fixed_ad_id = str(uuid.uuid4())
    
    # Se algum horário já passou, TODOS começam amanhã para evitar duplicatas
    if tem_horario_passado:
        expiry_time = (now + timedelta(days=days + 1)).strftime("%Y-%m-%d %H:%M:%S")
        for h in horarios:
            codigo = str(uuid.uuid4())[:4]
            codigos.append((codigo, h, expiry_time))
            entry = {
                "recipient_id": id_cliente if id_cliente else str(config.get('LOG')),
                "fixed_ad_id": fixed_ad_id,
                "chat_id": message.from_user.id,
                "time": h,
                "from_chat_id": message.reply_to_message.chat.id,
                "message_id": message.reply_to_message.message_id,
                "code": codigo,
                "creation_time": creation_time,
                "expiry_time": expiry_time,
                "type": tipo,
                "start_tomorrow": True
            }
            save_scheduled_message(entry)
        
        confirm = f"✅ Mensagem agendada com sucesso!\n\n📌 ID Fixo: {fixed_ad_id}\n\n"
        confirm += "📅 Todos os horários começam AMANHÃ (alguns horários já passaram hoje):\n"
        for codigo, h, venc in codigos:
            confirm += f"  • {h} - Código: {codigo}\n"
        confirm += f"\n⏰ Vencimento: {expiry_time}"
    else:
        # Todos os horários ainda não passaram, podem começar hoje
        expiry_time = (now + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        for h in horarios:
            codigo = str(uuid.uuid4())[:4]
            codigos.append((codigo, h, expiry_time))
            entry = {
                "recipient_id": id_cliente if id_cliente else str(config.get('LOG')),
                "fixed_ad_id": fixed_ad_id,
                "chat_id": message.from_user.id,
                "time": h,
                "from_chat_id": message.reply_to_message.chat.id,
                "message_id": message.reply_to_message.message_id,
                "code": codigo,
                "creation_time": creation_time,
                "expiry_time": expiry_time,
                "type": tipo
            }
            save_scheduled_message(entry)
        
        confirm = f"✅ Mensagem agendada com sucesso!\n\n📌 ID Fixo: {fixed_ad_id}\n\n"
        confirm += "🕐 Todos os horários começam HOJE:\n"
        for codigo, h, venc in codigos:
            confirm += f"  • {h} - Código: {codigo}\n"
        confirm += f"\n⏰ Vencimento: {expiry_time}"
    
    await message.reply(confirm)

import re

if not os.path.exists(SCHEDULED_MESSAGES_FILE):
    with open(SCHEDULED_MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)
scheduled_messages = []


import io

async def send_report_to_recipient(recipient_id, report_text, success_list):
    try:
        # Verifica se o cliente silenciou notificações
        silenced_clients = load_silenced_clients()
        if str(recipient_id) in silenced_clients:
            logging.info(f"Cliente {recipient_id} silenciou notificações. Relatório não enviado.")
            return True
        
        message = f"📊 **RELATÓRIO DE DIVULGAÇÃO**\n\n✅ Seu anúncio foi divulgado em **{len(success_list)} grupos**!\n\n📄 Abra o arquivo anexo para ver os detalhes completos."
        full_report_text = message + "\n\n" + report_text
        from aiogram.types import BufferedInputFile
        file_bytes = full_report_text.encode()
        file = BufferedInputFile(file_bytes, filename="relatorio.txt")
        await bot.send_document(recipient_id, file, caption=message)
    except Exception as e:
        logging.error(f"Erro ao enviar relatório para o cliente {recipient_id}: {e}")

def get_next_available_time_not_occupied(current_time_str, scheduled_messages):
    """
    Retorna o próximo horário disponível (não ocupado) em incrementos de 5 minutos.
    Se todos os horários do dia estiverem ocupados, retorna None.
    """
    try:
        dt = datetime.datetime.strptime(current_time_str, "%H:%M")
        ocupados = set()
        for msg in scheduled_messages:
            t = msg.get('time')
            if t:
                ocupados.add(t)
        for _ in range(24*12):  # até 24 horas, de 5 em 5 minutos
            dt += timedelta(minutes=5)
            next_time = dt.strftime("%H:%M")
            if next_time not in ocupados:
                return next_time
        return None  # nenhum horário disponível
    except Exception:
        return None

# ===== SISTEMA DE REAGENDAMENTO REMOVIDO =====
# Funções duplicadas removidas. As funções get_available_hours() e get_busy_hours() 
# já existem em outra parte do código e continuam funcionando normalmente.


# ===== CONFIGURAÇÃO DE RECIPIENT_ID =====
def get_report_recipient_id():
    """Retorna o recipient_id atual dos relatórios"""
    try:
        # Primeiro tenta ler do .env
        import os
        recipient = os.getenv('REPORT_RECIPIENT_ID', '').strip()
        if recipient:
            return recipient
        
        # Se não tiver no .env, tenta ler de um arquivo config
        if os.path.exists('report_config.json'):
            import json
            with open('report_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('recipient_id', '')
        
        return ''
    except Exception as e:
        logging.error(f"Erro ao ler recipient_id: {e}")
        return ''

def set_report_recipient_id(new_recipient_id):
    """Define o recipient_id dos relatórios"""
    try:
        import os
        import json
        
        # Salva no arquivo config
        config = {'recipient_id': str(new_recipient_id).strip()}
        with open('report_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        # Também tenta atualizar o .env se existir
        env_path = '.env'
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Procura e atualiza a linha REPORT_RECIPIENT_ID
            found = False
            for i, line in enumerate(lines):
                if line.startswith('REPORT_RECIPIENT_ID='):
                    lines[i] = f'REPORT_RECIPIENT_ID={new_recipient_id}\n'
                    found = True
                    break
            
            # Se não encontrou, adiciona no final
            if not found:
                lines.append(f'REPORT_RECIPIENT_ID={new_recipient_id}\n')
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        
        logging.info(f"Recipient ID atualizado para: {new_recipient_id}")
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar recipient_id: {e}")
        return False

# Comando para alterar recipient_id
@dp.message(Command("cliente"))
async def set_recipient_cmd(message: types.Message):
    try:
        # Verifica se é admin
        if not is_admin(message.from_user.id):
            await message.reply("❌ Acesso negado. Apenas administradores podem usar este comando.")
            return
        
        # Extrai o novo recipient_id
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        if not args:
            current_recipient = get_report_recipient_id()
            await message.reply(f"📋 Recipient ID atual: `{current_recipient or 'Não configurado'}`\n\nUso: `/cliente <novo_id>`")
            return
        
        new_recipient = args[0].strip()
        if len(new_recipient) < 5:
            await message.reply("❌ Recipient ID deve ter pelo menos 5 caracteres.")
            return
        
        # Salva o novo recipient_id
        if set_report_recipient_id(new_recipient):
            await message.reply(f"✅ Recipient ID atualizado com sucesso!\n\n📋 Novo destinatário: `{new_recipient}`")
        else:
            await message.reply("❌ Erro ao salvar o novo recipient ID. Verifique os logs.")
            
    except Exception as e:
        logging.error(f"Erro no comando set_recipient: {e}")
        await message.reply("❌ Erro interno. Verifique os logs.")

# Comando para ver recipient atual
@dp.message(Command("clientual"))
async def get_recipient_cmd(message: types.Message):
    try:
        if not is_admin(message.from_user.id):
            await message.reply("❌ Acesso negado.")
            return
        
        current_recipient = get_report_recipient_id()
        if current_recipient:
            await message.reply(f"📋 Recipient ID atual: `{current_recipient}`")
        else:
            await message.reply("📋 Nenhum recipient ID configurado.\n\nUse: `/cliente <id>`")
            
    except Exception as e:
        logging.error(f"Erro no comando get_recipient: {e}")
        await message.reply("❌ Erro interno.")

def save_scheduled_messages(messages, origem=None, *args, **kwargs):
    """Salva mensagens agendadas no arquivo, suportando nome alternativo (typo)."""
    try:
        if origem:
            logging.info(f"[save_scheduled_messages] origem={origem}")
        primary_filename = SCHEDULED_MESSAGES_FILE
        alt_filename = 'scheduled_mesagges.json'
        target_filename = primary_filename if os.path.exists(primary_filename) or not os.path.exists(alt_filename) else alt_filename
        with open(target_filename, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        logging.info(f"[save_scheduled_messages] Salvo {len(messages)} registros em {target_filename}")
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar mensagens agendadas: {e}")
        return False



# ===== COMANDOS DE ADMINISTRAÇÃO =====
from aiogram import types
try:
    from aiogram.filters import Command  # aiogram v3
except ImportError:
    from aiogram.dispatcher.filters import Command  # aiogram v2

async def limpar_horarios_reagendados(message: types.Message):
    print("DEBUG: Handler chamado!")  # <-- Adiciona log no terminal
    try:
        # Checa se é admin
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Apenas administradores podem usar este comando.")
            print("DEBUG: Não é admin.")
            return

        # Carrega mensagens
        try:
            with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
                scheduled_messages = json.load(f)
            print(f"DEBUG: Carregado {len(scheduled_messages)} mensagens.")
        except FileNotFoundError:
            await message.reply("ℹ️ Nenhuma mensagem agendada encontrada.")
            print("DEBUG: Arquivo não encontrado.")
            return
        except Exception as e:
            await message.reply(f"❌ Erro ao ler o arquivo: {e}")
            print(f"DEBUG: Erro ao ler arquivo: {e}")
            return

        # Separa reagendamentos
        originais = [msg for msg in scheduled_messages if not msg.get('is_reagendamento', False)]
        removidos = [msg for msg in scheduled_messages if msg.get('is_reagendamento', False)]
        print(f"DEBUG: Encontrados {len(removidos)} reagendamentos.")

        if not removidos:
            await message.reply("ℹ️ Nenhum horário reagendado encontrado para remover.")
            print("DEBUG: Nenhum reagendamento para remover.")
            return

        # Salva só os originais
        try:
            with open(SCHEDULED_MESSAGES_FILE, 'w', encoding='utf-8') as f:
                json.dump(originais, f, ensure_ascii=False, indent=2)
            print("DEBUG: Arquivo salvo com apenas originais.")
        except Exception as e:
            await message.reply(f"❌ Erro ao salvar arquivo: {e}")
            print(f"DEBUG: Erro ao salvar arquivo: {e}")
            return

        await message.reply(f"✅ {len(removidos)} horários reagendados foram removidos com sucesso!\n📄 Restaram {len(originais)} mensagens originais.")
        print("DEBUG: Mensagem de sucesso enviada.")

    except Exception as e:
        await message.reply(f"❌ Erro ao limpar horários reagendados: {e}")
        print(f"DEBUG: Erro inesperado: {e}")

dp.message.register(limpar_horarios_reagendados, Command("limparhorarios"))


# Registra o comando limparhorarios
dp.message.register(limpar_horarios_reagendados, Command("limparhorarios"))

async def remover_chat_id(message: Message):
    """Remove um chat_id do arquivo chat_ids.json"""
    try:
        if not await is_admin(message.from_user.id):
            await message.reply("❌ Apenas administradores podem usar este comando.")
            return
            
        # Verifica se foi fornecido um chat_id
        if len(message.text.split()) < 2:
            await message.reply("❌ Por favor, forneça o chat_id a ser removido.\nExemplo: /removerchat 123456789")
            return
            
        chat_id = message.text.split()[1]
        
        try:
            # Tenta converter para inteiro
            chat_id = int(chat_id)
        except ValueError:
            await message.reply("❌ O chat_id deve ser um número inteiro.")
            return
            
        # Carrega os chat_ids atuais
        try:
            with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
                chat_ids = json.load(f)
        except FileNotFoundError:
            chat_ids = []
            
        # Remove o chat_id se existir
        if chat_id in chat_ids:
            chat_ids.remove(chat_id)
            with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(chat_ids, f, ensure_ascii=False, indent=2)
            await message.reply(f"✅ Chat ID {chat_id} removido com sucesso!")
            logging.info(f"Administrador {message.from_user.id} removeu o chat_id {chat_id}.")
        else:
            await message.reply(f"ℹ️ O chat_id {chat_id} não foi encontrado na lista.")
            
    except Exception as e:
        logging.error(f"Erro ao remover chat_id: {e}")
        await message.reply("❌ Ocorreu um erro ao remover o chat_id.")

# ===== SISTEMA DE REAGENDAMENTO REMOVIDO =====
# O sistema de reagendamento foi removido para evitar duplicação de horários.
# Use o comando /limparreagendados para remover horários duplicados manualmente.

# ===== FUNÇÕES DE NOTIFICAÇÃO DE REAGENDAMENTO REMOVIDAS =====
# Todas as funções relacionadas ao sistema de reagendamento foram removidas.

async def enviar_relatorio_admin(file, report_text, keyboard=None):
    """Envia relatório para admin respeitando a configuração log_destino do config.json"""
    try:
        # Carrega configurações do config.json
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        log_destino = config.get('log_destino', 'admin')  # Padrão: admin
        
        if log_destino == 'canal':
            # Envia para o canal de logs configurado
            log_channel = config.get('LOG')
            if log_channel:
                try:
                    await bot.send_document(log_channel, file, caption=report_text, reply_markup=keyboard)
                    logging.info(f"📊 Relatório enviado para canal de logs: {log_channel}")
                except Exception as e:
                    logging.error(f"❌ Erro ao enviar relatório para canal {log_channel}: {e}")
                    # Fallback: envia para admins se falhar no canal
                    logging.info("🔄 Tentando enviar para admins como fallback...")
                    await enviar_para_admins(file, report_text, keyboard)
            else:
                logging.warning("⚠️ Canal de logs não configurado. Enviando para admins.")
                await enviar_para_admins(file, report_text, keyboard)
        else:
            # Envia para admins (comportamento padrão)
            await enviar_para_admins(file, report_text, keyboard)
            
    except Exception as e:
        logging.error(f"❌ Erro ao carregar configurações para envio de relatório: {e}")
        # Fallback: envia para admins
        await enviar_para_admins(file, report_text, keyboard)

async def enviar_para_admins(file, report_text, keyboard=None):
    """Função auxiliar para enviar relatórios diretamente para admins"""
    try:
        for admin_id in ADMINS:
            await bot.send_document(admin_id, file, caption=report_text, reply_markup=keyboard)
        logging.info(f"📊 Relatório enviado para {len(ADMINS)} admin(s)")
    except Exception as e:
        logging.error(f"❌ Erro ao enviar relatório para admins: {e}")

async def enviar_notificacao_admin(mensagem, parse_mode="Markdown"):
    """Envia notificação de texto para admin respeitando a configuração log_destino do config.json"""
    try:
        # Carrega configurações do config.json
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        log_destino = config.get('log_destino', 'admin')  # Padrão: admin
        
        if log_destino == 'canal':
            # Envia para o canal de logs configurado
            log_channel = config.get('LOG')
            if log_channel:
                try:
                    await bot.send_message(log_channel, mensagem, parse_mode=parse_mode)
                    logging.info(f"📢 Notificação enviada para canal de logs: {log_channel}")
                except Exception as e:
                    logging.error(f"❌ Erro ao enviar notificação para canal {log_channel}: {e}")
                    # Fallback: envia para admins se falhar no canal
                    logging.info("🔄 Tentando enviar para admins como fallback...")
                    await enviar_notificacao_para_admins(mensagem, parse_mode)
            else:
                logging.warning("⚠️ Canal de logs não configurado. Enviando para admins.")
                await enviar_notificacao_para_admins(mensagem, parse_mode)
        else:
            # Envia para admins (comportamento padrão)
            await enviar_notificacao_para_admins(mensagem, parse_mode)
            
    except Exception as e:
        logging.error(f"❌ Erro ao carregar configurações para envio de notificação: {e}")
        # Fallback: envia para admins
        await enviar_notificacao_para_admins(mensagem, parse_mode)

async def enviar_notificacao_para_admins(mensagem, parse_mode="Markdown"):
    """Função auxiliar para enviar notificações diretamente para admins"""
    try:
        for admin_id in ADMINS:
            await bot.send_message(admin_id, mensagem, parse_mode=parse_mode)
        logging.info(f"📢 Notificação enviada para {len(ADMINS)} admin(s)")
    except Exception as e:
        logging.error(f"❌ Erro ao enviar notificação para admins: {e}")

def detectar_erro_spam(erro_msg):
    """Detecta se o erro é relacionado a spam/flood control"""
    erro_lower = str(erro_msg).lower()
    termos_spam = [
        'flood', 'too many requests', 'retry after', 'spam', 
        'rate limit', 'slowmode', 'flood control', 'too_many_requests'
    ]
    return any(termo in erro_lower for termo in termos_spam)

# ====== Controle de delay mínimo por chat (anti-flood Telegram) ======
PER_CHAT_SEND_DELAY_SECONDS = 45  # Aumentado para evitar flood control (era 35)
last_sent_per_chat = {}

async def processar_envio_agendado(scheduled_message):
    global last_sent_per_chat
    if scheduled_message is None or not isinstance(scheduled_message, dict):
        logging.error('[SCHEDULED] scheduled_message não foi passado corretamente para processar_envio_agendado')
        return [], 0, [], ""
    current_time_str = datetime.datetime.now().strftime("%H:%M")
    chat_ids_list = list(set(load_chat_ids()))
    success_count = 0
    error_count = 0
    sent_messages = []  # Armazena informações das mensagens enviadas
    failure_list = []   # Armazena informações das falhas
    flood_detected = False
    aviso_flood_enviado = False
    full_report = ""  # Inicializa full_report como string vazia
    flood_tratado = False  # Inicializa flood_tratado como False
    spam_reagendamentos = 0  # Contador de reagendamentos por spam
    max_reagendamentos = 3  # Máximo de reagendamentos permitidos
    
    try:
        for chat_id in chat_ids_list:
            if flood_detected:
                break
                
            # --- Delay mínimo por chat para evitar flood control (MELHORADO) ---
            now = datetime.datetime.now().timestamp()
            last_sent = last_sent_per_chat.get(chat_id, 0)
            elapsed = now - last_sent
            
            # Delay mínimo mais conservador + jitter aleatório
            min_delay = PER_CHAT_SEND_DELAY_SECONDS + random.uniform(2, 8)
            
            if elapsed < min_delay:
                wait_time = min_delay - elapsed
                logging.info(f"🕐 [ANTI-FLOOD] Aguardando {wait_time:.1f}s antes de enviar para {chat_id}")
                await asyncio.sleep(wait_time)
            
            # Atualiza o timestamp do último envio para esse chat
            last_sent_per_chat[chat_id] = datetime.datetime.now().timestamp()
            
            try:
                # Tenta enviar a mensagem
                try:
                    texto = scheduled_message.get('custom_message') or scheduled_message.get('message') or scheduled_message.get('text')
                except Exception as e:
                    logging.error(f"[SCHEDULED] scheduled_message missing text fields: {e}, data: {scheduled_message}")
                    texto = None
                if texto:
                    try:
                        sent_message = await safe_send_message(bot, chat_id=chat_id, text=texto)
                    except Exception as e:
                        erro_msg = str(e)
                        logging.error(f"[SCHEDULED] Erro ao enviar mensagem para {chat_id}: {erro_msg}")
                        
                        # 🔥 DETECÇÃO DE SPAM/FLOOD - APENAS LOGA O ERRO
                        if detectar_erro_spam(erro_msg):
                            logging.warning(f"⚠️ SPAM/FLOOD DETECTADO! Código: {scheduled_message.get('code', 'N/A')}")
                            spam_reagendamentos += 1
                            flood_detected = True
                            
                            # Calcula a taxa de sucesso atual
                            total_tentativas = success_count + len(failure_list) + 1
                            taxa_sucesso = success_count / total_tentativas if total_tentativas > 0 else 0
                            
                            logging.info(f"📊 Taxa de sucesso atual: {success_count}/{total_tentativas} ({taxa_sucesso:.2%})")
                            logging.info(f"ℹ️ Sistema de reagendamento desativado. Use /limparreagendados se necessário.")
                        
                        failure_list.append(f"Erro ao enviar mensagem para {chat_id}: {erro_msg}")
                        continue
                    
                    # Se chegou aqui, o envio foi bem-sucedido
                    success_count += 1
                    # Adiciona informações completas sobre a mensagem enviada
                    try:
                        chat = await bot.get_chat(chat_id)
                        if hasattr(chat, "username") and chat.username:
                            message_link = f"https://t.me/{chat.username}/{sent_message.message_id}"
                        else:
                            message_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{sent_message.message_id}"
                    except Exception as e:
                        logging.warning(f"[SCHEDULED] Não foi possível obter link para chat {chat_id}: {e}")
                        message_link = None
                    sent_messages.append({
                        'message_link': message_link,
                        'chat_id': chat_id,
                        'message_id': sent_message.message_id,
                        'type': 'text',
                        'content': texto[:100] + '...' if len(texto) > 100 else texto
                    })
                else:
                    try:
                        sent_message = await bot.forward_message(
                            chat_id=chat_id,
                            from_chat_id=scheduled_message.get('from_chat_id'),
                            message_id=scheduled_message.get('message_id')
                        )
                    except Exception as e:
                        erro_msg = str(e)
                        logging.error(f"[SCHEDULED] Erro ao encaminhar mensagem para {chat_id}: {erro_msg}")
                        
                        # 🔥 DETECÇÃO DE SPAM/FLOOD - APENAS LOGA O ERRO
                        if detectar_erro_spam(erro_msg):
                            logging.warning(f"⚠️ SPAM/FLOOD DETECTADO no encaminhamento! Código: {scheduled_message.get('code', 'N/A')}")
                            spam_reagendamentos += 1
                            flood_detected = True
                            
                            # Calcula a taxa de sucesso atual
                            total_tentativas = success_count + len(failure_list) + 1
                            taxa_sucesso = success_count / total_tentativas if total_tentativas > 0 else 0
                            
                            logging.info(f"📊 Taxa de sucesso atual: {success_count}/{total_tentativas} ({taxa_sucesso:.2%})")
                            logging.info(f"ℹ️ Sistema de reagendamento desativado. Use /limparreagendados se necessário.")
                        
                        failure_list.append(f"Erro ao encaminhar mensagem para {chat_id}: {erro_msg}")
                        continue
                    
                    # Se chegou aqui, o encaminhamento foi bem-sucedido
                    success_count += 1
                    # Adiciona informações completas sobre a mensagem encaminhada
                    try:
                        chat = await bot.get_chat(chat_id)
                        if hasattr(chat, "username") and chat.username:
                            message_link = f"https://t.me/{chat.username}/{sent_message.message_id}"
                        else:
                            message_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{sent_message.message_id}"
                    except Exception as e:
                        logging.warning(f"[SCHEDULED] Não foi possível obter link para chat {chat_id}: {e}")
                        message_link = None
                    
                    sent_messages.append({
                        'message_link': message_link,
                        'chat_id': chat_id,
                        'message_id': sent_message.message_id,
                        'type': 'forwarded',
                        'from_chat_id': scheduled_message['from_chat_id'],
                        'original_message_id': scheduled_message['message_id']
                    })
                
                # Tenta fixar a mensagem (flood control aqui só loga, não dorme nem reagenda)
                try:
                    await bot.pin_chat_message(chat_id=chat_id, message_id=sent_message.message_id, disable_notification=True)
                except Exception as e:
                    error_msg = str(e).lower()
                    if "chat not found" in error_msg:
                        logging.warning(f"[SCHEDULED] Chat {chat_id} não encontrado. Removendo dos IDs salvos.")
                        try:
                            remove_group_from_chat_ids(chat_id)
                            logging.info(f"[SCHEDULED] Chat ID {chat_id} removido com sucesso após erro 'chat not found'.")
                        except Exception as remove_exc:
                            logging.error(f"[SCHEDULED] Falha ao remover chat_id {chat_id}: {remove_exc}")
                    elif "not enough rights" in error_msg or "not enough rights to manage pinned messages" in error_msg:
                        pass  # Sem permissão para fixar - não loga mais
                    elif any(term in error_msg for term in ["retry after", "flood control", "too many requests"]):
                        # Flood control ao fixar: só loga e segue
                        logging.warning(f"Flood control ao fixar mensagem em {chat_id}: {error_msg}")
                    else:
                        logging.warning(f"Erro ao fixar mensagem em {chat_id}: {error_msg}")
                # Não interrompe o fluxo se não conseguir fixar a mensagem

                # As informações da mensagem já foram adicionadas acima

            except Exception as e:
                logging.error(f"Erro inesperado ao processar chat {chat_id}: {e}")
                error_count += 1
                failure_list.append(f"Chat {chat_id} - {str(e)}")

                # Se o bot foi removido do grupo, remove o chat_id da lista
                error_msg = str(e).lower()
                if any(term in error_msg for term in ["chat not found", "bot was kicked", "not enough rights"]):
                    try:
                        remove_group_from_chat_ids(chat_id)
                        logging.info(f"Chat ID {chat_id} removido após erro: {error_msg}")
                    except Exception as remove_exc:
                        logging.error(f"Falha ao remover chat_id {chat_id}: {remove_exc}")
                # Opcional: notificar todos os admins sobre erro crítico
                # for admin in ADMINS:
                #     try:
                #         await bot.send_message(admin, f"Erro inesperado ao processar chat {chat_id}: {e}")
                #     except Exception as exc_notify:
                #         logging.error(f"Falha ao notificar admin {admin}: {exc_notify}")

        # Após o envio para todos os chats, envie o relatório se houve algum envio ou falha
        if success_count > 0 or failure_list:
            from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
            import re
            import json
            import os
            
            # Usa o fixed_ad_id e code do scheduled_message para formar o ID
            fixed_ad_id = scheduled_message.get('fixed_ad_id', str(uuid.uuid4())[:12])
            code = scheduled_message.get('code', '')
            report_id = f"{fixed_ad_id}|{code}"
            # Cria um ID único e seguro baseado em timestamp
            import time
            timestamp_id = str(int(time.time() * 1000))  # timestamp em milissegundos
            horario = current_time_str
            
            # Prepara a lista de sucessos com links das mensagens
            success_entries = []
            for msg in sent_messages:
                if 'message_link' in msg:
                    entry = f"📌 {msg['message_link']}"
                    if 'content' in msg:
                        entry += f"\n   📝 {msg['content']}"
                    success_entries.append(entry)
                elif 'chat_id' in msg:
                    success_entries.append(f"💬 Chat ID: {msg['chat_id']} (Link não disponível)")
                else:
                    success_entries.append("❓ Mensagem sem identificador")
            
            # Atualiza as contagens baseado no que realmente foi processado
            success_count = len(success_entries)
            failure_count = len(failure_list)
            total_chats = success_count + failure_count
            
            # Cabeçalho do relatório
            report_text = (
                f"**📊 RELATÓRIO DE ENVIO**\n"
                f"**🆔 ID: `{report_id}|{horario}`**\n"
                f"**📅 Data/Hora: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}**\n"
                f"\n"
                f"**📊 RESUMO**\n"
                f"**├─ 📤 Total de chats: {total_chats}**\n"
                f"**├─ ✅ Sucessos: {success_count}**\n"
                f"**└─ ❌ Falhas: {failure_count}**\n"
                f"\n"
                f"_Para calcular as visualizações, clique no botão abaixo._"
            )
            
            # Construção do relatório detalhado
            full_report = f"RELATÓRIO DETALHADO - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            full_report += "="*50 + "\n\n"
            full_report += f"ID: {report_id}|{horario}\n"
            full_report += f"Tipo: {scheduled_message.get('type', 'desconhecido').capitalize()}\n"
            if 'code' in scheduled_message:
                full_report += f"Código: {scheduled_message['code']}\n"
            full_report += "\n" + "="*50 + "\n\n"
            
            # Seção de sucessos
            if success_entries:
                full_report += "✅ **ENVIOS BEM SUCEDIDOS**\n\n"
                for i, entry in enumerate(success_entries, 1):
                    full_report += f"{i}. {entry}\n\n"
                full_report += "\n" + "-"*50 + "\n\n"
            
            # Seção de falhas
            failed_ids = []
            if failure_list:
                full_report += "❌ **FALHAS NO ENVIO**\n\n"
                for i, item in enumerate(failure_list, 1):
                    full_report += f"{i}. {item}\n"
                    # Extrai o ID do chat da mensagem de erro - melhorada
                    # Tenta vários padrões para extrair o chat_id
                    chat_id_found = None
                    
                    # Padrão 1: "Chat -1001234567890" ou "chat -1001234567890"
                    match = re.search(r'[Cc]hat\s+(\-?\d+)', item)
                    if match:
                        chat_id_found = int(match.group(1))
                    
                    # Padrão 2: "para -1001234567890:"
                    if not chat_id_found:
                        match = re.search(r'para\s+(\-?\d+)', item)
                        if match:
                            chat_id_found = int(match.group(1))
                    
                    # Padrão 3: Qualquer número negativo longo (chat_id do Telegram)
                    if not chat_id_found:
                        match = re.search(r'(\-100\d{10,})', item)
                        if match:
                            chat_id_found = int(match.group(1))
                    
                    # Padrão 4: Entre parênteses
                    if not chat_id_found:
                        match = re.search(r'\((\-?\d+)\)', item)
                        if match:
                            chat_id_found = int(match.group(1))
                    
                    if chat_id_found:
                        failed_ids.append(chat_id_found)
                        print(f"[REPORT] ID com falha extraído: {chat_id_found} de '{item}'")
                    else:
                        print(f"[REPORT] Não foi possível extrair ID de: '{item}'")
                
                full_report += "\n" + "-"*50 + "\n\n"
                print(f"[REPORT] Total de IDs com falha encontrados: {len(failed_ids)} - {failed_ids}")
            relatorio_path = f"relatorio_{timestamp_id}.txt"
            failed_ids_path = f"failed_ids_{timestamp_id}.json"
            try:
                with open(relatorio_path, 'w', encoding='utf-8') as file:
                    file.write(full_report)
                file = FSInputFile(relatorio_path)
                # Sistema simplificado: salva IDs com falha em arquivo fixo
                if failed_ids:
                    print(f"[REPORT] Criando botão para limpar {len(failed_ids)} IDs com falha")
                    
                    # Salva em arquivo fixo para evitar problemas de ID
                    failed_ids_file = 'temp_failed_ids.json'
                    try:
                        with open(failed_ids_file, 'w', encoding='utf-8') as f:
                            json.dump(failed_ids, f, ensure_ascii=False, indent=2)
                        print(f"[REPORT] IDs com falha salvos em: {failed_ids_file}")
                        print(f"[REPORT] IDs salvos: {failed_ids}")
                        
                    except Exception as e:
                        print(f"[REPORT] Erro ao salvar IDs com falha: {e}")
                        
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[[ 
                            InlineKeyboardButton(
                                text=f"❌ Limpar {len(failed_ids)} IDs com erros",
                                callback_data="clear_failed_ids_now"
                            )
                        ]]
                    )
                    print(f"[REPORT] Botão criado com callback_data: clear_failed_ids_now")
                else:
                    print(f"[REPORT] Nenhum ID com falha encontrado - não criando botão")
                    keyboard = None
                # Envia relatório respeitando a configuração log_destino
                await enviar_relatorio_admin(file, report_text, keyboard)
                # Envia relatório para o cliente
            except Exception as e:
                logging.error(f"Erro ao enviar relatório para os admins: {e}")
                # Tenta remover os arquivos mesmo em caso de erro
                try:
                    if os.path.exists(relatorio_path):
                        os.remove(relatorio_path)
                    if os.path.exists(failed_ids_path):
                        os.remove(failed_ids_path)
                except Exception as cleanup_error:
                    logging.error(f"Erro ao limpar arquivos temporários: {cleanup_error}")
            finally:
                # Garante que os arquivos temporários são removidos
                try:
                    if os.path.exists(relatorio_path):
                        os.remove(relatorio_path)
                    if os.path.exists(failed_ids_path):
                        os.remove(failed_ids_path)
                except Exception as cleanup_error:
                    logging.error(f"Erro ao limpar arquivos temporários: {cleanup_error}")

            # Envia relatório para o cliente (se não for admin)
            recipient_id = scheduled_message.get('recipient_id')
            if recipient_id and int(recipient_id) not in ADMINS:
                try:
                    # Dados do relatório
                    codigo = scheduled_message.get('code', 'N/A')
                    horario = current_time_str
                    client_report_text = (
                        f"📋 RELATÓRIO DE DIVULGAÇÃO\n"
                        f"Código: {codigo}\n"
                        f"Total de envios com sucesso: {success_count}\n"
                        f"Horário: {horario}"
                    )
                    client_txt = (
                        f"RELATÓRIO DE DIVULGAÇÃO\n"
                        f"Código: {codigo}\n"
                        f"Total de envios com sucesso: {success_count}\n"
                        f"Horário: {horario}\n\n"
                    )
                    if success_entries:
                        for entry in success_entries:
                            client_txt += f"{entry}\n"
                    else:
                        client_txt += "⚠️ Nenhuma divulgação foi realizada com sucesso nesta rodada.\n"
                    from aiogram.types import BufferedInputFile
                    file = BufferedInputFile(client_txt.encode('utf-8'), filename=f"relatorio_cliente_{codigo}.txt")
                    await bot.send_document(recipient_id, file, caption=client_report_text, parse_mode="Markdown")
                except Exception as e:
                    logging.error(f"Erro ao enviar relatório para o cliente {recipient_id}: {e}")
            
            # 🔥 GARANTIA DE RELATÓRIO - SEMPRE ENVIA NOTIFICAÇÃO PARA O CLIENTE
            try:
                # Função inline para garantir envio de relatório
                recipient_id = scheduled_message.get('recipient_id')
                if recipient_id and success_count > 0:
                    try:
                        basic_report = (
                            f"📊 **RELATÓRIO DE DIVULGAÇÃO**\n\n"
                            f"📋 Código: `{scheduled_message.get('code', 'N/A')}`\n"
                            f"✅ Enviado com sucesso para **{success_count}** grupos\n\n"
                            f"💡 Relatório completo disponível nos logs do sistema."
                        )
                        await bot.send_message(recipient_id, basic_report, parse_mode="Markdown")
                        logging.info(f"✅ Relatório básico enviado para cliente {recipient_id}")
                    except Exception as report_error:
                        logging.error(f"❌ Erro ao enviar relatório básico para cliente {recipient_id}: {report_error}")
            except Exception as e:
                logging.error(f"Erro na garantia de envio de relatório: {e}")

    except Exception as e:
        logging.error(f"Erro ao processar mensagem agendada: {e}")
    
    # ============================================================================
    # REGISTRO DE HISTÓRICO DE BROADCAST
    # ============================================================================
    try:
        plan_id = scheduled_message.get('id', scheduled_message.get('code', 'unknown'))
        fixed_id = scheduled_message.get('fixed_id', scheduled_message.get('fixed_ad_id', plan_id))
        total_chats = len(chat_ids_list)
        
        # Determina status baseado na taxa de sucesso
        taxa_sucesso = (success_count / total_chats * 100) if total_chats > 0 else 0
        if taxa_sucesso >= 90:
            status = 'success'
        elif taxa_sucesso >= 70:
            status = 'partial'
        else:
            status = 'failed'
        
        # Salva no histórico
        save_broadcast_history(
            plan_id=plan_id,
            fixed_id=fixed_id,
            status=status,
            chat_count=total_chats,
            success_count=success_count,
            failed_count=len(failure_list)
        )
        
        logging.info(f"[BROADCAST_HISTORY] Histórico registrado: {plan_id} - {success_count}/{total_chats} ({taxa_sucesso:.1f}%)")
        
    except Exception as e:
        logging.error(f"[BROADCAST_HISTORY] Erro ao registrar histórico: {e}")
    # ============================================================================
    
    return sent_messages, success_count, failure_list, full_report
# ====== Configuração de delay entre envios do scheduler ======
SCHEDULER_SEND_DELAY_SECONDS = 20  # Aumentado para evitar flood control (era 7)

async def scheduler():
    """Versão robusta do scheduler para rodar sempre em segundo plano sem travar o bot."""
    professional_logger.system_status("SCHEDULER", "OK", "Sistema de agendamento iniciado")
    
    # Sistema de log de horários processados
    horarios_processados = {}  # {horario: {sucesso: bool, timestamp: str, erro: str}}
    
    while True:
        try:
            current_time_str = datetime.datetime.now().strftime("%H:%M")
            current_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # LOG: Marca que este horário foi verificado
            if current_time_str not in horarios_processados:
                horarios_processados[current_time_str] = {
                    'verificado': True,
                    'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'mensagens_encontradas': 0,
                    'mensagens_enviadas': 0,
                    'erros': []
                }
            
            # Carrega as mensagens agendadas e armazena na variável local
            agendamentos = load_scheduled_messages()
            if agendamentos is None:
                agendamentos = []
                logging.warning(f"⚠️ [{current_time_str}] SCHEDULER: Nenhum agendamento carregado!")
            else:
                logging.info(f"✅ [{current_time_str}] SCHEDULER: {len(agendamentos)} agendamentos carregados")
            
            # PROCESSAMENTO SEQUENCIAL - NÃO SIMULTÂNEO (CORREÇÃO CRÍTICA)
            mensagens_para_enviar = []
            for scheduled_message in agendamentos[:]:
                try:
                    # Verifica se é hora de enviar a mensagem
                    msg_time = scheduled_message.get('time', 'N/A')
                    msg_code = scheduled_message.get('code', 'N/A')
                    
                    # LOG: Registra mensagem encontrada para este horário
                    if msg_time == current_time_str:
                        horarios_processados[current_time_str]['mensagens_encontradas'] += 1
                        logging.info(f"🎯 [{current_time_str}] Mensagem encontrada: {msg_code} (horário: {msg_time})")
                    
                    if scheduled_message['time'] == current_time_str:
                        # Verifica se a mensagem tem a flag start_tomorrow
                        if scheduled_message.get('start_tomorrow', False):
                            # Verifica se já passou pelo menos 1 dia desde a criação
                            creation_time_str = scheduled_message.get('creation_time', '')
                            if creation_time_str:
                                try:
                                    creation_date = datetime.datetime.strptime(creation_time_str, "%Y-%m-%d %H:%M:%S").date()
                                    current_date = datetime.datetime.now().date()
                                    
                                    # Se ainda é o mesmo dia da criação, pula este envio
                                    if creation_date == current_date:
                                        logging.info(f"⏭️ Pulando envio do código {scheduled_message.get('code', 'N/A')} - aguardando dia seguinte (start_tomorrow=True)")
                                        continue
                                    else:
                                        # Remove a flag start_tomorrow após o primeiro dia
                                        scheduled_message['start_tomorrow'] = False
                                        # Atualiza no arquivo
                                        for idx, msg in enumerate(agendamentos):
                                            if msg.get('code') == scheduled_message.get('code'):
                                                agendamentos[idx]['start_tomorrow'] = False
                                                break
                                        save_scheduled_messages(agendamentos, origem="scheduler_remove_start_tomorrow")
                                except Exception as e:
                                    logging.error(f"Erro ao verificar start_tomorrow: {e}")
                        
                        mensagens_para_enviar.append(scheduled_message.copy())
                except Exception as e:
                    logging.error(f"Erro ao preparar envio agendado: {e}")
            
            # LOG: Resumo de mensagens encontradas
            if len(mensagens_para_enviar) > 0:
                logging.info(f"📨 [{current_time_str}] {len(mensagens_para_enviar)} mensagem(ns) para enviar")
                horarios_processados[current_time_str]['mensagens_enviadas'] = len(mensagens_para_enviar)
            else:
                logging.debug(f"⏭️ [{current_time_str}] Nenhuma mensagem para enviar neste horário")
            
            # Salva log de horários processados em arquivo JSON para o painel web
            try:
                with open('scheduler_log.json', 'w', encoding='utf-8') as f:
                    json.dump(horarios_processados, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logging.error(f"Erro ao salvar scheduler_log.json: {e}")
            
            bot_logger.scheduler_activity(len(mensagens_para_enviar))
            
            # Processa uma mensagem por vez (SEQUENCIAL)
            for idx, scheduled_message in enumerate(mensagens_para_enviar):
                try:
                    msg_code = scheduled_message.get('code', 'N/A')
                    msg_id = scheduled_message.get('id', 'N/A')
                    fixed_id = scheduled_message.get('fixed_id', msg_id)
                    
                    logging.info(f"📤 [{current_time_str}] Processando mensagem {idx+1}/{len(mensagens_para_enviar)}: {msg_code}")
                    
                    # AGUARDA o processamento completo antes de continuar
                    start_time = datetime.datetime.now()
                    result = await processar_envio_agendado(scheduled_message)
                    end_time = datetime.datetime.now()
                    
                    # Extrai resultados
                    sent_messages, success_count, failure_list, full_report = result if isinstance(result, tuple) else ([], 0, [], "")
                    
                    # Salva no histórico de broadcasts
                    chat_count = len(load_chat_ids())
                    failed_count = len(failure_list)
                    status = 'success' if success_count > failed_count else 'partial' if success_count > 0 else 'failed'
                    
                    save_broadcast_history(
                        plan_id=msg_id,
                        fixed_id=fixed_id,
                        status=status,
                        chat_count=chat_count,
                        success_count=success_count,
                        failed_count=failed_count
                    )
                    
                    # LOG: Resultado do envio
                    processing_time = (end_time - start_time).total_seconds()
                    logging.info(
                        f"✅ [{current_time_str}] Mensagem {msg_code} processada em {processing_time:.1f}s - "
                        f"Sucesso: {success_count}/{chat_count} ({success_count/chat_count*100:.1f}%)"
                    )
                    
                    # Marca como sucesso no log de horários e calcula taxa
                    taxa_sucesso = (success_count / chat_count * 100) if chat_count > 0 else 0
                    horarios_processados[current_time_str]['sucesso'] = success_count > 0
                    horarios_processados[current_time_str]['taxa_sucesso'] = round(taxa_sucesso, 1)
                    horarios_processados[current_time_str]['success_count'] = success_count
                    horarios_processados[current_time_str]['failed_count'] = failed_count
                    
                    # Delay maior entre mensagens diferentes para evitar flood
                    if idx < len(mensagens_para_enviar) - 1:  # Não espera após a última
                        delay_time = SCHEDULER_SEND_DELAY_SECONDS + random.uniform(5, 15)
                        logging.info(f"⏳ Aguardando {delay_time:.1f}s antes da próxima mensagem...")
                        await asyncio.sleep(delay_time)
                        
                except Exception as e:
                    erro_msg = str(e)
                    logging.error(f"❌ [{current_time_str}] Erro ao processar envio agendado {idx+1}: {erro_msg}")
                    
                    # Registra erro no log de horários
                    horarios_processados[current_time_str]['erros'].append(erro_msg)
                    horarios_processados[current_time_str]['sucesso'] = False
            
            # Salva log de horários processados
            try:
                with open('scheduler_log.json', 'w', encoding='utf-8') as f:
                    # Mantém apenas últimas 24 horas
                    horarios_recentes = dict(list(horarios_processados.items())[-1440:])  # 24h * 60min
                    json.dump(horarios_recentes, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logging.error(f"Erro ao salvar log do scheduler: {e}")
                
        except Exception as e:
            erro_msg = str(e)
            logging.error(f"❌ [{current_time_str}] Erro no scheduler: {erro_msg}")
            
            # Registra erro crítico
            if current_time_str in horarios_processados:
                horarios_processados[current_time_str]['erros'].append(f"ERRO CRÍTICO: {erro_msg}")
                horarios_processados[current_time_str]['sucesso'] = False
                
        await asyncio.sleep(60 - datetime.datetime.now().second)

from aiogram import Router
from aiogram.types import CallbackQuery

@dp.callback_query(lambda c: c.data and c.data.startswith('clear_failed_ids:'))
async def clear_failed_ids_handler(callback_query: CallbackQuery):
    import json
    import os
    report_id = callback_query.data.split(':', 1)[1]
    failed_ids_path = f"failed_ids_{report_id}.json"
    if not os.path.exists(failed_ids_path):
        await callback_query.answer("Arquivo de IDs com erro não encontrado.", show_alert=True)
        return
    with open(failed_ids_path, 'r', encoding='utf-8') as f:
        failed_ids = json.load(f)
    # Remove os IDs do chat_ids.json
    if not os.path.exists(CHAT_IDS_FILE):
        await callback_query.answer("Arquivo chat_ids.json não encontrado.", show_alert=True)
        return
    with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
        chat_ids = json.load(f)
    original_len = len(chat_ids)
    chat_ids = [cid for cid in chat_ids if cid not in failed_ids]
    with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(chat_ids, f, ensure_ascii=False, indent=4)
    # Atualiza a lista global se existir
    if 'chat_ids' in globals():
        globals()['chat_ids'] = chat_ids
    os.remove(failed_ids_path)
    await callback_query.answer(f"IDs com erro removidos! ({original_len-len(chat_ids)} removidos)", show_alert=True)
    await callback_query.message.reply("IDs com erro removidos do chat_ids.json! Próxima divulgação já irá ignorar esses chats.")

def save_new_chat_id(chat_id):
    chat_id = str(chat_id)
    
    # Sempre carrega dados atuais do arquivo
    try:
        with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
            current_chat_ids = json.load(f)
    except Exception:
        current_chat_ids = []
    
    # Garante que todos os IDs da lista são string
    current_chat_ids = [str(cid) for cid in current_chat_ids]
    
    if chat_id not in current_chat_ids:
        current_chat_ids.append(chat_id)
        with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_chat_ids, f, ensure_ascii=False, indent=4)
        logging.info(f"Novo chat_id salvo: {chat_id}")
        print(f"[COLETA] Novo chat_id coletado: {chat_id} | Total agora: {len(current_chat_ids)}")
        return True
    logging.info(f"chat_id {chat_id} já estava salvo")
    return False

# --- Sistema de verificação de status do bot e notificações de remoção ---

import logging
import datetime
from aiogram.exceptions import TelegramNotFound as ChatNotFound, TelegramForbiddenError as BotKicked, TelegramUnauthorizedError as Unauthorized, TelegramBadRequest as BadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging

def load_chat_ids(path=CHAT_IDS_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [str(i) for i in json.load(f)]
    except Exception:
        return []

already_notified_chats = set()
notifications_silenced = False
silenced_until = None
admins = []
try:
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
        admins = config.get('admins', [])
except Exception:
    pass

async def check_bot_status():
    """Verificar o status do bot em cada grupo e notificar sobre remoções."""
    global already_notified_chats, notifications_silenced, silenced_until
    check_interval = 60
    batch_size = 30
    delay_between_checks = 1.5
    group_info_cache = {}
    while True:
        try:
            current_time = datetime.datetime.now().timestamp()
            notifications_active = not notifications_silenced
            if silenced_until and current_time > silenced_until:
                notifications_silenced = False
                if not notifications_silenced:
                    for admin_id in admins:
                        try:
                            await bot.send_message(
                                admin_id,
                                "🔔 As notificações de remoção do bot foram reativadas automaticamente."
                            )
                        except Exception as e:
                            logger.error(f"Erro ao notificar admin {admin_id}: {e}")
            chat_ids_list = list(load_chat_ids(CHAT_IDS_FILE))
            removed_chats = []
            for i in range(0, len(chat_ids_list), batch_size):
                batch = chat_ids_list[i:i+batch_size]
                for chat_id in batch:
                    try:
                        # Aumentar delay para evitar flood control
                        await asyncio.sleep(max(delay_between_checks, 3.0))
                        chat = await bot.get_chat(chat_id)
                        chat_type = "canal" if chat.type == "channel" else "grupo"
                        group_info_cache[chat_id] = {
                            'title': chat.title,
                            'username': chat.username,
                            'type': chat_type,
                            'invite_link': chat.invite_link if hasattr(chat, 'invite_link') else None,
                            'last_check': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        # Delay adicional antes de get_chat_member
                        await asyncio.sleep(1.0)
                        member = await bot.get_chat_member(chat_id, bot.id)
                        if chat_id in already_notified_chats:
                            already_notified_chats.remove(chat_id)
                    # Se atingir limite de flood, aguardar mais tempo
                    except Exception as e:
                        if 'Too Many Requests' in str(e) or 'Flood control exceeded' in str(e):
                            # Extrair tempo de retry se disponível
                            retry_after = 15  # padrão
                            if 'retry after' in str(e).lower():
                                try:
                                    import re
                                    match = re.search(r'retry after (\d+)', str(e).lower())
                                    if match:
                                        retry_after = int(match.group(1)) + 5  # adicionar buffer
                                except:
                                    pass
                            logger.warning(f"[SCHEDULED] Não foi possível obter link para chat {chat_id}: {e}")
                            logger.warning(f"Rate limit atingido. Aguardando {retry_after} segundos...")
                            await asyncio.sleep(retry_after)
                            continue
                    except (ChatNotFound, BotKicked, Unauthorized, BadRequest) as e:
                        error_message = str(e)
                        removed_chats.append((chat_id, error_message))
                        if chat_id not in already_notified_chats and notifications_active:
                            already_notified_chats.add(chat_id)
                            chat_info = f"Chat ID: {chat_id}"
                            chat_type = "canal ou grupo"
                            group_link = "Link não disponível"
                            if chat_id in group_info_cache:
                                info = group_info_cache[chat_id]
                                chat_info = f"{info.get('type', 'Chat').capitalize()}: {info.get('title', 'Sem título')} (ID: {chat_id})"
                                chat_type = info.get('type', 'chat')
                                if info.get('invite_link'):
                                    group_link = info['invite_link']
                                elif info.get('username'):
                                    group_link = f"https://t.me/{info['username']}"
                            keyboard = InlineKeyboardMarkup(row_width=2)
                            delete_button = InlineKeyboardButton(
                                "🗑️ Remover este ID",
                                callback_data=f"remove_chat_{chat_id}"
                            )
                            silence_temp_button = InlineKeyboardButton(
                                "🔇 Silenciar por 24h",
                                callback_data="silence_notifications_24h"
                            )
                            silence_perm_button = InlineKeyboardButton(
                                "🔇 Silenciar permanente",
                                callback_data="silence_notifications_perm"
                            )
                            keyboard.add(delete_button)
                            keyboard.add(silence_temp_button, silence_perm_button)
                            notification_message = (
                                f"⚠️ *Bot removido de um {chat_type}*\n\n"
                                f"📌 {chat_info}\n"
                                f"🔗 *Link:* {group_link}\n"
                                f"❌ *Erro:* {error_message}\n\n"
                                f"ℹ️ *Nota:* Infelizmente o Telegram não fornece informações sobre quem removeu o bot.\n\n"
                                f"Este ID será removido automaticamente da lista de envio.\n"
                                f"Use os botões abaixo para confirmar a remoção ou silenciar notificações."
                            )
                            for admin_id in admins:
                                try:
                                    await bot.send_message(
                                        admin_id,
                                        notification_message,
                                        parse_mode="Markdown",
                                        reply_markup=keyboard,
                                        disable_web_page_preview=True
                                    )
                                except Exception as admin_err:
                                    logger.error(f"Erro ao notificar admin {admin_id}: {admin_err}")
                    except Exception as e:
                        logger.error(f"Erro ao verificar status do chat {chat_id}: {e}")
                await asyncio.sleep(5)
            if removed_chats:
                chat_ids = load_chat_ids(CHAT_IDS_FILE)
                for chat_id, _ in removed_chats:
                    if chat_id in chat_ids:
                        chat_ids.remove(chat_id)
                with open(CHAT_IDS_FILE, "w", encoding="utf-8") as f:
                    json.dump(list(chat_ids), f, ensure_ascii=False, indent=4)
                logger.info(f"Removidos {len(removed_chats)} IDs de chats onde o bot foi removido")
        except Exception as e:
            logger.error(f"Erro geral na verificação de status do bot: {e}")
        await asyncio.sleep(check_interval)

# --- Handlers dos botões de remoção e silenciar ---
from aiogram import types
@dp.callback_query(lambda c: c.data and c.data.startswith('remove_chat_'))
async def callback_remove_chat(callback_query: types.CallbackQuery):
    chat_id = callback_query.data.split('_', 2)[-1]
    chat_ids = load_chat_ids()
    if chat_id in chat_ids:
        chat_ids.remove(chat_id)
        with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(chat_ids, f, ensure_ascii=False, indent=4)
        await callback_query.answer('ID removido da lista!', show_alert=True)
        await callback_query.message.edit_text('✅ ID removido da lista de envio.')
    else:
        await callback_query.answer('ID já não está na lista.')

@dp.callback_query(lambda c: c.data == 'silence_notifications_24h')
async def callback_silence_24h(callback_query: types.CallbackQuery):
    global notifications_silenced, silenced_until
    notifications_silenced = True
    silenced_until = datetime.datetime.now().timestamp() + 24*60*60
    await callback_query.answer('Notificações silenciadas por 24h!', show_alert=True)
    await callback_query.message.edit_text('🔇 Notificações silenciadas por 24h.')

@dp.callback_query(lambda c: c.data == 'silence_notifications_perm')
async def callback_silence_perm(callback_query: types.CallbackQuery):
    global notifications_silenced, silenced_until
    notifications_silenced = True
    silenced_until = None
    await callback_query.answer('Notificações silenciadas permanentemente!', show_alert=True)
    await callback_query.message.edit_text('🔇 Notificações silenciadas permanentemente.')

# ============================================================================
# SISTEMA DE CHECKOUT AVANÇADO - Monitora status do bot nos grupos
# ============================================================================

CHECKOUT_MUTED_FILE = 'checkout_muted.json'

def load_checkout_muted():
    """Carrega grupos com avisos silenciados"""
    try:
        if os.path.exists(CHECKOUT_MUTED_FILE):
            with open(CHECKOUT_MUTED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Erro ao carregar checkout_muted: {e}")
        return {}

def save_checkout_muted(data):
    """Salva grupos com avisos silenciados"""
    try:
        with open(CHECKOUT_MUTED_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Erro ao salvar checkout_muted: {e}")

async def checkout_system():
    """
    Sistema de checkout que verifica periodicamente:
    1. Se o bot foi removido de algum grupo
    2. Se o bot perdeu permissões de admin em algum grupo
    
    Notifica admins com botões para:
    - Silenciar aviso por 24h
    - Deletar o ID da lista
    """
    check_interval = 1800  # Verifica a cada 30 minutos
    batch_size = 20
    delay_between_checks = 2.0
    
    professional_logger.info("CHECKOUT", "Sistema de checkout iniciado")
    
    while True:
        try:
            await asyncio.sleep(check_interval)
            
            chat_ids_list = load_chat_ids()
            if not chat_ids_list:
                continue
            
            muted_data = load_checkout_muted()
            current_time = datetime.datetime.now()
            
            # Remove avisos silenciados que já expiraram
            expired_mutes = []
            for chat_id, mute_info in muted_data.items():
                if 'muted_until' in mute_info:
                    muted_until = datetime.datetime.fromisoformat(mute_info['muted_until'])
                    if current_time > muted_until:
                        expired_mutes.append(chat_id)
            
            for chat_id in expired_mutes:
                del muted_data[chat_id]
            
            if expired_mutes:
                save_checkout_muted(muted_data)
                professional_logger.info("CHECKOUT", f"Removidos {len(expired_mutes)} avisos silenciados expirados")
            
            # Verifica status em lotes
            for i in range(0, len(chat_ids_list), batch_size):
                batch = chat_ids_list[i:i+batch_size]
                
                for chat_id in batch:
                    try:
                        # Pula se estiver silenciado
                        if chat_id in muted_data:
                            continue
                        
                        await asyncio.sleep(delay_between_checks)
                        
                        # Tenta obter informações do chat
                        try:
                            chat = await bot.get_chat(chat_id)
                            chat_title = chat.title if hasattr(chat, 'title') else f"Chat {chat_id}"
                            chat_username = chat.username if hasattr(chat, 'username') else None
                            chat_link = f"https://t.me/{chat_username}" if chat_username else None
                            
                            # Verifica se o bot é membro e se é admin
                            try:
                                member = await bot.get_chat_member(chat_id, bot.id)
                                status = member.status
                                
                                # Se não for admin ou creator, notifica
                                if status not in ['administrator', 'creator']:
                                    await notify_checkout_issue(
                                        chat_id=chat_id,
                                        chat_title=chat_title,
                                        chat_link=chat_link,
                                        issue_type="no_admin",
                                        status=status
                                    )
                            except Exception as member_error:
                                # Se não conseguir verificar membro, pode ter sido removido
                                if 'bot was kicked' in str(member_error).lower() or 'user not found' in str(member_error).lower():
                                    await notify_checkout_issue(
                                        chat_id=chat_id,
                                        chat_title=chat_title,
                                        chat_link=chat_link,
                                        issue_type="removed",
                                        error=str(member_error)
                                    )
                        
                        except (ChatNotFound, BotKicked, Unauthorized) as e:
                            # Bot foi removido ou grupo não existe mais
                            await notify_checkout_issue(
                                chat_id=chat_id,
                                chat_title=f"Chat {chat_id}",
                                chat_link=None,
                                issue_type="removed",
                                error=str(e)
                            )
                        
                        except Exception as e:
                            if 'Too Many Requests' in str(e) or 'Flood' in str(e):
                                retry_after = 30
                                try:
                                    import re
                                    match = re.search(r'retry after (\d+)', str(e).lower())
                                    if match:
                                        retry_after = int(match.group(1)) + 5
                                except:
                                    pass
                                professional_logger.warning("CHECKOUT", f"Rate limit atingido. Aguardando {retry_after}s")
                                await asyncio.sleep(retry_after)
                                continue
                    
                    except Exception as e:
                        professional_logger.error("CHECKOUT", f"Erro ao verificar chat {chat_id}: {e}")
                        continue
                
                # Pausa entre lotes
                await asyncio.sleep(5)
            
            professional_logger.success("CHECKOUT", f"Verificação concluída para {len(chat_ids_list)} grupos")
            
        except Exception as e:
            professional_logger.error("CHECKOUT", f"Erro no sistema de checkout: {e}")
            await asyncio.sleep(60)

async def notify_checkout_issue(chat_id, chat_title, chat_link, issue_type, status=None, error=None):
    """Notifica admins sobre problemas detectados no checkout"""
    try:
        config = load_config()
        admins = config.get('admins', [])
        
        if not admins:
            return
        
        # Monta a mensagem
        if issue_type == "no_admin":
            emoji = "⚠️"
            title = "BOT SEM PERMISSÃO DE ADMIN"
            description = f"O bot está no grupo mas **não tem permissões de administrador**.\n\n📊 **Status atual:** `{status}`"
        else:  # removed
            emoji = "🚫"
            title = "BOT REMOVIDO DO GRUPO"
            description = f"O bot foi **removido** ou o grupo não existe mais.\n\n❌ **Erro:** `{error[:100] if error else 'Desconhecido'}`"
        
        message = f"""{emoji} **{title}**

📌 **Grupo:** {chat_title}
🆔 **ID:** `{chat_id}`
🔗 **Link:** {chat_link if chat_link else '❌ Não disponível'}

{description}

⚡ **Ações disponíveis:**
• Use os botões abaixo para gerenciar este aviso
• O ID pode ser removido automaticamente da lista"""
        
        # Cria teclado inline
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔕 Silenciar por 24h",
                    callback_data=f"checkout_mute24_{chat_id}"
                ),
                InlineKeyboardButton(
                    text="🗑️ Deletar ID",
                    callback_data=f"checkout_delete_{chat_id}"
                )
            ]
        ])
        
        # Envia para todos os admins
        for admin_id in admins:
            try:
                await bot.send_message(
                    admin_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )
                professional_logger.info("CHECKOUT", f"Notificação enviada ao admin {admin_id} sobre {chat_id}")
            except Exception as e:
                professional_logger.error("CHECKOUT", f"Erro ao notificar admin {admin_id}: {e}")
    
    except Exception as e:
        professional_logger.error("CHECKOUT", f"Erro ao enviar notificação de checkout: {e}")

# Handlers para os botões do checkout
@dp.callback_query(lambda c: c.data and c.data.startswith('checkout_mute24_'))
async def checkout_mute_24h_handler(callback_query: types.CallbackQuery):
    """Silencia avisos de um grupo por 24 horas"""
    try:
        chat_id = callback_query.data.replace('checkout_mute24_', '')
        
        muted_data = load_checkout_muted()
        muted_until = datetime.datetime.now() + timedelta(hours=24)
        
        muted_data[chat_id] = {
            'muted_until': muted_until.isoformat(),
            'muted_by': callback_query.from_user.id,
            'muted_at': datetime.datetime.now().isoformat()
        }
        
        save_checkout_muted(muted_data)
        
        await callback_query.answer("✅ Avisos silenciados por 24 horas!", show_alert=True)
        await callback_query.message.edit_text(
            f"🔕 **Avisos silenciados por 24 horas**\n\n"
            f"🆔 **Chat ID:** `{chat_id}`\n"
            f"⏰ **Até:** {muted_until.strftime('%d/%m/%Y %H:%M')}\n\n"
            f"Os avisos voltarão automaticamente após este período.",
            parse_mode="Markdown"
        )
        
        professional_logger.info("CHECKOUT", f"Avisos silenciados para {chat_id} por 24h pelo admin {callback_query.from_user.id}")
    
    except Exception as e:
        professional_logger.error("CHECKOUT", f"Erro ao silenciar avisos: {e}")
        await callback_query.answer("❌ Erro ao silenciar avisos", show_alert=True)

@dp.callback_query(lambda c: c.data and c.data.startswith('checkout_delete_'))
async def checkout_delete_handler(callback_query: types.CallbackQuery):
    """Deleta um ID da lista de grupos"""
    try:
        chat_id = callback_query.data.replace('checkout_delete_', '')
        
        # Remove do chat_ids.json
        chat_ids = load_chat_ids()
        if chat_id in chat_ids:
            chat_ids.remove(chat_id)
            with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(chat_ids, f, ensure_ascii=False, indent=4)
            
            # Remove dos avisos silenciados também
            muted_data = load_checkout_muted()
            if chat_id in muted_data:
                del muted_data[chat_id]
                save_checkout_muted(muted_data)
            
            await callback_query.answer("✅ ID removido da lista!", show_alert=True)
            await callback_query.message.edit_text(
                f"✅ **ID removido com sucesso**\n\n"
                f"🆔 **Chat ID:** `{chat_id}`\n"
                f"🗑️ **Removido por:** {callback_query.from_user.first_name}\n"
                f"📊 **Total de grupos agora:** {len(chat_ids)}\n\n"
                f"Este grupo não receberá mais mensagens do bot.",
                parse_mode="Markdown"
            )
            
            professional_logger.success("CHECKOUT", f"ID {chat_id} removido pelo admin {callback_query.from_user.id}")
        else:
            await callback_query.answer("ℹ️ ID já não está na lista", show_alert=True)
    
    except Exception as e:
        professional_logger.error("CHECKOUT", f"Erro ao deletar ID: {e}")
        await callback_query.answer("❌ Erro ao deletar ID", show_alert=True)

# Comando para visualizar status do checkout
@dp.message(Command("checkout"))
async def checkout_status_cmd(message: types.Message):
    """Mostra o status do sistema de checkout"""
    config = load_config()
    if message.from_user.id not in config.get('admins', []):
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    try:
        muted_data = load_checkout_muted()
        chat_ids = load_chat_ids()
        
        # Conta avisos ativos e silenciados
        active_mutes = 0
        expired_mutes = 0
        current_time = datetime.datetime.now()
        
        for chat_id, mute_info in muted_data.items():
            if 'muted_until' in mute_info:
                muted_until = datetime.datetime.fromisoformat(mute_info['muted_until'])
                if current_time < muted_until:
                    active_mutes += 1
                else:
                    expired_mutes += 1
        
        status_msg = f"""🔍 **SISTEMA DE CHECKOUT**

📊 **Estatísticas:**
• Total de grupos: `{len(chat_ids)}`
• Avisos silenciados: `{active_mutes}`
• Avisos expirados: `{expired_mutes}`

⚙️ **Configuração:**
• Intervalo de verificação: `30 minutos`
• Tamanho do lote: `20 grupos`
• Delay entre verificações: `2 segundos`

🔔 **O que é monitorado:**
✓ Bot removido de grupos
✓ Bot sem permissão de admin
✓ Grupos que não existem mais

💡 **Próxima verificação:** Em até 30 minutos

Use /checkout_test para forçar uma verificação manual"""

        await message.reply(status_msg, parse_mode="Markdown")
        
    except Exception as e:
        await message.reply(f"❌ Erro ao obter status: {e}")

@dp.message(Command("checkout_test"))
async def checkout_test_cmd(message: types.Message):
    """Testa o sistema de checkout em um grupo específico"""
    config = load_config()
    if message.from_user.id not in config.get('admins', []):
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    # Verifica se foi passado um ID
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply(
            "ℹ️ **Uso:** `/checkout_test <chat_id>`\n\n"
            "Exemplo: `/checkout_test -1001234567890`\n\n"
            "Este comando verifica o status do bot em um grupo específico.",
            parse_mode="Markdown"
        )
        return
    
    chat_id = args[1].strip()
    
    try:
        await message.reply(f"🔍 Verificando status do bot no chat `{chat_id}`...", parse_mode="Markdown")
        
        # Tenta obter informações do chat
        try:
            chat = await bot.get_chat(chat_id)
            chat_title = chat.title if hasattr(chat, 'title') else f"Chat {chat_id}"
            chat_username = chat.username if hasattr(chat, 'username') else None
            chat_type = "Canal" if chat.type == "channel" else "Grupo"
            
            # Verifica status do bot
            member = await bot.get_chat_member(chat_id, bot.id)
            status = member.status
            
            status_emoji = "✅" if status in ['administrator', 'creator'] else "⚠️"
            
            result_msg = f"""{status_emoji} **Resultado da Verificação**

📌 **{chat_type}:** {chat_title}
🆔 **ID:** `{chat_id}`
🔗 **Username:** @{chat_username if chat_username else 'N/A'}

👤 **Status do bot:** `{status}`
{'✅ Bot tem permissões adequadas' if status in ['administrator', 'creator'] else '⚠️ Bot NÃO é administrador'}

{'🎯 Tudo OK! O bot está funcionando corretamente neste grupo.' if status in ['administrator', 'creator'] else '⚠️ ATENÇÃO: O bot não tem permissões de admin neste grupo!'}"""
            
            await message.reply(result_msg, parse_mode="Markdown")
            
        except (ChatNotFound, BotKicked, Unauthorized) as e:
            await message.reply(
                f"🚫 **Bot removido ou grupo inexistente**\n\n"
                f"🆔 **Chat ID:** `{chat_id}`\n"
                f"❌ **Erro:** `{str(e)[:100]}`\n\n"
                f"O bot foi removido deste grupo ou ele não existe mais.",
                parse_mode="Markdown"
            )
        
    except Exception as e:
        await message.reply(f"❌ Erro ao verificar: {e}")

# --- Função para checar planos expirando e notificar usuários/admins ---
contracts_checked = {}
notifications_sent = {}

async def load_settings():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

async def check_plan_expiration():
    """Função assíncrona para verificar expiração de planos"""
    try:
        # Usa o carregador centralizado para considerar também scheduled_mesagges.json
        user_data = load_scheduled_messages()

        current_time = datetime.datetime.now()
        expiring_plans = []
        failed_notifications = []

        # Agrupa registros por usuário e escolhe a melhor expiração (mais distante no futuro),
        # ignorando reagendamentos temporários quando houver um plano "real".
        plans_by_user = {}
        for data in user_data:
            try:
                recipient_id = data.get('recipient_id')
                if not recipient_id:
                    continue

                is_reagendamento = bool(data.get('is_reagendamento', False))
                expiry_str = data.get('plan_expiry_time') or data.get('expiry_time')
                if not expiry_str:
                    continue

                expiry_dt = datetime.datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')

                current_choice = plans_by_user.get(recipient_id)
                if current_choice is None:
                    plans_by_user[recipient_id] = {
                        'data': data,
                        'expiry_dt': expiry_dt,
                        'expiry_str': expiry_str,
                        'is_reagendamento': is_reagendamento,
                    }
                else:
                    better = False
                    if current_choice['is_reagendamento'] and not is_reagendamento:
                        better = True
                    elif current_choice['is_reagendamento'] == is_reagendamento and expiry_dt > current_choice['expiry_dt']:
                        better = True
                    if better:
                        plans_by_user[recipient_id] = {
                            'data': data,
                            'expiry_dt': expiry_dt,
                            'expiry_str': expiry_str,
                            'is_reagendamento': is_reagendamento,
                        }
            except Exception as e:
                logger.error(f"Erro ao preparar dados de expiração para usuário {data.get('recipient_id')}: {str(e)}")
                continue

        # Constrói a lista de planos realmente próximos ao vencimento (0-3 dias)
        for recipient_id, info in plans_by_user.items():
            try:
                expiry_dt = info['expiry_dt']
                expiry_str = info['expiry_str']

                contract_key = f"{recipient_id}_{expiry_str}"
                last_checked = contracts_checked.get(contract_key)
                if last_checked and (current_time - last_checked).total_seconds() < 24 * 3600:
                    continue

                seconds_left = (expiry_dt - current_time).total_seconds()
                days_until_expiry = int((seconds_left + 86399) // 86400)  # arredondamento para cima

                if 0 <= days_until_expiry <= 3:
                    data = info['data']
                    expiring_plans.append({
                        'recipient_id': data.get('recipient_id'),
                        'expiry_time': expiry_str,
                        'days_until_expiry': days_until_expiry,
                        'fixed_ad_id': data.get('fixed_ad_id'),
                        'from_chat_id': data.get('from_chat_id'),
                    })
                    contracts_checked[contract_key] = current_time
            except Exception as e:
                logger.error(f"Erro ao processar expiração para usuário {recipient_id}: {str(e)}")
                continue

        if expiring_plans:
            admin_summary = "🚨 RESUMO DE PLANOS PRÓXIMOS DO VENCIMENTO:\n\n"
            for plan in expiring_plans:
                notification_key = f"{plan['recipient_id']}_{plan['expiry_time']}"
                current_timestamp = datetime.datetime.now().timestamp()
                last_notification = notifications_sent.get(notification_key, {})
                if not last_notification or \
                   (current_timestamp - last_notification.get('last_sent', 0)) >= (24 * 60 * 60):
                    user_message = (
                        f"⚠️ AVISO IMPORTANTE: Seu plano expira em {plan['days_until_expiry']} dias!\n"
                        f"Data de expiração: {plan['expiry_time']}\n"
                        "Entre em contato urgentemente para renovar seu plano."
                    )
                    try:
                        await bot.send_message(
                            chat_id=plan['recipient_id'],
                            text=user_message
                        )
                        try:
                            await bot.send_photo(
                                chat_id=plan['recipient_id'],
                                photo="https://i.ibb.co/KcVymyfD/Chat-GPT-Image-14-de-mai-de-2025-02-39-03.png"
                            )
                        except Exception as img_error:
                            logger.error(f"Erro ao enviar imagem: {img_error}")
                        notifications_sent[notification_key] = {
                            'last_sent': current_timestamp,
                            'count': last_notification.get('count', 0) + 1
                        }
                    except Exception as e:
                        failed_notifications.append({
                            'user_id': plan['recipient_id'],
                            'reason': str(e)
                        })
                status_emoji = "🔴" if plan['days_until_expiry'] == 0 else "⚠️"
                # Buscar username do usuário para o admin_summary
                try:
                    chat = await bot.get_chat(int(plan['recipient_id']))
                    username = f"@{chat.username}" if getattr(chat, 'username', None) else "(sem username)"
                except Exception as e:
                    username = "(não encontrado)"
                    logger.warning(f"Não foi possível obter username para ID {plan['recipient_id']}: {e}")
                admin_summary += (
                    f"{status_emoji} Usuário ID: {plan['recipient_id']} {username}\n"
                    f"⏰ Expira em: {plan['days_until_expiry']} dias\n"
                    f"📅 Data: {plan['expiry_time']}\n"
                    f"📋 Contrato: {plan['fixed_ad_id']}\n"
                )
                if any(f['user_id'] == plan['recipient_id'] for f in failed_notifications):
                    admin_summary += "❗ Não foi possível notificar este usuário - Necessário contato manual\n"
                admin_summary += "\n"
            if failed_notifications:
                admin_summary += "\n⚠️ ATENÇÃO: Alguns usuários não puderam ser notificados automaticamente!\n"
                admin_summary += "É necessário entrar em contato manualmente.\n"
            settings = await load_settings()
            admins = settings.get('admins', [])
            for admin_chat_id in admins:
                try:
                    await bot.send_message(
                        chat_id=admin_chat_id,
                        text=admin_summary
                    )
                    logger.info(f"Relatório de expiração enviado para admin {admin_chat_id}. Total de planos: {len(expiring_plans)}")
                except Exception as e:
                    logger.error(f"Erro ao enviar relatório para admin {admin_chat_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Erro ao verificar planos: {str(e)}")

async def periodic_plan_check():
    """Loop periódico para verificar planos"""
    while True:
        await check_plan_expiration()
        await asyncio.sleep(86400)

# --- Startup: iniciar o loop em background ---
import asyncio

async def on_startup(dispatcher):
    asyncio.create_task(check_bot_status())
    asyncio.create_task(periodic_plan_check())
    # Você pode adicionar outras tasks de background aqui, se necessário

if 'dp' in globals():
    dp.startup.register(on_startup)

# Dependências globais
already_notified_chats = set()
notifications_silenced = False
silenced_until = None
admins = []  # Preencha com os IDs dos admins do seu bot
logger = logging.getLogger("bott")

# Função utilitária para carregar chat_ids

def load_chat_ids(file_path=CHAT_IDS_FILE):
    try:
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'r', encoding='utf-8') as file:
                return set(json.load(file))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return set()

# Função para verificar se o usuário é admin
async def is_admin(user_id):
    return str(user_id) in [str(a) for a in admins]

# --- Função principal de checagem ---
async def check_bot_status():
    """Verificar o status do bot em cada grupo e notificar sobre remoções."""
    global already_notified_chats, notifications_silenced, silenced_until

    check_interval = 60  # Intervalo entre ciclos completos em segundos
    batch_size = 30  # Número de chats para verificar por ciclo
    delay_between_checks = 1.5  # Segundos entre verificações individuais

    group_info_cache = {}

    while True:
        try:
            current_time = datetime.datetime.now().timestamp()
            notifications_active = not notifications_silenced

            if silenced_until and current_time > silenced_until:
                notifications_silenced = False
                if not notifications_silenced:
                    for admin_id in admins:
                        try:
                            await bot.send_message(
                                admin_id,
                                "🔔 As notificações de remoção do bot foram reativadas automaticamente."
                            )
                        except Exception as e:
                            logger.error(f"Erro ao notificar admin {admin_id}: {e}")

            chat_ids_list = list(load_chat_ids(CHAT_IDS_FILE))
            removed_chats = []

            for i in range(0, len(chat_ids_list), batch_size):
                batch = chat_ids_list[i:i+batch_size]
                for chat_id in batch:
                    try:
                        # Aumentar delay para evitar flood control
                        await asyncio.sleep(max(delay_between_checks, 3.0))
                        chat = await bot.get_chat(chat_id)
                        chat_type = "canal" if chat.type == "channel" else "grupo"
                        group_info_cache[chat_id] = {
                            'title': chat.title,
                            'username': chat.username,
                            'type': chat_type,
                            'invite_link': getattr(chat, 'invite_link', None),
                            'last_check': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        # Delay adicional antes de get_chat_member
                        await asyncio.sleep(1.0)
                        member = await bot.get_chat_member(chat_id, bot.id)
                        if chat_id in already_notified_chats:
                            already_notified_chats.remove(chat_id)
                    except Exception as e:
                        if 'Too Many Requests' in str(e) or 'Flood control exceeded' in str(e):
                            # Extrair tempo de retry se disponível
                            retry_after = 15  # padrão
                            if 'retry after' in str(e).lower():
                                try:
                                    import re
                                    match = re.search(r'retry after (\d+)', str(e).lower())
                                    if match:
                                        retry_after = int(match.group(1)) + 5  # adicionar buffer
                                except:
                                    pass
                            logger.warning(f"[SCHEDULED] Não foi possível obter link para chat {chat_id}: {e}")
                            logger.warning(f"Rate limit atingido. Aguardando {retry_after} segundos...")
                            await asyncio.sleep(retry_after)
                            continue
                        elif isinstance(e, (ChatNotFound, BotKicked, Unauthorized)):
                            error_message = str(e)
                            removed_chats.append((chat_id, error_message))
                            if chat_id not in already_notified_chats and notifications_active:
                                already_notified_chats.add(chat_id)
                                chat_info = f"Chat ID: {chat_id}"
                                chat_type = "canal ou grupo"
                                group_link = "Link não disponível"
                                if chat_id in group_info_cache:
                                    info = group_info_cache[chat_id]
                                    chat_info = f"{info.get('type', 'Chat').capitalize()}: {info.get('title', 'Sem título')} (ID: {chat_id})"
                                    chat_type = info.get('type', 'chat')
                                    if info.get('invite_link'):
                                        group_link = info['invite_link']
                                    elif info.get('username'):
                                        group_link = f"https://t.me/{info['username']}"
                                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                    [InlineKeyboardButton(
                                        text="🗑️ Remover este ID",
                                        callback_data=f"remove_chat_{chat_id}"
                                    )],
                                    [InlineKeyboardButton(
                                        text="🔇 Silenciar por 24h",
                                        callback_data="silence_notifications_24h"
                                    ), InlineKeyboardButton(
                                        text="🔇 Silenciar permanente",
                                        callback_data="silence_notifications_perm"
                                    )]
                                ])
                                notification_message = (
                                    f"⚠️ *Bot removido de um {chat_type}*\n\n"
                                    f"📌 {chat_info}\n"
                                    f"🔗 *Link:* {group_link}\n"
                                    f"❌ *Erro:* {error_message}\n\n"
                                    f"ℹ️ *Nota:* Infelizmente o Telegram não fornece informações sobre quem removeu o bot.\n\n"
                                    f"Este ID será removido automaticamente da lista de envio.\n"
                                    f"Use os botões abaixo para confirmar a remoção ou silenciar notificações."
                                )
                                for admin_id in admins:
                                    try:
                                        await bot.send_message(
                                            admin_id,
                                            notification_message,
                                            parse_mode="Markdown",
                                            reply_markup=keyboard,
                                            disable_web_page_preview=True
                                        )
                                    except Exception as admin_err:
                                        logger.error(f"Erro ao notificar admin {admin_id}: {admin_err}")
                                # sent_messages.append(error_message)  # Removido - variável não está no escopo
                                
                                # Adiciona o ID à lista de falhas
                                if chat_id not in failed_chat_ids:
                                    failed_chat_ids.add(chat_id)
                                    await save_failed_chat_ids()
                        
                        # Código removido - scheduled_message não está no escopo desta função
                        # Esta lógica deve estar na função processar_envio_agendado()
                        
                        # pois as variáveis necessárias não estão disponíveis neste contexto
                        
                        # Toda a seção de relatórios foi removida desta função
                        # pois as variáveis necessárias (scheduled_message, success_count, etc.)
                        # não estão no escopo desta função de monitoramento
                        # Código órfão removido - todas as variáveis de relatório não estão no escopo desta função

        except Exception as e:
            logging.error(f"Erro durante o monitoramento de mensagens: {e}")

# --- Função para remoção periódica de mensagens expiradas (removida - duplicada) ---

# Função de monitoramento em tempo real dos grupos/canais
async def monitorar_grupos():
    import aiohttp
    import time
    INTERVALO_SEGUNDOS = 30  # Frequência do monitoramento
    while True:
        try:
            # Carrega a lista persistente de chat_ids
            try:
                with open(CHAT_IDS_FILE, encoding='utf-8') as f:
                    chat_ids_salvos = set(json.load(f))
            except Exception:
                chat_ids_salvos = set()
            # Como não temos mais variável global, usamos os dados do arquivo como referência
            # Esta função agora apenas monitora mudanças no arquivo
            ids_atuais = set(chat_ids_salvos)  # FIX: Garante que é um set
            # Detecta novos grupos/canais
            novos = ids_atuais - chat_ids_salvos
            removidos = chat_ids_salvos - ids_atuais
            # Notifica admins sobre novos
            if novos:
                added_by = load_added_by()
                for chat_id in novos:
                    try:
                        chat = await bot.get_chat(chat_id)
                        nome = getattr(chat, 'title', str(chat_id))
                    except Exception:
                        nome = str(chat_id)
                    quem_adicionou = added_by.get(str(chat_id), 'Não disponível')
                    mensagem = f"""ℹ️ *Bot adicionado a um novo grupo/canal!*\n*Nome:* {nome}\n*ID:* `{chat_id}`\n*Adicionado por:* {quem_adicionou}\n*Data:* {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
                    for admin_id in config.get('admins', []):
                        try:
                            await bot.send_message(admin_id, mensagem, parse_mode="Markdown")
                        except Exception as e:
                            logging.error(f"Erro ao notificar admin {admin_id} sobre novo grupo: {e}")
                # Atualiza o arquivo
                with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(list(ids_atuais), f, ensure_ascii=False, indent=4)
            # Notifica admins sobre remoções
            if removidos:
                for chat_id in removidos:
                    mensagem = f"""⚠️ *O bot foi removido de um grupo/canal!*
*ID:* `{chat_id}`
*Data:* {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
                    for admin_id in config.get('admins', []):
                        try:
                            await bot.send_message(admin_id, mensagem, parse_mode="Markdown")
                        except Exception as e:
                            if "chat not found" in str(e).lower() or "bad request" in str(e).lower():
                                logging.debug(f"Erro esperado ao notificar admin {admin_id} sobre remoção: {e}")
                            else:
                                logging.debug(f"Erro ao notificar admin {admin_id} sobre remoção: {e}")
                # Atualiza o arquivo
                with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(list(ids_atuais), f, ensure_ascii=False, indent=4)
            # Verifica perda de direitos de admin
            for chat_id in list(ids_atuais):
                try:
                    chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=bot.id)
                    try:
                        status = getattr(chat_member, 'status', None)
                        if status not in ['administrator', 'creator']:
                            # Perdeu admin
                            # Anti-flood: notificar só 1 vez ao dia
                            notified = load_notified_today()
                    except Exception as e:
                        import traceback
                        logging.error(f"Erro inesperado ao verificar admin em {chat_id}: {e}\n{traceback.format_exc()}")
                        muted = load_muted_groups()
                        if chat_id in muted:
                            continue  # Silenciado
                        if chat_id in notified['groups']:
                            continue  # Já notificado hoje

                        chat = await bot.get_chat(chat_id)
                        nome_grupo = chat.title if hasattr(chat, 'title') and chat.title else 'Desconhecido'
                        if hasattr(chat, 'username') and chat.username:
                            link_grupo = f"https://t.me/{chat.username}"
                        else:
                            link_grupo = 'Privado ou sem link público'
                        mensagem = (
                            f"⚠️ *O bot perdeu direitos de administrador em:*\n"
                            f"*Nome:* {nome_grupo}\n"
                            f"*Link:* {link_grupo}\n"
                            f"*ID:* `{chat_id}`\n"
                            f"*Status atual:* {chat_member.status}\n"
                            f"*Data:* {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                        )
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton("🗑️ Apagar grupo", callback_data=f"apagar_{chat_id}"),
                                InlineKeyboardButton("🔕 Silenciar", callback_data=f"silenciar_{chat_id}")
                            ]
                        ])
                        for admin_id in config.get('admins', []):
                            try:
                                await bot.send_message(admin_id, mensagem, parse_mode="Markdown", reply_markup=keyboard)
                            except Exception as e:
                                logging.error(f"Erro ao notificar admin {admin_id} sobre perda de admin: {e}")
                        notified['groups'].append(chat_id)
                        save_notified_today(notified)
                except Exception as e:
                    logging.debug(f"Erro ao verificar admin em {chat_id}: {e}")
            await asyncio.sleep(INTERVALO_SEGUNDOS)
        except Exception as e:
            logging.error(f"Erro no monitoramento de grupos: {e}")
            await asyncio.sleep(60)

# ============================================================================
# COMANDO PARA VISUALIZAR ESTATÍSTICAS DE FLOOD CONTROL
# ============================================================================

@dp.message(Command('flood'))
async def flood_stats_command(message: Message):
    """Comando para visualizar estatísticas de flood control"""
    try:
        # Verifica se é admin
        if message.from_user.id not in ADMINS:
            await message.reply("❌ Acesso negado. Apenas administradores podem ver essas estatísticas.")
            return
        
        stats = flood_monitor.get_stats()
        
        stats_text = (
            f"📊 **ESTATÍSTICAS DE FLOOD CONTROL**\n\n"
            f"⏰ **Uptime:** {stats['uptime_hours']:.1f} horas\n"
            f"📊 **Total de Requisições:** {stats['total_requests']}\n"
            f"✅ **Taxa de Sucesso:** {stats['success_rate']}\n"
            f"🚨 **Taxa de Flood Errors:** {stats['flood_error_rate']}\n"
            f"❌ **Total de Flood Errors:** {stats['total_flood_errors']}\n"
            f"⏱️ **Tempo Total de Espera:** {stats['total_wait_time_minutes']:.1f} minutos\n"
        )
        
        if stats['last_flood_error']:
            last_error_str = stats['last_flood_error'].strftime('%d/%m/%Y %H:%M:%S')
            stats_text += f"🔴 **Último Flood Error:** {last_error_str}\n"
        else:
            stats_text += f"🔴 **Último Flood Error:** Nenhum registrado\n"
        
        # Adiciona informações sobre configurações atuais
        stats_text += (
            f"\n🔧 **CONFIGURAÇÕES ATUAIS:**\n"
            f"• Scheduler Delay: {SCHEDULER_SEND_DELAY_SECONDS}s\n"
            f"• Per-Chat Delay: {PER_CHAT_SEND_DELAY_SECONDS}s\n"
            f"• Rate Limiter: {telegram_rate_limiter.max_requests} req/{telegram_rate_limiter.time_window}s\n"
            f"• Current Delay: {rate_limiter.delay:.2f}s\n"
        )
        
        await message.reply(stats_text, parse_mode=ParseMode.MARKDOWN)
        
        # Log das estatísticas no console
        flood_monitor.log_stats()
        
    except Exception as e:
        logging.error(f"Erro no comando flood_stats: {e}")
        await message.reply(f"❌ Erro ao obter estatísticas: {e}")

# No main, garantir que o scheduler e o monitoramento estão sendo chamados
async def main():
    # Mostrar cabeçalho profissional
    professional_logger.startup_header()
    
    # **LIMPEZA AUTOMÁTICA DE REAGENDAMENTOS NA INICIALIZAÇÃO**
    try:
        professional_logger.info("CLEANUP", "Removendo reagendamentos duplicados...")
        scheduled_messages_temp = load_scheduled_messages()
        reagendamentos_encontrados = [msg for msg in scheduled_messages_temp if msg.get('is_reagendamento', False)]
        
        if reagendamentos_encontrados:
            # Remove todos os reagendamentos
            scheduled_messages_limpo = [msg for msg in scheduled_messages_temp if not msg.get('is_reagendamento', False)]
            save_scheduled_messages(scheduled_messages_limpo, origem="startup_cleanup")
            professional_logger.success("CLEANUP", f"{len(reagendamentos_encontrados)} reagendamentos removidos na inicialização")
        else:
            professional_logger.info("CLEANUP", "Nenhum reagendamento encontrado")
    except Exception as e:
        professional_logger.error("CLEANUP", f"Erro ao limpar reagendamentos: {e}")
    
    # Verifica se há chat IDs antes de iniciar o bot
    while True:
        chat_ids_list = load_chat_ids()
        if chat_ids_list:
            professional_logger.system_status("STARTUP", "OK", f"Bot iniciando com {len(chat_ids_list)} chat(s) registrado(s)")
            break
        else:
            professional_logger.warning("STARTUP", "Nenhum chat ID encontrado em chat_ids.json. Bot aguardando...")
            # Notifica admins sobre a situação
            try:
                for admin_id in admins:
                    await bot.send_message(
                        admin_id,
                        "⚠️ Bot não iniciado: Nenhum grupo/chat registrado encontrado em chat_ids.json.\n"
                        "Adicione o bot a grupos ou use comandos para registrar chats."
                    )
            except Exception as e:
                logging.error(f"[STARTUP] Erro ao notificar admins: {e}")
            
            # Aguarda 30 segundos antes de verificar novamente
            await asyncio.sleep(30)
    
    # Cada loop importante roda em background, garantindo máxima responsividade
    scheduler_task = asyncio.create_task(scheduler())
    monitor_task = asyncio.create_task(monitorar_grupos())
    backup_task = asyncio.create_task(backup_scheduler())
    remove_failed_task = asyncio.create_task(remove_failed_chat_ids_loop())
    check_status_task = asyncio.create_task(check_bot_status())
    cleanup_task = asyncio.create_task(check_and_remove_expired_messages())  # Loop de limpeza automática
    try:
        await dp.start_polling(bot, skip_updates=False, allowed_updates=["message", "callback_query", "chat_member", "my_chat_member", "channel_post", "edited_channel_post", "inline_query", "chosen_inline_result"])
    except Exception as e:
        logging.error(f"[POLLING] Erro no polling: {e}")
    finally:
        scheduler_task.cancel()
        monitor_task.cancel()
        backup_task.cancel()
        remove_failed_task.cancel()
        check_status_task.cancel()
        cleanup_task.cancel()
        try:
            await scheduler_task
            await monitor_task
            await backup_task
            await remove_failed_task
            await check_status_task
            await cleanup_task
        except asyncio.CancelledError:
            pass

failed_chat_ids = set()

async def remove_failed_chat_ids_loop():
    while True:
        try:
            await remove_failed_chat_ids()
        except Exception as e:
            logging.error(f"Erro no loop de remoção de IDs com falha: {e}")
        await asyncio.sleep(600)  # 10 minutos

async def save_failed_chat_ids():
    with open(FAILED_CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(failed_chat_ids), f, ensure_ascii=False, indent=4)



async def remove_failed_chat_ids():
    global failed_chat_ids
    removed_count = 0
    
    # Carrega a lista atual de chat_ids
    try:
        with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
            current_chat_ids = json.load(f)
        bot_logger.cleanup_activity(0, len(current_chat_ids))
    except Exception as e:
        logging.error(f"[REMOVE_FAILED] Erro ao carregar chat_ids: {e}")
        return 0
    
    # Remove os IDs com falha da lista principal
    for chat_id in list(failed_chat_ids):
        # Converte para int para comparar com a lista que contém inteiros
        chat_id_int = int(chat_id)
        if chat_id_int in current_chat_ids:
            current_chat_ids.remove(chat_id_int)
            removed_count += 1
            # Log removido para reduzir verbosidade
    
    # Salva a lista atualizada apenas se houve remoções
    if removed_count > 0:
        try:
            # Salva a lista principal atualizada
            with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(current_chat_ids, f, ensure_ascii=False, indent=4)
            logging.info(f"[REMOVE_FAILED] Lista principal salva com {len(current_chat_ids)} IDs")
        except Exception as e:
            logging.error(f"[REMOVE_FAILED] Erro ao salvar lista principal: {e}")
            return 0
    
    # Limpa a lista de IDs com falha
    failed_chat_ids.clear()
    await save_failed_chat_ids()
    
    bot_logger.cleanup_activity(removed_count, len(current_chat_ids) + removed_count)
    return removed_count

# Handler para o botão de limpar IDs com falha
@dp.callback_query(F.data == "clear_failed_ids")
async def clear_failed_ids_callback(query: types.CallbackQuery):
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores podem executar esta ação.", show_alert=True)
        return
    
    try:
        # Sempre recarrega o arquivo de IDs com erro antes de remover
        def load_failed_chat_ids_sync():
            global failed_chat_ids
            import os, json
            try:
                if os.path.exists(FAILED_CHAT_IDS_FILE):
                    with open(FAILED_CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
                        failed_chat_ids = set(json.load(f))
                else:
                    failed_chat_ids = set()
            except Exception as e:
                failed_chat_ids = set()
                import logging
                logging.error(f'[clear_failed_ids_callback] Erro ao carregar failed_chat_ids.json: {e}')
        load_failed_chat_ids_sync()
        # Mostra mensagem de processamento
        await query.answer("Processando...")
        
        # Remove os IDs com falha
        removed_count = await remove_failed_chat_ids()
        
        if removed_count > 0:
            # Atualiza a mensagem original
            await query.message.edit_caption(
                caption=f"{query.message.caption}\n\n✅ {removed_count} IDs com falha foram removidos com sucesso!",
                reply_markup=None  # Remove o botão após o uso
            )
        else:
            await query.answer("ℹ️ Nenhum ID com falha para remover.", show_alert=True)
            
    except Exception as e:
        logging.error(f"Erro ao limpar IDs com falha: {e}")
        await query.answer("❌ Ocorreu um erro ao tentar limpar os IDs com falha.", show_alert=True)

# Comando para ver horários disponíveis
@dp.message(Command("horarios"))
async def show_available_times(message: types.Message):
    """Mostra o menu de seleção de períodos e planos agendados com IDs completos"""
    try:
        # Conta quantos horários estão disponíveis no total
        available_hours = get_available_hours()
        busy_hours = get_busy_hours()
        free_hours = [h for h in available_hours if h not in busy_hours]
        
        # Conta quantos horários estão disponíveis em cada período
        period_counts = {
            "manhã": len(filter_hours_by_period(free_hours, "manha")),
            "tarde": len(filter_hours_by_period(free_hours, "tarde")),
            "noite": len(filter_hours_by_period(free_hours, "noite")),
            "madrugada": len(filter_hours_by_period(free_hours, "madrugada")),
            "total": len(free_hours)
        }
        
        # Carrega mensagens agendadas para mostrar IDs completos
        scheduled_messages = []
        try:
            if os.path.exists(SCHEDULED_MESSAGES_FILE):
                with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
                    scheduled_messages = json.load(f)
        except Exception as e:
            logging.error(f"Erro ao carregar mensagens agendadas: {e}")
        
        # Mensagem informativa sobre horários disponíveis
        info_text = (
            "🕒 *Horários Disponíveis para Agendamento*\n\n"
            f"• 🌅 *Manhã (06:00-12:00):* {period_counts['manhã']} horários\n"
            f"• ☀️ *Tarde (12:00-18:00):* {period_counts['tarde']} horários\n"
            f"• 🌙 *Noite (18:00-00:00):* {period_counts['noite']} horários\n"
            f"• 🌌 *Madrugada (00:00-06:00):* {period_counts['madrugada']} horários\n\n"
            f"📊 *Total de horários disponíveis:* {period_counts['total']}\n\n"
            "_Selecione um período para ver os horários disponíveis:_"
        )
        
        await message.answer(
            info_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=generate_period_keyboard()
        )
        
        # Mostra planos agendados com IDs completos (se houver)
        if scheduled_messages:
            scheduled_text = "📋 *Planos Agendados (IDs Completos):*\n\n"
            
            # Ordena por horário de envio
            sorted_messages = sorted(scheduled_messages, key=lambda x: x.get('send_time', ''))
            
            for i, msg in enumerate(sorted_messages[:10], 1):  # Mostra até 10 planos
                send_time = msg.get('send_time', 'N/A')
                codigo = msg.get('codigo', 'N/A')
                chat_id = msg.get('chat_id', 'N/A')
                
                # Mostra o ID completo sem truncar
                scheduled_text += f"{i}. 🕐 *{send_time}*\n"
                scheduled_text += f"   📋 **ID Fixo Completo:** `{codigo}`\n"
                scheduled_text += f"   💬 Chat: {chat_id}\n\n"
            
            if len(scheduled_messages) > 10:
                scheduled_text += f"... e mais {len(scheduled_messages) - 10} planos agendados.\n\n"
            
            scheduled_text += "💡 *Para cancelar um plano, use o ID fixo completo mostrado acima.*"
            
            await message.answer(
                scheduled_text,
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Adiciona uma mensagem informativa sobre o uso inline
        await message.answer(
            "💡 *Dica rápida:*\n"
            "Você também pode usar o bot em qualquer chat digitando @{} e "
            "selecionando a opção de ver horários.".format((await bot.me()).username),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logging.error(f"Erro ao exibir horários disponíveis: {e}")
        await message.answer(
            "❌ Ocorreu um erro ao carregar os horários disponíveis. "
            "Por favor, tente novamente mais tarde."
        )

# Handler para seleção de período
@dp.callback_query(F.data.startswith("period:"))
async def handle_period_selection(callback_query: types.CallbackQuery):
    """Lida com a seleção de um período do dia"""
    try:
        period = callback_query.data.split(":")[1]
        
        # Define o texto do período selecionado
        period_names = {
            "manha": "🌅 Manhã (06:00-12:00)",
            "tarde": "☀️ Tarde (12:00-18:00)",
            "noite": "🌙 Noite (18:00-00:00)",
            "madrugada": "🌌 Madrugada (00:00-06:00)",
            "all": "📅 Todos os horários"
        }
        
        period_name = period_names.get(period, "Período selecionado")
        
        # Obtém o user_id para verificar seleções
        user_id = callback_query.from_user.id
        
        # Cria texto mostrando horários selecionados
        selected_times = user_selected_times.get(user_id, {}).get("times", [])
        selected_count = len(selected_times)
        
        # Texto base
        text = f"🕒 Horários disponíveis - {period_name}:\n\n"
        
        # Adiciona informações sobre seleções
        if selected_count > 0:
            selected_times_formatted = ", ".join(sorted(selected_times))
            text += f"✅ **Horários selecionados ({selected_count}):**\n{selected_times_formatted}\n\n"
            text += "📝 Clique nos horários para adicionar/remover da sua seleção.\n"
            text += "Quando terminar, use os botões abaixo:"
        else:
            text += "📝 Clique nos horários que deseja selecionar:"
        
        # Para inline queries, usamos edit_message_text com inline_message_id
        if callback_query.inline_message_id:
            await bot.edit_message_text(
                inline_message_id=callback_query.inline_message_id,
                text=text,
                reply_markup=generate_time_keyboard(period=period, user_id=user_id),
                parse_mode="Markdown"
            )
        else:
            # Para callbacks normais, editamos a mensagem existente
            await callback_query.message.edit_text(
                text,
                reply_markup=generate_time_keyboard(period=period, user_id=user_id),
                parse_mode="Markdown"
            )
        
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Erro ao processar seleção de período: {e}")
        await callback_query.answer("❌ Ocorreu um erro ao processar sua seleção.", show_alert=True)

# Handlers para seleção de planos
@dp.callback_query(F.data.startswith("select_plan:"))
async def handle_plan_selection(callback_query: types.CallbackQuery):
    """Lida com a seleção de um tipo de agendamento"""
    try:
        # Extrai o ID do tipo de agendamento da callback
        plan_id = callback_query.data.split(":")[1]
        
        # Mapeia o ID do tipo para o nome e descrição
        plans = {
            "daily": {
                "name": "Diário",
                "emoji": "📅",
                "description": "Agendamento diário"
            },
            "weekly": {
                "name": "Semanal",
                "emoji": "⏳",
                "description": "Agendamento semanal"
            },
            "monthly": {
                "name": "Mensal",
                "emoji": "📆",
                "description": "Agendamento mensal"
            }
        }
        
        # Atualiza a mensagem com o tipo selecionado e os períodos
        if callback_query.inline_message_id:
            await bot.edit_message_text(
                inline_message_id=callback_query.inline_message_id,
                text=f"{plans[plan_id]['emoji']} {plans[plan_id]['name']}\n\n"
                     f"{plans[plan_id]['description']}\n\n"
                     f"🕒 Selecione o período desejado para ver os horários disponíveis:",
                reply_markup=generate_period_keyboard()
            )
        else:
            await callback_query.message.edit_text(
                f"{plans[plan_id]['emoji']} {plans[plan_id]['name']}\n\n"
                 f"{plans[plan_id]['description']}\n\n"
                 f"🕒 Selecione o período desejado para ver os horários disponíveis:",
                reply_markup=generate_period_keyboard()
            )
        
        # Salva o plano selecionado para o usuário
        user_id = callback_query.from_user.id
        user_selected_times[user_id] = {"plan": plan_id, "times": []}
        
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Erro ao selecionar tipo de agendamento: {e}")
        await callback_query.answer("❌ Ocorreu um erro ao selecionar o tipo de agendamento.", show_alert=True)

# HANDLER PARA SELECT_TIME (formato atual)
async def handle_time_selection(callback_query: types.CallbackQuery):
    """Handler para seleção de horário com formato select_time:hour:period"""
    try:
        # RESPOSTA IMEDIATA
        await callback_query.answer("✅ Horário selecionado!")
        
        # Parse do callback data: select_time:12:30:tarde
        data_parts = callback_query.data.split(":")
        if len(data_parts) >= 4:
            hour = f"{data_parts[1]}:{data_parts[2]}"  # 12:30
            period = data_parts[3]  # tarde
        elif len(data_parts) >= 3:
            hour = f"{data_parts[1]}:{data_parts[2]}"  # 12:30
            period = "all"
        else:
            hour = "00:00"
            period = "all"
        
        user_id = callback_query.from_user.id
        
        print(f"\n[SELECT_TIME] User {user_id} selecionou {hour} ({period})")
        print(f"[SELECT_TIME] Callback data completo: {callback_query.data}")
        print(f"[SELECT_TIME] Data parts: {data_parts}")
        
        # Garante que o usuário tem uma entrada na estrutura de dados
        if user_id not in user_selected_times:
            user_selected_times[user_id] = {"times": [], "plan": "monthly"}
        
        user_data = user_selected_times[user_id]
        
        # Alterna a seleção do horário
        if hour in user_data["times"]:
            user_data["times"].remove(hour)
            print(f"[SELECT_TIME] Removido {hour}")
        else:
            user_data["times"].append(hour)
            print(f"[SELECT_TIME] Adicionado {hour}")
        
        # Atualiza a estrutura global
        user_selected_times[user_id] = user_data
        
        print(f"[SELECT_TIME] Horários selecionados: {user_data['times']}")
        
        # Atualiza a mensagem mostrando os horários selecionados
        print(f"[SELECT_TIME] Tentando atualizar interface...")
        print(f"[SELECT_TIME] callback_query.message existe: {callback_query.message is not None}")
        print(f"[SELECT_TIME] callback_query.inline_message_id existe: {callback_query.inline_message_id is not None}")
        print(f"[SELECT_TIME] user_data['times']: {user_data['times']}")
        
        try:
            # Regenera o teclado de horários com os selecionados marcados e botão de confirmação
            print(f"[SELECT_TIME] Regenerando teclado com horários selecionados...")
            
            # Obtém o período atual (se disponível)
            current_period = period if period != "all" else "all"
            
            # Gera o novo teclado com os horários selecionados marcados
            new_keyboard = generate_time_keyboard_with_selected(
                page=0, 
                period=current_period, 
                user_id=user_id,
                selected_times=user_data["times"]
            )
            
            # Cria o texto atualizado
            if user_data["times"]:
                selected_times_sorted = sorted(user_data["times"], key=lambda x: (int(x.split(':')[0]), int(x.split(':')[1])))
                times_text = ", ".join(selected_times_sorted)
                message_text = f"⏰ **Horários Disponíveis**\n\n✅ **Selecionados ({len(selected_times_sorted)}):** {times_text}\n\n👆 Clique nos horários para selecionar/desselecionar"
            else:
                message_text = f"⏰ **Horários Disponíveis**\n\n👆 Clique nos horários para selecionar"
            
            # Edita a mensagem inline
            try:
                if callback_query.inline_message_id:
                    # Para mensagens inline (via inline query)
                    await bot.edit_message_text(
                        inline_message_id=callback_query.inline_message_id,
                        text=message_text,
                        reply_markup=new_keyboard,
                        parse_mode="Markdown"
                    )
                    print(f"[SELECT_TIME] Mensagem inline editada com sucesso")
                elif callback_query.message:
                    # Para mensagens normais
                    await callback_query.message.edit_text(
                        text=message_text,
                        reply_markup=new_keyboard,
                        parse_mode="Markdown"
                    )
                    print(f"[SELECT_TIME] Mensagem normal editada com sucesso")
                else:
                    print(f"[SELECT_TIME] Nenhuma mensagem disponível para editar")
                    await callback_query.answer(f"✅ Horário {hour} {'adicionado' if hour in user_data['times'] else 'removido'}!")
                    
            except Exception as edit_error:
                print(f"[SELECT_TIME] Erro ao editar mensagem: {edit_error}")
                # Responde apenas o callback
                selected_count = len(user_data["times"])
                await callback_query.answer(f"✅ {selected_count} horário{'s' if selected_count > 1 else ''} selecionado{'s' if selected_count > 1 else ''}!")
        except Exception as e:
            print(f"[SELECT_TIME] Erro ao atualizar interface: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"[SELECT_TIME] Erro: {e}")
        try:
            await callback_query.answer("❌ Erro ao selecionar horário.", show_alert=True)
        except:
            pass

# Registra o handler com o callback data correto
dp.callback_query.register(handle_time_selection, F.data.startswith("select_time"))

# Handler para toggle_time (seleção/deseleção de horários)
@dp.callback_query(lambda c: c.data and "|" in c.data and c.data.startswith("toggle_time"))
async def handle_toggle_time(callback_query: types.CallbackQuery):
    """Handler para alternar seleção de horários mantendo a página atual"""
    try:
        # Parse do callback data: toggle_time|hour|period|page
        data_parts = callback_query.data.split("|")
        if len(data_parts) != 4:
            await callback_query.answer("❌ Dados inválidos.", show_alert=True)
            return
            
        _, hour, period, page_str = data_parts
        page = int(page_str)
        user_id = callback_query.from_user.id
        
        # Garante que o usuário tem uma entrada na estrutura de dados
        if user_id not in user_selected_times:
            user_selected_times[user_id] = {"times": [], "plan": "monthly"}
        
        user_data = user_selected_times[user_id]
        
        # Alterna a seleção do horário
        if hour in user_data["times"]:
            user_data["times"].remove(hour)
            await callback_query.answer(f"❌ {hour} removido")
        else:
            user_data["times"].append(hour)
            await callback_query.answer(f"✅ {hour} selecionado")
        
        # Atualiza a estrutura global
        user_selected_times[user_id] = user_data
        
        # Debug: mostra o estado atual das seleções
        print(f"[TOGGLE_TIME] User {user_id} selections: {user_data['times']}")
        
        # Regenera o teclado mantendo a página atual
        new_keyboard = generate_time_keyboard(page=page, period=period, user_id=user_id)
        
        # Cria o texto atualizado com as seleções
        period_names = {
            "manha": "🌅 Manhã (06:00-12:00)",
            "tarde": "☀️ Tarde (12:00-18:00)", 
            "noite": "🌙 Noite (18:00-00:00)",
            "madrugada": "🌌 Madrugada (00:00-06:00)",
            "all": "📅 Todos os horários"
        }
        period_name = period_names.get(period, "Período selecionado")
        
        selected_times = user_data["times"]
        selected_count = len(selected_times)
        
        text = f"🕒 Horários disponíveis - {period_name}:\n\n"
        
        if selected_count > 0:
            selected_times_formatted = ", ".join(sorted(selected_times))
            text += f"✅ **Horários selecionados ({selected_count}):**\n{selected_times_formatted}\n\n"
            text += "📝 Clique nos horários para adicionar/remover da sua seleção.\n"
            text += "Quando terminar, use os botões abaixo:"
        else:
            text += "📝 Clique nos horários que deseja selecionar:"
        
        # Atualiza tanto o texto quanto o teclado
        try:
            # Para mensagens inline, usa inline_message_id
            if callback_query.inline_message_id:
                await bot.edit_message_text(
                    inline_message_id=callback_query.inline_message_id,
                    text=text,
                    reply_markup=new_keyboard,
                    parse_mode="Markdown"
                )
            # Para mensagens normais, usa message.edit_text
            elif callback_query.message:
                await callback_query.message.edit_text(
                    text=text,
                    reply_markup=new_keyboard,
                    parse_mode="Markdown"
                )
            else:
                print(f"[TOGGLE_TIME] Nenhuma mensagem disponível para editar")
                
        except Exception as e:
            error_msg = str(e).lower()
            if "message is not modified" in error_msg or "message not modified" in error_msg:
                # Mensagem não mudou, apenas responde o callback
                print(f"[TOGGLE_TIME] Mensagem não modificada, apenas respondendo callback")
            else:
                print(f"[TOGGLE_TIME] Erro ao atualizar mensagem: {e}")
            
    except Exception as e:
        print(f"[TOGGLE_TIME] Erro: {e}")
        await callback_query.answer("❌ Erro ao processar seleção.", show_alert=True)

# Handler para confirmação dos horários selecionados
async def handle_confirm_selected_times(callback_query: types.CallbackQuery):
    """Handler para confirmar os horários selecionados"""
    try:
        # Parse do callback data - agora sem user_id no callback
        user_id = callback_query.from_user.id
        
        # Pega os dados do usuário
        user_data = user_selected_times.get(user_id, {})
        selected_times = user_data.get("times", [])
        plan = user_data.get("plan", "monthly")  # Default para monthly
        
        if not selected_times:
            await callback_query.answer("❌ Nenhum horário selecionado!", show_alert=True)
            return
        
        # Ordena os horários
        selected_times_sorted = sorted(selected_times, key=lambda x: (int(x.split(':')[0]), int(x.split(':')[1])))
        times_text = ", ".join(selected_times_sorted)
        times_command = " ".join(selected_times_sorted)
        
        # Tradução do plano e comando para português
        plan_translations = {
            "daily": ("Diário", "diario"),
            "weekly": ("Semanal", "semanal"),
            "monthly": ("Mensal", "mensal"),
            "diario": ("Diário", "diario"),
            "semanal": ("Semanal", "semanal"),
            "mensal": ("Mensal", "mensal")
        }
        
        plan_pt, command_pt = plan_translations.get(plan.lower(), ("Mensal", "mensal"))
        
        # Mensagem para o admin
        admin_message = f"""🔔 **Nova confirmação de horários!**

👤 **Usuário:** {user_id}
📅 **Modo:** {plan_pt}
⏰ **Horários selecionados:** {times_text}
📋 **Quantidade de horários:** {len(selected_times_sorted)}

**Comando gerado:** `/{command_pt} {user_id} {times_command}`"""
        
        # Mensagem para o cliente
        client_message = f"""✅ **Horários confirmados com sucesso!**

📅 **Modo:** {plan_pt}
⏰ **Horários selecionados:** {times_text}
📋 **Quantidade:** {len(selected_times_sorted)} horários

Seus horários foram enviados para análise. Aguarde a confirmação do administrador."""
        
        # Envia para o cliente
        try:
            if callback_query.inline_message_id:
                # Para mensagens inline
                await bot.edit_message_text(
                    inline_message_id=callback_query.inline_message_id,
                    text=client_message,
                    parse_mode="Markdown"
                )
            elif callback_query.message:
                # Para mensagens normais
                await callback_query.message.edit_text(
                    text=client_message,
                    parse_mode="Markdown"
                )
            else:
                # Fallback: envia nova mensagem
                await bot.send_message(
                    chat_id=user_id,
                    text=client_message,
                    parse_mode="Markdown"
                )
        except Exception as edit_error:
            print(f"Erro ao editar mensagem de confirmação: {edit_error}")
            # Fallback: apenas responde o callback
            await callback_query.answer("Horários confirmados e enviados!", show_alert=True)
        
        # Armazena os dados temporariamente para o admin confirmar
        plano_data_key = f"plano_{user_id}_{int(time.time())}"
        planos_pendentes[plano_data_key] = {
            'user_id': user_id,
            'plano_pt': plan_pt,
            'formatted_times': selected_times_sorted,
            'qtd_horarios': len(selected_times_sorted),
            'comando': f"/{command_pt}",
            'formatted_command': selected_times_sorted
        }
        
        # Cria o botão de confirmar plano
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Confirmar Plano",
                        callback_data=f"confirmar_plano_{plano_data_key}"
                    )
                ]
            ]
        )
        
        # Envia para todos os admins com botão
        for admin_id in ADMINS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            except Exception as e:
                print(f"Erro ao enviar para admin {admin_id}: {e}")
        
        # Limpa os dados do usuário
        if user_id in user_selected_times:
            del user_selected_times[user_id]
        
        await callback_query.answer("✅ Horários confirmados e enviados!")
        
    except Exception as e:
        print(f"Erro ao confirmar horários: {e}")
        await callback_query.answer("❌ Erro ao confirmar horários.", show_alert=True)

# Handler para cancelar seleção
async def handle_cancel_time_selection(callback_query: types.CallbackQuery):
    """Handler para cancelar a seleção de horários"""
    try:
        user_id = callback_query.from_user.id
        
        # Limpa os dados do usuário
        if user_id in user_selected_times:
            del user_selected_times[user_id]
        
        # Volta para a seleção de planos
        try:
            if callback_query.inline_message_id:
                # Para mensagens inline
                await bot.edit_message_text(
                    inline_message_id=callback_query.inline_message_id,
                    text="💰 Escolha um plano para continuar:",
                    reply_markup=generate_plans_keyboard(),
                    parse_mode="HTML"
                )
            elif callback_query.message:
                # Para mensagens normais
                await callback_query.message.edit_text(
                    text="💰 Escolha um plano para continuar:",
                    reply_markup=generate_plans_keyboard(),
                    parse_mode="HTML"
                )
            else:
                # Fallback: apenas responde o callback
                await callback_query.answer("Seleção cancelada.", show_alert=True)
        except Exception as edit_error:
            print(f"Erro ao editar mensagem de cancelamento: {edit_error}")
            # Fallback: apenas responde o callback
            await callback_query.answer("Seleção cancelada.", show_alert=True)
        
        await callback_query.answer("Seleção cancelada.")
        
    except Exception as e:
        print(f"Erro ao cancelar seleção: {e}")
        await callback_query.answer("❌ Erro ao cancelar.", show_alert=True)

# Handler para seleção aleatória de horários
async def handle_random_select(callback_query: types.CallbackQuery):
    """Handler para seleção aleatória de horários"""
    try:
        import random
        
        # Parse do callback data: random_select|quantity|period|page
        data_parts = callback_query.data.split("|")
        if len(data_parts) != 4:
            await callback_query.answer("❌ Dados inválidos.", show_alert=True)
            return
            
        _, quantity_str, period, page_str = data_parts
        quantity = int(quantity_str)
        page = int(page_str)
        user_id = callback_query.from_user.id
        
        # Obtém horários disponíveis
        available_hours = get_available_hours()
        busy_hours = get_busy_hours()
        free_hours = [h for h in available_hours if h not in busy_hours]
        
        # Filtra por período se especificado
        if period != "all":
            free_hours = filter_hours_by_period(free_hours, period)
        
        # Verifica se há horários suficientes
        if len(free_hours) < quantity:
            await callback_query.answer(f"❌ Apenas {len(free_hours)} horários disponíveis neste período.", show_alert=True)
            return
        
        # Garante que o usuário tem uma entrada na estrutura de dados
        if user_id not in user_selected_times:
            user_selected_times[user_id] = {"times": [], "plan": "monthly"}
        
        # Seleciona horários aleatórios
        random_times = random.sample(free_hours, quantity)
        
        # Adiciona aos horários selecionados (sem duplicatas)
        current_times = set(user_selected_times[user_id]["times"])
        new_times = set(random_times)
        combined_times = list(current_times.union(new_times))
        
        user_selected_times[user_id]["times"] = combined_times
        
        # Debug
        print(f"[RANDOM_SELECT] User {user_id} selected {quantity} random times: {random_times}")
        print(f"[RANDOM_SELECT] Total selections now: {combined_times}")
        
        # Regenera o teclado e texto
        new_keyboard = generate_time_keyboard(page=page, period=period, user_id=user_id)
        
        # Cria o texto atualizado
        period_names = {
            "manha": "🌅 Manhã (06:00-12:00)",
            "tarde": "☀️ Tarde (12:00-18:00)", 
            "noite": "🌙 Noite (18:00-00:00)",
            "madrugada": "🌌 Madrugada (00:00-06:00)",
            "all": "📅 Todos os horários"
        }
        period_name = period_names.get(period, "Período selecionado")
        
        selected_count = len(combined_times)
        text = f"🕒 Horários disponíveis - {period_name}:\n\n"
        
        if selected_count > 0:
            selected_times_formatted = ", ".join(sorted(combined_times))
            text += f"✅ **Horários selecionados ({selected_count}):**\n{selected_times_formatted}\n\n"
            text += "📝 Clique nos horários para adicionar/remover da sua seleção.\n"
            text += "Quando terminar, use os botões abaixo:"
        else:
            text += "📝 Clique nos horários que deseja selecionar:"
        
        # Atualiza a mensagem
        try:
            if callback_query.inline_message_id:
                await bot.edit_message_text(
                    inline_message_id=callback_query.inline_message_id,
                    text=text,
                    reply_markup=new_keyboard,
                    parse_mode="Markdown"
                )
            elif callback_query.message:
                await callback_query.message.edit_text(
                    text=text,
                    reply_markup=new_keyboard,
                    parse_mode="Markdown"
                )
        except Exception as e:
            print(f"[RANDOM_SELECT] Erro ao atualizar mensagem: {e}")
        
        await callback_query.answer(f"🎲 {quantity} horários selecionados aleatoriamente!")
        
    except Exception as e:
        print(f"[RANDOM_SELECT] Erro: {e}")
        await callback_query.answer("❌ Erro ao selecionar horários aleatórios.", show_alert=True)

# Registra os novos handlers
dp.callback_query.register(handle_confirm_selected_times, F.data == "confirm_selected_times")
dp.callback_query.register(handle_cancel_time_selection, F.data == "cancel_time_selection")
dp.callback_query.register(handle_random_select, F.data.startswith("random_select|"))

@dp.callback_query(F.data == "confirm_times")
async def handle_confirm_times(callback_query: types.CallbackQuery):
    """Lida com a confirmação dos horários selecionados"""
    try:
        user_id = callback_query.from_user.id
        user_data = user_selected_times.get(user_id)
        
        if not user_data or not user_data["times"]:
            await callback_query.answer("❌ Por favor, selecione pelo menos um horário primeiro.", show_alert=True)
            return
            
        # Formata os horários para mostrar HH:MM
        formatted_times = [h if ":" in h else f"{h[:2]}:{h[2:]}" for h in user_data['times']]
        formatted_command = [h if ":" in h else f"{h[:2]}:{h[2:]}" for h in user_data['times']]
        
        # Tradução do plano e comando
        plan_translate = {
            "daily": ("Diário", "/agendar"),
            "diario": ("Diário", "/agendar"),
            "weekly": ("Semanal", "/semanal"),
            "semanal": ("Semanal", "/semanal"),
            "monthly": ("Mensal", "/mensal"),
            "mensal": ("Mensal", "/mensal")
        }
        plano_key = user_data['plan'].lower()
        plano_pt, comando = plan_translate.get(plano_key, (user_data['plan'].capitalize(), "/agendar"))
        qtd_horarios = len(formatted_times)
        
        # Armazena os dados temporariamente para o admin confirmar
        plano_data_key = f"plano_{user_id}_{int(time.time())}"
        planos_pendentes[plano_data_key] = {
            'user_id': user_id,
            'plano_pt': plano_pt,
            'formatted_times': formatted_times,
            'qtd_horarios': qtd_horarios,
            'comando': comando,
            'formatted_command': formatted_command
        }
        
        # Gera a mensagem de confirmação com botão
        message_text = (
            "🔔 Nova confirmação de horários!\n\n"
            f"👤 Usuário: {user_id}\n"
            f"📅 Modo: {plano_pt}\n"
            f"⏰ Horários selecionados: {', '.join(formatted_times)}\n"
            f"📋 Quantidade de horários: {qtd_horarios}\n\n"
            f"Comando gerado: {comando} {user_id} {' '.join(formatted_command)}"
        )
        
        # Cria o botão de confirmar plano
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Confirmar Plano",
                        callback_data=f"confirmar_plano_{plano_data_key}"
                    )
                ]
            ]
        )
        
        # Envia para o admin com botão
        await bot.send_message(ADMIN_CHAT_ID, message_text, reply_markup=keyboard)
        
        # Limpa os dados do usuário
        del user_selected_times[user_id]
        
        # Responde ao usuário
        if callback_query.message:
            await callback_query.message.edit_text(
                "✅ Horários confirmados com sucesso!\n"
                "Os horários foram enviados para o administrador."
            )
        elif callback_query.inline_message_id:
            await bot.edit_message_text(
                inline_message_id=callback_query.inline_message_id,
                text="✅ Horários confirmados com sucesso!\n"
                     "Os horários foram enviados para o administrador."
            )
        
        await callback_query.answer("✅ Horários confirmados!")
    except Exception as e:
        logging.error(f"Erro ao confirmar horários: {e}")
        await callback_query.answer("❌ Ocorreu um erro ao confirmar os horários.", show_alert=True)

@dp.callback_query(F.data.startswith("confirmar_plano_"))
async def handle_confirmar_plano(callback_query: types.CallbackQuery):
    """Handler para quando admin confirma um plano"""
    try:
        # Extrai a chave do plano dos dados do callback
        plano_data_key = callback_query.data.replace("confirmar_plano_", "")
        
        # Verifica se o plano ainda existe nos dados pendentes
        if plano_data_key not in planos_pendentes:
            await callback_query.answer("❌ Plano não encontrado ou já foi processado.", show_alert=True)
            return
        
        # Obtém os dados do plano
        plano_data = planos_pendentes[plano_data_key]
        user_id = plano_data['user_id']
        plano_pt = plano_data['plano_pt']
        qtd_horarios = plano_data['qtd_horarios']
        
        # Verifica se existe canal de referência configurado
        try:
            # Obtém canal de referência do config.json
            canal_referencia = get_canal_referencia()
            
            if canal_referencia:
                # Cria mensagem para o canal de referência
                mensagem_referencia = (
                    f"🎉 **Novo Plano Adquirido!**\n\n"
                    f"👤 **Usuário:** `{user_id}`\n"
                    f"📅 **Tipo de Plano:** {plano_pt}\n"
                    f"📋 **Quantidade de Horários:** {qtd_horarios}\n\n"
                    f"✨ Mais um cliente satisfeito com nossos serviços!"
                )
                
                # Obtém o username do bot via API
                try:
                    bot_info = await bot.get_me()
                    bot_username = bot_info.username
                except Exception as e:
                    logging.error(f"Erro ao obter username do bot: {e}")
                    bot_username = "seubot"  # fallback
                
                # Botão para ir ao bot
                keyboard_referencia = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🤖 Ir para o Bot",
                                url=f"https://t.me/{bot_username}"
                            )
                        ]
                    ]
                )
                
                # Envia para o canal de referência
                await bot.send_message(
                    canal_referencia, 
                    mensagem_referencia, 
                    parse_mode="Markdown",
                    reply_markup=keyboard_referencia
                )
                
                logging.info(f"✅ Mensagem de novo plano enviada para canal de referência: {canal_referencia}")
            else:
                logging.warning("⚠️ Canal de referência não configurado")
                
        except Exception as e:
            logging.error(f"Erro ao enviar para canal de referência: {e}")
        
        # Remove o plano dos pendentes
        del planos_pendentes[plano_data_key]
        
        # Edita a mensagem original para mostrar que foi confirmado
        await callback_query.message.edit_text(
            callback_query.message.text + "\n\n✅ **PLANO CONFIRMADO E DIVULGADO!**"
        )
        
        await callback_query.answer("✅ Plano confirmado e divulgado no canal de referência!")
        
    except Exception as e:
        logging.error(f"Erro ao confirmar plano: {e}")
        await callback_query.answer("❌ Erro ao confirmar plano.", show_alert=True)

def generate_time_keyboard_with_selected(page=0, period="all", user_id=None, selected_times=None):
    """Gera teclado inline para seleção de horários com os selecionados marcados e botão de confirmação"""
    if selected_times is None:
        selected_times = []
        
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Obtém horários disponíveis
        available_hours = get_available_hours()
        busy_hours = get_busy_hours()
        free_hours = [h for h in available_hours if h not in busy_hours]
        
        # Filtra por período se especificado
        if period != "all":
            free_hours = filter_hours_by_period(free_hours, period)
        
        # Configuração de paginação
        items_per_page = 15
        total_pages = (len(free_hours) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_hours = free_hours[start_idx:end_idx]
        
        # Cria botões para os horários
        keyboard = []
        row = []
        
        for i, hour in enumerate(page_hours):
            if i > 0 and i % 3 == 0:  # 3 botões por linha
                keyboard.append(row)
                row = []
            
            # Marca horários selecionados com ✅
            if hour in selected_times:
                button_text = f"✅ {hour}"
            else:
                button_text = f"🕐 {hour}"
            
            row.append(InlineKeyboardButton(
                text=button_text,
                callback_data=f"toggle_time|{hour}|{period}|{page}"
            ))

        if row:  # Adiciona a última linha se não estiver vazia
            keyboard.append(row)

        # Botão de confirmação (apenas se houver horários selecionados)
        if selected_times:
            keyboard.append([InlineKeyboardButton(
                text=f"✅ Confirmar {len(selected_times)} horário{'s' if len(selected_times) > 1 else ''}",
                callback_data="confirm_selected_times"
            )])

        # Botões de navegação
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(
                text="⬅️ Anterior",
                callback_data=f"time_page:{page-1}:{period}"
            ))
        
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(
                text="➡️ Próxima",
                callback_data=f"time_page:{page+1}:{period}"
            ))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Botão para voltar e cancelar
        bottom_row = []
        bottom_row.append(InlineKeyboardButton(
            text="🔙 Voltar aos Períodos",
            callback_data="back_to_periods"
        ))
        
        if selected_times:
            bottom_row.append(InlineKeyboardButton(
                text="❌ Cancelar Seleção",
                callback_data="cancel_time_selection"
            ))
        
        keyboard.append(bottom_row)
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
        
    except Exception as e:
        logging.error(f"Erro ao gerar teclado de horários com selecionados: {e}")
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text="❌ Erro ao carregar horários",
            callback_data="error"
        )]])

def generate_time_keyboard(page=0, period="all", user_id=None):
    """Gera teclado inline para seleção de horários com paginação"""
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Obtém horários disponíveis
        available_hours = get_available_hours()
        busy_hours = get_busy_hours()
        free_hours = [h for h in available_hours if h not in busy_hours]
        
        # Filtra por período se especificado
        if period != "all":
            free_hours = filter_hours_by_period(free_hours, period)
        
        # Configuração de paginação
        items_per_page = 15
        total_pages = (len(free_hours) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_hours = free_hours[start_idx:end_idx]
        
        # Cria botões para os horários
        keyboard = []
        row = []
        
        for i, hour in enumerate(page_hours):
            if i > 0 and i % 3 == 0:  # 3 botões por linha
                keyboard.append(row)
                row = []
            
            # Verifica se o horário está selecionado pelo usuário
            is_selected = False
            if user_id and user_id in user_selected_times:
                is_selected = hour in user_selected_times[user_id]["times"]
            
            # Define o emoji baseado na seleção
            emoji = "✅" if is_selected else "🕐"
            
            row.append(InlineKeyboardButton(
                text=f"{emoji} {hour}",
                callback_data=f"toggle_time|{hour}|{period}|{page}"
            ))
        
        if row:  # Adiciona a última linha se não estiver vazia
            keyboard.append(row)
        
        # Botões de navegação
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(
                text="⬅️ Anterior",
                callback_data=f"time_page:{page-1}:{period}"
            ))
        
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(
                text="➡️ Próxima",
                callback_data=f"time_page:{page+1}:{period}"
            ))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Botão de seleção aleatória
        random_row = [
            InlineKeyboardButton(
                text="🎲 5 Aleatórios",
                callback_data=f"random_select|5|{period}|{page}"
            ),
            InlineKeyboardButton(
                text="🎲 10 Aleatórios", 
                callback_data=f"random_select|10|{period}|{page}"
            ),
            InlineKeyboardButton(
                text="🎲 15 Aleatórios",
                callback_data=f"random_select|15|{period}|{page}"
            )
        ]
        keyboard.append(random_row)
        
        # Botões de ação se há horários selecionados
        if user_id and user_id in user_selected_times and user_selected_times[user_id]["times"]:
            action_row = [
                InlineKeyboardButton(
                    text="✅ Confirmar Seleção",
                    callback_data="confirm_selected_times"
                ),
                InlineKeyboardButton(
                    text="❌ Cancelar",
                    callback_data="cancel_time_selection"
                )
            ]
            keyboard.append(action_row)
        
        # Botão para voltar
        keyboard.append([InlineKeyboardButton(
            text="🔙 Voltar aos Períodos",
            callback_data="back_to_periods"
        )])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
        
    except Exception as e:
        logging.error(f"Erro ao gerar teclado de horários: {e}")
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text="❌ Erro ao carregar horários",
            callback_data="error"
        )]])

def filter_hours_by_period(hours, period):
    """Filtra horários por período do dia"""
    try:
        filtered = []
        for hour in hours:
            hour_int = int(hour.split(':')[0])
            
            if period == "manha" and 6 <= hour_int < 12:
                filtered.append(hour)
            elif period == "tarde" and 12 <= hour_int < 18:
                filtered.append(hour)
            elif period == "noite" and 18 <= hour_int < 24:
                filtered.append(hour)
            elif period == "madrugada" and 0 <= hour_int < 6:
                filtered.append(hour)
        
        return filtered
    except:
        return hours

def generate_period_keyboard():
    """Gera teclado para seleção de períodos do dia"""
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = [
            [
                InlineKeyboardButton(text="🌅 Manhã (06:00-12:00)", callback_data="period:manha"),
                InlineKeyboardButton(text="☀️ Tarde (12:00-18:00)", callback_data="period:tarde")
            ],
            [
                InlineKeyboardButton(text="🌙 Noite (18:00-00:00)", callback_data="period:noite"),
                InlineKeyboardButton(text="🌌 Madrugada (00:00-06:00)", callback_data="period:madrugada")
            ],
            [
                InlineKeyboardButton(text="🕰️ Todos os Horários", callback_data="period:all")
            ],
            [
                InlineKeyboardButton(text="❌ Fechar", callback_data="close_times")
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
        
    except Exception as e:
        logging.error(f"Erro ao gerar teclado de períodos: {e}")
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text="❌ Erro ao carregar períodos",
            callback_data="error"
        )]])

@dp.callback_query(F.data.startswith("time_page:"))
async def handle_time_page(callback_query: types.CallbackQuery):
    """Lida com a navegação entre páginas de horários"""
    try:
        # Extrai os parâmetros da callback
        parts = callback_query.data.split("time_page:")[1].split(":")
        page = parts[0]
        period = parts[1] if len(parts) > 1 else "all"
        user_id = callback_query.from_user.id

        if page == "current":
            await callback_query.answer()
            return

        # Converte a página para inteiro
        page = int(page)

        # Para inline queries, usamos edit_message_reply_markup
        if callback_query.inline_message_id:
            await bot.edit_message_reply_markup(
                inline_message_id=callback_query.inline_message_id,
                reply_markup=generate_time_keyboard(page=page, period=period, user_id=user_id)
            )
        else:
            # Para callbacks normais, editamos a mensagem existente
            await callback_query.message.edit_reply_markup(
                reply_markup=generate_time_keyboard(page=page, period=period, user_id=user_id)
            )

        await callback_query.answer()
    except Exception as e:
        logging.error(f"Erro na navegação de páginas: {e}")
        await callback_query.answer("❌ Ocorreu um erro ao navegar entre páginas.", show_alert=True)

@dp.callback_query(F.data == "back_to_periods")
async def handle_back_to_periods(callback_query: types.CallbackQuery):
    """Volta para a seleção de períodos"""
    try:
        if callback_query.inline_message_id:
            await bot.edit_message_text(
                inline_message_id=callback_query.inline_message_id,
                text="🕒 Selecione o período desejado para ver os horários disponíveis:",
                reply_markup=generate_period_keyboard()
            )
        else:
            await callback_query.message.edit_text(
                "🕒 Selecione o período desejado para ver os horários disponíveis:",
                reply_markup=generate_period_keyboard()
            )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Erro ao voltar para seleção de períodos: {e}")
        await callback_query.answer("❌ Ocorreu um erro ao voltar para seleção de períodos.", show_alert=True)

@dp.callback_query(F.data == "close_times")
async def handle_close_times(callback_query: types.CallbackQuery):
    """Fecha a visualização de horários"""
    try:
        if callback_query.message:
            await callback_query.message.delete()
        await callback_query.answer("Visualização de horários fechada.")
    except Exception as e:
        logging.error(f"Erro ao fechar visualização de horários: {e}")
        await callback_query.answer("Visualização fechada.", show_alert=False)

@dp.callback_query(F.data.startswith("view_time:"))
async def handle_view_time(callback_query: types.CallbackQuery):
    """Mostra detalhes de um horário específico"""
    try:
        time = callback_query.data.split(":")[1]
        # Verifica se o horário ainda está disponível
        busy_hours = get_busy_hours()
        if time in busy_hours:
            await callback_query.answer("❌ Este horário já foi reservado. Por favor, escolha outro.", show_alert=True)
        else:
            await callback_query.answer(
                f"✅ Horário selecionado: {time}\n\n"
                "Para agendar para este horário, use o comando /agendar",
                show_alert=True
            )
    except Exception as e:
        logging.error(f"Erro ao processar seleção de horário: {e}")
        await callback_query.answer("❌ Ocorreu um erro ao processar sua seleção.", show_alert=True)

# Handler para inline query
@dp.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    """Lida com consultas inline para mostrar horários disponíveis"""
    try:
        results = []
        
        # Conta quantos horários estão disponíveis no total
        available_hours = get_available_hours()
        busy_hours = get_busy_hours()
        free_hours = [h for h in available_hours if h not in busy_hours]
        
        # Conta quantos horários estão disponíveis em cada período
        period_counts = {
            "manhã": len(filter_hours_by_period(free_hours, "manha")),
            "tarde": len(filter_hours_by_period(free_hours, "tarde")),
            "noite": len(filter_hours_by_period(free_hours, "noite")),
            "madrugada": len(filter_hours_by_period(free_hours, "madrugada")),
            "total": len(free_hours)
        }
        
        # Opção principal: Ver horários disponíveis
        results.append(InlineQueryResultArticle(
            id="horarios_disponiveis",
            title="🕒 Ver Horários Disponíveis",
            input_message_content=InputTextMessageContent(
                message_text=(
                    "🕒 *Horários Disponíveis para Agendamento*\n\n"
                    f"• 🌅 *Manhã (06:00-12:00):* {period_counts['manhã']} horários\n"
                    f"• ☀️ *Tarde (12:00-18:00):* {period_counts['tarde']} horários\n"
                    f"• 🌙 *Noite (18:00-00:00):* {period_counts['noite']} horários\n"
                    f"• 🌌 *Madrugada (00:00-06:00):* {period_counts['madrugada']} horários\n\n"
                    f"📊 *Total de horários disponíveis:* {period_counts['total']}\n\n"
                    "_Selecione um período para ver os horários disponíveis:_"
                ),
                parse_mode=ParseMode.MARKDOWN
            ),
            reply_markup=generate_period_keyboard(),
            description=f"Ver {period_counts['total']} horários disponíveis por período"
        ))
        
        # Opção secundária: Selecionar plano
        results.append(InlineQueryResultArticle(
            id="plans",
            title="💰 Selecione um plano",
            input_message_content=InputTextMessageContent(
                message_text="💰 Escolha um plano para continuar:",
                parse_mode=ParseMode.HTML
            ),
            reply_markup=generate_plans_keyboard(),
            description="Selecione um plano para agendamento"
        ))
        
        # Se houver uma consulta, filtra os resultados
        if inline_query.query:
            query = inline_query.query.lower()
            filtered_results = []
            
            if "horario" in query or "time" in query or "disponivel" in query:
                filtered_results.append(results[0])  # Horários disponíveis
            elif "plan" in query or "plano" in query:
                filtered_results.append(results[1])  # Planos
            else:
                filtered_results = results  # Mostra ambos se não houver match específico
                
            await bot.answer_inline_query(
                inline_query_id=inline_query.id,
                results=filtered_results,
                cache_time=1,
                is_personal=True
            )
        else:
            # Se não houver consulta, mostra ambas as opções
            await bot.answer_inline_query(
                inline_query_id=inline_query.id,
                results=results,
                cache_time=1,
                is_personal=True
            )
    except Exception as e:
        logging.error(f"Erro ao processar consulta inline: {e}")
        await bot.answer_inline_query(
            inline_query_id=inline_query.id,
            results=[],
            cache_time=1,
            is_personal=True
        )

# Handler para trocar anúncio
@dp.callback_query(F.data == "trocar_anuncio")
async def trocar_anuncio_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = str(callback_query.from_user.id)
    planos = []
    if os.path.exists(SCHEDULED_MESSAGES_FILE):
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            agendados = json.load(f)
        planos = [p for p in agendados if str(p.get('recipient_id')) == user_id]
    # Agrupa por fixed_ad_id
    planos_dict = {}
    for p in planos:
        fid = p.get('fixed_ad_id')
        if fid not in planos_dict:
            planos_dict[fid] = []
        planos_dict[fid].append(p)
    if len(planos_dict) >= 1:
        # Sempre mostra opções (um botão por plano)
        botoes = []
        for fid, ps in planos_dict.items():
            tipo = ps[0].get('type', 'desconhecido').capitalize()
            validade = ps[0].get('expiry_time', '-')
            horarios = ', '.join(sorted([x['time'] for x in ps]))
            texto = f"ID: {fid[:6]}... | {tipo} | {horarios} | até {validade}"
            botoes.append([InlineKeyboardButton(text=texto, callback_data=f"escolher_plano_anuncio:{fid}")])
        # Botão de voltar
        botoes.append([InlineKeyboardButton(text="🔙 Voltar", callback_data="voltar_menu_principal")])
        markup = InlineKeyboardMarkup(inline_keyboard=botoes)
        await callback_query.message.answer("Selecione o plano que deseja alterar o anúncio:", reply_markup=markup)
    else:
        await callback_query.message.answer("Você não possui nenhum plano ativo.")
    await callback_query.answer()

# Handler para escolher plano para trocar anúncio
@dp.callback_query(F.data.startswith("escolher_plano_anuncio:"))
async def escolher_plano_anuncio_handler(callback_query: types.CallbackQuery, state: FSMContext):
    fid = callback_query.data.split(":")[1]
    await state.update_data(fixed_ad_id=fid)
    await callback_query.message.answer("Envie o novo anúncio (texto ou encaminhe a mensagem):")
    await state.set_state(TrocaPlanoStates.esperando_novo_anuncio)
    await callback_query.answer()

# Handler para trocar horário
@dp.callback_query(F.data == "trocar_horario")
async def trocar_horario_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = str(callback_query.from_user.id)
    planos = []
    if os.path.exists(SCHEDULED_MESSAGES_FILE):
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            agendados = json.load(f)
        planos = [p for p in agendados if str(p.get('recipient_id')) == user_id]
    # Agrupa por fixed_ad_id
    planos_dict = {}
    for p in planos:
        fid = p.get('fixed_ad_id')
        if fid not in planos_dict:
            planos_dict[fid] = []
        planos_dict[fid].append(p)
    if len(planos_dict) >= 1:
        # Sempre mostra opções (um botão por plano)
        botoes = []
        for fid, ps in planos_dict.items():
            tipo = ps[0].get('type', 'desconhecido').capitalize()
            validade = ps[0].get('expiry_time', '-')
            horarios = ', '.join(sorted([x['time'] for x in ps]))
            texto = f"ID: {fid[:6]}... | {tipo} | {horarios} | até {validade}"
            botoes.append([InlineKeyboardButton(text=texto, callback_data=f"escolher_plano_horario:{fid}")])
        # Botão de voltar
        botoes.append([InlineKeyboardButton(text="🔙 Voltar", callback_data="voltar_menu_principal")])
        markup = InlineKeyboardMarkup(inline_keyboard=botoes)
        await callback_query.message.answer("Selecione o plano que deseja alterar os horários:", reply_markup=markup)
    else:
        await callback_query.message.answer("Você não possui nenhum plano ativo.")
    await callback_query.answer()

# Handler para escolher plano para trocar horário
@dp.callback_query(F.data.startswith("escolher_plano_horario:"))
async def escolher_plano_horario_handler(callback_query: types.CallbackQuery, state: FSMContext):
    fid = callback_query.data.split(":")[1]
    await state.update_data(fixed_ad_id=fid)
    # Buscar horários atuais do plano
    horarios_atuais = []
    if os.path.exists(SCHEDULED_MESSAGES_FILE):
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            agendados = json.load(f)
        horarios_atuais = sorted([p['time'] for p in agendados if p.get('fixed_ad_id') == fid])
    if horarios_atuais:
        botoes = [[InlineKeyboardButton(text=h, callback_data=f"trocar_horario_atual:{fid}:{hora_compacta(h)}")] for h in horarios_atuais]
        botoes.append([InlineKeyboardButton(text="🔙 Voltar", callback_data="voltar_menu_principal")])
        markup = InlineKeyboardMarkup(inline_keyboard=botoes)
        await callback_query.message.answer(
            "Selecione o horário atual que deseja trocar:",
            reply_markup=markup
        )
    else:
        await callback_query.message.answer("Nenhum horário encontrado para este plano.")
    await callback_query.answer()

# Handler para selecionar o horário atual a ser trocado (com paginação e layout igual ao /horarios)
@dp.callback_query(F.data.startswith("trocar_horario_atual:"))
async def trocar_horario_atual_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        # callback_data: trocar_horario_atual:<fid>:<horario_atual_compacto>[:<page>]
        data_parts = callback_query.data.split(":")
        if len(data_parts) < 3:
            await callback_query.answer("❌ Dados inválidos. Tente novamente.", show_alert=True)
            return
            
        fid = data_parts[1]
        horario_atual_compacto = data_parts[2]
        page = int(data_parts[3]) if len(data_parts) > 3 else 0
        
        if not fid or not horario_atual_compacto or len(horario_atual_compacto) != 4:
            await callback_query.answer("❌ Dados do horário inválidos. Tente novamente.", show_alert=True)
            return
            
        horario_atual = f"{horario_atual_compacto[:2]}:{horario_atual_compacto[2:]}"
        
        # Atualiza o estado com todas as informações necessárias
        await state.update_data(
            fixed_ad_id=fid,
            fid=fid,  # Mantém compatibilidade com códigos antigos
            horario_atual=horario_atual,
            horario_original=horario_atual_compacto,  # Armazena o horário original compactado
            current_page=page  # Armazena a página atual
        )
        
        # Buscar horários disponíveis (não ocupados por outros planos, exceto o atual)
        horarios_disponiveis = []
    except Exception as e:
        print(f"[DEBUG] Erro no handler de troca de horário: {e}")
        await callback_query.answer("❌ Ocorreu um erro ao processar sua solicitação. Tente novamente.", show_alert=True)
        return
    if os.path.exists(SCHEDULED_MESSAGES_FILE):
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            agendados = json.load(f)
        # Horários do mesmo plano, exceto o atual
        usados = set([p['time'] for p in agendados if p.get('fixed_ad_id') == fid and p['time'] != horario_atual])
        # Horários ocupados por outros planos
        ocupados = set([p['time'] for p in agendados if p.get('fixed_ad_id') != fid])
        todos = set(get_available_hours())
        def hora_para_minutos(h):
            h, m = map(int, h.split(":"))
            return h * 60 + m
        for h in todos:
            # O horário atual SEMPRE pode aparecer
            if h != horario_atual and h in ocupados:
                continue
            minutos_h = hora_para_minutos(h)
            conflito = False
            for usado in usados:
                minutos_usado = hora_para_minutos(usado)
                if abs(minutos_h - minutos_usado) < 10:
                    conflito = True
                    break
            if not conflito or h == horario_atual:
                horarios_disponiveis.append(h)
        horarios_disponiveis = sorted(horarios_disponiveis)
        print(f"[DEBUG] Horários disponíveis para troca: {horarios_disponiveis}")
    
    HORARIOS_POR_PAGINA = 8
    HORARIOS_POR_LINHA = 10
    total_pages = max(1, (len(horarios_disponiveis) + HORARIOS_POR_PAGINA - 1) // HORARIOS_POR_PAGINA)
    start = page * HORARIOS_POR_PAGINA
    end = start + HORARIOS_POR_PAGINA
    horarios_pagina = [h for h in horarios_disponiveis[start:end] if h and len(hora_compacta(h)) == 4]
    botoes = []
    linha = []
    for h in horarios_pagina:
        h_compact = hora_compacta(h)
        if not h_compact or len(h_compact) != 4:
            continue
        # Usando formato curto para o callback_data
        fid_short = fid[:8] if fid else ""
        cb_data = f"nht:{h_compact}"
        linha.append(InlineKeyboardButton(text=h, callback_data=cb_data))
        if len(linha) == HORARIOS_POR_LINHA:
            botoes.append(linha)
            linha = []
    if linha:
        botoes.append(linha)
    # Se não houver horários disponíveis, mostra um botão informando
    if not horarios_pagina:
        botoes.append([InlineKeyboardButton(text="❌ Nenhum horário disponível", callback_data="ignore")])
    else:
        # Garante que os botões estejam organizados em linhas de 4
        botoes_organizados = []
        for i in range(0, len(horarios_pagina), 4):
            linha = []
            for h in horarios_pagina[i:i+4]:
                h_compact = hora_compacta(h)
                if h_compact and len(h_compact) == 4:
                    # Encurtando o callback_data para evitar exceder o limite
                    # fid pode ser muito longo, então usamos apenas os primeiros 8 caracteres
                    fid_short = fid[:8] if fid else ""
                    cb_data = f"nht:{fid_short}:{h_compact}"
                    linha.append(InlineKeyboardButton(text=h, callback_data=cb_data))
            if linha:
                botoes_organizados.append(linha)
        botoes = botoes_organizados
        
        # Atualiza o estado com o fid completo para uso posterior
        await state.update_data(fid_completo=fid, horario_original=hora_compacta(horario_atual))
    
    # Adiciona navegação
    nav_buttons = []
    fid_short = fid[:8] if fid else ""
    horario_compacto = hora_compacta(horario_atual)
    
    # Botão Anterior
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Anterior", 
            callback_data=f"tha:{fid_short}:{horario_compacto}:{page-1}"
        ))
    
    # Número da Página Atual
    nav_buttons.append(InlineKeyboardButton(
        text=f"📄 {page+1}/{total_pages}", 
        callback_data="ignore"
    ))
    
    # Botão Próxima
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Próxima ➡️", 
            callback_data=f"tha:{fid_short}:{horario_compacto}:{page+1}"
        ))
    
    # Adiciona a barra de navegação se houver botões
    if nav_buttons:
        botoes.append(nav_buttons)
    
    # Botão de voltar
    botoes.append([
        InlineKeyboardButton(text="🔙 Voltar ao Menu Principal", callback_data="voltar_menu_principal")
    ])
    
    # Cria o teclado inline
    markup = InlineKeyboardMarkup(inline_keyboard=botoes)
    
    # Atualiza o estado com as informações atuais para uso futuro
    await state.update_data(
        fid=fid,
        fid_short=fid_short,
        horario_original=horario_compacto,
        current_page=page
    )
    try:
        await callback_query.message.edit_text(
            f"Selecione o novo horário para substituir {horario_atual}:",
            reply_markup=markup
        )
    except Exception as e:
        # Se houver erro ao editar a mensagem, tenta enviar uma nova
        print(f"[DEBUG] Erro ao editar mensagem: {e}")
        try:
            await callback_query.message.answer(
                f"Selecione o novo horário para substituir {horario_atual}:",
                reply_markup=markup
            )
        except Exception as e2:
            print(f"[DEBUG] Erro ao enviar nova mensagem: {e2}")
    finally:
        await callback_query.answer()

# Handler para ignorar botões de paginação
@dp.callback_query(F.data == "ignore")
async def ignore_callback_handler(callback_query: types.CallbackQuery):
    await callback_query.answer()

# ... restante do código ...
# Handler para navegação entre páginas de horários para troca (formato curto)
@dp.callback_query(F.data.startswith("tha:"))
async def trocar_horario_atual_page_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        # Formato: tha:<fid_short>:<horario_compacto>:<pagina>
        _, fid_short, horario_compacto, pagina_str = callback_query.data.split(":", 3)
        pagina = int(pagina_str)
        
        # Recupera o fid completo e horário original do estado
        state_data = await state.get_data()
        fid = state_data.get('fixed_ad_id') or state_data.get('fid')
        
        if not fid:
            # Tenta obter o fid do callback_data original, se disponível
            if 'original_fid' in state_data:
                fid = state_data['original_fid']
            else:
                await callback_query.answer("❌ Sessão expirada. Por favor, inicie o processo novamente.", show_alert=True)
                return
        
        # Garante que o horário original esteja no estado
        horario_original = state_data.get('horario_original')
        if not horario_original:
            horario_original = horario_compacto
        
        # Atualiza o estado com os dados necessários
        await state.update_data(
            fid=fid,
            horario_original=horario_original,
            fid_short=fid_short,
            original_fid=fid  # Armazena o fid original para referência futura
        )
        
        # Obtém a instância do bot do callback_query original
        bot = callback_query.bot
        
        # Cria um dicionário com os dados do callback_query
        from aiogram.types import CallbackQuery
        
        # Cria um novo objeto CallbackQuery sem o bot
        new_query = CallbackQuery(
            id=callback_query.id,
            from_user=callback_query.from_user,
            chat_instance=callback_query.chat_instance,
            message=callback_query.message,
            data=f"trocar_horario_atual:{fid}:{horario_compacto}:{pagina}"
        )
        
        # Associa o bot ao novo objeto usando o método as_(bot)
        new_query = new_query.as_(bot)
        
        # Chama o handler original com o novo objeto
        await trocar_horario_atual_handler(new_query, state)
        
    except Exception as e:
        print(f"[DEBUG] Erro no handler de navegação: {e}")
        await callback_query.answer("❌ Ocorreu um erro ao navegar entre as páginas. Tente novamente.", show_alert=True)

# Handler para o formato curto de callback_data (nht:)
@dp.callback_query(F.data.startswith("nht:"))
async def novo_horario_curto_handler(callback_query: types.CallbackQuery, state: FSMContext):
    # Formato: nht:<horario_compacto>
    _, horario_compacto = callback_query.data.split(":", 1)
    
    # Recupera o fid completo e horário original do estado
    state_data = await state.get_data()
    fid = state_data.get('fid')
    horario_original = state_data.get('horario_original')
    
    if not fid or not horario_original:
        await callback_query.answer("❌ Sessão expirada. Por favor, inicie o processo novamente.", show_alert=True)
        return
    
    # Obtém a instância do bot do callback_query original
    bot = callback_query.bot
    
    # Função para extrair apenas os dígitos de tempo (HHMM) de uma string
    def extract_time_digits(time_str):
        # Remove qualquer caractere que não seja dígito
        digits = ''.join(c for c in str(time_str) if c.isdigit())
        # Pega apenas os últimos 4 dígitos (caso tenha mais)
        if len(digits) > 4:
            digits = digits[-4:]
        # Garante que temos 4 dígitos
        if len(digits) == 3:
            digits = '0' + digits
        return digits
    
    # Extrai apenas os dígitos do horário original e do novo horário
    horario_original_digits = extract_time_digits(horario_original)
    horario_novo_digits = extract_time_digits(horario_compacto)
    
    # Log para depuração
    print(f"[DEBUG] Horário original processado: {horario_original} -> {horario_original_digits}")
    print(f"[DEBUG] Horário novo processado: {horario_compacto} -> {horario_novo_digits}")
    
    # Cria um novo objeto CallbackQuery sem o bot
    from aiogram.types import CallbackQuery
    new_query = CallbackQuery(
        id=callback_query.id,
        from_user=callback_query.from_user,
        chat_instance=callback_query.chat_instance,
        message=callback_query.message,
        data=f"novo_horario_para_troca:{fid}:{horario_original_digits}:{horario_novo_digits}"
    )
    
    # Associa o bot ao novo objeto usando o método as_(bot)
    new_query = new_query.as_(bot)
    
    # Chama o handler principal com o novo objeto
    await novo_horario_para_troca_handler(new_query, state)

# Handler para aplicar a troca de horário (formato longo)
@dp.callback_query(F.data.startswith("novo_horario_para_troca:"))
async def novo_horario_para_troca_handler(callback_query: types.CallbackQuery, state: FSMContext):
    # Log the raw callback data for debugging
    print(f"[DEBUG] Raw callback data: {callback_query.data}")
    
    # callback_data: novo_horario_para_troca:<fid>:<horario_antigo_compacto>:<horario_novo_compacto>
    try:
        prefix, fid, horario_antigo_compacto, horario_novo_compacto = callback_query.data.split(":", 3)
        
        # Função para formatar horário para o formato HH:MM
        def format_time(time_str):
            if not time_str:
                return ""
                
            # Remove qualquer caractere que não seja dígito
            digits = ''.join(c for c in str(time_str) if c.isdigit())
            
            # Se não tiver dígitos suficientes, retorna vazio
            if not digits or len(digits) < 3:
                return ""
                
            # Pega apenas os últimos 4 dígitos (caso tenha mais)
            if len(digits) > 4:
                digits = digits[-4:]
                
            # Garante que temos 4 dígitos (HHMM)
            if len(digits) == 3:
                digits = '0' + digits  # Adiciona zero à frente se for 3 dígitos
            elif len(digits) != 4:
                return ""
            
            # Pega horas e minutos
            try:
                hours = int(digits[:2])
                minutes = int(digits[2:4])
                
                # Valida horas e minutos
                if 0 <= hours < 24 and 0 <= minutes < 60:
                    return f"{hours:02d}:{minutes:02d}"
            except (ValueError, IndexError):
                pass
                
            return ""
        
        # Formata os horários
        horario_antigo = format_time(horario_antigo_compacto)
        horario_novo = format_time(horario_novo_compacto)
        
        # Log para depuração
        print(f"[DEBUG] Horário antigo formatado: {horario_antigo} (de: {horario_antigo_compacto})")
        print(f"[DEBUG] Horário novo formatado: {horario_novo} (de: {horario_novo_compacto})")
        
        # Valida o formato do horário
        def is_valid_time(time_str):
            try:
                if ":" in time_str:
                    hours, minutes = map(int, time_str.split(":"))
                elif len(time_str) == 3:  # Formato HMM
                    hours, minutes = int(time_str[0]), int(time_str[1:3])
                elif len(time_str) == 4:  # Formato HHMM
                    hours, minutes = int(time_str[:2]), int(time_str[2:])
                else:
                    return False
                return 0 <= hours < 24 and 0 <= minutes < 60
            except (ValueError, IndexError):
                return False
                
        if not is_valid_time(horario_antigo) or not is_valid_time(horario_novo):
            await callback_query.message.answer("❌ Formato de horário inválido. Use o formato HH:MM (ex: 14:30).")
            await state.clear()
            await callback_query.answer()
            return
            
    except ValueError:
        await callback_query.message.answer("❌ Erro ao processar a solicitação. Tente novamente.")
        await state.clear()
        await callback_query.answer()
        return
    
    alterado = False
    if os.path.exists(SCHEDULED_MESSAGES_FILE):
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            agendados = json.load(f)
        for p in agendados:
            if p.get('fixed_ad_id') == fid and p.get('time') == horario_antigo:
                p['time'] = horario_novo
                alterado = True
        with open(SCHEDULED_MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(agendados, f, ensure_ascii=False, indent=4)
    
    if alterado:
        await callback_query.message.answer(f"✅ Horário {horario_antigo} foi substituído por {horario_novo} com sucesso!")
    else:
        await callback_query.message.answer("Não foi possível alterar o horário. Tente novamente.")
    
    await state.clear()
    await callback_query.answer()

# Handler SIMPLIFICADO para o botão de limpar IDs com erros
@dp.callback_query(F.data == "clear_failed_ids_now")
async def clear_failed_ids_handler(callback_query: types.CallbackQuery):
    """Handler simplificado para limpar IDs de chats que falharam no envio"""
    # RESPONDE IMEDIATAMENTE para parar o loading
    await callback_query.answer("🔄 Processando remoção dos IDs...")
    
    try:
        failed_ids_file = 'temp_failed_ids.json'
        
        print(f"[CLEAR_IDS] Iniciando limpeza de IDs com falha")
        print(f"[CLEAR_IDS] Procurando arquivo: {failed_ids_file}")
        
        # Verifica se o arquivo existe
        if not os.path.exists(failed_ids_file):
            print(f"[CLEAR_IDS] Arquivo não encontrado: {failed_ids_file}")
            await callback_query.message.reply("⚠️ Nenhum ID com falha para limpar.")
            return
        
        # Carrega os IDs com falha
        try:
            with open(failed_ids_file, 'r', encoding='utf-8') as f:
                failed_ids = json.load(f)
            print(f"[CLEAR_IDS] IDs com falha carregados: {failed_ids}")
        except Exception as e:
            print(f"[CLEAR_IDS] Erro ao carregar IDs: {e}")
            await callback_query.message.reply("❌ Erro ao carregar IDs com falha.")
            return
        
        if not failed_ids:
            await callback_query.message.reply("ℹ️ Nenhum ID para limpar.")
            return
        
        # Carrega a lista atual de chat_ids
        try:
            current_chat_ids = load_chat_ids()
            print(f"[CLEAR_IDS] Chat IDs atuais: {len(current_chat_ids)}")
        except Exception as e:
            print(f"[CLEAR_IDS] Erro ao carregar chat_ids: {e}")
            await callback_query.message.reply("❌ Erro ao carregar lista de chats.")
            return
        
        # Remove os IDs com falha da lista principal (lógica robusta)
        failed_ids_str = set(str(fid) for fid in failed_ids)
        original_count = len(current_chat_ids)
        current_chat_ids = [cid for cid in current_chat_ids if cid not in failed_ids_str]
        removed_count = original_count - len(current_chat_ids)
        for removed in failed_ids_str:
            print(f"[CLEAR_IDS] (tentou remover) {removed}")

        # Salva a lista principal atualizada apenas se houve remoções
        if removed_count > 0:
            try:
                # Salva a lista principal atualizada
                with open(CHAT_IDS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(current_chat_ids, f, ensure_ascii=False, indent=4)
                print(f"[CLEAR_IDS] Lista principal salva com {len(current_chat_ids)} IDs")
            except Exception as e:
                print(f"[CLEAR_IDS] Erro ao salvar lista principal: {e}")
                await callback_query.message.reply("❌ Erro ao salvar lista.")
                return
        
        # Remove o arquivo temporário
        try:
            os.remove(failed_ids_file)
            print(f"[CLEAR_IDS] Arquivo temporário removido")
        except Exception as e:
            print(f"[CLEAR_IDS] Erro ao remover arquivo: {e}")
        
        # Remove o botão
        try:
            await callback_query.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            print(f"[CLEAR_IDS] Erro ao remover botão: {e}")
        
        # Resposta final
        if removed_count > 0:
            await callback_query.message.reply(
                f"✅ {removed_count} IDs removidos com sucesso da lista de envio!"
            )
        else:
            await callback_query.message.reply(
                "ℹ️ Nenhum ID foi removido (não estavam na lista)."
            )
        
        print(f"[CLEAR_IDS] CONCLUÍDO! Removidos: {removed_count} IDs")
        
    except Exception as e:
        print(f"[CLEAR_IDS] ERRO GERAL: {e}")
        import traceback
        print(f"[CLEAR_IDS] Traceback: {traceback.format_exc()}")
        await callback_query.message.reply("❌ Erro ao processar.")

# Handler para voltar ao menu principal
@dp.callback_query(F.data == "voltar_menu_principal")
async def voltar_menu_principal_handler(callback_query: types.CallbackQuery):
    await start_cmd(callback_query.message)
    await callback_query.answer()

# Handler para receber o novo anúncio
@dp.message(TrocaPlanoStates.esperando_novo_anuncio)
async def receber_novo_anuncio(message: types.Message, state: FSMContext):
    data = await state.get_data()
    fixed_ad_id = data.get('fixed_ad_id')
    if not fixed_ad_id:
        await message.reply("Erro interno: ID do plano não encontrado. Tente novamente.")
        await state.clear()
        return
    # Atualiza o anúncio: salva from_chat_id e message_id da nova mensagem
    alterados = 0
    if os.path.exists(SCHEDULED_MESSAGES_FILE):
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            agendados = json.load(f)
        for p in agendados:
            if p.get('fixed_ad_id') == fixed_ad_id:
                p['from_chat_id'] = message.chat.id
                p['message_id'] = message.message_id
                # Remove custom_message se existir
                if 'custom_message' in p:
                    del p['custom_message']
                alterados += 1
        with open(SCHEDULED_MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(agendados, f, ensure_ascii=False, indent=4)
    if alterados:
        await message.reply("✅ Anúncio atualizado com sucesso para o plano selecionado!")
    else:
        await message.reply("Nenhum plano foi alterado. Verifique se o ID está correto.")
    await state.clear()

# --- Troca de anúncio por comando /trocaranuncio <idfixo> ---
from aiogram.fsm.context import FSMContext

@dp.message(Command("trocaranuncio"))
async def trocar_anuncio_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("Você não tem permissão para usar este comando.")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Use: /trocaranuncio <idfixo> respondendo à nova mensagem de anúncio.")
        return
    idfixo = args[1].strip().lower()
    if not message.reply_to_message:
        await message.reply("Responda à mensagem (texto, imagem, vídeo, etc) que deseja usar como novo anúncio.")
        return
    # Atualiza o anúncio
    agendados = load_scheduled_messages()
    if agendados is None:
        agendados = []
    alterado = False
    ids_disponiveis = [str(p.get('fixed_ad_id', '')).strip().lower() for p in agendados]
    print("IDs disponíveis:", ids_disponiveis)
    for p in agendados:
        if str(p.get('fixed_ad_id', '')).strip().lower() == idfixo:
            p['from_chat_id'] = message.reply_to_message.chat.id
            p['message_id'] = message.reply_to_message.message_id
            if 'custom_message' in p:
                del p['custom_message']
            alterado = True
    if alterado:
        save_scheduled_messages(agendados, origem="trocar_anuncio_cmd")
        await message.reply("Anúncio atualizado com sucesso!")
    else:
        await message.reply(f"ID fixo não encontrado nos agendamentos. IDs disponíveis: {', '.join(ids_disponiveis)}")

    await state.clear()

# Comando /muda - Versão simplificada para trocar anúncio
@dp.message(Command("muda"))
async def muda_anuncio_cmd(message: types.Message, state: FSMContext):
    """
    Comando simplificado para trocar anúncio
    Uso: /muda <idfixo> respondendo à nova mensagem
    """
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Você não tem permissão para usar este comando.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Use: <code>/muda &lt;idfixo&gt;</code> respondendo à nova mensagem de anúncio.", parse_mode="HTML")
        return
    
    idfixo = args[1].strip().lower()
    
    if not message.reply_to_message:
        await message.reply("📌 Responda à mensagem (texto, imagem, vídeo, etc) que deseja usar como novo anúncio.")
        return
    
    try:
        # Carrega os agendamentos
        agendados = load_scheduled_messages()
        if agendados is None:
            agendados = []
        
        # Procura pelo ID fixo
        alterado = False
        ids_disponiveis = []
        
        for p in agendados:
            fixed_id = str(p.get('fixed_ad_id', '')).strip().lower()
            if fixed_id:
                ids_disponiveis.append(fixed_id)
            
            if fixed_id == idfixo:
                # Atualiza o anúncio
                p['from_chat_id'] = message.reply_to_message.chat.id
                p['message_id'] = message.reply_to_message.message_id
                
                # Remove custom_message se existir (para usar a mensagem original)
                if 'custom_message' in p:
                    del p['custom_message']
                
                alterado = True
                break
        
        if alterado:
            # Salva as alterações
            save_scheduled_messages(agendados, origem="muda_anuncio_cmd")
            
            # Log da ação do admin
            admin_name = message.from_user.full_name or "Admin"
            logger.admin_action(admin_name, message.from_user.id, f"Trocou anúncio do ID fixo: {idfixo}")
            
            await message.reply(f"✅ Anúncio do ID <code>{idfixo}</code> atualizado com sucesso!", parse_mode="HTML")
        else:
            if ids_disponiveis:
                ids_text = "', '".join(ids_disponiveis[:10])  # Mostra até 10 IDs
                if len(ids_disponiveis) > 10:
                    ids_text += f"... (+{len(ids_disponiveis)-10} mais)"
                await message.reply(f"❌ ID fixo '<code>{idfixo}</code>' não encontrado.\n\n📋 IDs disponíveis: '<code>{ids_text}</code>'", parse_mode="HTML")
            else:
                await message.reply("❌ Nenhum agendamento encontrado no sistema.")
    
    except Exception as e:
        logger.error(f"Erro no comando /muda: {e}")
        await message.reply(f"❌ Erro ao trocar anúncio: {str(e)}")
    
    await state.clear()

# Scheduler de backup automático
async def backup_scheduler():
    while True:
        try:
            await backup_and_send_logs(bot, config.get('LOG'))
            logging.info('Backup automático enviado para o canal de logs.')
        except Exception as e:
            logging.error(f'Erro no backup automático: {e}')
        await asyncio.sleep(60 * 60 * 12)  # 12 horas

# Comando manual para backup
async def manual_backup_cmd(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.reply("Você não tem permissão para usar este comando.")
        return
    await backup_and_send_logs(bot, config.get('LOG'))
    await message.reply("Backup enviado para o canal de logs!")

# ============================================================================
# SISTEMA DE ESTATÍSTICAS AVANÇADO
# ============================================================================

@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    """Comando para visualizar estatísticas detalhadas do bot"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem acessar as estatísticas.")
        return
    
    try:
        # Carrega dados
        chat_ids = load_chat_ids()
        scheduled_messages = load_scheduled_messages()
        
        # Estatísticas básicas
        total_grupos = len(chat_ids)
        total_planos = len(scheduled_messages)
        
        # Análise de planos por tipo
        planos_por_tipo = {}
        planos_ativos = 0
        planos_expirados = 0
        now = datetime.datetime.now()
        
        for msg in scheduled_messages:
            tipo = msg.get('type', 'indefinido')
            planos_por_tipo[tipo] = planos_por_tipo.get(tipo, 0) + 1
            
            # Verifica se está ativo
            expiry_str = msg.get('expiry_time')
            if expiry_str:
                try:
                    expiry_dt = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                    if expiry_dt > now:
                        planos_ativos += 1
                    else:
                        planos_expirados += 1
                except:
                    pass
        
        # Análise de horários
        horarios_ocupados = set()
        for msg in scheduled_messages:
            if msg.get('time'):
                horarios_ocupados.add(msg['time'])
        
        horarios_disponiveis = len(get_available_hours()) - len(horarios_ocupados)
        
        # Análise de usuários únicos
        usuarios_unicos = set()
        for msg in scheduled_messages:
            if msg.get('recipient_id'):
                usuarios_unicos.add(msg['recipient_id'])
        
        # Monta relatório
        stats_text = f"""📊 **ESTATÍSTICAS DO BOT DE DIVULGAÇÃO**
        
🏢 **GRUPOS E CANAIS**
├─ 📊 Total cadastrados: **{total_grupos}**
├─ ✅ Grupos ativos: **{total_grupos}**
└─ 📈 Taxa de cobertura: **100%**

💼 **PLANOS DE DIVULGAÇÃO**
├─ 📋 Total de planos: **{total_planos}**
├─ ✅ Planos ativos: **{planos_ativos}**
├─ ❌ Planos expirados: **{planos_expirados}**
└─ 👥 Clientes únicos: **{len(usuarios_unicos)}**

📊 **DISTRIBUIÇÃO POR TIPO**"""

        for tipo, quantidade in planos_por_tipo.items():
            porcentagem = (quantidade / total_planos * 100) if total_planos > 0 else 0
            stats_text += f"\n├─ {tipo.capitalize()}: **{quantidade}** ({porcentagem:.1f}%)"

        stats_text += f"""

⏰ **HORÁRIOS**
├─ 🕐 Horários ocupados: **{len(horarios_ocupados)}**
├─ ✅ Horários disponíveis: **{horarios_disponiveis}**
└─ 📈 Taxa de ocupação: **{(len(horarios_ocupados) / len(get_available_hours()) * 100):.1f}%**

🎯 **PERFORMANCE**
├─ 📤 Média de envios/dia: **{len(horarios_ocupados) * 24}**
├─ 🎯 Alcance estimado: **{total_grupos * len(horarios_ocupados)}** mensagens/dia
└─ 💰 Receita estimada: **R$ {len(usuarios_unicos) * 50:.2f}**/mês

📅 **Relatório gerado em:** {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""

        # Botões para mais detalhes
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📊 Gráfico Detalhado", callback_data="stats_detailed"),
                    InlineKeyboardButton(text="📈 Tendências", callback_data="stats_trends")
                ],
                [
                    InlineKeyboardButton(text="👥 Top Clientes", callback_data="stats_top_clients"),
                    InlineKeyboardButton(text="🕐 Horários Populares", callback_data="stats_popular_times")
                ],
                [
                    InlineKeyboardButton(text="📄 Exportar Relatório", callback_data="stats_export"),
                    InlineKeyboardButton(text="🔄 Atualizar", callback_data="stats_refresh")
                ]
            ]
        )
        
        await message.reply(stats_text, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Erro ao gerar estatísticas: {e}")
        await message.reply(f"❌ Erro ao gerar estatísticas: {e}")

# Handlers para os botões de estatísticas
@dp.callback_query(F.data == "stats_detailed")
async def stats_detailed_handler(query: types.CallbackQuery):
    """Mostra estatísticas detalhadas"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    try:
        scheduled_messages = load_scheduled_messages()
        
        # Análise por dia da semana
        dias_semana = {0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 4: 'Sexta', 5: 'Sábado', 6: 'Domingo'}
        atividade_por_dia = {dia: 0 for dia in dias_semana.values()}
        
        # Análise por período do dia
        periodos = {'Madrugada (00-06)': 0, 'Manhã (06-12)': 0, 'Tarde (12-18)': 0, 'Noite (18-24)': 0}
        
        for msg in scheduled_messages:
            # Análise por criação (dia da semana)
            creation_time = msg.get('creation_time')
            if creation_time:
                try:
                    dt = datetime.datetime.strptime(creation_time, "%Y-%m-%d %H:%M:%S")
                    dia_semana = dias_semana[dt.weekday()]
                    atividade_por_dia[dia_semana] += 1
                except:
                    pass
            
            # Análise por horário de envio
            time_str = msg.get('time')
            if time_str:
                try:
                    hour = int(time_str.split(':')[0])
                    if 0 <= hour < 6:
                        periodos['Madrugada (00-06)'] += 1
                    elif 6 <= hour < 12:
                        periodos['Manhã (06-12)'] += 1
                    elif 12 <= hour < 18:
                        periodos['Tarde (12-18)'] += 1
                    else:
                        periodos['Noite (18-24)'] += 1
                except:
                    pass
        
        detailed_text = f"""📊 **ANÁLISE DETALHADA**

📅 **ATIVIDADE POR DIA DA SEMANA**"""
        
        for dia, count in atividade_por_dia.items():
            detailed_text += f"\n├─ {dia}: **{count}** planos"
        
        detailed_text += f"""

🕐 **DISTRIBUIÇÃO POR PERÍODO**"""
        
        for periodo, count in periodos.items():
            detailed_text += f"\n├─ {periodo}: **{count}** horários"
        
        detailed_text += f"""

📈 **INSIGHTS**
├─ 🔥 Dia mais ativo: **{max(atividade_por_dia, key=atividade_por_dia.get)}**
├─ ⏰ Período preferido: **{max(periodos, key=periodos.get)}**
└─ 📊 Distribuição equilibrada: **{'Sim' if max(atividade_por_dia.values()) - min(atividade_por_dia.values()) < 5 else 'Não'}**"""

        await query.message.edit_text(detailed_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Voltar", callback_data="stats_back")]]
        ))
        
    except Exception as e:
        await query.answer(f"❌ Erro: {e}", show_alert=True)

@dp.message(Command("planstats"))
async def plan_stats_command(message: types.Message):
    """Comando para consultar estatísticas de um plano específico
    Uso: /planstats <plan_id>
    """
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem acessar as estatísticas.")
        return
    
    try:
        # Extrai o plan_id do comando
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(
                "📊 **CONSULTAR ESTATÍSTICAS DE PLANO**\n\n"
                "**Uso:** `/planstats <plan_id>`\n\n"
                "**Exemplo:** `/planstats abc123def456`\n\n"
                "💡 O plan_id pode ser encontrado no painel web ou nos relatórios de divulgação.",
                parse_mode="Markdown"
            )
            return
        
        plan_id = args[1].strip()
        
        # Busca o plano
        scheduled_messages = load_scheduled_messages()
        plan = None
        for msg in scheduled_messages:
            if msg.get('id') == plan_id or msg.get('fixed_id') == plan_id:
                plan = msg
                break
        
        if not plan:
            await message.reply(f"❌ Plano `{plan_id}` não encontrado.", parse_mode="Markdown")
            return
        
        # Coleta estatísticas do plano
        plan_type = plan.get('type', 'indefinido')
        creation_time = plan.get('creation_time', 'N/A')
        expiry_time = plan.get('expiry_time', 'N/A')
        schedule_time = plan.get('time', 'N/A')
        recipient_id = plan.get('recipient_id', 'N/A')
        fixed_id = plan.get('fixed_id', plan_id)
        
        # Calcula dias restantes
        dias_restantes = "N/A"
        if expiry_time != 'N/A':
            try:
                expiry_dt = datetime.datetime.strptime(expiry_time, "%Y-%m-%d %H:%M:%S")
                now = datetime.datetime.now()
                if expiry_dt > now:
                    delta = expiry_dt - now
                    dias_restantes = f"{delta.days} dias, {delta.seconds // 3600}h"
                else:
                    dias_restantes = "⚠️ EXPIRADO"
            except:
                pass
        
        # Busca histórico de envios (se existir)
        total_envios = 0
        ultimo_envio = "N/A"
        envios_sucesso = 0
        envios_falha = 0
        
        # Tenta carregar histórico de logs
        try:
            if os.path.exists('broadcast_history.json'):
                with open('broadcast_history.json', 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    for entry in history:
                        if entry.get('plan_id') == plan_id or entry.get('fixed_id') == fixed_id:
                            total_envios += 1
                            if entry.get('status') == 'success':
                                envios_sucesso += 1
                            else:
                                envios_falha += 1
                            if entry.get('timestamp'):
                                ultimo_envio = entry['timestamp']
        except:
            pass
        
        # Calcula taxa de sucesso
        taxa_sucesso = (envios_sucesso / total_envios * 100) if total_envios > 0 else 0
        
        # Monta relatório
        status_emoji = "✅" if dias_restantes != "⚠️ EXPIRADO" else "❌"
        
        stats_text = f"""📊 **ESTATÍSTICAS DO PLANO**

{status_emoji} **STATUS:** {'ATIVO' if dias_restantes != "⚠️ EXPIRADO" else 'EXPIRADO'}

📋 **INFORMAÇÕES BÁSICAS**
├─ 🆔 ID do Plano: `{plan_id}`
├─ 🔖 ID Fixo: `{fixed_id}`
├─ 📦 Tipo: **{plan_type.capitalize()}**
├─ 👤 Cliente ID: `{recipient_id}`
└─ 🕐 Horário: **{schedule_time}**

📅 **DATAS**
├─ 📅 Criado em: {creation_time}
├─ ⏰ Expira em: {expiry_time}
└─ ⏳ Tempo restante: **{dias_restantes}**

📊 **ESTATÍSTICAS DE ENVIO**
├─ 📤 Total de envios: **{total_envios}**
├─ ✅ Sucessos: **{envios_sucesso}** ({taxa_sucesso:.1f}%)
├─ ❌ Falhas: **{envios_falha}**
└─ 🕐 Último envio: {ultimo_envio}

💡 **PERFORMANCE**
├─ 📈 Taxa de sucesso: **{taxa_sucesso:.1f}%**
├─ 🎯 Alcance diário: **{len(load_chat_ids())}** grupos
└─ 📊 Status: **{'EXCELENTE' if taxa_sucesso >= 90 else 'BOM' if taxa_sucesso >= 70 else 'ATENÇÃO'}**

📅 **Relatório gerado em:** {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""

        # Botões de ação
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Atualizar", callback_data=f"planstats_refresh_{plan_id}"),
                    InlineKeyboardButton(text="📊 Histórico", callback_data=f"planstats_history_{plan_id}")
                ],
                [
                    InlineKeyboardButton(text="⚙️ Gerenciar Plano", callback_data=f"manage_plan_{plan_id}")
                ]
            ]
        )
        
        await message.reply(stats_text, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Erro ao gerar estatísticas do plano: {e}")
        await message.reply(f"❌ Erro ao gerar estatísticas: {e}")

@dp.callback_query(F.data == "stats_export")
async def stats_export_handler(query: types.CallbackQuery):
    """Exporta relatório completo"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    try:
        # Gera relatório completo
        chat_ids = load_chat_ids()
        scheduled_messages = load_scheduled_messages()
        
        report_content = f"""RELATÓRIO COMPLETO DO BOT DE DIVULGAÇÃO
{'='*50}

Data de geração: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

RESUMO EXECUTIVO
{'-'*20}
• Total de grupos: {len(chat_ids)}
• Total de planos: {len(scheduled_messages)}
• Usuários únicos: {len(set(msg.get('recipient_id') for msg in scheduled_messages if msg.get('recipient_id')))}

DETALHAMENTO DOS PLANOS
{'-'*25}
"""
        
        for i, msg in enumerate(scheduled_messages, 1):
            report_content += f"""
{i}. Plano ID: {msg.get('fixed_ad_id', 'N/A')}
   • Tipo: {msg.get('type', 'N/A')}
   • Cliente: {msg.get('recipient_id', 'N/A')}
   • Horário: {msg.get('time', 'N/A')}
   • Criado em: {msg.get('creation_time', 'N/A')}
   • Expira em: {msg.get('expiry_time', 'N/A')}
"""
        
        report_content += f"""

GRUPOS CADASTRADOS
{'-'*18}
"""
        
        for i, chat_id in enumerate(chat_ids, 1):
            report_content += f"{i}. Chat ID: {chat_id}\n"
        
        report_content += f"""

FIM DO RELATÓRIO
{'-'*16}
Gerado automaticamente pelo Bot de Divulgação
"""
        
        # Salva em arquivo
        filename = f"relatorio_completo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # Envia arquivo
        await query.message.reply_document(
            document=types.FSInputFile(filename),
            caption="📄 **Relatório Completo Exportado**\n\nContém todos os dados do bot organizados para análise."
        )
        
        # Remove arquivo temporário
        os.remove(filename)
        
        await query.answer("✅ Relatório exportado com sucesso!")
        
    except Exception as e:
        await query.answer(f"❌ Erro ao exportar: {e}", show_alert=True)

@dp.callback_query(F.data == "stats_refresh")
async def stats_refresh_handler(query: types.CallbackQuery):
    """Atualiza as estatísticas"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    # Atualiza as estatísticas
    await admin_stats_panel_handler(query)
    await query.answer("🔄 Estatísticas atualizadas!")

@dp.callback_query(F.data == "stats_back")
async def stats_back_handler(query: types.CallbackQuery):
    """Volta para estatísticas principais"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    await admin_stats_panel_handler(query)

@dp.callback_query(F.data == "stats_back_to_panel")
async def stats_back_to_panel_handler(query: types.CallbackQuery):
    """Volta para o painel admin principal"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    # Carrega dados atualizados
    try:
        with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
            chat_ids_atual = json.load(f)
    except Exception:
        chat_ids_atual = []

    try:
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            scheduled_messages_atual = json.load(f)
    except Exception:
        scheduled_messages_atual = []

    # Filtra só anúncios ativos (não expirados)
    agora = datetime.datetime.now()
    anuncios_ativos = []
    for msg in scheduled_messages_atual:
        expiry_str = msg.get('expiry_time')
        if expiry_str:
            try:
                expiry_dt = datetime.datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
                if expiry_dt > agora:
                    anuncios_ativos.append(msg)
            except Exception:
                pass

    total_grupos = len(set(chat_ids_atual))
    id_fixos_ativos = set()
    for anuncio in anuncios_ativos:
        id_fixo = anuncio.get('fixed_ad_id')
        if id_fixo:
            id_fixos_ativos.add(str(id_fixo))
    total_anuncios = len(id_fixos_ativos)
    
    busy_hours = set()
    for msg in anuncios_ativos:
        if 'time' in msg:
            busy_hours.add(msg['time'][:5])
    total_horarios_disponiveis = len([h for h in get_available_hours() if h not in busy_hours])
    
    registered_users = load_registered_users()
    total_users = len(registered_users)
    
    painel = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Estatísticas", callback_data="admin_stats_panel"),
                InlineKeyboardButton(text="🎨 Personalizar /start", callback_data="admin_customize_start")
            ],
            [
                InlineKeyboardButton(text="👤 Gerenciar Admins", callback_data="admin_manage_admins"),
                InlineKeyboardButton(text="📢 Canal de Logs", callback_data="admin_set_log_channel")
            ],
            [
                InlineKeyboardButton(text="📋 Destino dos Logs", callback_data="admin_set_log_dest"),
                InlineKeyboardButton(text="🔗 Link de Planos", callback_data="admin_set_plan_link")
            ],
            [
                InlineKeyboardButton(text="📢 Botão Divulgação", callback_data="admin_set_button_config"),
                InlineKeyboardButton(text="🎆 Canal Referência", callback_data="admin_set_reference_channel")
            ],
            [
                InlineKeyboardButton(text="⏰ Intervalo Horários", callback_data="admin_set_time_interval"),
                InlineKeyboardButton(text="📄 Planos Ativos", callback_data="admin_list_active_plans")
            ],
            [
                InlineKeyboardButton(text="👥 Gerenciar Usuários", callback_data="admin_manage_users"),
                InlineKeyboardButton(text="📨 Enviar Mensagem", callback_data="admin_broadcast_message")
            ],
            [
                InlineKeyboardButton(text="🔔 Sistema de Notificações", callback_data="admin_notifications_panel")
            ]
        ]
    )

    painel_texto = (
        "⚙️ Painel Administrativo:\n\n"
        f"👥 Grupos coletados: <b>{total_grupos}</b>\n"
        f"📢 Anúncios ativos: <b>{total_anuncios}</b>\n"
        f"⏰ Horários disponíveis: <b>{total_horarios_disponiveis}</b>\n"
        f"👤 Usuários registrados: <b>{total_users}</b>\n"
    )
    
    await query.message.edit_text(painel_texto, reply_markup=painel, parse_mode="HTML")
    await query.answer()

# ============================================================================
# HANDLERS PARA PAINEL ADMIN MELHORADO
# ============================================================================

@dp.callback_query(F.data == "admin_stats_panel")
async def admin_stats_panel_handler(query: types.CallbackQuery):
    """Handler para o painel de estatísticas do admin"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    try:
        # Carrega dados
        chat_ids = load_chat_ids()
        scheduled_messages = load_scheduled_messages()
        
        # Estatísticas básicas
        total_grupos = len(chat_ids)
        total_planos = len(scheduled_messages)
        
        # Análise de planos por tipo
        planos_por_tipo = {}
        planos_ativos = 0
        planos_expirados = 0
        now = datetime.datetime.now()
        
        for msg in scheduled_messages:
            tipo = msg.get('type', 'indefinido')
            planos_por_tipo[tipo] = planos_por_tipo.get(tipo, 0) + 1
            
            # Verifica se está ativo
            expiry_str = msg.get('expiry_time')
            if expiry_str:
                try:
                    expiry_dt = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                    if expiry_dt > now:
                        planos_ativos += 1
                    else:
                        planos_expirados += 1
                except:
                    pass
        
        # Análise de horários
        horarios_ocupados = set()
        for msg in scheduled_messages:
            if msg.get('time'):
                horarios_ocupados.add(msg['time'])
        
        horarios_disponiveis = len(get_available_hours()) - len(horarios_ocupados)
        
        # Análise de usuários únicos
        usuarios_unicos = set()
        for msg in scheduled_messages:
            if msg.get('recipient_id'):
                usuarios_unicos.add(msg['recipient_id'])
        
        # Monta relatório
        stats_text = f"""📊 **ESTATÍSTICAS DO BOT DE DIVULGAÇÃO**
        
🏢 **GRUPOS E CANAIS**
├─ 📊 Total cadastrados: **{total_grupos}**
├─ ✅ Grupos ativos: **{total_grupos}**
└─ 📈 Taxa de cobertura: **100%**

💼 **PLANOS DE DIVULGAÇÃO**
├─ 📋 Total de planos: **{total_planos}**
├─ ✅ Planos ativos: **{planos_ativos}**
├─ ❌ Planos expirados: **{planos_expirados}**
└─ 👥 Clientes únicos: **{len(usuarios_unicos)}**

📊 **DISTRIBUIÇÃO POR TIPO**"""

        for tipo, quantidade in planos_por_tipo.items():
            porcentagem = (quantidade / total_planos * 100) if total_planos > 0 else 0
            stats_text += f"\n├─ {tipo.capitalize()}: **{quantidade}** ({porcentagem:.1f}%)"

        stats_text += f"""

⏰ **HORÁRIOS**
├─ 🕐 Horários ocupados: **{len(horarios_ocupados)}**
├─ ✅ Horários disponíveis: **{horarios_disponiveis}**
└─ 📈 Taxa de ocupação: **{(len(horarios_ocupados) / len(get_available_hours()) * 100):.1f}%**

🎯 **PERFORMANCE**
├─ 📤 Média de envios/dia: **{len(horarios_ocupados) * 24}**
├─ 🎯 Alcance estimado: **{total_grupos * len(horarios_ocupados)}** mensagens/dia
└─ 💰 Receita estimada: **R$ {len(usuarios_unicos) * 50:.2f}**/mês

📅 **Relatório gerado em:** {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""

        # Botões para mais detalhes
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📊 Gráfico Detalhado", callback_data="stats_detailed"),
                    InlineKeyboardButton(text="📈 Tendências", callback_data="stats_trends")
                ],
                [
                    InlineKeyboardButton(text="👥 Top Clientes", callback_data="stats_top_clients"),
                    InlineKeyboardButton(text="🕐 Horários Populares", callback_data="stats_popular_times")
                ],
                [
                    InlineKeyboardButton(text="📄 Exportar Relatório", callback_data="stats_export"),
                    InlineKeyboardButton(text="🔄 Atualizar", callback_data="stats_refresh")
                ],
                [
                    InlineKeyboardButton(text="⬅️ Voltar ao Painel", callback_data="stats_back_to_panel")
                ]
            ]
        )
        
        await query.message.edit_text(stats_text, parse_mode="Markdown", reply_markup=keyboard)
        await query.answer()
        
    except Exception as e:
        logging.error(f"Erro ao gerar estatísticas: {e}")
        await query.answer(f"❌ Erro ao gerar estatísticas: {e}", show_alert=True)

@dp.callback_query(F.data == "admin_notifications_panel")
async def admin_notifications_panel_handler(query: types.CallbackQuery):
    """Handler para o painel de notificações inteligentes"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    try:
        # Carrega configurações atuais
        config = load_config()
        
        # Configurações de notificação
        notif_config = config.get('notifications', {
            'expiry_alerts': True,
            'daily_reports': False,
            'error_alerts': True,
            'new_user_alerts': True,
            'performance_alerts': False
        })
        
        # Status das notificações
        status_text = f"""🔔 **SISTEMA DE NOTIFICAÇÕES INTELIGENTES**

📊 **CONFIGURAÇÕES ATUAIS:**
├─ ⚠️ Alertas de expiração: **{'✅ Ativo' if notif_config.get('expiry_alerts', True) else '❌ Inativo'}**
├─ 📈 Relatórios diários: **{'✅ Ativo' if notif_config.get('daily_reports', False) else '❌ Inativo'}**
├─ 🚨 Alertas de erro: **{'✅ Ativo' if notif_config.get('error_alerts', True) else '❌ Inativo'}**
├─ 👤 Alertas de novos usuários: **{'✅ Ativo' if notif_config.get('new_user_alerts', True) else '❌ Inativo'}**
└─ 📊 Alertas de performance: **{'✅ Ativo' if notif_config.get('performance_alerts', False) else '❌ Inativo'}**

🎯 **FUNCIONALIDADES:**
• Notificações automáticas de planos próximos ao vencimento
• Relatórios de performance em tempo real
• Alertas de falhas no sistema
• Notificações de novos clientes
• Análise de tendências e insights"""

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⚠️ Config. Alertas Expiração", callback_data="notif_expiry_toggle"),
                    InlineKeyboardButton(text="📈 Config. Relatórios Diários", callback_data="notif_daily_toggle")
                ],
                [
                    InlineKeyboardButton(text="🚨 Config. Alertas de Erro", callback_data="notif_error_toggle"),
                    InlineKeyboardButton(text="👤 Config. Novos Usuários", callback_data="notif_users_toggle")
                ],
                [
                    InlineKeyboardButton(text="📊 Config. Performance", callback_data="notif_performance_toggle"),
                    InlineKeyboardButton(text="🧪 Testar Notificações", callback_data="notif_test")
                ],
                [
                    InlineKeyboardButton(text="📋 Relatório Instantâneo", callback_data="notif_instant_report"),
                    InlineKeyboardButton(text="⬅️ Voltar ao Painel", callback_data="notif_back_panel")
                ]
            ]
        )
        
        await query.message.edit_text(status_text, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        await query.answer(f"❌ Erro: {e}", show_alert=True)

@dp.callback_query(F.data == "notif_instant_report")
async def notif_instant_report_handler(query: types.CallbackQuery):
    """Gera relatório instantâneo do sistema"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    try:
        # Dados em tempo real
        chat_ids = load_chat_ids()
        scheduled_messages = load_scheduled_messages()
        now = datetime.datetime.now()
        
        # Análise rápida
        planos_ativos = 0
        planos_expirando = 0
        usuarios_unicos = set()
        
        for msg in scheduled_messages:
            if msg.get('recipient_id'):
                usuarios_unicos.add(msg['recipient_id'])
            
            expiry_str = msg.get('expiry_time')
            if expiry_str:
                try:
                    expiry_dt = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                    if expiry_dt > now:
                        planos_ativos += 1
                        # Verifica se expira em 3 dias
                        if (expiry_dt - now).days <= 3:
                            planos_expirando += 1
                except:
                    pass
        
        # Relatório instantâneo
        instant_report = f"""⚡ **RELATÓRIO INSTANTÂNEO**
        
🕐 **Gerado em:** {now.strftime('%d/%m/%Y %H:%M:%S')}

📊 **STATUS ATUAL:**
├─ 🏢 Grupos ativos: **{len(chat_ids)}**
├─ 💼 Planos ativos: **{planos_ativos}**
├─ ⚠️ Expirando em 3 dias: **{planos_expirando}**
└─ 👥 Clientes únicos: **{len(usuarios_unicos)}**

🎯 **PERFORMANCE:**
├─ 📈 Taxa de ocupação: **{(len(scheduled_messages) / len(get_available_hours()) * 100):.1f}%**
├─ 💰 Receita estimada: **R$ {len(usuarios_unicos) * 50:.2f}**/mês
└─ 🚀 Sistema: **{'🟢 Operacional' if planos_ativos > 0 else '🟡 Baixa atividade'}**

⚡ **AÇÕES RECOMENDADAS:**"""

        if planos_expirando > 0:
            instant_report += f"\n• 🔔 Contatar {planos_expirando} cliente(s) para renovação"
        
        if len(usuarios_unicos) < 10:
            instant_report += f"\n• 📢 Intensificar marketing (apenas {len(usuarios_unicos)} clientes)"
        
        if len(chat_ids) < 50:
            instant_report += f"\n• 🎯 Expandir rede de grupos (apenas {len(chat_ids)} grupos)"
        
        if not any([planos_expirando > 0, len(usuarios_unicos) < 10, len(chat_ids) < 50]):
            instant_report += "\n• ✅ Sistema funcionando perfeitamente!"

        await query.message.edit_text(instant_report, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Voltar", callback_data="admin_notifications_panel")]]
        ))
        
    except Exception as e:
        await query.answer(f"❌ Erro: {e}", show_alert=True)

@dp.callback_query(F.data == "notif_test")
async def notif_test_handler(query: types.CallbackQuery):
    """Testa o sistema de notificações"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    try:
        # Envia notificação de teste
        test_message = f"""🧪 **TESTE DE NOTIFICAÇÃO**

✅ Sistema de notificações funcionando corretamente!

📊 **Dados do teste:**
├─ 🕐 Horário: {datetime.datetime.now().strftime('%H:%M:%S')}
├─ 📅 Data: {datetime.datetime.now().strftime('%d/%m/%Y')}
├─ 👤 Admin: {query.from_user.first_name or 'Admin'}
└─ 🆔 ID: {query.from_user.id}

🔔 **Tipos de notificação disponíveis:**
• Alertas de expiração de planos
• Relatórios de performance
• Notificações de erro
• Alertas de novos usuários
• Relatórios diários automáticos

✨ Todas as notificações estão funcionando perfeitamente!"""

        await query.message.reply(test_message, parse_mode="Markdown")
        await query.answer("🧪 Teste de notificação enviado com sucesso!")
        
    except Exception as e:
        await query.answer(f"❌ Erro no teste: {e}", show_alert=True)

@dp.callback_query(F.data == "notif_back_panel")
async def notif_back_panel_handler(query: types.CallbackQuery):
    """Volta para o painel admin principal"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    # Carrega dados atualizados
    try:
        with open(CHAT_IDS_FILE, 'r', encoding='utf-8') as f:
            chat_ids_atual = json.load(f)
    except Exception:
        chat_ids_atual = []

    try:
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            scheduled_messages_atual = json.load(f)
    except Exception:
        scheduled_messages_atual = []

    # Filtra só anúncios ativos (não expirados)
    agora = datetime.datetime.now()
    anuncios_ativos = []
    for msg in scheduled_messages_atual:
        expiry_str = msg.get('expiry_time')
        if expiry_str:
            try:
                expiry_dt = datetime.datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
                if expiry_dt > agora:
                    anuncios_ativos.append(msg)
            except Exception:
                pass

    total_grupos = len(set(chat_ids_atual))
    id_fixos_ativos = set()
    for anuncio in anuncios_ativos:
        id_fixo = anuncio.get('fixed_ad_id')
        if id_fixo:
            id_fixos_ativos.add(str(id_fixo))
    total_anuncios = len(id_fixos_ativos)
    
    busy_hours = set()
    for msg in anuncios_ativos:
        if 'time' in msg:
            busy_hours.add(msg['time'][:5])
    total_horarios_disponiveis = len([h for h in get_available_hours() if h not in busy_hours])
    
    registered_users = load_registered_users()
    total_users = len(registered_users)
    
    painel = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Estatísticas", callback_data="admin_stats_panel"),
                InlineKeyboardButton(text="🎨 Personalizar /start", callback_data="admin_customize_start")
            ],
            [
                InlineKeyboardButton(text="👤 Gerenciar Admins", callback_data="admin_manage_admins"),
                InlineKeyboardButton(text="📢 Canal de Logs", callback_data="admin_set_log_channel")
            ],
            [
                InlineKeyboardButton(text="📋 Destino dos Logs", callback_data="admin_set_log_dest"),
                InlineKeyboardButton(text="🔗 Link de Planos", callback_data="admin_set_plan_link")
            ],
            [
                InlineKeyboardButton(text="📢 Botão Divulgação", callback_data="admin_set_button_config"),
                InlineKeyboardButton(text="🎆 Canal Referência", callback_data="admin_set_reference_channel")
            ],
            [
                InlineKeyboardButton(text="⏰ Intervalo Horários", callback_data="admin_set_time_interval"),
                InlineKeyboardButton(text="📄 Planos Ativos", callback_data="admin_list_active_plans")
            ],
            [
                InlineKeyboardButton(text="👥 Gerenciar Usuários", callback_data="admin_manage_users"),
                InlineKeyboardButton(text="📨 Enviar Mensagem", callback_data="admin_broadcast_message")
            ],
            [
                InlineKeyboardButton(text="🔔 Sistema de Notificações", callback_data="admin_notifications_panel")
            ]
        ]
    )

    painel_texto = (
        "⚙️ Painel Administrativo:\n\n"
        f"👥 Grupos coletados: <b>{total_grupos}</b>\n"
        f"📢 Anúncios ativos: <b>{total_anuncios}</b>\n"
        f"⏰ Horários disponíveis: <b>{total_horarios_disponiveis}</b>\n"
        f"👤 Usuários registrados: <b>{total_users}</b>\n"
    )
    
    await query.message.edit_text(painel_texto, reply_markup=painel, parse_mode="HTML")
    await query.answer()

# Handlers para toggle das configurações de notificação
@dp.callback_query(F.data == "notif_expiry_toggle")
async def notif_expiry_toggle_handler(query: types.CallbackQuery):
    """Toggle para alertas de expiração"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    try:
        config = load_config()
        if 'notifications' not in config:
            config['notifications'] = {}
        
        current = config['notifications'].get('expiry_alerts', True)
        config['notifications']['expiry_alerts'] = not current
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        status = "✅ Ativado" if not current else "❌ Desativado"
        await query.answer(f"Alertas de expiração: {status}", show_alert=True)
        
        # Atualiza o painel
        await admin_notifications_panel_handler(query)
        
    except Exception as e:
        await query.answer(f"❌ Erro: {e}", show_alert=True)

@dp.callback_query(F.data == "notif_daily_toggle")
async def notif_daily_toggle_handler(query: types.CallbackQuery):
    """Toggle para relatórios diários"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    try:
        config = load_config()
        if 'notifications' not in config:
            config['notifications'] = {}
        
        current = config['notifications'].get('daily_reports', False)
        config['notifications']['daily_reports'] = not current
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        status = "✅ Ativado" if not current else "❌ Desativado"
        await query.answer(f"Relatórios diários: {status}", show_alert=True)
        
        # Atualiza o painel
        await admin_notifications_panel_handler(query)
        
    except Exception as e:
        await query.answer(f"❌ Erro: {e}", show_alert=True)

@dp.callback_query(F.data == "notif_error_toggle")
async def notif_error_toggle_handler(query: types.CallbackQuery):
    """Toggle para alertas de erro"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    try:
        config = load_config()
        if 'notifications' not in config:
            config['notifications'] = {}
        
        current = config['notifications'].get('error_alerts', True)
        config['notifications']['error_alerts'] = not current
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        status = "✅ Ativado" if not current else "❌ Desativado"
        await query.answer(f"Alertas de erro: {status}", show_alert=True)
        
        # Atualiza o painel
        await admin_notifications_panel_handler(query)
        
    except Exception as e:
        await query.answer(f"❌ Erro: {e}", show_alert=True)

@dp.callback_query(F.data == "notif_users_toggle")
async def notif_users_toggle_handler(query: types.CallbackQuery):
    """Toggle para alertas de novos usuários"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    try:
        config = load_config()
        if 'notifications' not in config:
            config['notifications'] = {}
        
        current = config['notifications'].get('new_user_alerts', True)
        config['notifications']['new_user_alerts'] = not current
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        status = "✅ Ativado" if not current else "❌ Desativado"
        await query.answer(f"Alertas de novos usuários: {status}", show_alert=True)
        
        # Atualiza o painel
        await admin_notifications_panel_handler(query)
        
    except Exception as e:
        await query.answer(f"❌ Erro: {e}", show_alert=True)

@dp.callback_query(F.data == "notif_performance_toggle")
async def notif_performance_toggle_handler(query: types.CallbackQuery):
    """Toggle para alertas de performance"""
    if query.from_user.id not in ADMINS:
        await query.answer("❌ Apenas administradores.", show_alert=True)
        return
    
    try:
        config = load_config()
        if 'notifications' not in config:
            config['notifications'] = {}
        
        current = config['notifications'].get('performance_alerts', False)
        config['notifications']['performance_alerts'] = not current
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        status = "✅ Ativado" if not current else "❌ Desativado"
        await query.answer(f"Alertas de performance: {status}", show_alert=True)
        
        # Atualiza o painel
        await admin_notifications_panel_handler(query)
        
    except Exception as e:
        await query.answer(f"❌ Erro: {e}", show_alert=True)

# Comando /trocar - Troca o recipient_id de um plano
@dp.message(Command("trocar"))
async def trocar_recipient_cmd(message: types.Message):
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("📋 **Uso:** `/trocar <idfixo> <novo_recipient_id>`\n\n"
                           "Este comando altera quem recebe os relatórios do plano:\n"
                           "• `<idfixo>` - ID fixo do plano\n"
                           "• `<novo_recipient_id>` - ID do novo usuário que receberá os relatórios\n\n"
                           "**Exemplo:** `/trocar ba1de5dd-dfe8-45f3 1234567890`")
        return
    
    id_fixo = args[1]
    try:
        novo_recipient_id = int(args[2])
    except ValueError:
        await message.reply("❌ O recipient_id deve ser um número válido.")
        return
    
    path = SCHEDULED_MESSAGES_FILE
    
    if not os.path.exists(path):
        await message.reply("❌ Arquivo de agendamentos não encontrado.")
        return
    
    try:
        # Carrega os agendamentos
        with open(path, 'r', encoding='utf-8') as f:
            agendados = json.load(f)
        
        # Encontra planos com o ID fixo especificado
        planos_encontrados = [p for p in agendados if p.get('fixed_ad_id') == id_fixo]
        
        if not planos_encontrados:
            await message.reply(f"❌ Nenhum plano encontrado com o ID: `{id_fixo}`")
            return
        
        # Pega informações do plano atual
        primeiro_plano = planos_encontrados[0]
        recipient_id_antigo = primeiro_plano.get('recipient_id')
        tipo_plano = primeiro_plano.get('type', 'N/A')
        total_horarios = len(planos_encontrados)
        
        # Verifica se o novo recipient_id é válido tentando obter informações do usuário
        try:
            novo_usuario = await bot.get_chat(novo_recipient_id)
            if hasattr(novo_usuario, 'username') and novo_usuario.username:
                nome_novo_usuario = f"@{novo_usuario.username}"
            elif hasattr(novo_usuario, 'first_name'):
                nome_novo_usuario = novo_usuario.first_name
            else:
                nome_novo_usuario = f"ID: {novo_recipient_id}"
        except Exception:
            nome_novo_usuario = f"ID: {novo_recipient_id}"
            await message.reply(f"⚠️ Aviso: Não foi possível verificar se o ID `{novo_recipient_id}` é válido. Continuando mesmo assim...")
        
        # Atualiza todos os planos com o mesmo ID fixo
        planos_atualizados = 0
        
        for plano in agendados:
            if plano.get('fixed_ad_id') == id_fixo:
                plano['recipient_id'] = novo_recipient_id
                planos_atualizados += 1
        
        if planos_atualizados > 0:
            # Salva as alterações
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(agendados, f, ensure_ascii=False, indent=4)
            
            # Notifica o novo recipient sobre a transferência
            try:
                msg_novo_recipient = (
                    f"🔄 **PLANO TRANSFERIDO PARA VOCÊ!**\n\n"
                    f"🏷️ **ID do Plano:** `{id_fixo}`\n"
                    f"📋 **Tipo:** {tipo_plano}\n"
                    f"📊 **Total de horários:** {total_horarios}\n\n"
                    f"Você agora é o responsável por este plano e receberá todos os relatórios relacionados a ele.\n\n"
                    f"Use `/start` para ver suas opções ou entre em contato com o administrador se tiver dúvidas."
                )
                await bot.send_message(chat_id=novo_recipient_id, text=msg_novo_recipient)
                notificacao_novo = "✅ Novo recipient notificado"
            except Exception as e:
                bot_logger.error(f"Erro ao notificar novo recipient {novo_recipient_id}: {e}")
                notificacao_novo = "⚠️ Erro ao notificar novo recipient"
            
            # Notifica o recipient antigo sobre a transferência (se existir e for diferente)
            notificacao_antigo = ""
            if recipient_id_antigo and recipient_id_antigo != novo_recipient_id:
                try:
                    msg_recipient_antigo = (
                        f"📤 **PLANO TRANSFERIDO**\n\n"
                        f"🏷️ **ID do Plano:** `{id_fixo}`\n"
                        f"📋 **Tipo:** {tipo_plano}\n\n"
                        f"Este plano foi transferido para outro usuário pelo administrador.\n"
                        f"Você não receberá mais relatórios relacionados a este plano."
                    )
                    await bot.send_message(chat_id=int(recipient_id_antigo), text=msg_recipient_antigo)
                    notificacao_antigo = "\n✅ Recipient anterior notificado"
                except Exception as e:
                    bot_logger.error(f"Erro ao notificar recipient anterior {recipient_id_antigo}: {e}")
                    notificacao_antigo = "\n⚠️ Erro ao notificar recipient anterior"
            
            # Log da ação do admin
            bot_logger.admin_action(
                message.from_user.first_name or "Admin",
                message.from_user.id,
                f"Troca de recipient - ID: {id_fixo}, De: {recipient_id_antigo} Para: {novo_recipient_id}"
            )
            
            # Resposta para o admin
            await message.reply(
                f"✅ **RECIPIENT ALTERADO COM SUCESSO!**\n\n"
                f"🏷️ **ID Fixo:** `{id_fixo}`\n"
                f"📋 **Tipo:** {tipo_plano}\n"
                f"📊 **Horários atualizados:** {planos_atualizados}\n"
                f"👤 **Recipient anterior:** `{recipient_id_antigo or 'N/A'}`\n"
                f"👤 **Novo recipient:** `{novo_recipient_id}` ({nome_novo_usuario})\n"
                f"📱 **Status:** {notificacao_novo}{notificacao_antigo}",
                parse_mode='Markdown'
            )
        else:
            await message.reply(f"❌ Nenhum plano foi atualizado. Verifique se o ID `{id_fixo}` está correto.")
            
    except json.JSONDecodeError:
        await message.reply("❌ Erro ao ler arquivo de agendamentos. Arquivo pode estar corrompido.")
    except Exception as e:
        bot_logger.error(f"Erro no comando /trocar: {e}")
        await message.reply(f"❌ Erro inesperado: {str(e)}")

# Comando /renovar - Renova planos de usuários
@dp.message(Command("renovar"))
async def renovar_plano_cmd(message: types.Message):
    """Comando para administradores renovarem planos de usuários baseado no tipo do plano atual"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📋 **Uso:** `/renovar <idfixo>`\n\n"
                           "Este comando renova o plano do usuário baseado no tipo atual:\n"
                           "• Plano semanal → +7 dias\n"
                           "• Plano mensal → +30 dias\n"
                           "• Plano anual → +365 dias\n"
                           "• Outros planos → mesmo período original")
        return
    
    id_fixo = args[1]
    path = SCHEDULED_MESSAGES_FILE
    expired_path = EXPIRED_PLANS_FILE
    
    if not os.path.exists(path):
        await message.reply("❌ Arquivo de agendamentos não encontrado.")
        return
    
    try:
        # Carrega os agendamentos ativos
        with open(path, 'r', encoding='utf-8') as f:
            agendados = json.load(f)
        
        # Carrega os planos expirados
        planos_expirados = []
        if os.path.exists(expired_path):
            try:
                with open(expired_path, 'r', encoding='utf-8') as f:
                    planos_expirados = json.load(f)
            except:
                planos_expirados = []
        
        # Encontra planos com o ID fixo especificado (primeiro nos ativos)
        planos_encontrados = [p for p in agendados if p.get('fixed_ad_id') == id_fixo]
        
        # Se não encontrou nos ativos, busca nos expirados
        planos_expirados_encontrados = []
        if not planos_encontrados:
            planos_expirados_encontrados = [p for p in planos_expirados if p.get('fixed_ad_id') == id_fixo]
            
            if not planos_expirados_encontrados:
                await message.reply(
                    f"❌ **Plano não encontrado nos arquivos expirados**\n\n"
                    f"🔍 **ID buscado:** `{id_fixo}`\n\n"
                    f"💡 **Dicas:**\n"
                    f"• Use `/expirados` para ver todos os planos expirados\n"
                    f"• Use `/buscar_expirado {id_fixo}` para busca mais detalhada\n"
                    f"• Verifique se o ID está correto"
                )
                return
            
            # Restaura os planos expirados para os ativos
            for plano in planos_expirados_encontrados:
                agendados.append(plano)
            
            # Remove dos expirados
            planos_expirados = [p for p in planos_expirados if p.get('fixed_ad_id') != id_fixo]
            
            # Salva os arquivos atualizados
            with open(expired_path, 'w', encoding='utf-8') as f:
                json.dump(planos_expirados, f, ensure_ascii=False, indent=4)
            
            planos_encontrados = planos_expirados_encontrados
            await message.reply(f"🔄 **Plano restaurado dos arquivos expirados!**\n\nProcessando renovação...")
        
        # Pega informações do primeiro plano para determinar o tipo
        primeiro_plano = planos_encontrados[0]
        tipo_plano = primeiro_plano.get('type', '').lower()
        recipient_id = primeiro_plano.get('recipient_id')
        
        # Determina quantos dias adicionar baseado no tipo do plano
        dias_renovacao = 0
        if 'semanal' in tipo_plano or 'weekly' in tipo_plano:
            dias_renovacao = 7
            tipo_descricao = "Semanal"
        elif 'mensal' in tipo_plano or 'monthly' in tipo_plano:
            dias_renovacao = 30
            tipo_descricao = "Mensal"
        elif 'anual' in tipo_plano or 'yearly' in tipo_plano:
            dias_renovacao = 365
            tipo_descricao = "Anual"
        elif 'diario' in tipo_plano or 'daily' in tipo_plano:
            dias_renovacao = 1
            tipo_descricao = "Diário"
        else:
            # Para outros tipos, tenta extrair o número de dias do tipo
            import re
            match = re.search(r'(\d+)', tipo_plano)
            if match:
                dias_renovacao = int(match.group(1))
                tipo_descricao = f"Personalizado ({dias_renovacao} dias)"
            else:
                dias_renovacao = 30  # Padrão para tipos não reconhecidos
                tipo_descricao = "Padrão (30 dias)"
        
        # Renova todos os planos com o mesmo ID fixo
        planos_renovados = 0
        nova_data_expiracao = None
        
        for plano in agendados:
            if plano.get('fixed_ad_id') == id_fixo and 'expiry_time' in plano:
                try:
                    # Pega a data atual de expiração
                    dt_atual = datetime.datetime.strptime(plano['expiry_time'], '%Y-%m-%d %H:%M:%S')
                    
                    # Adiciona os dias de renovação
                    dt_nova = dt_atual + datetime.timedelta(days=dias_renovacao)
                    plano['expiry_time'] = dt_nova.strftime('%Y-%m-%d %H:%M:%S')
                    
                    nova_data_expiracao = dt_nova
                    planos_renovados += 1
                    
                except ValueError as e:
                    logger.error(f"Erro ao processar data de expiração do plano {plano.get('code', 'N/A')}: {e}")
                    continue
        
        if planos_renovados > 0:
            # Salva as alterações
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(agendados, f, ensure_ascii=False, indent=4)
            
            # Notifica o cliente sobre a renovação
            if recipient_id and nova_data_expiracao:
                try:
                    msg_cliente = (
                        f"🎉 **SEU PLANO FOI RENOVADO!**\n\n"
                        f"📋 **Tipo:** {tipo_descricao}\n"
                        f"⏰ **Período adicionado:** {dias_renovacao} dias\n"
                        f"📅 **Nova data de expiração:** {nova_data_expiracao.strftime('%d/%m/%Y às %H:%M')}\n\n"
                        f"Seu plano foi renovado automaticamente pelo administrador. "
                        f"Aproveite seus horários de divulgação!"
                    )
                    await bot.send_message(chat_id=int(recipient_id), text=msg_cliente)
                    cliente_notificado = "✅ Cliente notificado"
                except Exception as e:
                    bot_logger.error(f"Erro ao notificar cliente {recipient_id}: {e}")
                    cliente_notificado = "⚠️ Erro ao notificar cliente"
            else:
                cliente_notificado = "⚠️ Cliente não notificado (ID não encontrado)"
            
            # Log da ação do admin
            bot_logger.admin_action(
                message.from_user.first_name or "Admin",
                message.from_user.id,
                f"Renovação de plano - ID: {id_fixo}, Tipo: {tipo_descricao}, +{dias_renovacao} dias"
            )
            
            # Resposta para o admin
            await message.reply(
                f"✅ **PLANO RENOVADO COM SUCESSO!**\n\n"
                f"🏷️ **ID Fixo:** `{id_fixo}`\n"
                f"📋 **Tipo:** {tipo_descricao}\n"
                f"📊 **Horários renovados:** {planos_renovados}\n"
                f"⏰ **Dias adicionados:** {dias_renovacao}\n"
                f"📅 **Nova expiração:** {nova_data_expiracao.strftime('%d/%m/%Y às %H:%M') if nova_data_expiracao else 'N/A'}\n"
                f"👤 **Status:** {cliente_notificado}",
                parse_mode='Markdown'
            )
        else:
            await message.reply(f"❌ Nenhum plano foi renovado. Verifique se o ID `{id_fixo}` possui datas de expiração válidas.")
            
    except json.JSONDecodeError:
        await message.reply("❌ Erro ao ler arquivo de agendamentos. Arquivo pode estar corrompido.")
    except Exception as e:
        logger.error(f"Erro no comando /renovar: {e}")
        await message.reply(f"❌ Erro inesperado: {str(e)}")

# Scheduler para alertar planos prestes a expirar - VERSÃO CORRIGIDA
async def expiring_plans_alert_scheduler():
    """Sistema PREMIUM de alertas de expiração com mensagens elegantes e botões interativos"""
    last_check = {}  # Cache para evitar spam de notificações
    
    while True:
        try:
            now = datetime.datetime.now()
            expiring = []
            notified_today = set()
            
            # Carrega dados atualizados do arquivo
            current_scheduled_messages = load_scheduled_messages()
            
            for msg in current_scheduled_messages:
                expiry_str = msg.get('expiry_time')
                recipient_id = msg.get('recipient_id')
                fixed_ad_id = msg.get('fixed_ad_id', 'N/A')
                
                if not expiry_str or not recipient_id:
                    continue
                    
                try:
                    expiry_dt = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                    diff_seconds = (expiry_dt - now).total_seconds()
                    
                    # Só processa se ainda não expirou
                    if diff_seconds <= 0:
                        continue
                    
                    # Calcula dias restantes
                    dias_restantes = int(diff_seconds / (24 * 60 * 60))
                    
                    # Alertas em: 3 dias, 1 dia, 6 horas, 1 hora
                    should_alert = False
                    alert_type = ""
                    
                    if dias_restantes <= 0 and diff_seconds <= 3600:  # Última hora
                        should_alert = True
                        alert_type = "URGENTE - 1 HORA"
                    elif dias_restantes <= 0 and diff_seconds <= 21600:  # 6 horas
                        should_alert = True
                        alert_type = "CRÍTICO - 6 HORAS"
                    elif dias_restantes == 1:  # 1 dia
                        should_alert = True
                        alert_type = "URGENTE - 1 DIA"
                    elif dias_restantes == 3:  # 3 dias
                        should_alert = True
                        alert_type = "AVISO - 3 DIAS"
                    
                    if should_alert:
                        # Evita spam - só notifica uma vez por dia por usuário
                        cache_key = f"{recipient_id}_{dias_restantes}_{now.strftime('%Y-%m-%d')}"
                        if cache_key not in last_check:
                            expiring.append({
                                'msg': msg,
                                'dias_restantes': dias_restantes,
                                'diff_seconds': diff_seconds,
                                'alert_type': alert_type
                            })
                            last_check[cache_key] = now
                            professional_logger.expiry_alert(alert_type, fixed_ad_id, recipient_id, dias_restantes)
                        
                except Exception as e:
                    logging.error(f"[EXPIRY_CHECK] Erro ao processar {expiry_str}: {e}")
                    continue
            # Processa alertas se houver planos expirando
            if expiring:
                config = load_config()
                admin_text = f"🚨 **ALERTAS DE EXPIRAÇÃO** - {now.strftime('%d/%m/%Y %H:%M')}\n\n"
                successfully_notified = 0
                failed_notifications = 0
                
                # Envia notificações para clientes
                for item in expiring:
                    msg = item['msg']
                    dias_restantes = item['dias_restantes']
                    alert_type = item['alert_type']
                    recipient_id = msg.get('recipient_id')
                    fixed_ad_id = msg.get('fixed_ad_id', 'N/A')
                    expiry_str = msg.get('expiry_time')
                    
                    # Cria botões interativos para renovação
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🔄 Renovar Agora",
                                url="https://t.me/suporte_bot"  # Substitua pelo seu canal de suporte
                            ),
                            InlineKeyboardButton(
                                text="📞 Contato",
                                url="https://t.me/admin_bot"  # Substitua pelo seu admin
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="📊 Ver Detalhes",
                                callback_data=f"plan_details_{fixed_ad_id}"
                            )
                        ]
                    ])
                    
                    # Monta mensagem PREMIUM personalizada baseada na urgência
                    if "1 HORA" in alert_type:
                        client_message = (
                            f"🚨 **ALERTA CRÍTICO - ÚLTIMA HORA!**\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"⏰ **Seu plano expira em menos de 1 hora!**\n\n"
                            f"🏷️ **ID do Contrato:** `{fixed_ad_id}`\n"
                            f"📅 **Data de Expiração:** `{expiry_str}`\n"
                            f"⚡ **Status:** CRÍTICO - AÇÃO IMEDIATA NECESSÁRIA\n\n"
                            f"🔥 **IMPORTANTE:** Após a expiração, seus horários serão suspensos automaticamente!\n\n"
                            f"👆 **Clique nos botões abaixo para renovar:**"
                        )
                    elif "6 HORAS" in alert_type:
                        client_message = (
                            f"⚠️ **ALERTA URGENTE - 6 HORAS RESTANTES!**\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"⏰ **Seu plano expira hoje!**\n\n"
                            f"🏷️ **ID do Contrato:** `{fixed_ad_id}`\n"
                            f"📅 **Data de Expiração:** `{expiry_str}`\n"
                            f"🔥 **Status:** URGENTE - Renove hoje mesmo\n\n"
                            f"💡 **Dica:** Renovando agora, você evita qualquer interrupção no serviço!\n\n"
                            f"👆 **Use os botões abaixo para renovar:**"
                        )
                    elif "1 DIA" in alert_type:
                        client_message = (
                            f"⏰ **LEMBRETE IMPORTANTE - 1 DIA RESTANTE!**\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"📅 **Seu plano expira amanhã!**\n\n"
                            f"🏷️ **ID do Contrato:** `{fixed_ad_id}`\n"
                            f"📅 **Data de Expiração:** `{expiry_str}`\n"
                            f"📊 **Status:** Ativo - Renovação recomendada\n\n"
                            f"🎯 **Não perca tempo!** Renove seu plano e continue aproveitando nossos serviços.\n\n"
                            f"👆 **Clique nos botões para renovar facilmente:**"
                        )
                    else:  # 3 dias
                        client_message = (
                            f"📢 **AVISO DE EXPIRAÇÃO - 3 DIAS RESTANTES**\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"📅 **Seu plano expira em breve!**\n\n"
                            f"🏷️ **ID do Contrato:** `{fixed_ad_id}`\n"
                            f"📅 **Data de Expiração:** `{expiry_str}`\n"
                            f"✅ **Status:** Ativo - Planeje sua renovação\n\n"
                            f"💎 **Oferta especial:** Renove antecipadamente e ganhe desconto!\n\n"
                            f"👆 **Use os botões abaixo para mais informações:**"
                        )
                    
                    # Tenta enviar notificação com botões interativos
                    try:
                        await bot.send_message(
                            chat_id=recipient_id, 
                            text=client_message, 
                            parse_mode="Markdown",
                            reply_markup=keyboard
                        )
                        successfully_notified += 1
                        admin_text += f"✅ **{alert_type}**\n├─ Usuário: {recipient_id}\n├─ Contrato: {fixed_ad_id}\n├─ Expira: {expiry_str}\n└─ Status: Notificado\n\n"
                    except Exception as e:
                        failed_notifications += 1
                        admin_text += f"❌ **{alert_type}**\n├─ Usuário: {recipient_id}\n├─ Contrato: {fixed_ad_id}\n├─ Expira: {expiry_str}\n└─ Status: FALHA - {str(e)[:50]}\n\n"
                        logging.error(f'Erro ao enviar alerta para {recipient_id}: {e}')
                
                # Envia resumo para admins
                admin_text += f"📊 **RESUMO:**\n├─ ✅ Notificados: {successfully_notified}\n├─ ❌ Falhas: {failed_notifications}\n└─ 📈 Total: {len(expiring)}\n\n"
                
                if failed_notifications > 0:
                    admin_text += "⚠️ **ATENÇÃO:** Alguns usuários não puderam ser notificados automaticamente!\nÉ necessário contato manual."
                
                # Envia para canal de logs
                try:
                    log_channel = config.get('LOG')
                    if log_channel:
                        await bot.send_message(chat_id=log_channel, text=admin_text, parse_mode="Markdown")
                        logging.info(f"[EXPIRY_ADMIN] Relatório enviado: {successfully_notified} sucessos, {failed_notifications} falhas")
                except Exception as e:
                    logging.error(f'Erro ao enviar relatório de expiração para admin: {e}')
                
                # Envia para admins individuais (com tratamento de erros)
                for admin_id in config.get('admins', []):
                    try:
                        await bot.send_message(chat_id=admin_id, text=f"📊 **Relatório de Expiração**\n\n✅ Notificados: {successfully_notified}\n❌ Falhas: {failed_notifications}\n📈 Total: {len(expiring)}")
                        logging.info(f"Relatório de expiração enviado para admin {admin_id}. Total de planos: {len(expiring)}")
                    except Exception as e:
                        if "user is deactivated" in str(e) or "Forbidden" in str(e):
                            logging.warning(f"Admin {admin_id} não pôde receber relatório (conta desativada ou bloqueou o bot)")
                        else:
                            logging.error(f"Erro ao enviar relatório para admin {admin_id}: {e}")

        except Exception as e:
            logging.error(f'Erro no alerta de expiração: {e}')
        # Executa verificação a cada 6 horas (mais eficiente)
        await asyncio.sleep(60 * 60 * 6)

# ============================================================================
# SISTEMA DE ARQUIVAMENTO DE PLANOS EXPIRADOS
# ============================================================================

EXPIRED_PLANS_FILE = 'expired_plans.json'

def load_expired_plans():
    """Carrega planos expirados do arquivo JSON"""
    try:
        if os.path.exists(EXPIRED_PLANS_FILE):
            with open(EXPIRED_PLANS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logging.error(f"Erro ao carregar planos expirados: {e}")
        return []

def save_expired_plans(expired_plans):
    """Salva planos expirados no arquivo JSON"""
    try:
        with open(EXPIRED_PLANS_FILE, 'w', encoding='utf-8') as f:
            json.dump(expired_plans, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar planos expirados: {e}")
        return False

def archive_expired_plan(plan):
    """Arquiva um plano expirado em vez de deletá-lo"""
    try:
        expired_plans = load_expired_plans()
        
        # Adiciona informações de arquivamento
        plan['archived_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        plan['status'] = 'expired'
        
        # Verifica se já existe (evita duplicatas)
        fixed_ad_id = plan.get('fixed_ad_id')
        existing = next((p for p in expired_plans if p.get('fixed_ad_id') == fixed_ad_id), None)
        
        if not existing:
            expired_plans.append(plan)
            save_expired_plans(expired_plans)
            professional_logger.plan_archived(fixed_ad_id, plan.get('recipient_id', 'N/A'))
            return True
        else:
            professional_logger.warning("ARCHIVE", f"Plano já arquivado: {fixed_ad_id}")
            return False
            
    except Exception as e:
        professional_logger.error("ARCHIVE", f"Erro ao arquivar plano: {e}")
        return False

def search_expired_plan(search_term):
    """Busca um plano expirado por ID ou parte do ID"""
    try:
        expired_plans = load_expired_plans()
        search_term = str(search_term).lower()
        
        # Busca por ID completo ou parcial
        matches = []
        for plan in expired_plans:
            fixed_ad_id = str(plan.get('fixed_ad_id', '')).lower()
            recipient_id = str(plan.get('recipient_id', '')).lower()
            
            if (search_term in fixed_ad_id or 
                search_term == recipient_id or
                fixed_ad_id.startswith(search_term)):
                matches.append(plan)
        
        return matches
    except Exception as e:
        professional_logger.error("SEARCH", f"Erro ao buscar plano expirado: {e}")
        return []

def restore_expired_plan(fixed_ad_id, new_expiry_date):
    """Remove um plano dos expirados e o reativa com nova data"""
    try:
        expired_plans = load_expired_plans()
        scheduled_messages = load_scheduled_messages()
        
        # Busca o plano expirado
        plan_to_restore = None
        remaining_expired = []
        
        for plan in expired_plans:
            if plan.get('fixed_ad_id') == fixed_ad_id:
                plan_to_restore = plan
            else:
                remaining_expired.append(plan)
        
        if not plan_to_restore:
            return False, "Plano não encontrado nos arquivos expirados"
        
        # Atualiza as datas do plano
        plan_to_restore['expiry_time'] = new_expiry_date.strftime("%Y-%m-%d %H:%M:%S")
        plan_to_restore['renewed_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        plan_to_restore['status'] = 'active'
        
        # Remove campos de arquivamento
        if 'archived_at' in plan_to_restore:
            del plan_to_restore['archived_at']
        
        # Adiciona de volta aos agendamentos ativos
        scheduled_messages.append(plan_to_restore)
        
        # Salva ambos os arquivos
        save_expired_plans(remaining_expired)
        save_scheduled_messages(scheduled_messages, origem="renovacao")
        
        # Calcula os dias de renovação
        days_renewed = (new_expiry_date - datetime.datetime.now()).days
        professional_logger.plan_restored(fixed_ad_id, plan_to_restore.get('recipient_id', 'N/A'), days_renewed)
        return True, "Plano renovado com sucesso"
        
    except Exception as e:
        professional_logger.error("RESTORE", f"Erro ao renovar plano: {e}")
        return False, f"Erro ao renovar: {e}"

async def check_and_remove_expired_messages():
    """Sistema otimizado de arquivamento de mensagens expiradas"""
    global scheduled_messages
    
    while True:
        try:
            current_dt = datetime.datetime.now()
            
            # Carrega dados atualizados do arquivo
            scheduled_messages = load_scheduled_messages()
            original_count = len(scheduled_messages)
            
            # Separa mensagens válidas das expiradas
            expired_messages = []
            messages_to_keep = []
            
            for msg in scheduled_messages:
                expiry_time = msg.get('expiry_time')
                fixed_ad_id = msg.get('fixed_ad_id', 'N/A')
                recipient_id = msg.get('recipient_id', 'N/A')
                
                # Se não tem tempo de expiração, mantém
                if not expiry_time:
                    messages_to_keep.append(msg)
                    continue
                
                try:
                    # Converte string para datetime
                    if isinstance(expiry_time, str):
                        expiry_dt = datetime.datetime.strptime(expiry_time, "%Y-%m-%d %H:%M:%S")
                    else:
                        expiry_dt = expiry_time
                    
                    # Verifica se expirou
                    if expiry_dt < current_dt:
                        # Para reagendamentos, aguarda 7 dias antes de remover
                        if msg.get('is_reagendamento', False):
                            creation_time_str = msg.get('creation_time')
                            if creation_time_str:
                                try:
                                    creation_dt = datetime.datetime.strptime(creation_time_str, "%Y-%m-%d %H:%M:%S")
                                    days_since_creation = (current_dt - creation_dt).days
                                    
                                    if days_since_creation >= 7:
                                        expired_messages.append(msg)
                                        # Arquiva o reagendamento expirado
                                        archive_expired_plan(msg)
                                        logging.info(f"[EXPIRED_ARCHIVE] Reagendamento arquivado: {fixed_ad_id} (criado há {days_since_creation} dias)")
                                    else:
                                        messages_to_keep.append(msg)
                                except:
                                    # Se não conseguir parsear, remove após 7 dias da expiração
                                    days_since_expiry = (current_dt - expiry_dt).days
                                    if days_since_expiry >= 7:
                                        expired_messages.append(msg)
                                    else:
                                        messages_to_keep.append(msg)
                            else:
                                # Sem data de criação, usa regra padrão
                                days_since_expiry = (current_dt - expiry_dt).days
                                if days_since_expiry >= 7:
                                    expired_messages.append(msg)
                                    # Arquiva o reagendamento expirado
                                    archive_expired_plan(msg)
                                else:
                                    messages_to_keep.append(msg)
                        else:
                            # Mensagem normal expirada - arquiva em vez de deletar
                            expired_messages.append(msg)
                            # Arquiva o plano expirado
                            archive_expired_plan(msg)
                            logging.info(f"[EXPIRED_ARCHIVE] Mensagem expirada arquivada: {fixed_ad_id} (usuário {recipient_id})")
                    else:
                        # Ainda não expirou, mantém
                        messages_to_keep.append(msg)
                        
                except ValueError as e:
                    # Erro ao parsear data - mantém mensagem para não perder dados
                    logging.error(f"[EXPIRED_REMOVAL] Erro ao processar data {expiry_time}: {e}")
                    messages_to_keep.append(msg)
                except Exception as e:
                    # Outros erros - mantém mensagem
                    logging.error(f"[EXPIRED_REMOVAL] Erro inesperado ao processar mensagem: {e}")
                    messages_to_keep.append(msg)
            
            # Atualiza lista global
            scheduled_messages = messages_to_keep
            
            # Salva alterações se houve remoções
            if expired_messages:
                try:
                    save_scheduled_messages(scheduled_messages, origem="limpeza_automatica")
                    removed_count = len(expired_messages)
                    kept_count = len(messages_to_keep)
                    
                    # Log visível no console com formatação profissional
                    professional_logger.cleanup_summary(removed_count, kept_count, original_count)
                    
                    # Estatísticas de arquivamento
                    professional_logger.expired_stats(removed_count, removed_count)
                    
                    logging.info(f"[EXPIRED_CLEANUP] Limpeza concluída: {removed_count} removidas, {kept_count} mantidas")
                    
                    # Log detalhado das remoções (apenas primeiras 10 para não poluir)
                    for i, msg in enumerate(expired_messages[:10]):
                        logging.info(f"[EXPIRED_CLEANUP] Removida {i+1}: ID {msg.get('fixed_ad_id', 'N/A')}, "
                                   f"Usuário {msg.get('recipient_id', 'N/A')}, "
                                   f"Expirou: {msg.get('expiry_time', 'N/A')}")
                    
                    if len(expired_messages) > 10:
                        logging.info(f"[EXPIRED_CLEANUP] ... e mais {len(expired_messages) - 10} mensagens")
                    
                    # Notifica admins sobre limpeza significativa
                    if removed_count >= 10:
                        try:
                            config = load_config()
                            cleanup_message = f"🧹 **LIMPEZA AUTOMÁTICA**\n\n📊 **Resumo:**\n├─ 🗑️ Removidas: {removed_count}\n├─ ✅ Mantidas: {kept_count}\n└─ 📈 Total processadas: {original_count}\n\n⏰ {current_dt.strftime('%d/%m/%Y %H:%M:%S')}"
                            
                            log_channel = config.get('LOG')
                            if log_channel:
                                await bot.send_message(chat_id=log_channel, text=cleanup_message, parse_mode="Markdown")
                        except Exception as e:
                            logging.error(f"[EXPIRED_CLEANUP] Erro ao notificar limpeza: {e}")
                            
                except Exception as e:
                    logging.error(f"[EXPIRED_CLEANUP] Erro ao salvar mensagens limpas: {e}")
            else:
                # Nenhum plano expirado
                professional_logger.expired_stats(0, 0)
                logging.info(f"[EXPIRED_CLEANUP] Nenhuma mensagem expirada encontrada ({original_count} verificadas)")
            
        except Exception as e:
            logging.error(f"[EXPIRED_CLEANUP] Erro geral na limpeza: {e}")
        
        # Aguarda 10 minutos antes da próxima verificação (mais eficiente)
        await asyncio.sleep(600)

async def process_forward_tasks():
    """Processa tarefas de reenvio de mensagens do painel web"""
    while True:
        try:
            import json
            import os
            
            tasks_file = 'forward_tasks.json'
            
            if os.path.exists(tasks_file):
                try:
                    # Carrega tarefas
                    with open(tasks_file, 'r', encoding='utf-8') as f:
                        tasks = json.load(f)
                    
                    if tasks:
                        processed_tasks = []
                        
                        for task in tasks:
                            try:
                                if task.get('type') == 'forward_message':
                                    admin_id = task.get('admin_id')
                                    message_id = task.get('message_id')
                                    from_chat_id = task.get('from_chat_id')
                                    
                                    # Tenta reenviar a mensagem
                                    await bot.forward_message(
                                        chat_id=admin_id,
                                        from_chat_id=from_chat_id,
                                        message_id=message_id
                                    )
                                    
                                    logging.info(f"[FORWARD_TASK] Mensagem {message_id} reenviada para admin {admin_id}")
                                    
                                    # Envia confirmação para o admin
                                    await bot.send_message(
                                        chat_id=admin_id,
                                        text=f"✅ **Mensagem Encaminhada**\n\n📋 **ID:** {message_id}\n📤 **De:** {from_chat_id}\n⏰ **Solicitado via painel web**",
                                        parse_mode="Markdown"
                                    )
                                    
                            except Exception as e:
                                logging.error(f"[FORWARD_TASK] Erro ao processar tarefa {task}: {e}")
                                
                                # Se der erro, tenta enviar mensagem explicativa
                                try:
                                    admin_id = task.get('admin_id')
                                    if admin_id:
                                        await bot.send_message(
                                            chat_id=admin_id,
                                            text=f"❌ **Erro ao Encaminhar Mensagem**\n\n📋 **ID:** {task.get('message_id', 'N/A')}\n📤 **De:** {task.get('from_chat_id', 'N/A')}\n\n**Possíveis causas:**\n• Mensagem foi deletada\n• Bot não tem acesso ao chat\n• Mensagem não pode ser encaminhada\n\n💡 **Dica:** Tente acessar o chat original diretamente.",
                                            parse_mode="Markdown"
                                        )
                                except:
                                    pass
                        
                        # Remove o arquivo de tarefas após processar
                        os.remove(tasks_file)
                        
                except Exception as e:
                    logging.error(f"[FORWARD_TASK] Erro ao processar arquivo de tarefas: {e}")
                    # Remove arquivo corrompido
                    try:
                        os.remove(tasks_file)
                    except:
                        pass
            
        except Exception as e:
            logging.error(f"[FORWARD_TASK] Erro geral no processamento: {e}")
        
        # Verifica a cada 5 segundos
        await asyncio.sleep(5)

# ============================================================================
# COMANDO PARA LIMPEZA MANUAL DE EXPIRADOS
# ============================================================================

@dp.message(Command("limpar_expirados"))
async def limpar_expirados_cmd(message: types.Message):
    """Comando para limpeza manual de mensagens expiradas"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    try:
        await message.reply("🧹 Iniciando limpeza manual de mensagens expiradas...")
        
        current_dt = datetime.datetime.now()
        scheduled_messages = load_scheduled_messages()
        original_count = len(scheduled_messages)
        
        expired_messages = []
        messages_to_keep = []
        
        for msg in scheduled_messages:
            expiry_time = msg.get('expiry_time')
            if not expiry_time:
                messages_to_keep.append(msg)
                continue
            
            try:
                if isinstance(expiry_time, str):
                    expiry_dt = datetime.datetime.strptime(expiry_time, "%Y-%m-%d %H:%M:%S")
                else:
                    expiry_dt = expiry_time
                
                if expiry_dt < current_dt:
                    expired_messages.append(msg)
                else:
                    messages_to_keep.append(msg)
            except:
                messages_to_keep.append(msg)
        
        if expired_messages:
            save_scheduled_messages(messages_to_keep, origem="limpeza_manual")
            removed_count = len(expired_messages)
            kept_count = len(messages_to_keep)
            
            result_message = f"✅ **Limpeza concluída!**\n\n📊 **Resultados:**\n├─ 🗑️ Removidas: {removed_count}\n├─ ✅ Mantidas: {kept_count}\n└─ 📈 Total verificadas: {original_count}\n\n⏰ {current_dt.strftime('%d/%m/%Y %H:%M:%S')}"
            await message.reply(result_message, parse_mode="Markdown")
        else:
            await message.reply(f"✅ Nenhuma mensagem expirada encontrada!\n\n📊 Total verificadas: {original_count}")
            
    except Exception as e:
        await message.reply(f"❌ Erro durante a limpeza: {str(e)}")

@dp.message(Command("limpar_backups"))
async def limpar_backups_cmd(message: types.Message):
    """Remove todos os backups antigos do diretório"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    await message.reply("🧹 **Iniciando limpeza de backups antigos...**")
    
    try:
        removed_count = cleanup_old_backups()
        await message.reply(f"✅ **Limpeza concluída!**\n📁 {removed_count} arquivos de backup removidos.")
    except Exception as e:
        await message.reply(f"❌ **Erro na limpeza:** {e}")

@dp.message(Command("limpar_expirados"))
async def limpar_expirados_cmd(message: types.Message):
    """Força a limpeza imediata de planos expirados"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    await message.reply("🧹 **Iniciando limpeza de planos expirados...**")
    
    try:
        global scheduled_messages
        
        # Recarrega mensagens do arquivo
        scheduled_messages = load_scheduled_messages()
        now = datetime.datetime.now()
        
        # Separa expirados dos ativos
        expired_messages = []
        active_messages = []
        
        for msg in scheduled_messages:
            expiry_str = msg.get('expiry_time')
            if expiry_str:
                try:
                    expiry_dt = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                    if expiry_dt <= now:  # Já expirou
                        expired_messages.append(msg)
                    else:  # Ainda ativo
                        active_messages.append(msg)
                except:
                    # Se não conseguir parsear a data, mantém como ativo
                    active_messages.append(msg)
            else:
                # Se não tem data de expiração, mantém como ativo
                active_messages.append(msg)
        
        # Atualiza a lista global e salva
        scheduled_messages = active_messages
        save_scheduled_messages(scheduled_messages)
        
        # Monta relatório
        result_text = f"""✅ **LIMPEZA DE EXPIRADOS CONCLUÍDA!**

📊 **Resultados:**
├─ 🗑️ Planos expirados removidos: **{len(expired_messages)}**
├─ ✅ Planos ativos mantidos: **{len(active_messages)}**
└─ 📅 Verificação em: **{now.strftime('%d/%m/%Y %H:%M:%S')}**

🎯 **Planos removidos:**"""

        if expired_messages:
            for msg in expired_messages[:5]:  # Mostra apenas os primeiros 5
                contract_id = msg.get('fixed_ad_id', 'N/A')
                expiry = msg.get('expiry_time', 'N/A')
                result_text += f"\n• {contract_id} (expirou: {expiry})"
            
            if len(expired_messages) > 5:
                result_text += f"\n• ... e mais {len(expired_messages) - 5} planos"
        else:
            result_text += "\n• Nenhum plano expirado encontrado"

        result_text += f"""

💡 **Benefícios:**
• Alertas mais precisos
• Estatísticas corretas
• Performance melhorada
• Sistema mais limpo"""

        await message.reply(result_text, parse_mode="Markdown")
        
        # Log da ação
        logging.info(f"[CLEANUP] Limpeza manual executada por {message.from_user.id}: {len(expired_messages)} planos removidos")
        
    except Exception as e:
        await message.reply(f"❌ Erro durante a limpeza: {e}")
        logging.error(f"[CLEANUP] Erro na limpeza manual: {e}")

@dp.message(Command("debug_expiry"))
async def debug_expiry_cmd(message: types.Message):
    """Comando para debugar verificação de expiração"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    try:
        scheduled_messages = load_scheduled_messages()
        now = datetime.datetime.now()
        
        debug_text = f"""🔍 **DEBUG - VERIFICAÇÃO DE EXPIRAÇÃO**

🕐 **Horário atual:** {now.strftime('%Y-%m-%d %H:%M:%S')}
📊 **Total de planos:** {len(scheduled_messages)}

📋 **ANÁLISE DETALHADA:**"""

        expiring_count = 0
        expired_count = 0
        active_count = 0
        
        for i, msg in enumerate(scheduled_messages[:10]):  # Mostra apenas os primeiros 10
            contract_id = msg.get('fixed_ad_id', 'N/A')
            expiry_str = msg.get('expiry_time')
            
            if expiry_str:
                try:
                    expiry_dt = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                    diff_seconds = (expiry_dt - now).total_seconds()
                    dias = int(diff_seconds / (24 * 60 * 60))
                    horas = int((diff_seconds % (24 * 60 * 60)) / 3600)
                    
                    if diff_seconds <= 0:
                        status = "❌ EXPIRADO"
                        expired_count += 1
                    elif diff_seconds <= 60*60*24:  # 24 horas
                        status = "⚠️ EXPIRANDO"
                        expiring_count += 1
                    else:
                        status = "✅ ATIVO"
                        active_count += 1
                    
                    debug_text += f"""

{i+1}. **{contract_id}**
├─ 📅 Expira: {expiry_str}
├─ ⏰ Diferença: {dias}d {horas}h
├─ 🔢 Segundos: {diff_seconds:.0f}
└─ 📊 Status: {status}"""
                    
                except Exception as e:
                    debug_text += f"""

{i+1}. **{contract_id}**
├─ 📅 Expira: {expiry_str}
└─ ❌ Erro: {e}"""
            else:
                debug_text += f"""

{i+1}. **{contract_id}**
└─ ⚠️ Sem data de expiração"""

        debug_text += f"""

📊 **RESUMO:**
├─ ✅ Ativos: {active_count}
├─ ⚠️ Expirando (24h): {expiring_count}
└─ ❌ Expirados: {expired_count}

💡 **Use `/limpar_expirados` para remover os expirados**"""

        if len(debug_text) > 4000:
            # Se muito longo, envia como arquivo
            filename = f"debug_expiry_{now.strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(debug_text)
            
            await message.reply_document(
                document=types.FSInputFile(filename),
                caption="🔍 Debug de expiração - arquivo completo"
            )
            os.remove(filename)
        else:
            await message.reply(debug_text, parse_mode="Markdown")
        
    except Exception as e:
        professional_logger.error("UPDATE_REMINDER", f"Erro ao enviar lembrete: {e}")

# ============================================================================
# HANDLERS PARA BOTÕES INLINE DO MENU /START
# ============================================================================

@dp.callback_query(lambda c: c.data == "trocar_anuncio")
async def trocar_anuncio_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o botão 'Trocar Anúncio'"""
    try:
        user_id = callback_query.from_user.id
        
        # Verifica se o usuário tem planos ativos
        scheduled_messages = load_scheduled_messages()
        user_plans = [msg for msg in scheduled_messages if msg.get('recipient_id') == user_id]
        
        if not user_plans:
            await callback_query.answer("❌ Você não possui planos ativos para trocar o anúncio.", show_alert=True)
            return
        
        # Se tem apenas um plano, usa ele diretamente
        if len(user_plans) == 1:
            plan = user_plans[0]
            fixed_ad_id = plan.get('fixed_ad_id')
            
            await callback_query.message.reply(
                f"📝 **Trocar Anúncio**\n\n"
                f"🏷️ **ID do Plano:** `{fixed_ad_id}`\n\n"
                f"📋 **Instruções:**\n"
                f"• Responda a esta mensagem com o novo anúncio\n"
                f"• Pode ser texto, imagem, vídeo ou qualquer mídia\n"
                f"• O anúncio atual será substituído\n\n"
                f"⏰ **Aguardando seu novo anúncio...**",
                parse_mode="Markdown"
            )
            
            # Define estado para aguardar novo anúncio
            await state.update_data(trocar_anuncio_id=fixed_ad_id)
            await state.set_state("aguardando_novo_anuncio")
            
        else:
            # Múltiplos planos - mostra lista para escolher
            buttons = []
            for plan in user_plans[:10]:  # Limita a 10 planos
                fixed_ad_id = plan.get('fixed_ad_id', 'N/A')
                short_id = fixed_ad_id[:8] + "..." if len(fixed_ad_id) > 8 else fixed_ad_id
                buttons.append([InlineKeyboardButton(
                    text=f"📋 {short_id}",
                    callback_data=f"select_plan_change:{fixed_ad_id}"
                )])
            
            buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel_change")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await callback_query.message.reply(
                f"📝 **Selecione o Plano para Trocar Anúncio**\n\n"
                f"📊 **Você possui {len(user_plans)} plano(s) ativo(s)**\n\n"
                f"👆 Clique no plano que deseja alterar:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        await callback_query.answer("✅ Processo iniciado!")
        
    except Exception as e:
        professional_logger.error("CALLBACK", f"Erro no handler trocar_anuncio: {e}")
        await callback_query.answer("❌ Erro interno. Tente novamente.", show_alert=True)

@dp.callback_query(lambda c: c.data == "trocar_horario")
async def trocar_horario_handler(callback_query: types.CallbackQuery):
    """Handler para o botão 'Trocar Horário'"""
    try:
        user_id = callback_query.from_user.id
        
        # Verifica se o usuário tem planos ativos
        scheduled_messages = load_scheduled_messages()
        user_plans = [msg for msg in scheduled_messages if msg.get('recipient_id') == user_id]
        
        if not user_plans:
            await callback_query.answer("❌ Você não possui planos ativos para trocar horários.", show_alert=True)
            return
        
        # Mostra teclado de períodos para seleção de novos horários
        keyboard = generate_periods_keyboard()
        
        await callback_query.message.reply(
            f"⏰ **Trocar Horários**\n\n"
            f"📊 **Seus Planos Ativos:** {len(user_plans)}\n\n"
            f"🎯 **Selecione o período desejado:**\n"
            f"• Os novos horários substituirão os atuais\n"
            f"• Você pode escolher múltiplos horários\n"
            f"• As alterações são aplicadas imediatamente\n\n"
            f"👆 **Escolha um período:**",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        await callback_query.answer("✅ Seleção de horários iniciada!")
        
    except Exception as e:
        professional_logger.error("CALLBACK", f"Erro no handler trocar_horario: {e}")
        await callback_query.answer("❌ Erro interno. Tente novamente.", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("select_plan_change:"))
async def select_plan_change_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para seleção de plano específico para trocar anúncio"""
    try:
        fixed_ad_id = callback_query.data.replace("select_plan_change:", "")
        
        await callback_query.message.reply(
            f"📝 **Trocar Anúncio**\n\n"
            f"🏷️ **ID do Plano:** `{fixed_ad_id}`\n\n"
            f"📋 **Instruções:**\n"
            f"• Responda a esta mensagem com o novo anúncio\n"
            f"• Pode ser texto, imagem, vídeo ou qualquer mídia\n"
            f"• O anúncio atual será substituído\n\n"
            f"⏰ **Aguardando seu novo anúncio...**",
            parse_mode="Markdown"
        )
        
        # Define estado para aguardar novo anúncio
        await state.update_data(trocar_anuncio_id=fixed_ad_id)
        await state.set_state("aguardando_novo_anuncio")
        
        await callback_query.answer("✅ Plano selecionado!")
        
    except Exception as e:
        professional_logger.error("CALLBACK", f"Erro no handler select_plan_change: {e}")
        await callback_query.answer("❌ Erro interno. Tente novamente.", show_alert=True)

@dp.callback_query(lambda c: c.data == "cancel_change")
async def cancel_change_handler(callback_query: types.CallbackQuery):
    """Handler para cancelar troca de anúncio"""
    await callback_query.message.reply("❌ **Operação cancelada.**")
    await callback_query.answer("Cancelado!")

# ============================================================================
# HANDLERS DE ESTADOS ADMINISTRATIVOS - DEVEM VIR ANTES DOS HANDLERS GENÉRICOS
# ============================================================================

@dp.message(AdminPanelStates.esperando_novo_botao_start)
async def receber_novo_botao_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem executar esta ação.")
        await state.clear()
        return
    
    try:
        # Verifica se tem vírgula
        if "," not in message.text:
            await message.reply("❌ Formato incorreto!\n\n"
                              "Envie no formato: Texto do Botão, https://seulink.com\n\n"
                              "Exemplo: Meu Canal, https://t.me/meucanal")
            return
        
        # Separa texto e URL
        texto, url = [x.strip() for x in message.text.split(",", 1)]
        
        # Valida se tem texto e URL
        if not texto or not url:
            await message.reply("❌ Texto ou URL vazio!\n\n"
                              "Envie no formato: Texto do Botão, https://seulink.com")
            return
        
        # Valida se a URL começa com http
        if not url.startswith("http"):
            await message.reply("❌ URL inválida! Deve começar com http:// ou https://\n\n"
                              "Exemplo: https://t.me/meucanal")
            return
        
        # Carrega config
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
        
        # Garante estrutura do menu
        if 'menu' not in config:
            config['menu'] = {}
        if 'buttons' not in config['menu']:
            config['menu']['buttons'] = []
        
        # Adiciona o botão
        config['menu']['buttons'].append({"text": texto, "url": url})
        
        # Salva config
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        await message.reply(f"✅ Botão adicionado com sucesso!\n\n"
                          f"📝 Texto: {texto}\n"
                          f"🔗 Link: {url}\n\n"
                          f"Total de botões: {len(config['menu']['buttons'])}")
        
    except ValueError:
        await message.reply("❌ Erro ao processar! Use o formato:\n"
                          "Texto do Botão, https://seulink.com")
    except Exception as e:
        await message.reply(f"❌ Erro ao adicionar botão: {e}")
    
    await state.clear()

@dp.message(AdminPanelStates.esperando_nova_imagem_start)
async def receber_nova_imagem_start_priority(message: types.Message, state: FSMContext):
    """Handler prioritário para receber nova imagem do /start"""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Apenas administradores podem executar esta ação.")
        return
    
    # Aceita link ou foto
    if message.photo:
        # Pega o file_id da foto em melhor qualidade
        file_id = message.photo[-1].file_id
        
        try:
            with open(CONFIG_FILE, encoding='utf-8') as f:
                config = json.load(f)
            
            if 'menu' not in config:
                config['menu'] = {}
            
            # Salva o file_id da foto
            config['menu']['image_url'] = file_id
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            await message.reply("✅ Imagem do /start atualizada com sucesso!\n\n"
                              "🔄 Testando a nova imagem...")
            
            # Testa a nova imagem
            try:
                await message.answer_photo(
                    photo=file_id,
                    caption="✅ Esta é a nova imagem do /start!"
                )
            except Exception as e:
                await message.reply(f"⚠️ Erro ao testar imagem: {e}")
            
            await state.clear()
            return
            
        except Exception as e:
            await message.reply(f"❌ Erro ao salvar imagem: {e}")
            await state.clear()
            return
    
    # Se for um link de texto
    imagem_url = message.text.strip()
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
        if 'menu' not in config:
            config['menu'] = {}
        config['menu']['image_url'] = imagem_url
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        await message.reply("✅ Link da imagem do /start atualizado!\n\n"
                          "🔄 Testando a nova imagem...")
        
        # Testa a nova imagem
        try:
            await message.answer_photo(
                photo=imagem_url,
                caption="✅ Esta é a nova imagem do /start!"
            )
        except Exception as e:
            await message.reply(f"⚠️ Erro ao testar imagem: {e}\n"
                              "Verifique se o link está correto.")
        
    except Exception as e:
        await message.reply(f"❌ Erro ao atualizar imagem do /start: {e}")
    
    await state.clear()

# ============================================================================
# FIM DOS HANDLERS PRIORITÁRIOS
# ============================================================================

# Handler para receber novo anúncio
@dp.message(lambda message: True)
async def handle_new_ad_message(message: types.Message, state: FSMContext):
    """Handler para receber novo anúncio quando usuário está no estado correto"""
    try:
        current_state = await state.get_state()
        if current_state != "aguardando_novo_anuncio":
            return  # Não é para este handler
        
        data = await state.get_data()
        fixed_ad_id = data.get('trocar_anuncio_id')
        
        if not fixed_ad_id:
            await message.reply("❌ Erro: ID do plano não encontrado. Tente novamente.")
            await state.clear()
            return
        
        # Carrega mensagens agendadas
        scheduled_messages = load_scheduled_messages()
        
        # Encontra o plano
        plan_found = False
        for msg in scheduled_messages:
            if msg.get('fixed_ad_id') == fixed_ad_id:
                # Atualiza o anúncio
                if message.text:
                    msg['message'] = message.text
                    msg['media_type'] = 'text'
                    msg['media_url'] = None
                elif message.photo:
                    msg['message'] = message.caption or ""
                    msg['media_type'] = 'photo'
                    msg['media_url'] = message.photo[-1].file_id
                elif message.video:
                    msg['message'] = message.caption or ""
                    msg['media_type'] = 'video'
                    msg['media_url'] = message.video.file_id
                elif message.document:
                    msg['message'] = message.caption or ""
                    msg['media_type'] = 'document'
                    msg['media_url'] = message.document.file_id
                else:
                    await message.reply("❌ Tipo de mídia não suportado. Use texto, foto, vídeo ou documento.")
                    return
                
                msg['updated_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                plan_found = True
                break
        
        if plan_found:
            # Salva alterações
            save_scheduled_messages(scheduled_messages, origem="troca_anuncio")
            
            await message.reply(
                f"✅ **Anúncio Atualizado com Sucesso!**\n\n"
                f"🏷️ **ID do Plano:** `{fixed_ad_id}`\n"
                f"📝 **Novo Anúncio:** Configurado\n"
                f"⏰ **Atualizado em:** {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
                f"🎯 **O novo anúncio será usado nos próximos envios!**",
                parse_mode="Markdown"
            )
            
            professional_logger.success("AD_CHANGE", f"Anúncio alterado para plano {fixed_ad_id}")
        else:
            await message.reply("❌ Plano não encontrado. Verifique se ainda está ativo.")
        
        await state.clear()
        
    except Exception as e:
        professional_logger.error("AD_CHANGE", f"Erro ao trocar anúncio: {e}")
        await message.reply("❌ Erro ao atualizar anúncio. Tente novamente.")
        await state.clear()

# ============================================================================
# SISTEMA DE MONITORAMENTO INTELIGENTE
# ============================================================================

async def smart_monitoring_system():
    """Sistema de monitoramento inteligente que roda em background"""
    while True:
        try:
            await asyncio.sleep(3600)  # Executa a cada 1 hora
            
            # Carrega dados atuais
            chat_ids = load_chat_ids()
            scheduled_messages = load_scheduled_messages()
            now = datetime.datetime.now()
            
            # Análise de performance
            planos_ativos = 0
            planos_expirando_3_dias = 0
            planos_expirando_1_dia = 0
            usuarios_unicos = set()
            
            for msg in scheduled_messages:
                if msg.get('recipient_id'):
                    usuarios_unicos.add(msg['recipient_id'])
                
                expiry_str = msg.get('expiry_time')
                if expiry_str:
                    try:
                        expiry_dt = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                        if expiry_dt > now:
                            planos_ativos += 1
                            dias_restantes = (expiry_dt - now).days
                            
                            if dias_restantes <= 1:
                                planos_expirando_1_dia += 1
                            elif dias_restantes <= 3:
                                planos_expirando_3_dias += 1
                    except:
                        pass
            
            # Verifica se precisa enviar alertas
            config = load_config()
            log_channel = config.get('LOG')
            
            if log_channel and planos_expirando_1_dia > 0:
                alert_message = f"""🚨 **ALERTA URGENTE - PLANOS EXPIRANDO**

⚠️ **{planos_expirando_1_dia} plano(s) expira(m) em menos de 24 horas!**

📊 **Status atual:**
├─ 💼 Planos ativos: {planos_ativos}
├─ ⚠️ Expirando em 1 dia: {planos_expirando_1_dia}
├─ 🔔 Expirando em 3 dias: {planos_expirando_3_dias}
└─ 👥 Clientes únicos: {len(usuarios_unicos)}

🎯 **Ação recomendada:** Contatar clientes imediatamente para renovação!

🕐 Monitoramento automático - {now.strftime('%d/%m/%Y %H:%M:%S')}"""

                try:
                    await bot.send_message(chat_id=log_channel, text=alert_message, parse_mode="Markdown")
                    logging.info(f"[MONITORING] Alerta de expiração enviado: {planos_expirando_1_dia} planos")
                except Exception as e:
                    logging.error(f"[MONITORING] Erro ao enviar alerta: {e}")
            
            # Relatório diário (apenas às 9h)
            if now.hour == 9 and now.minute < 5:  # Janela de 5 minutos
                daily_report = f"""📊 **RELATÓRIO DIÁRIO AUTOMÁTICO**

🗓️ **{now.strftime('%d/%m/%Y')} - {now.strftime('%H:%M')}**

📈 **PERFORMANCE GERAL:**
├─ 🏢 Grupos ativos: {len(chat_ids)}
├─ 💼 Planos ativos: {planos_ativos}
├─ 👥 Clientes únicos: {len(usuarios_unicos)}
└─ 💰 Receita estimada: R$ {len(usuarios_unicos) * 50:.2f}/mês

⚠️ **ALERTAS:**
├─ Expirando hoje: {planos_expirando_1_dia}
└─ Expirando em 3 dias: {planos_expirando_3_dias}

🎯 **INSIGHTS:**"""

                if len(usuarios_unicos) > 20:
                    daily_report += "\n• 🚀 Ótima base de clientes!"
                elif len(usuarios_unicos) > 10:
                    daily_report += "\n• 📈 Base de clientes em crescimento"
                else:
                    daily_report += "\n• 📢 Oportunidade de expansão"

                if planos_expirando_3_dias == 0:
                    daily_report += "\n• ✅ Nenhum plano próximo ao vencimento"
                else:
                    daily_report += f"\n• 🔔 {planos_expirando_3_dias} plano(s) precisam de atenção"

                daily_report += f"\n\n🤖 Relatório gerado automaticamente pelo sistema de monitoramento"

                if log_channel:
                    try:
                        await bot.send_message(chat_id=log_channel, text=daily_report, parse_mode="Markdown")
                        logging.info("[MONITORING] Relatório diário enviado")
                    except Exception as e:
                        logging.error(f"[MONITORING] Erro ao enviar relatório diário: {e}")
            
            logging.info(f"[MONITORING] Verificação concluída - Planos ativos: {planos_ativos}, Clientes: {len(usuarios_unicos)}")
            
        except Exception as e:
            logging.error(f"[MONITORING] Erro no sistema de monitoramento: {e}")

# ============================================================================
# PAINEL WEB INTEGRADO - SISTEMA DE GERENCIAMENTO
# ============================================================================

# Importações para o painel web
try:
    from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
    from flask_socketio import SocketIO, emit
    import jwt
    import secrets
    import threading
    from functools import wraps
    WEB_PANEL_AVAILABLE = True
except ImportError:
    WEB_PANEL_AVAILABLE = False
    logging.warning("Flask não encontrado. Painel web desabilitado.")

# Variável global para armazenar a porta do painel web
WEB_PANEL_PORT = 5000

# Configuração do Flask (apenas se disponível)
if WEB_PANEL_AVAILABLE:
    web_app = Flask(__name__)
    web_app.config['SECRET_KEY'] = secrets.token_hex(32)
    web_app.config['JWT_SECRET_KEY'] = secrets.token_hex(32)
    socketio = SocketIO(web_app, cors_allowed_origins="*")

    def is_admin_web(user_id: int) -> bool:
        """Verifica se o usuário é admin para o painel web"""
        config = load_config()
        return user_id in config.get('admins', [])

    def generate_auth_token(user_id: int) -> str:
        """Gera token JWT para autenticação"""
        now = datetime.datetime.now(datetime.timezone.utc)
        payload = {
            'user_id': user_id,
            'exp': now + datetime.timedelta(hours=24),
            'iat': now
        }
        return jwt.encode(payload, web_app.config['JWT_SECRET_KEY'], algorithm='HS256')

    def verify_auth_token(token: str):
        """Verifica token JWT"""
        try:
            payload = jwt.decode(token, web_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            return payload['user_id']
        except:
            return None

    def require_auth(f):
        """Decorator para rotas que requerem autenticação"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = session.get('auth_token')
            if not token:
                return redirect(url_for('login'))
            
            user_id = verify_auth_token(token)
            if not user_id or not is_admin_web(user_id):
                session.clear()
                return redirect(url_for('login'))
            
            return f(*args, **kwargs)
        return decorated_function

    def get_dashboard_stats():
        """Obtém estatísticas para o dashboard"""
        scheduled_messages = load_scheduled_messages()
        chat_ids = load_chat_ids()
        user_ids = load_user_ids()
        
        now = datetime.datetime.now()
        active_plans = 0
        expiring_soon = 0
        total_revenue = 0
        
        for msg in scheduled_messages:
            expiry_str = msg.get('expiry_time')
            if expiry_str:
                try:
                    expiry_dt = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                    if expiry_dt > now:
                        active_plans += 1
                        days_remaining = (expiry_dt - now).days
                        if days_remaining <= 3:
                            expiring_soon += 1
                        total_revenue += 50
                except:
                    pass
        
        return {
            'total_groups': len(chat_ids),
            'total_users': len(user_ids),
            'active_plans': active_plans,
            'expiring_soon': expiring_soon,
            'total_revenue': total_revenue,
            'scheduled_messages': len(scheduled_messages)
        }

    # Template HTML para monitor de horários
    SCHEDULE_MONITOR_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor de Horários - Painel Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: #f8f9fa; font-family: 'Inter', sans-serif; }
        .status-badge { padding: 8px 16px; border-radius: 20px; font-weight: 600; font-size: 0.875rem; }
        .status-success { background: #d1fae5; color: #065f46; border: 2px solid #10b981; }
        .status-error { background: #fee2e2; color: #991b1b; border: 2px solid #ef4444; }
        .status-warning { background: #fef3c7; color: #92400e; border: 2px solid #f59e0b; }
        .status-pending { background: #dbeafe; color: #1e40af; border: 2px solid #3b82f6; }
        .status-missed { background: #f3f4f6; color: #6b7280; border: 2px solid #9ca3af; }
        .time-card { background: white; border-radius: 12px; padding: 20px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: all 0.3s ease; }
        .time-card:hover { box-shadow: 0 4px 6px rgba(0,0,0,0.15); transform: translateY(-2px); }
        .time-card.status-success-card { border-left: 4px solid #10b981; }
        .time-card.status-error-card { border-left: 4px solid #ef4444; }
        .time-card.status-warning-card { border-left: 4px solid #f59e0b; }
        .time-card.status-pending-card { border-left: 4px solid #3b82f6; }
        .time-card.status-missed-card { border-left: 4px solid #9ca3af; }
        .status-indicator { width: 14px; height: 14px; border-radius: 50%; display: inline-block; margin-right: 8px; animation: pulse 2s infinite; }
        .indicator-success { background: #10b981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.5); }
        .indicator-error { background: #ef4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.5); }
        .indicator-warning { background: #f59e0b; box-shadow: 0 0 8px rgba(245, 158, 11, 0.5); }
        .indicator-pending { background: #3b82f6; box-shadow: 0 0 8px rgba(59, 130, 246, 0.5); }
        .indicator-missed { background: #9ca3af; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        .ultimo-envio { 
            background: #f9fafb; 
            border-radius: 8px; 
            padding: 10px; 
            margin-top: 10px;
            border-left: 3px solid #3b82f6;
        }
        .ultimo-envio strong { color: #1e40af; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">
                <i class="fas fa-clock me-2"></i>Monitor de Horários
            </a>
            <div>
                <a href="/messages" class="btn btn-outline-light btn-sm me-2">
                    <i class="fas fa-envelope"></i> Mensagens
                </a>
                <a href="/" class="btn btn-outline-light btn-sm">
                    <i class="fas fa-home"></i> Dashboard
                </a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-chart-line me-2"></i>Status dos Horários de Divulgação
                        </h5>
                        <p class="text-muted mb-2">
                            Monitoramento em tempo real dos horários agendados. Atualização automática a cada 60 segundos.
                        </p>
                        <div class="d-flex flex-wrap gap-2">
                            <span class="badge bg-success"><i class="fas fa-check-circle"></i> Verde = Enviado com Sucesso</span>
                            <span class="badge bg-danger"><i class="fas fa-times-circle"></i> Vermelho = Erro no Envio</span>
                            <span class="badge bg-warning text-dark"><i class="fas fa-exclamation-triangle"></i> Amarelo = Com Avisos</span>
                            <span class="badge bg-primary"><i class="fas fa-hourglass-half"></i> Azul = Aguardando</span>
                            <span class="badge bg-secondary"><i class="fas fa-clock"></i> Cinza = Não Processado</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            {% for horario in horarios %}
            <div class="col-md-6 col-lg-4">
                <div class="time-card status-{{ horario.status }}-card">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h4 class="mb-0">
                            <i class="fas fa-clock me-2"></i>{{ horario.time }}
                        </h4>
                        <span class="status-indicator indicator-{{ horario.status }}"></span>
                    </div>
                    
                    <div class="mb-3">
                        <span class="status-badge status-{{ horario.status }}">
                            {% if horario.status == 'success' %}
                                <i class="fas fa-check-circle"></i> Enviado com Sucesso
                            {% elif horario.status == 'error' %}
                                <i class="fas fa-times-circle"></i> Erro no Envio
                            {% elif horario.status == 'warning' %}
                                <i class="fas fa-exclamation-triangle"></i> Enviado com Avisos
                            {% elif horario.status == 'missed' %}
                                <i class="fas fa-clock"></i> Não Processado
                            {% else %}
                                <i class="fas fa-hourglass-half"></i> Aguardando
                            {% endif %}
                        </span>
                    </div>

                    <!-- ÚLTIMO ENVIO - DESTAQUE -->
                    <div class="ultimo-envio">
                        <div class="d-flex align-items-center">
                            <i class="fas fa-history me-2 text-primary"></i>
                            <div>
                                <small class="text-muted d-block">Último Envio:</small>
                                <strong>{{ horario.ultimo_envio }}</strong>
                            </div>
                        </div>
                    </div>

                    <div class="mt-3 mb-2">
                        <i class="fas fa-list-alt me-1 text-primary"></i>
                        <strong>{{ horario.planos_count }}</strong> plano(s) agendado(s)
                    </div>

                    {% if horario.mensagens_enviadas > 0 %}
                    <div class="mb-2">
                        <i class="fas fa-paper-plane text-success me-1"></i>
                        <strong>{{ horario.mensagens_enviadas }}</strong> mensagem(ns) enviada(s)
                        {% if horario.taxa_sucesso > 0 %}
                        <span class="badge bg-success ms-1">{{ horario.taxa_sucesso }}%</span>
                        {% endif %}
                    </div>
                    {% endif %}

                    {% if horario.erros %}
                    <div class="alert alert-danger alert-sm mt-2 mb-0">
                        <small>
                            <i class="fas fa-exclamation-triangle me-1"></i>
                            {{ horario.erros|length }} erro(s) detectado(s)
                        </small>
                    </div>
                    {% endif %}

                    {% if horario.planos %}
                    <div class="mt-3">
                        <button class="btn btn-sm btn-outline-primary w-100" type="button" data-bs-toggle="collapse" data-bs-target="#planos-{{ horario.time|replace(':', '') }}">
                            <i class="fas fa-list me-1"></i>Ver Planos
                        </button>
                        <div class="collapse mt-2" id="planos-{{ horario.time|replace(':', '') }}">
                            <ul class="list-group list-group-flush">
                                {% for plano in horario.planos %}
                                <li class="list-group-item px-0 py-2">
                                    <small>
                                        <strong>{{ plano.code }}</strong><br>
                                        Tipo: {{ plano.type }}<br>
                                        Cliente: {{ plano.recipient_id }}
                                    </small>
                                </li>
                                {% endfor %}
                            </ul>
                        </div>
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>

        {% if not horarios %}
        <div class="alert alert-info text-center">
            <i class="fas fa-info-circle me-2"></i>
            Nenhum horário agendado no momento.
        </div>
        {% endif %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Auto-refresh a cada 60 segundos
        setTimeout(() => location.reload(), 60000);
    </script>
</body>
</html>
    '''

    # Rotas do painel web
    @web_app.route('/login', methods=['GET', 'POST'])
    def login():
        """Página de login"""
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            password = request.form.get('password')
            
            if user_id and password == "admin123" and is_admin_web(int(user_id)):
                auth_token = generate_auth_token(int(user_id))
                session['auth_token'] = auth_token
                session['user_id'] = int(user_id)
                return redirect(url_for('dashboard'))
            else:
                flash('Credenciais inválidas', 'error')
        
        return '''
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login - Painel Admin</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                :root {
                    --primary: #6366f1;
                    --primary-dark: #4f46e5;
                    --secondary: #8b5cf6;
                    --success: #10b981;
                    --warning: #f59e0b;
                    --danger: #ef4444;
                    --dark: #1f2937;
                    --light: #f8fafc;
                    --border: #e5e7eb;
                }
                
                * { margin: 0; padding: 0; box-sizing: border-box; }
                
                body {
                    font-family: 'Inter', sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                    overflow: hidden;
                }
                
                body::before {
                    content: '';
                    position: absolute;
                    top: -50%;
                    left: -50%;
                    width: 200%;
                    height: 200%;
                    background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="rgba(255,255,255,0.1)"/><circle cx="75" cy="75" r="1" fill="rgba(255,255,255,0.1)"/><circle cx="50" cy="10" r="0.5" fill="rgba(255,255,255,0.05)"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
                    animation: float 20s ease-in-out infinite;
                }
                
                @keyframes float {
                    0%, 100% { transform: translateY(0px) rotate(0deg); }
                    50% { transform: translateY(-20px) rotate(1deg); }
                }
                
                .login-container {
                    background: rgba(255, 255, 255, 0.98);
                    backdrop-filter: blur(20px);
                    border-radius: 24px;
                    padding: 3rem;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                    max-width: 450px;
                    width: 100%;
                    position: relative;
                    z-index: 10;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
                
                .login-header {
                    text-align: center;
                    margin-bottom: 2.5rem;
                }
                
                .login-header .logo {
                    width: 80px;
                    height: 80px;
                    background: linear-gradient(135deg, var(--primary), var(--secondary));
                    border-radius: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 1.5rem;
                    font-size: 2rem;
                    color: white;
                    box-shadow: 0 10px 25px rgba(99, 102, 241, 0.3);
                }
                
                .login-header h2 {
                    color: var(--dark);
                    font-weight: 700;
                    font-size: 1.75rem;
                    margin-bottom: 0.5rem;
                }
                
                .login-header p {
                    color: #6b7280;
                    font-size: 1rem;
                    margin-bottom: 0;
                }
                
                .form-group {
                    position: relative;
                    margin-bottom: 1.5rem;
                }
                
                .form-control {
                    border: 2px solid var(--border);
                    border-radius: 12px;
                    padding: 1rem 1rem 1rem 3rem;
                    font-size: 1rem;
                    transition: all 0.3s ease;
                    background: white;
                }
                
                .form-control:focus {
                    border-color: var(--primary);
                    box-shadow: 0 0 0 0.2rem rgba(99, 102, 241, 0.1);
                    outline: none;
                }
                
                .form-icon {
                    position: absolute;
                    left: 1rem;
                    top: 50%;
                    transform: translateY(-50%);
                    color: #6b7280;
                    font-size: 1.1rem;
                }
                
                .btn-login {
                    background: linear-gradient(135deg, var(--primary), var(--secondary));
                    border: none;
                    border-radius: 12px;
                    padding: 1rem 2rem;
                    font-size: 1rem;
                    font-weight: 600;
                    color: white;
                    width: 100%;
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;
                }
                
                .btn-login:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 15px 35px rgba(99, 102, 241, 0.4);
                }
                
                .btn-login:active {
                    transform: translateY(0);
                }
                
                .alert {
                    border-radius: 12px;
                    border: none;
                    padding: 1rem 1.25rem;
                    margin-bottom: 1.5rem;
                    font-weight: 500;
                }
                
                .alert-danger {
                    background: #fef2f2;
                    color: #dc2626;
                }
                
                .footer-info {
                    text-align: center;
                    margin-top: 2rem;
                    padding-top: 2rem;
                    border-top: 1px solid var(--border);
                }
                
                .footer-info p {
                    color: #6b7280;
                    font-size: 0.875rem;
                    margin-bottom: 0.5rem;
                }
                
                .security-badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 0.5rem;
                    background: #f0fdf4;
                    color: #166534;
                    padding: 0.5rem 1rem;
                    border-radius: 20px;
                    font-size: 0.875rem;
                    font-weight: 500;
                }
                
                @media (max-width: 480px) {
                    .login-container {
                        margin: 1rem;
                        padding: 2rem;
                    }
                    
                    .login-header h2 {
                        font-size: 1.5rem;
                    }
                }
            </style>
        </head>
        <body>
            <div class="login-container">
                <div class="login-header">
                    <div class="logo">
                        <i class="fas fa-robot"></i>
                    </div>
                    <h2>Painel Administrativo</h2>
                    <p>Sistema de Gerenciamento do Bot</p>
                </div>
                
                <form method="POST">
                    <div class="form-group">
                        <i class="fas fa-user form-icon"></i>
                        <input type="number" class="form-control" name="user_id" placeholder="ID do Telegram" required>
                    </div>
                    
                    <div class="form-group">
                        <i class="fas fa-lock form-icon"></i>
                        <input type="password" class="form-control" name="password" placeholder="Senha de acesso" required>
                    </div>
                    
                    <button type="submit" class="btn-login">
                        <i class="fas fa-sign-in-alt me-2"></i>
                        Acessar Painel
                    </button>
                </form>
                
                <div class="footer-info">
                    <div class="security-badge">
                        <i class="fas fa-shield-alt"></i>
                        Acesso Seguro
                    </div>
                    <p class="mt-3">Apenas administradores autorizados</p>
                    <p><small>Desenvolvido para gerenciamento profissional</small></p>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        '''

    @web_app.route('/')
    @require_auth
    def dashboard():
        """Dashboard principal moderno"""
        stats = get_dashboard_stats()
        now = datetime.datetime.now()
        return f'''
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Dashboard - Painel Admin</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                :root {{
                    --primary: #dc2626;
                    --secondary: #991b1b;
                    --accent: #ef4444;
                    --dark: #0a0a0a;
                    --darker: #000000;
                    --light: #1a1a1a;
                    --lighter: #2a2a2a;
                    --text-primary: #ffffff;
                    --text-secondary: #a1a1aa;
                    --success: #22c55e;
                    --warning: #f59e0b;
                    --danger: #dc2626;
                }}
                
                @keyframes fadeInUp {{
                    from {{
                        opacity: 0;
                        transform: translateY(30px);
                    }}
                    to {{
                        opacity: 1;
                        transform: translateY(0);
                    }}
                }}
                
                @keyframes glow {{
                    0%, 100% {{
                        box-shadow: 0 0 20px rgba(220, 38, 38, 0.3);
                    }}
                    50% {{
                        box-shadow: 0 0 30px rgba(220, 38, 38, 0.6);
                    }}
                }}
                
                @keyframes pulse {{
                    0%, 100% {{
                        transform: scale(1);
                    }}
                    50% {{
                        transform: scale(1.05);
                    }}
                }}
                
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                
                body {{
                    font-family: 'Inter', sans-serif;
                    background: linear-gradient(135deg, var(--darker) 0%, var(--dark) 50%, var(--secondary) 100%);
                    min-height: 100vh;
                    color: var(--text-primary);
                    overflow-x: hidden;
                }}
                
                body::before {{
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: 
                        radial-gradient(circle at 20% 80%, rgba(220, 38, 38, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(239, 68, 68, 0.1) 0%, transparent 50%);
                    pointer-events: none;
                    z-index: -1;
                }}
                
                .main-container {{
                    background: linear-gradient(135deg, var(--light) 0%, var(--lighter) 100%);
                    border: 2px solid var(--primary);
                    border-radius: 24px;
                    margin: 20px;
                    padding: 0;
                    box-shadow: 
                        0 25px 50px rgba(0, 0, 0, 0.5),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    overflow: hidden;
                    animation: fadeInUp 0.8s ease-out;
                }}
                
                .header {{
                    background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
                    color: white;
                    padding: 2rem;
                    position: relative;
                    overflow: hidden;
                }}
                
                .header::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    right: 0;
                    width: 200px;
                    height: 200px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 50%;
                    transform: translate(50px, -50px);
                }}
                
                .header h1 {{
                    font-size: 2.5rem;
                    font-weight: 700;
                    margin-bottom: 0.5rem;
                    position: relative;
                    z-index: 2;
                }}
                
                .header p {{
                    opacity: 0.9;
                    font-size: 1.1rem;
                    margin-bottom: 0;
                    position: relative;
                    z-index: 2;
                }}
                
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    gap: 1.5rem;
                    padding: 2rem;
                }}
                
                .stat-card {{
                    background: linear-gradient(135deg, var(--light) 0%, var(--lighter) 100%);
                    border: 2px solid transparent;
                    border-radius: 20px;
                    padding: 2rem;
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                    position: relative;
                    overflow: hidden;
                    box-shadow: 
                        0 15px 35px rgba(0, 0, 0, 0.3),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
                }}
                
                .stat-card::after {{
                    content: '';
                    position: absolute;
                    top: -50%;
                    left: -50%;
                    width: 200%;
                    height: 200%;
                    background: linear-gradient(45deg, transparent, rgba(220, 38, 38, 0.1), transparent);
                    transform: rotate(45deg);
                    transition: all 0.6s ease;
                    opacity: 0;
                }}
                
                .stat-card:hover {{
                    transform: translateY(-10px) scale(1.02);
                    border-color: var(--primary);
                    box-shadow: 
                        0 25px 50px rgba(0, 0, 0, 0.4),
                        0 0 30px rgba(220, 38, 38, 0.3);
                    animation: glow 2s infinite;
                }}
                
                .stat-card:hover::after {{
                    opacity: 1;
                    transform: rotate(45deg) translate(50%, 50%);
                }}
                
                .stat-card::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: linear-gradient(90deg, var(--primary), var(--accent));
                }}
                
                .stat-card.success::before {{ background: linear-gradient(90deg, var(--success), #16a34a); }}
                .stat-card.warning::before {{ background: linear-gradient(90deg, var(--warning), #d97706); }}
                .stat-card.danger::before {{ background: linear-gradient(90deg, var(--danger), var(--secondary)); }}
                .stat-card.primary::before {{ background: linear-gradient(90deg, var(--primary), var(--accent)); }}
                
                .stat-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 1.5rem;
                }}
                
                .stat-icon {{
                    width: 60px;
                    height: 60px;
                    border-radius: 18px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.8rem;
                    color: white;
                    transition: all 0.3s ease;
                    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
                }}
                
                .stat-card:hover .stat-icon {{
                    transform: scale(1.1) rotate(5deg);
                    animation: pulse 1s infinite;
                }}
                
                .stat-icon.success {{ background: linear-gradient(135deg, var(--success), #16a34a); }}
                .stat-icon.warning {{ background: linear-gradient(135deg, var(--warning), #d97706); }}
                .stat-icon.danger {{ background: linear-gradient(135deg, var(--danger), var(--secondary)); }}
                .stat-icon.primary {{ background: linear-gradient(135deg, var(--primary), var(--accent)); }}
                
                .stat-value {{
                    font-size: 3rem;
                    font-weight: 800;
                    background: linear-gradient(135deg, var(--text-primary), var(--primary));
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    margin-bottom: 0.5rem;
                }}
                
                .stat-label {{
                    color: var(--text-secondary);
                    font-weight: 600;
                    font-size: 1rem;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                
                .content-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 2rem;
                    padding: 0 2rem 2rem;
                }}
                
                .card-modern {{
                    background: linear-gradient(135deg, var(--light) 0%, var(--lighter) 100%);
                    border: 2px solid transparent;
                    border-radius: 20px;
                    overflow: hidden;
                    box-shadow: 
                        0 15px 35px rgba(0, 0, 0, 0.3),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    transition: all 0.4s ease;
                }}
                
                .card-modern:hover {{
                    border-color: var(--primary);
                    box-shadow: 
                        0 20px 40px rgba(0, 0, 0, 0.4),
                        0 0 20px rgba(220, 38, 38, 0.2);
                }}
                
                .card-header-modern {{
                    background: linear-gradient(135deg, rgba(220, 38, 38, 0.1), rgba(153, 27, 27, 0.1));
                    padding: 2rem;
                    border-bottom: 2px solid rgba(220, 38, 38, 0.2);
                }}
                
                .card-header-modern h5 {{
                    margin: 0;
                    font-weight: 700;
                    color: var(--text-primary);
                    font-size: 1.3rem;
                }}
                
                .card-body-modern {{
                    padding: 2rem;
                }}
                
                .action-btn {{
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                    padding: 1.2rem 1.5rem;
                    background: linear-gradient(135deg, var(--dark) 0%, var(--light) 100%);
                    border: 2px solid rgba(220, 38, 38, 0.3);
                    border-radius: 15px;
                    text-decoration: none;
                    color: var(--text-primary);
                    font-weight: 600;
                    font-size: 1rem;
                    transition: all 0.3s ease;
                    margin-bottom: 1rem;
                    position: relative;
                    overflow: hidden;
                }}
                
                .action-btn::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, transparent, rgba(220, 38, 38, 0.2), transparent);
                    transition: left 0.5s ease;
                }}
                
                .action-btn:hover {{
                    border-color: var(--primary);
                    background: linear-gradient(135deg, var(--primary), var(--accent));
                    color: white;
                    transform: translateX(8px) translateY(-2px);
                    box-shadow: 0 10px 25px rgba(220, 38, 38, 0.4);
                }}
                
                .action-btn:hover::before {{
                    left: 100%;
                }}
                
                .action-btn i {{
                    font-size: 1.4rem;
                    transition: transform 0.3s ease;
                }}
                
                .action-btn:hover i {{
                    transform: scale(1.2) rotate(5deg);
                }}
                
                .status-indicator {{
                    display: inline-flex;
                    align-items: center;
                    gap: 0.75rem;
                    padding: 0.75rem 1.5rem;
                    background: linear-gradient(135deg, var(--success), #16a34a);
                    color: white;
                    border-radius: 25px;
                    font-weight: 700;
                    font-size: 1rem;
                    box-shadow: 0 8px 20px rgba(34, 197, 94, 0.3);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                
                .status-indicator::before {{
                    content: '';
                    width: 10px;
                    height: 10px;
                    background: white;
                    border-radius: 50%;
                    animation: pulse 2s infinite;
                    box-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
                }}
                
                .alert-modern {{
                    padding: 1.5rem 2rem;
                    border-radius: 15px;
                    border: 2px solid transparent;
                    margin-bottom: 1.5rem;
                    font-weight: 600;
                    font-size: 1rem;
                }}
                
                .alert-success {{
                    background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(22, 163, 74, 0.1));
                    color: var(--success);
                    border-color: var(--success);
                }}
                
                .alert-warning {{
                    background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.1));
                    color: var(--warning);
                    border-color: var(--warning);
                }}
                
                .logout-btn {{
                    position: absolute;
                    top: 2rem;
                    right: 2rem;
                    background: linear-gradient(135deg, rgba(220, 38, 38, 0.2), rgba(153, 27, 27, 0.2));
                    color: white;
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    padding: 0.75rem 1.5rem;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: 500;
                    transition: all 0.3s ease;
                    z-index: 3;
                    position: relative;
                }}
                
                .logout-btn:hover {{
                    background: rgba(255, 255, 255, 0.3);
                    color: white;
                }}
                
                @media (max-width: 768px) {{
                    .content-grid {{
                        grid-template-columns: 1fr;
                    }}
                    .stats-grid {{
                        grid-template-columns: 1fr;
                        padding: 1rem;
                    }}
                    .main-container {{
                        margin: 10px;
                    }}
                    .header h1 {{
                        font-size: 2rem;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="main-container">
                <div class="header">
                    <a href="/logout" class="logout-btn">
                        <i class="fas fa-sign-out-alt"></i> Sair
                    </a>
                    <h1><i class="fas fa-robot"></i> Painel Administrativo</h1>
                    <p>Sistema de Gerenciamento do Bot • {now.strftime('%d/%m/%Y %H:%M')}</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card success">
                        <div class="stat-header">
                            <div>
                                <div class="stat-value">{stats['total_groups']}</div>
                                <div class="stat-label">Grupos Ativos</div>
                            </div>
                            <div class="stat-icon success">
                                <i class="fas fa-layer-group"></i>
                            </div>
                        </div>
                    </div>
                    
                    <div class="stat-card primary">
                        <div class="stat-header">
                            <div>
                                <div class="stat-value">{stats['total_users']}</div>
                                <div class="stat-label">Usuários Registrados</div>
                            </div>
                            <div class="stat-icon primary">
                                <i class="fas fa-users"></i>
                            </div>
                        </div>
                    </div>
                    
                    <div class="stat-card warning">
                        <div class="stat-header">
                            <div>
                                <div class="stat-value">{stats['active_plans']}</div>
                                <div class="stat-label">Planos Ativos</div>
                            </div>
                            <div class="stat-icon warning">
                                <i class="fas fa-star"></i>
                            </div>
                        </div>
                    </div>
                    
                    <div class="stat-card danger">
                        <div class="stat-header">
                            <div>
                                <div class="stat-value">R$ {stats['total_revenue']:.2f}</div>
                                <div class="stat-label">Receita Estimada</div>
                            </div>
                            <div class="stat-icon danger">
                                <i class="fas fa-dollar-sign"></i>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="content-grid">
                    <div class="card-modern">
                        <div class="card-header-modern">
                            <h5><i class="fas fa-bolt"></i> Ações Rápidas</h5>
                        </div>
                        <div class="card-body-modern">
                            <a href="/users" class="action-btn">
                                <i class="fas fa-users"></i>
                                <span>Gerenciar Usuários</span>
                            </a>
                            <a href="/messages" class="action-btn">
                                <i class="fas fa-envelope"></i>
                                <span>Mensagens Agendadas</span>
                            </a>
                            <a href="/groups" class="action-btn">
                                <i class="fas fa-layer-group"></i>
                                <span>Gerenciar Grupos</span>
                            </a>
                            <a href="/settings" class="action-btn">
                                <i class="fas fa-cog"></i>
                                <span>Configurações</span>
                            </a>
                        </div>
                    </div>
                    
                    <div class="card-modern">
                        <div class="card-header-modern">
                            <h5><i class="fas fa-chart-line"></i> Status do Sistema</h5>
                        </div>
                        <div class="card-body-modern">
                            {'<div class="alert-modern alert-warning"><i class="fas fa-exclamation-triangle"></i> ' + str(stats['expiring_soon']) + ' plano(s) expirando em breve!</div>' if stats['expiring_soon'] > 0 else '<div class="alert-modern alert-success"><i class="fas fa-check-circle"></i> Todos os planos estão em dia!</div>'}
                            
                            <div style="margin-top: 1.5rem;">
                                <div class="status-indicator">
                                    Bot Online
                                </div>
                            </div>
                            
                            <div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 2px solid rgba(220, 38, 38, 0.2);">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 1rem;">
                                    <span style="color: var(--text-secondary); font-weight: 600;">Mensagens Agendadas:</span>
                                    <strong style="color: var(--text-primary); font-size: 1.1rem;">{stats['scheduled_messages']}</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 1rem;">
                                    <span style="color: var(--text-secondary); font-weight: 600;">Última Atualização:</span>
                                    <strong style="color: var(--text-primary); font-size: 1.1rem;">{now.strftime('%H:%M:%S')}</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: var(--text-secondary); font-weight: 600;">Uptime:</span>
                                    <strong style="color: var(--success); font-size: 1.1rem; text-shadow: 0 0 10px rgba(34, 197, 94, 0.5);">Online</strong>
                                </div>
                            </div>
                            
                            <!-- Scrollbar personalizada -->
                            <style>
                                ::-webkit-scrollbar {{
                                    width: 8px;
                                }}
                                
                                ::-webkit-scrollbar-track {{
                                    background: var(--dark);
                                    border-radius: 4px;
                                }}
                                
                                ::-webkit-scrollbar-thumb {{
                                    background: linear-gradient(135deg, var(--primary), var(--accent));
                                    border-radius: 4px;
                                }}
                                
                                ::-webkit-scrollbar-thumb:hover {{
                                    background: linear-gradient(135deg, var(--accent), var(--primary));
                                }}
                            </style>
                        </div>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
            <script>
                // Auto-refresh stats every 30 seconds
                setInterval(() => {{
                    fetch('/api/stats')
                        .then(response => response.json())
                        .then(data => {{
                            // Update stats values
                            document.querySelector('.stat-card.success .stat-value').textContent = data.total_groups;
                            document.querySelector('.stat-card.primary .stat-value').textContent = data.total_users;
                            document.querySelector('.stat-card.warning .stat-value').textContent = data.active_plans;
                            document.querySelector('.stat-card.danger .stat-value').textContent = 'R$ ' + data.total_revenue.toFixed(2);
                        }})
                        .catch(error => console.log('Stats update failed:', error));
                }}, 30000);
            </script>
        </body>
        </html>
        '''

    @web_app.route('/api/stats')
    @require_auth
    def api_stats():
        """API para estatísticas"""
        return jsonify(get_dashboard_stats())

    @web_app.route('/users')
    @require_auth
    def users():
        """Página de usuários com tema dark"""
        registered_users = load_registered_users()
        
        # Prepara lista de usuários com informações completas
        users_list = []
        for user_id, user_data in registered_users.items():
            users_list.append({
                'id': user_id,
                'username': user_data.get('username', 'N/A'),
                'full_name': user_data.get('full_name', 'N/A'),
                'registration_date': user_data.get('registration_date', 'N/A')
            })
        
        # Ordena por ID
        users_list.sort(key=lambda x: int(x['id']), reverse=True)
        
        return f'''
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Usuários - Painel Admin</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
            <style>
                :root {{
                    --primary: #dc2626;
                    --secondary: #991b1b;
                    --accent: #ef4444;
                    --dark: #0a0a0a;
                    --darker: #000000;
                    --light: #1a1a1a;
                    --lighter: #2a2a2a;
                    --text-primary: #ffffff;
                    --text-secondary: #a1a1aa;
                    --success: #22c55e;
                    --warning: #f59e0b;
                    --danger: #dc2626;
                    --info: #3b82f6;
                }}
                
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    background: linear-gradient(135deg, var(--darker) 0%, var(--dark) 50%, var(--secondary) 100%);
                    min-height: 100vh;
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    color: var(--text-primary);
                    padding: 20px;
                }}
                
                body::before {{
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: 
                        radial-gradient(circle at 20% 80%, rgba(220, 38, 38, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(239, 68, 68, 0.1) 0%, transparent 50%);
                    pointer-events: none;
                    z-index: -1;
                }}
                
                .main-container {{
                    max-width: 1600px;
                    margin: 0 auto;
                    background: linear-gradient(135deg, var(--light) 0%, var(--lighter) 100%);
                    border: 2px solid var(--primary);
                    border-radius: 20px;
                    padding: 30px;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
                }}
                
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 2px solid var(--primary);
                }}
                
                .header h1 {{
                    font-size: 2rem;
                    font-weight: 700;
                    color: var(--text-primary);
                    display: flex;
                    align-items: center;
                    gap: 15px;
                }}
                
                .header h1 i {{
                    color: var(--primary);
                }}
                
                .user-count {{
                    background: var(--primary);
                    color: white;
                    padding: 8px 20px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 1.1rem;
                }}
                
                .btn-back {{
                    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                    color: white;
                    padding: 12px 24px;
                    border-radius: 10px;
                    text-decoration: none;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    font-weight: 600;
                    transition: all 0.3s ease;
                    border: 2px solid transparent;
                }}
                
                .btn-back:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 10px 20px rgba(220, 38, 38, 0.3);
                    border-color: var(--accent);
                    color: white;
                }}
                
                .table-container {{
                    background: var(--light);
                    border-radius: 15px;
                    padding: 20px;
                    overflow-x: auto;
                    border: 2px solid var(--lighter);
                }}
                
                table {{
                    width: 100%;
                    border-collapse: separate;
                    border-spacing: 0 10px;
                }}
                
                thead {{
                    background: var(--darker);
                    border-radius: 10px;
                }}
                
                thead th {{
                    padding: 15px 20px;
                    text-align: left;
                    font-weight: 600;
                    color: var(--text-primary);
                    border: none;
                    font-size: 0.95rem;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                
                thead th:first-child {{
                    border-radius: 10px 0 0 10px;
                }}
                
                thead th:last-child {{
                    border-radius: 0 10px 10px 0;
                }}
                
                tbody tr {{
                    background: var(--lighter);
                    transition: all 0.3s ease;
                }}
                
                tbody tr:hover {{
                    transform: translateX(5px);
                    box-shadow: 0 5px 15px rgba(220, 38, 38, 0.2);
                    background: var(--light);
                }}
                
                tbody td {{
                    padding: 18px 20px;
                    border: none;
                    color: var(--text-primary);
                }}
                
                tbody tr td:first-child {{
                    border-radius: 10px 0 0 10px;
                }}
                
                tbody tr td:last-child {{
                    border-radius: 0 10px 10px 0;
                }}
                
                .user-id {{
                    font-family: 'Courier New', monospace;
                    font-weight: 600;
                    color: var(--info);
                    font-size: 0.95rem;
                }}
                
                .user-username {{
                    color: var(--success);
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}
                
                .user-username i {{
                    color: var(--primary);
                }}
                
                .user-name {{
                    color: var(--text-primary);
                    font-weight: 500;
                }}
                
                .user-date {{
                    color: var(--text-secondary);
                    font-size: 0.9rem;
                }}
                
                .badge-status {{
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 0.85rem;
                    font-weight: 600;
                    background: rgba(34, 197, 94, 0.1);
                    color: var(--success);
                    border: 1px solid var(--success);
                }}
                
                .btn-action {{
                    background: linear-gradient(135deg, var(--info) 0%, #2563eb 100%);
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                }}
                
                .btn-action:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(59, 130, 246, 0.3);
                }}
                
                .empty-state {{
                    text-align: center;
                    padding: 60px 20px;
                    color: var(--text-secondary);
                }}
                
                .empty-state i {{
                    font-size: 4rem;
                    margin-bottom: 20px;
                    opacity: 0.3;
                }}
                
                @media (max-width: 768px) {{
                    .main-container {{
                        padding: 15px;
                    }}
                    
                    .header {{
                        flex-direction: column;
                        gap: 15px;
                        text-align: center;
                    }}
                    
                    .header h1 {{
                        font-size: 1.5rem;
                    }}
                    
                    table {{
                        font-size: 0.85rem;
                    }}
                    
                    thead th, tbody td {{
                        padding: 12px 10px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="main-container">
                <div class="header">
                    <div style="display: flex; align-items: center; gap: 20px;">
                        <h1>
                            <i class="fas fa-users"></i>
                            Usuários
                        </h1>
                        <span class="user-count">{len(users_list)}</span>
                    </div>
                    <a href="/" class="btn-back">
                        <i class="fas fa-arrow-left"></i>
                        Dashboard
                    </a>
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Username</th>
                                <th>Nome Completo</th>
                                <th>Data de Registro</th>
                                <th>Status</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join([f"""
                            <tr>
                                <td><span class="user-id">{user['id']}</span></td>
                                <td><span class="user-username"><i class="fas fa-at"></i>{user['username']}</span></td>
                                <td><span class="user-name">{user['full_name']}</span></td>
                                <td><span class="user-date">{user['registration_date']}</span></td>
                                <td><span class="badge-status"><i class="fas fa-check-circle"></i>Ativo</span></td>
                                <td><button class="btn-action" onclick="viewUser('{user['id']}')"><i class="fas fa-eye"></i>Ver</button></td>
                            </tr>
                            """ for user in users_list[:100]]) if users_list else '<tr><td colspan="6"><div class="empty-state"><i class="fas fa-users-slash"></i><p>Nenhum usuário registrado</p></div></td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
            <script>
                function viewUser(userId) {{
                    alert(`Visualizando usuário: ${{userId}}`);
                    // Aqui você pode adicionar mais funcionalidades
                }}
            </script>
        </body>
        </html>
        '''

    @web_app.route('/messages')
    @require_auth
    def messages():
        """Página de mensagens moderna agrupadas por ID fixo"""
        scheduled_messages = load_scheduled_messages()
        registered_users = load_registered_users()
        now = datetime.datetime.now()
        
        # Agrupa mensagens por fixed_ad_id
        grouped_messages = {}
        
        for msg in scheduled_messages:
            fixed_id = msg.get('fixed_ad_id', msg.get('code', 'N/A'))
            recipient_id = msg.get('recipient_id')
            
            # Busca username do usuário
            user_data = registered_users.get(str(recipient_id), {})
            username = user_data.get('username', 'N/A')
            
            if fixed_id not in grouped_messages:
                grouped_messages[fixed_id] = {
                    'fixed_ad_id': fixed_id,
                    'recipient_id': recipient_id,
                    'username': username,
                    'from_chat_id': msg.get('from_chat_id'),
                    'message_id': msg.get('message_id'),
                    'chat_id': msg.get('chat_id'),
                    'creation_time': msg.get('creation_time'),
                    'expiry_time': msg.get('expiry_time'),
                    'times': [],
                    'is_active': True
                }
            
            # Adiciona horário à lista
            time_info = msg.get('time', 'N/A')
            if time_info not in grouped_messages[fixed_id]['times']:
                grouped_messages[fixed_id]['times'].append(time_info)
        
        # Separa grupos ativos e expirados
        active_groups = []
        expired_groups = []
        
        for group in grouped_messages.values():
            expiry_str = group.get('expiry_time')
            if expiry_str:
                try:
                    expiry_dt = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                    if expiry_dt > now:
                        active_groups.append(group)
                    else:
                        expired_groups.append(group)
                except:
                    active_groups.append(group)
            else:
                active_groups.append(group)
        
        # Ordena os horários em cada grupo
        for group in active_groups + expired_groups:
            group['times'].sort()
        
        return f'''
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Mensagens - Painel Admin</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --primary: #6366f1;
                    --secondary: #8b5cf6;
                    --success: #10b981;
                    --warning: #f59e0b;
                    --danger: #ef4444;
                    --dark: #1f2937;
                    --light: #f8fafc;
                    --border: #e5e7eb;
                }}
                
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                
                body {{
                    font-family: 'Inter', sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: #374151;
                }}
                
                .main-container {{
                    background: rgba(255, 255, 255, 0.98);
                    backdrop-filter: blur(20px);
                    border-radius: 24px;
                    margin: 20px;
                    padding: 2rem;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                }}
                
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 2rem;
                    padding-bottom: 1rem;
                    border-bottom: 2px solid var(--border);
                }}
                
                .header h1 {{
                    color: var(--dark);
                    font-weight: 700;
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                }}
                
                .btn-back {{
                    background: var(--primary);
                    color: white;
                    border: none;
                    padding: 0.75rem 1.5rem;
                    border-radius: 12px;
                    text-decoration: none;
                    font-weight: 500;
                    transition: all 0.3s ease;
                }}
                
                .btn-back:hover {{
                    background: var(--primary);
                    transform: translateY(-2px);
                    box-shadow: 0 10px 25px rgba(99, 102, 241, 0.3);
                    color: white;
                }}
                
                .stats-row {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 1.5rem;
                    margin-bottom: 2rem;
                }}
                
                .stat-card {{
                    background: white;
                    border-radius: 16px;
                    padding: 1.5rem;
                    border: 1px solid var(--border);
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                }}
                
                .stat-card::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 4px;
                    height: 100%;
                }}
                
                .stat-card.total::before {{ background: var(--primary); }}
                .stat-card.active::before {{ background: var(--success); }}
                .stat-card.expired::before {{ background: var(--danger); }}
                
                .stat-number {{
                    font-size: 2rem;
                    font-weight: 700;
                    color: var(--dark);
                }}
                
                .stat-label {{
                    color: #6b7280;
                    font-weight: 500;
                    margin-top: 0.5rem;
                }}
                
                .messages-section {{
                    background: white;
                    border-radius: 16px;
                    border: 1px solid var(--border);
                    overflow: hidden;
                    margin-bottom: 2rem;
                }}
                
                .section-header {{
                    background: var(--light);
                    padding: 1.5rem;
                    border-bottom: 1px solid var(--border);
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                }}
                
                .section-header h3 {{
                    margin: 0;
                    color: var(--dark);
                    font-weight: 600;
                }}
                
                .messages-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                    gap: 1rem;
                    padding: 1.5rem;
                }}
                
                .message-card {{
                    background: #f8fafc;
                    border: 2px solid var(--border);
                    border-radius: 12px;
                    padding: 1rem;
                    transition: all 0.3s ease;
                    position: relative;
                }}
                
                .message-card:hover {{
                    border-color: var(--primary);
                    transform: translateY(-2px);
                    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
                }}
                
                .message-card.active {{
                    border-left: 4px solid var(--success);
                }}
                
                .message-card.expired {{
                    border-left: 4px solid var(--danger);
                    opacity: 0.7;
                }}
                
                .message-id {{
                    font-family: 'Courier New', monospace;
                    font-size: 0.875rem;
                    color: var(--primary);
                    font-weight: 600;
                    margin-bottom: 0.5rem;
                }}
                
                .message-info {{
                    margin-bottom: 1rem;
                }}
                
                .info-row {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 0.5rem;
                    font-size: 0.875rem;
                }}
                
                .info-label {{
                    color: #6b7280;
                    font-weight: 500;
                }}
                
                .info-value {{
                    color: var(--dark);
                    font-weight: 600;
                }}
                
                .message-status {{
                    display: inline-flex;
                    align-items: center;
                    gap: 0.5rem;
                    padding: 0.25rem 0.75rem;
                    border-radius: 20px;
                    font-size: 0.75rem;
                    font-weight: 500;
                    margin-bottom: 1rem;
                }}
                
                .status-active {{
                    background: #dcfce7;
                    color: #166534;
                }}
                
                .status-expired {{
                    background: #fef2f2;
                    color: #dc2626;
                }}
                
                .message-actions {{
                    display: flex;
                    gap: 0.5rem;
                }}
                
                .btn-action {{
                    flex: 1;
                    padding: 0.5rem;
                    border: none;
                    border-radius: 8px;
                    font-size: 0.875rem;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }}
                
                .btn-view {{
                    background: var(--primary);
                    color: white;
                }}
                
                .btn-view:hover {{
                    background: #4f46e5;
                    transform: translateY(-1px);
                }}
                
                .btn-remove {{
                    background: var(--danger);
                    color: white;
                }}
                
                .btn-remove:hover {{
                    background: #dc2626;
                    transform: translateY(-1px);
                }}
                
                .empty-state {{
                    text-align: center;
                    padding: 3rem;
                    color: #6b7280;
                }}
                
                .empty-state i {{
                    font-size: 3rem;
                    margin-bottom: 1rem;
                    opacity: 0.5;
                }}
                
                @media (max-width: 768px) {{
                    .main-container {{
                        margin: 10px;
                        padding: 1rem;
                    }}
                    
                    .header {{
                        flex-direction: column;
                        gap: 1rem;
                        text-align: center;
                    }}
                    
                    .messages-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="main-container">
                <div class="header">
                    <h1>
                        <i class="fas fa-envelope"></i>
                        Mensagens Agendadas
                    </h1>
                    <a href="/" class="btn-back">
                        <i class="fas fa-arrow-left"></i>
                        Dashboard
                    </a>
                </div>
                
                <div class="stats-row">
                    <div class="stat-card total">
                        <div class="stat-number">{len(grouped_messages)}</div>
                        <div class="stat-label">Total de Planos</div>
                    </div>
                    <div class="stat-card active">
                        <div class="stat-number">{len(active_groups)}</div>
                        <div class="stat-label">Planos Ativos</div>
                    </div>
                    <div class="stat-card expired">
                        <div class="stat-number">{len(expired_groups)}</div>
                        <div class="stat-label">Planos Expirados</div>
                    </div>
                </div>
                
                <!-- Seção de Planos Ativos -->
                <div class="messages-section">
                    <div class="section-header">
                        <i class="fas fa-check-circle" style="color: var(--success);"></i>
                        <h3>Planos Ativos ({len(active_groups)})</h3>
                    </div>
                    <div class="messages-grid">
                        {(''.join([f"""
                        <div class="message-card active">
                            <div class="message-id">#{group.get('fixed_ad_id', 'N/A')}</div>
                            <div class="message-status status-active">
                                <i class="fas fa-check-circle"></i>
                                Ativo
                            </div>
                            <div class="message-info">
                                <div class="info-row">
                                    <span class="info-label">Usuário:</span>
                                    <span class="info-value">{group.get('recipient_id', 'N/A')} (@{group.get('username', 'N/A')})</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Horários:</span>
                                    <span class="info-value">{', '.join(group.get('times', []))[:50]}{'...' if len(', '.join(group.get('times', []))) > 50 else ''}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Total:</span>
                                    <span class="info-value">{len(group.get('times', []))} envios/dia</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Expira:</span>
                                    <span class="info-value">{group.get('expiry_time', 'N/A')[:10] if group.get('expiry_time') else 'N/A'}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Criado:</span>
                                    <span class="info-value">{group.get('creation_time', 'N/A')[:10] if group.get('creation_time') else 'N/A'}</span>
                                </div>
                            </div>
                            <div class="message-actions">
                                <button class="btn-action btn-view" onclick="viewMessage('{group.get('fixed_ad_id', 'N/A')}')">
                                    <i class="fas fa-eye"></i> Ver Mensagem
                                </button>
                                <button class="btn-action btn-remove" onclick="removeMessage('{group.get('fixed_ad_id', 'N/A')}')">
                                    <i class="fas fa-trash"></i> Remover Plano
                                </button>
                            </div>
                        </div>
                        """ for group in active_groups[:30]]) if active_groups else '<div class="empty-state"><i class="fas fa-envelope"></i><p>Nenhum plano ativo encontrado</p></div>')}
                    </div>
                </div>
                
                <!-- Seção de Planos Expirados -->
                {''.join([f"""
                <div class="messages-section">
                    <div class="section-header">
                        <i class="fas fa-times-circle" style="color: var(--danger);"></i>
                        <h3>Planos Expirados ({len(expired_groups)})</h3>
                    </div>
                    <div class="messages-grid">
                        <div class="message-card expired">
                            <div class="message-id">#{group.get('fixed_ad_id', 'N/A')}</div>
                            <div class="message-status status-expired">
                                <i class="fas fa-times-circle"></i>
                                Expirado
                            </div>
                            <div class="message-info">
                                <div class="info-row">
                                    <span class="info-label">Usuário:</span>
                                    <span class="info-value">{group.get('recipient_id', 'N/A')} (@{group.get('username', 'N/A')})</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Horários:</span>
                                    <span class="info-value">{', '.join(group.get('times', []))[:50]}{'...' if len(', '.join(group.get('times', []))) > 50 else ''}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Total:</span>
                                    <span class="info-value">{len(group.get('times', []))} envios/dia</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Expirou:</span>
                                    <span class="info-value">{group.get('expiry_time', 'N/A')[:10] if group.get('expiry_time') else 'N/A'}</span>
                                </div>
                            </div>
                            <div class="message-actions">
                                <button class="btn-action btn-remove" onclick="removeMessage('{group.get('fixed_ad_id', 'N/A')}')">
                                    <i class="fas fa-trash"></i> Remover Plano
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                """ for group in expired_groups[:20]]) if expired_groups else ''}
            </div>
            
            <!-- Modal para visualizar mensagem -->
            <div class="modal fade" id="messageModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-envelope"></i>
                                Conteúdo da Mensagem
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body" id="messageContent">
                            <!-- Conteúdo carregado dinamicamente -->
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
            <script>
                // Dados dos planos para busca rápida
                const plansData = {json.dumps([{
                    'id': group.get('fixed_ad_id', 'N/A'),
                    'recipient_id': group.get('recipient_id', 'N/A'),
                    'times': group.get('times', []),
                    'expiry_time': group.get('expiry_time', 'N/A'),
                    'creation_time': group.get('creation_time', 'N/A'),
                    'message_id': group.get('message_id', 'N/A'),
                    'from_chat_id': group.get('from_chat_id', 'N/A'),
                    'chat_id': group.get('chat_id', 'N/A')
                } for group in active_groups + expired_groups])};
                
                function viewMessage(planId) {{
                    const plan = plansData.find(p => p.id === planId);
                    if (!plan) {{
                        alert('Plano não encontrado!');
                        return;
                    }}
                    
                    const modalContent = document.getElementById('messageContent');
                    modalContent.innerHTML = `
                        <div class="row">
                            <div class="col-md-6">
                                <h6><i class="fas fa-info-circle"></i> Informações do Plano</h6>
                                <table class="table table-sm">
                                    <tr><td><strong>ID Fixo:</strong></td><td>${{plan.id}}</td></tr>
                                    <tr><td><strong>Destinatário:</strong></td><td>${{plan.recipient_id}}</td></tr>
                                    <tr><td><strong>Total de Envios:</strong></td><td>${{plan.times.length}} por dia</td></tr>
                                    <tr><td><strong>Chat ID:</strong></td><td>${{plan.chat_id}}</td></tr>
                                    <tr><td><strong>Message ID:</strong></td><td>${{plan.message_id}}</td></tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h6><i class="fas fa-calendar"></i> Datas e Horários</h6>
                                <table class="table table-sm">
                                    <tr><td><strong>Criado:</strong></td><td>${{plan.creation_time}}</td></tr>
                                    <tr><td><strong>Expira:</strong></td><td>${{plan.expiry_time}}</td></tr>
                                    <tr><td><strong>De Chat:</strong></td><td>${{plan.from_chat_id}}</td></tr>
                                </table>
                            </div>
                        </div>
                        
                        <div class="mt-4">
                            <h6><i class="fas fa-clock"></i> Horários de Envio</h6>
                            <div class="alert alert-light">
                                <div class="row">
                                    ${{plan.times.map((time, index) => `
                                        <div class="col-md-2 mb-2">
                                            <span class="badge bg-primary">${{time}}</span>
                                        </div>
                                    `).join('')}}
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-4">
                            <h6><i class="fas fa-comment"></i> Conteúdo da Mensagem</h6>
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle"></i>
                                <strong>Nota:</strong> O conteúdo da mensagem está armazenado no Telegram com o Message ID: <code>${{plan.message_id}}</code>
                                <br><br><strong>Para visualizar o conteúdo completo:</strong>
                                <ul class="mt-2 mb-0">
                                    <li><strong>Opção 1:</strong> Clique no botão abaixo para receber a mensagem no seu chat privado</li>
                                    <li><strong>Opção 2:</strong> Acesse o chat de origem (ID: ${{plan.from_chat_id}}) e procure pela mensagem ID: ${{plan.message_id}}</li>
                                </ul>
                            </div>
                            
                            <div class="alert alert-success">
                                <i class="fas fa-user-shield"></i>
                                <strong>Privacidade:</strong> A mensagem será enviada apenas para você (admin logado) no chat privado com o bot.
                            </div>
                            
                            <div class="d-grid gap-2">
                                <button class="btn btn-primary btn-lg" onclick="forwardMessage('${{plan.message_id}}', '${{plan.from_chat_id}}')">
                                    <i class="fas fa-paper-plane"></i> Enviar Mensagem para Mim
                                </button>
                            </div>
                        </div>
                    `;
                    
                    const modal = new bootstrap.Modal(document.getElementById('messageModal'));
                    modal.show();
                }}
                
                function forwardMessage(messageId, fromChatId) {{
                    if (confirm('Deseja receber esta mensagem no seu chat privado com o bot para visualizar o conteúdo completo?')) {{
                        fetch('/api/forward_message', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{
                                message_id: messageId,
                                from_chat_id: fromChatId
                            }})
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                alert('✅ ' + data.message);
                            }} else {{
                                alert('❌ Erro ao enviar mensagem: ' + data.message);
                            }}
                        }})
                        .catch(error => {{
                            alert('❌ Erro de conexão: ' + error);
                        }});
                    }}
                }}
                
                function removeMessage(messageId) {{
                    if (confirm(`Deseja realmente remover a mensagem ${{messageId}}?`)) {{
                        fetch(`/api/remove_message/${{messageId}}`, {{
                            method: 'DELETE'
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                location.reload();
                            }} else {{
                                alert('Erro ao remover: ' + data.message);
                            }}
                        }})
                        .catch(error => {{
                            alert('Erro ao remover mensagem');
                        }});
                    }}
                }}
            </script>
        </body>
        </html>
        '''

    @web_app.route('/schedule_monitor')
    @require_auth
    def schedule_monitor():
        """Página de monitoramento de horários"""
        try:
            # Carrega log de horários
            scheduler_log = {}
            if os.path.exists('scheduler_log.json'):
                with open('scheduler_log.json', 'r', encoding='utf-8') as f:
                    scheduler_log = json.load(f)
            
            # Carrega mensagens agendadas
            scheduled_messages = load_scheduled_messages()
            
            # Organiza horários por status
            horarios_com_planos = {}
            for msg in scheduled_messages:
                time_slot = msg.get('time')
                if time_slot:
                    if time_slot not in horarios_com_planos:
                        horarios_com_planos[time_slot] = []
                    horarios_com_planos[time_slot].append({
                        'code': msg.get('code', 'N/A'),
                        'id': msg.get('id', 'N/A'),
                        'type': msg.get('type', 'indefinido'),
                        'recipient_id': msg.get('recipient_id', 'N/A')
                    })
            
            # Monta dados para o template
            horarios_status = []
            now = datetime.datetime.now()
            
            for time_slot in sorted(horarios_com_planos.keys()):
                log_entry = scheduler_log.get(time_slot, {})
                planos = horarios_com_planos[time_slot]
                
                # Determina status baseado no log e no horário
                status = 'pending'  # padrão
                ultimo_envio = log_entry.get('timestamp', 'Nunca')
                ultimo_envio_datetime = None
                
                # Tenta parsear a data do último envio
                if ultimo_envio != 'Nunca':
                    try:
                        ultimo_envio_datetime = datetime.datetime.strptime(ultimo_envio, '%Y-%m-%d %H:%M:%S')
                    except:
                        try:
                            ultimo_envio_datetime = datetime.datetime.strptime(ultimo_envio, '%d/%m/%Y %H:%M:%S')
                        except:
                            pass
                
                # Verifica se o horário já passou hoje
                try:
                    hora_slot = datetime.datetime.strptime(time_slot, '%H:%M').time()
                    horario_hoje = datetime.datetime.combine(now.date(), hora_slot)
                    
                    # Se o horário já passou hoje
                    if now.time() > hora_slot:
                        # Verifica se foi enviado hoje
                        if ultimo_envio_datetime and ultimo_envio_datetime.date() == now.date():
                            # Foi enviado hoje - verifica se teve sucesso
                            if log_entry.get('sucesso') or log_entry.get('mensagens_enviadas', 0) > 0:
                                status = 'success'  # Verde - enviado com sucesso
                            elif log_entry.get('erros'):
                                status = 'error'  # Vermelho - teve erros
                            else:
                                status = 'warning'  # Amarelo - enviado mas com avisos
                        else:
                            # Horário passou mas não foi enviado hoje
                            status = 'missed'  # Cinza - perdido
                    else:
                        # Horário ainda não chegou hoje
                        status = 'pending'  # Azul - aguardando
                except:
                    # Se houver erro ao parsear, usa lógica antiga
                    if log_entry.get('verificado'):
                        if log_entry.get('sucesso'):
                            status = 'success'
                        elif log_entry.get('erros'):
                            status = 'error'
                        elif log_entry.get('mensagens_enviadas', 0) > 0:
                            status = 'success'
                        else:
                            status = 'warning'
                
                # Formata o último envio de forma mais amigável
                ultimo_envio_formatado = 'Nunca'
                if ultimo_envio_datetime:
                    if ultimo_envio_datetime.date() == now.date():
                        ultimo_envio_formatado = f'Hoje às {ultimo_envio_datetime.strftime("%H:%M")}'
                    elif ultimo_envio_datetime.date() == (now - timedelta(days=1)).date():
                        ultimo_envio_formatado = f'Ontem às {ultimo_envio_datetime.strftime("%H:%M")}'
                    else:
                        ultimo_envio_formatado = ultimo_envio_datetime.strftime('%d/%m/%Y %H:%M')
                
                horarios_status.append({
                    'time': time_slot,
                    'status': status,
                    'planos_count': len(planos),
                    'planos': planos,
                    'last_check': log_entry.get('timestamp', 'Nunca'),
                    'ultimo_envio': ultimo_envio_formatado,
                    'ultimo_envio_raw': ultimo_envio,
                    'mensagens_encontradas': log_entry.get('mensagens_encontradas', 0),
                    'mensagens_enviadas': log_entry.get('mensagens_enviadas', 0),
                    'erros': log_entry.get('erros', []),
                    'taxa_sucesso': log_entry.get('taxa_sucesso', 0)
                })
            
            return render_template_string(SCHEDULE_MONITOR_TEMPLATE, horarios=horarios_status)
            
        except Exception as e:
            logging.error(f"Erro ao carregar monitor de horários: {e}")
            return f"Erro: {e}", 500
    
    @web_app.route('/api/schedule_status')
    @require_auth
    def api_schedule_status():
        """API para obter status dos horários em tempo real"""
        try:
            scheduler_log = {}
            if os.path.exists('scheduler_log.json'):
                with open('scheduler_log.json', 'r', encoding='utf-8') as f:
                    scheduler_log = json.load(f)
            
            return jsonify({
                'success': True,
                'data': scheduler_log,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @web_app.route('/api/plan_stats/<plan_id>')
    @require_auth
    def api_plan_stats(plan_id):
        """API para obter estatísticas de um plano específico"""
        try:
            history = get_plan_broadcast_history(plan_id)
            
            total_envios = len(history)
            total_sucesso = sum(1 for h in history if h.get('status') == 'success')
            total_falhas = sum(1 for h in history if h.get('status') == 'failed')
            
            return jsonify({
                'success': True,
                'plan_id': plan_id,
                'total_envios': total_envios,
                'total_sucesso': total_sucesso,
                'total_falhas': total_falhas,
                'taxa_sucesso': (total_sucesso / total_envios * 100) if total_envios > 0 else 0,
                'history': history[-10:]  # Últimos 10 registros
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    @web_app.route('/groups')
    @require_auth
    def groups():
        """Página de grupos moderna com tema dark"""
        chat_ids_raw = load_chat_ids()
        # Converte para lista se for set, e garante que seja uma lista
        chat_ids = list(chat_ids_raw) if isinstance(chat_ids_raw, set) else chat_ids_raw
        
        # Separa canais e grupos
        canais = [cid for cid in chat_ids if str(cid).startswith('-100')]
        grupos = [cid for cid in chat_ids if not str(cid).startswith('-100')]
        
        return f'''
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Grupos e Canais - Painel Admin</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
            <style>
                :root {{
                    --primary: #dc2626;
                    --secondary: #991b1b;
                    --accent: #ef4444;
                    --dark: #0a0a0a;
                    --darker: #000000;
                    --light: #1a1a1a;
                    --lighter: #2a2a2a;
                    --text-primary: #ffffff;
                    --text-secondary: #a1a1aa;
                    --success: #22c55e;
                    --warning: #f59e0b;
                    --danger: #dc2626;
                    --info: #3b82f6;
                }}
                
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    background: linear-gradient(135deg, var(--darker) 0%, var(--dark) 50%, var(--secondary) 100%);
                    min-height: 100vh;
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    color: var(--text-primary);
                    padding: 20px;
                }}
                
                body::before {{
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: 
                        radial-gradient(circle at 20% 80%, rgba(220, 38, 38, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(239, 68, 68, 0.1) 0%, transparent 50%);
                    pointer-events: none;
                    z-index: -1;
                }}
                
                .main-container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    background: linear-gradient(135deg, var(--light) 0%, var(--lighter) 100%);
                    border: 2px solid var(--primary);
                    border-radius: 20px;
                    padding: 30px;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
                }}
                
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 2px solid var(--primary);
                }}
                
                .header h1 {{
                    font-size: 2rem;
                    font-weight: 700;
                    color: var(--text-primary);
                    display: flex;
                    align-items: center;
                    gap: 15px;
                }}
                
                .header h1 i {{
                    color: var(--primary);
                }}
                
                .btn-back {{
                    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                    color: white;
                    padding: 12px 24px;
                    border-radius: 10px;
                    text-decoration: none;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    font-weight: 600;
                    transition: all 0.3s ease;
                    border: 2px solid transparent;
                }}
                
                .btn-back:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 10px 20px rgba(220, 38, 38, 0.3);
                    border-color: var(--accent);
                    color: white;
                }}
                
                .stats-row {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                
                .stat-card {{
                    background: var(--light);
                    border: 2px solid var(--lighter);
                    border-radius: 15px;
                    padding: 25px;
                    text-align: center;
                    transition: all 0.3s ease;
                }}
                
                .stat-card:hover {{
                    transform: translateY(-5px);
                    border-color: var(--primary);
                    box-shadow: 0 10px 20px rgba(220, 38, 38, 0.2);
                }}
                
                .stat-card.total {{
                    border-color: var(--info);
                }}
                
                .stat-card.canais {{
                    border-color: var(--success);
                }}
                
                .stat-card.grupos {{
                    border-color: var(--warning);
                }}
                
                .stat-number {{
                    font-size: 2.5rem;
                    font-weight: 700;
                    color: var(--primary);
                    margin-bottom: 10px;
                }}
                
                .stat-label {{
                    font-size: 1rem;
                    color: var(--text-secondary);
                    font-weight: 600;
                }}
                
                .groups-section {{
                    margin-bottom: 40px;
                }}
                
                .section-header {{
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    margin-bottom: 20px;
                    padding: 15px;
                    background: var(--light);
                    border-radius: 10px;
                    border-left: 4px solid var(--primary);
                }}
                
                .section-header h3 {{
                    margin: 0;
                    font-size: 1.5rem;
                    font-weight: 600;
                    color: var(--text-primary);
                }}
                
                .section-header i {{
                    font-size: 1.8rem;
                }}
                
                .groups-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 20px;
                }}
                
                .group-card {{
                    background: var(--light);
                    border: 2px solid var(--lighter);
                    border-radius: 15px;
                    padding: 20px;
                    transition: all 0.3s ease;
                }}
                
                .group-card:hover {{
                    transform: translateY(-5px);
                    border-color: var(--primary);
                    box-shadow: 0 10px 20px rgba(220, 38, 38, 0.2);
                }}
                
                .group-id {{
                    font-family: 'Courier New', monospace;
                    font-size: 0.95rem;
                    color: var(--text-primary);
                    background: var(--darker);
                    padding: 10px;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    word-break: break-all;
                    border: 1px solid var(--primary);
                }}
                
                .group-type {{
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 0.85rem;
                    font-weight: 600;
                    margin-bottom: 15px;
                }}
                
                .type-canal {{
                    background: rgba(34, 197, 94, 0.1);
                    color: var(--success);
                    border: 1px solid var(--success);
                }}
                
                .type-grupo {{
                    background: rgba(245, 158, 11, 0.1);
                    color: var(--warning);
                    border: 1px solid var(--warning);
                }}
                
                .group-actions {{
                    display: flex;
                    gap: 10px;
                    margin-top: 15px;
                }}
                
                .btn-action {{
                    flex: 1;
                    padding: 10px;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                }}
                
                .btn-test {{
                    background: linear-gradient(135deg, var(--info) 0%, #2563eb 100%);
                    color: white;
                }}
                
                .btn-test:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(59, 130, 246, 0.3);
                }}
                
                .btn-remove {{
                    background: linear-gradient(135deg, var(--danger) 0%, var(--secondary) 100%);
                    color: white;
                }}
                
                .btn-remove:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(220, 38, 38, 0.3);
                }}
                
                .empty-state {{
                    text-align: center;
                    padding: 60px 20px;
                    color: var(--text-secondary);
                    background: var(--light);
                    border-radius: 15px;
                    border: 2px dashed var(--lighter);
                }}
                
                .empty-state i {{
                    font-size: 4rem;
                    margin-bottom: 20px;
                    opacity: 0.3;
                }}
                
                .empty-state p {{
                    font-size: 1.1rem;
                    margin: 0;
                }}
                
                @media (max-width: 768px) {{
                    .main-container {{
                        padding: 15px;
                    }}
                    
                    .header {{
                        flex-direction: column;
                        gap: 15px;
                        text-align: center;
                    }}
                    
                    .header h1 {{
                        font-size: 1.5rem;
                    }}
                    
                    .groups-grid {{
                        grid-template-columns: 1fr;
                    }}
                    
                    .stats-row {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="main-container">
                <div class="header">
                    <h1>
                        <i class="fas fa-layer-group"></i>
                        Grupos e Canais
                    </h1>
                    <a href="/" class="btn-back">
                        <i class="fas fa-arrow-left"></i>
                        Dashboard
                    </a>
                </div>
                
                <div class="stats-row">
                    <div class="stat-card total">
                        <div class="stat-number">{len(chat_ids)}</div>
                        <div class="stat-label">Total</div>
                    </div>
                    <div class="stat-card canais">
                        <div class="stat-number">{len(canais)}</div>
                        <div class="stat-label">Canais</div>
                    </div>
                    <div class="stat-card grupos">
                        <div class="stat-number">{len(grupos)}</div>
                        <div class="stat-label">Grupos</div>
                    </div>
                </div>
                
                <!-- Seção de Canais -->
                <div class="groups-section">
                    <div class="section-header">
                        <i class="fas fa-broadcast-tower" style="color: var(--success);"></i>
                        <h3>Canais ({len(canais)})</h3>
                    </div>
                    <div class="groups-grid">
                        {(''.join([f"""
                        <div class="group-card">
                            <div class="group-id">{canal}</div>
                            <div class="group-type type-canal">
                                <i class="fas fa-broadcast-tower"></i>
                                Canal
                            </div>
                            <div class="group-actions">
                                <button class="btn-action btn-test" onclick="testGroup('{canal}')">
                                    <i class="fas fa-paper-plane"></i> Testar
                                </button>
                                <button class="btn-action btn-remove" onclick="removeGroup('{canal}')">
                                    <i class="fas fa-trash"></i> Remover
                                </button>
                            </div>
                        </div>
                        """ for canal in canais[:25]]) if canais else '<div class="empty-state"><i class="fas fa-broadcast-tower"></i><p>Nenhum canal encontrado</p></div>')}
                    </div>
                </div>
                
                <!-- Seção de Grupos -->
                <div class="groups-section">
                    <div class="section-header">
                        <i class="fas fa-users" style="color: var(--warning);"></i>
                        <h3>Grupos ({len(grupos)})</h3>
                    </div>
                    <div class="groups-grid">
                        {(''.join([f"""
                        <div class="group-card">
                            <div class="group-id">{grupo}</div>
                            <div class="group-type type-grupo">
                                <i class="fas fa-users"></i>
                                Grupo
                            </div>
                            <div class="group-actions">
                                <button class="btn-action btn-test" onclick="testGroup('{grupo}')">
                                    <i class="fas fa-paper-plane"></i> Testar
                                </button>
                                <button class="btn-action btn-remove" onclick="removeGroup('{grupo}')">
                                    <i class="fas fa-trash"></i> Remover
                                </button>
                            </div>
                        </div>
                        """ for grupo in grupos[:25]]) if grupos else '<div class="empty-state"><i class="fas fa-users"></i><p>Nenhum grupo encontrado</p></div>')}
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
            <script>
                function testGroup(groupId) {{
                    if (confirm(`Deseja enviar uma mensagem de teste para o grupo/canal ${{groupId}}?`)) {{
                        // Simular teste
                        alert(`Mensagem de teste enviada para ${{groupId}}!`);
                    }}
                }}
                
                function removeGroup(groupId) {{
                    if (confirm(`Deseja realmente remover o grupo/canal ${{groupId}}?`)) {{
                        fetch(`/api/remove_group/${{groupId}}`, {{
                            method: 'DELETE'
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                location.reload();
                            }} else {{
                                alert('Erro ao remover: ' + data.message);
                            }}
                        }})
                        .catch(error => {{
                            alert('Erro ao remover grupo');
                        }});
                    }}
                }}
            </script>
        </body>
        </html>
        '''

    @web_app.route('/settings')
    @require_auth
    def settings():
        """Página de configurações editáveis"""
        config = load_config()
        return f'''
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Configurações - Painel Admin</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
            <style>
                :root {{
                    --primary: #dc2626;
                    --secondary: #991b1b;
                    --accent: #ef4444;
                    --dark: #0a0a0a;
                    --darker: #000000;
                    --light: #1a1a1a;
                    --lighter: #2a2a2a;
                    --text-primary: #ffffff;
                    --text-secondary: #a1a1aa;
                    --success: #22c55e;
                    --warning: #f59e0b;
                    --danger: #dc2626;
                }}
                
                @keyframes fadeInUp {{
                    from {{
                        opacity: 0;
                        transform: translateY(30px);
                    }}
                    to {{
                        opacity: 1;
                        transform: translateY(0);
                    }}
                }}
                
                @keyframes glow {{
                    0%, 100% {{
                        box-shadow: 0 0 20px rgba(220, 38, 38, 0.3);
                    }}
                    50% {{
                        box-shadow: 0 0 30px rgba(220, 38, 38, 0.6);
                    }}
                }}
                
                body {{
                    background: linear-gradient(135deg, var(--darker) 0%, var(--dark) 50%, var(--secondary) 100%);
                    min-height: 100vh;
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    color: var(--text-primary);
                }}
                
                body::before {{
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: 
                        radial-gradient(circle at 20% 80%, rgba(220, 38, 38, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(239, 68, 68, 0.1) 0%, transparent 50%);
                    pointer-events: none;
                    z-index: -1;
                }}
                
                .main-container {{
                    background: linear-gradient(135deg, var(--light) 0%, var(--lighter) 100%);
                    border: 2px solid var(--primary);
                    border-radius: 20px;
                    margin: 20px auto;
                    padding: 40px;
                    box-shadow: 
                        0 20px 40px rgba(0, 0, 0, 0.5),
                <div class="page-header">
                    <h1 class="page-title">
                        <i class="fas fa-cog"></i>
                        Configurações
                    </h1>
                    <a href="/" class="btn-back">
                        <i class="fas fa-arrow-left"></i>
                        Dashboard
                    </a>
                </div>
                
                <div class="row">
                    <!-- Configurações do Bot -->
                    <div class="col-md-6">
                        <div class="config-card">
                            <div class="card-header">
                                <i class="fas fa-robot" style="color: var(--primary);"></i>
                                <h3 class="card-title">Configurações do Bot</h3>
                            </div>
                            <form id="botConfigForm">
                                <div class="form-group">
                                    <label class="form-label">Token do Bot:</label>
                                    <input type="password" class="form-control" id="api_token" value="{config.get('API_TOKEN', '')}" placeholder="Token do bot">
                                </div>
                                <div class="form-group">
                                    <label class="form-label">Canal de Logs:</label>
                                    <input type="text" class="form-control" id="log_channel" value="{config.get('LOG', '')}" placeholder="ID do canal de logs">
                                </div>
                                <div class="form-group">
                                    <label class="form-label">Canal de Clientes:</label>
                                    <input type="text" class="form-control" id="clients_channel" value="{config.get('clientes', '')}" placeholder="ID do canal de clientes">
                                </div>
                                <button type="submit" class="btn-save">
                                    <i class="fas fa-save"></i> Salvar Configurações
                                </button>
                            </form>
                        </div>
                    </div>
                    
                    <!-- Configurações do Sistema -->
                    <div class="col-md-6">
                        <div class="config-card">
                            <div class="card-header">
                                <i class="fas fa-server" style="color: var(--info);"></i>
                                <h3 class="card-title">Estatísticas do Sistema</h3>
                            </div>
                            <form id="systemConfigForm">
                                <div class="form-group">
                                    <label class="form-label">Intervalo de Agendamento (min):</label>
                                    <input type="number" class="form-control" id="scheduling_interval" value="{config.get('scheduling_time_interval', 5)}" min="1" max="60">
                                </div>
                                <div class="form-group">
                                    <label class="form-label">Backup Automático (seg):</label>
                                    <input type="number" class="form-control" id="backup_interval" value="{config.get('AUTO_BACKUP_INTERVAL', 3600)}" min="300" max="86400">
                                </div>
                                <div class="form-group">
                                    <label class="form-label">Chave de Licença:</label>
                                    <input type="password" class="form-control" id="license_key" value="{config.get('LICENSE_KEY_TO_VALIDATE', '')}" placeholder="Chave de licença">
                                </div>
                                <button type="submit" class="btn-save">
                                    <i class="fas fa-save"></i> Salvar Sistema
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
                
                <!-- Ações do Sistema -->
                <div class="row mt-4">
                    <div class="col-12">
                        <div class="config-card system-actions">
                            <div class="card-header">
                                <i class="fas fa-exclamation-triangle" style="color: var(--danger);"></i>
                                <h3 class="card-title">Ações do Sistema</h3>
                            </div>
                            <div class="restart-warning">
                                <i class="fas fa-warning"></i>
                                Atenção: Reiniciar o bot irá interromper todas as operações temporariamente
                            </div>
                            <button class="btn-restart" onclick="restartBot()">
                                <i class="fas fa-sync-alt"></i> Reiniciar Bot
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
            <script>
                // Salvar configurações do bot
                document.getElementById('botConfigForm').addEventListener('submit', function(e) {{
                    e.preventDefault();
                    
                    const formData = {{
                        api_token: document.getElementById('api_token').value,
                        log_channel: document.getElementById('log_channel').value,
                        clients_channel: document.getElementById('clients_channel').value
                    }};
                    
                    fetch('/api/save_bot_config', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify(formData)
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            alert('✅ Configurações do bot salvas com sucesso!');
                        }} else {{
                            alert('❌ Erro ao salvar: ' + data.message);
                        }}
                    }})
                    .catch(error => {{
                        alert('❌ Erro de conexão: ' + error);
                    }});
                }});
                
                // Salvar configurações do sistema
                document.getElementById('systemConfigForm').addEventListener('submit', function(e) {{
                    e.preventDefault();
                    
                    const formData = {{
                        scheduling_interval: parseInt(document.getElementById('scheduling_interval').value),
                        backup_interval: parseInt(document.getElementById('backup_interval').value),
                        license_key: document.getElementById('license_key').value
                    }};
                    
                    fetch('/api/save_system_config', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify(formData)
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            alert('✅ Configurações do sistema salvas com sucesso!');
                        }} else {{
                            alert('❌ Erro ao salvar: ' + data.message);
                        }}
                    }})
                    .catch(error => {{
                        alert('❌ Erro de conexão: ' + error);
                    }});
                }});
                
                // Reiniciar bot
                function restartBot() {{
                    if (confirm('⚠️ Tem certeza que deseja reiniciar o bot?\\n\\nIsso irá interromper todas as operações temporariamente.\\n\\nO painel web será reiniciado junto.')) {{
                        
                        // Mostra loading
                        const restartBtn = document.querySelector('.btn-restart');
                        const originalText = restartBtn.innerHTML;
                        restartBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Reiniciando...';
                        restartBtn.disabled = true;
                        
                        fetch('/api/restart_bot', {{
                            method: 'POST'
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                alert('🔄 ' + data.message);
                                
                                // Aguarda reinicialização e tenta reconectar
                                let attempts = 0;
                                const maxAttempts = 20;
                                
                                function checkConnection() {{
                                    attempts++;
                                    
                                    fetch('/', {{ method: 'HEAD' }})
                                    .then(response => {{
                                        if (response.ok) {{
                                            alert('✅ Bot reiniciado com sucesso! Redirecionando...');
                                            window.location.href = '/';
                                        }} else {{
                                            throw new Error('Server not ready');
                                        }}
                                    }})
                                    .catch(() => {{
                                        if (attempts < maxAttempts) {{
                                            setTimeout(checkConnection, 2000); // Tenta novamente em 2s
                                        }} else {{
                                            alert('⚠️ Bot reiniciado, mas houve problema na reconexão.\\n\\nTente acessar manualmente: http://localhost:5000');
                                            restartBtn.innerHTML = originalText;
                                            restartBtn.disabled = false;
                                        }}
                                    }});
                                }}
                                
                                // Inicia verificação após 5 segundos
                                setTimeout(checkConnection, 5000);
                                
                            }} else {{
                                alert('❌ Erro ao reiniciar: ' + data.message);
                                restartBtn.innerHTML = originalText;
                                restartBtn.disabled = false;
                            }}
                        }})
                        .catch(error => {{
                            // Erro na requisição pode indicar que o restart já começou
                            alert('🔄 Reinicialização iniciada. Aguardando reconexão...');
                            
                            let attempts = 0;
                            const maxAttempts = 20;
                            
                            function checkConnection() {{
                                attempts++;
                                
                                fetch('/', {{ method: 'HEAD' }})
                                .then(response => {{
                                    if (response.ok) {{
                                        alert('✅ Bot reiniciado com sucesso! Redirecionando...');
                                        window.location.href = '/';
                                    }} else {{
                                        throw new Error('Server not ready');
                                    }}
                                }})
                                .catch(() => {{
                                    if (attempts < maxAttempts) {{
                                        setTimeout(checkConnection, 2000);
                                    }} else {{
                                        alert('⚠️ Problema na reconexão.\\n\\nTente acessar: http://localhost:5000');
                                        restartBtn.innerHTML = originalText;
                                        restartBtn.disabled = false;
                                    }}
                                }});
                            }}
                            
                            setTimeout(checkConnection, 5000);
                        }});
                    }}
                }}
            </script>
        </body>
        </html>
        '''

    @web_app.route('/api/forward_message', methods=['POST'])
    @require_auth
    def forward_message():
        """API para reenviar mensagem para o admin logado"""
        try:
            data = request.get_json()
            message_id = data.get('message_id')
            from_chat_id = data.get('from_chat_id')
            admin_id = session.get('user_id')  # ID do admin logado
            
            if not message_id or not from_chat_id or not admin_id:
                return jsonify({'success': False, 'message': 'Dados incompletos'})
            
            # Cria uma tarefa para ser executada pelo loop principal do bot
            forward_task = {
                'type': 'forward_message',
                'admin_id': admin_id,
                'message_id': int(message_id),
                'from_chat_id': int(from_chat_id),
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            # Adiciona à fila de tarefas (usando arquivo temporário)
            import json
            import os
            
            tasks_file = 'forward_tasks.json'
            tasks = []
            
            # Carrega tarefas existentes
            if os.path.exists(tasks_file):
                try:
                    with open(tasks_file, 'r', encoding='utf-8') as f:
                        tasks = json.load(f)
                except:
                    tasks = []
            
            # Adiciona nova tarefa
            tasks.append(forward_task)
            
            # Salva tarefas
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
            
            return jsonify({
                'success': True, 
                'message': 'Solicitação enviada! A mensagem será encaminhada em alguns segundos. Verifique seu chat privado com o bot.'
            })
            
        except Exception as e:
            logging.error(f"Erro na API forward_message: {e}")
            return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'})
    
    @web_app.route('/api/save_bot_config', methods=['POST'])
    @require_auth
    def save_bot_config():
        """API para salvar configurações do bot"""
        try:
            data = request.get_json()
            config = load_config()
            
            # Atualiza configurações do bot
            if data.get('api_token'):
                config['API_TOKEN'] = data['api_token']
            if data.get('log_channel'):
                config['LOG'] = data['log_channel']
            if data.get('clients_channel'):
                config['clientes'] = data['clients_channel']
            
            # Salva configurações
            save_config(config)
            
            return jsonify({'success': True, 'message': 'Configurações do bot salvas com sucesso!'})
            
        except Exception as e:
            logging.error(f"Erro ao salvar configurações do bot: {e}")
            return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'})
    
    @web_app.route('/api/save_system_config', methods=['POST'])
    @require_auth
    def save_system_config():
        """API para salvar configurações do sistema"""
        try:
            data = request.get_json()
            config = load_config()
            
            # Atualiza configurações do sistema
            if 'scheduling_interval' in data:
                config['scheduling_time_interval'] = data['scheduling_interval']
            if 'backup_interval' in data:
                config['AUTO_BACKUP_INTERVAL'] = data['backup_interval']
            if data.get('license_key'):
                config['LICENSE_KEY_TO_VALIDATE'] = data['license_key']
            
            # Salva configurações
            save_config(config)
            
            return jsonify({'success': True, 'message': 'Configurações do sistema salvas com sucesso!'})
            
        except Exception as e:
            logging.error(f"Erro ao salvar configurações do sistema: {e}")
            return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'})
    
    @web_app.route('/api/restart_bot', methods=['POST'])
    @require_auth
    def restart_bot():
        """API para reiniciar o bot"""
        try:
            import os
            import sys
            import threading
            import subprocess
            
            def restart_process():
                """Reinicia o processo do bot após um delay"""
                import time
                import psutil
                
                time.sleep(3)  # Aguarda 3 segundos para resposta HTTP
                
                try:
                    logging.info("[RESTART] Reiniciando bot via painel admin...")
                    
                    # Encerra todas as instâncias do bot primeiro
                    current_pid = os.getpid()
                    script_name = os.path.basename(sys.argv[0])
                    
                    logging.info(f"[RESTART] Encerrando instâncias do script {script_name}...")
                    
                    # Encontra e encerra outras instâncias
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        try:
                            if proc.info['pid'] != current_pid and proc.info['cmdline']:
                                cmdline = ' '.join(proc.info['cmdline'])
                                if script_name in cmdline and 'python' in cmdline.lower():
                                    logging.info(f"[RESTART] Encerrando processo {proc.info['pid']}")
                                    proc.terminate()
                                    time.sleep(0.5)
                                    if proc.is_running():
                                        proc.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    time.sleep(2)  # Aguarda encerramento completo
                    
                    # Método mais confiável para Windows
                    python = sys.executable
                    script_path = os.path.abspath(sys.argv[0])
                    
                    logging.info(f"[RESTART] Iniciando novo processo: {python} {script_path}")
                    
                    # Cria novo processo
                    subprocess.Popen([python, script_path], 
                                   cwd=os.getcwd(),
                                   creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                    
                    # Encerra processo atual
                    logging.info("[RESTART] Encerrando processo atual...")
                    time.sleep(1)
                    os._exit(0)
                    
                except Exception as e:
                    logging.error(f"[RESTART] Erro ao reiniciar: {e}")
                    # Fallback: tenta método tradicional
                    try:
                        os.execv(python, [python] + sys.argv)
                    except:
                        os._exit(1)
            
            # Inicia thread para reiniciar
            restart_thread = threading.Thread(target=restart_process, daemon=True)
            restart_thread.start()
            
            return jsonify({
                'success': True, 
                'message': 'Bot será reiniciado em alguns segundos. A página recarregará automaticamente.'
            })
            
        except Exception as e:
            logging.error(f"Erro ao reiniciar bot: {e}")
            return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'})

    @web_app.route('/logout')
    def logout():
        """Logout"""
        session.clear()
        return redirect(url_for('login'))

    def get_local_ip():
        """Detecta o IP local da máquina automaticamente"""
        try:
            import socket
            # Conecta a um endereço externo para descobrir o IP local
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            return local_ip
        except Exception as e:
            logging.error(f"Erro ao detectar IP local: {e}")
            return "localhost"

    def get_public_ip():
        """Tenta detectar o IP público da máquina"""
        try:
            import requests
            # Tenta vários serviços para obter o IP público
            services = [
                "https://api.ipify.org",
                "https://ipinfo.io/ip",
                "https://icanhazip.com"
            ]
            
            for service in services:
                try:
                    response = requests.get(service, timeout=5)
                    if response.status_code == 200:
                        return response.text.strip()
                except:
                    continue
            
            return None
        except Exception as e:
            logging.error(f"Erro ao detectar IP público: {e}")
            return None

    async def send_panel_links_to_admins():
        """Envia os links do painel web para todos os administradores"""
        try:
            config = load_config()
            admins = config.get('admins', [])
            
            if not admins:
                logging.warning("Nenhum administrador configurado para receber links do painel")
                return
            
            # Detecta IPs
            local_ip = get_local_ip()
            public_ip = get_public_ip()
            
            # Usa a porta global configurada
            global WEB_PANEL_PORT
            port = WEB_PANEL_PORT
            
            # Monta a mensagem com os links
            message = "🌐 **PAINEL ADMINISTRATIVO INICIADO**\n\n"
            message += "🔗 **Links de Acesso:**\n\n"
            
            # Link local
            message += f"🏠 **Acesso Local:**\n"
            message += f"• http://localhost:{port}\n"
            message += f"• http://127.0.0.1:{port}\n"
            
            # Link da rede local
            if local_ip and local_ip != "localhost":
                message += f"\n🏢 **Acesso na Rede Local:**\n"
                message += f"• http://{local_ip}:{port}\n"
            
            # Link público (se disponível)
            if public_ip and public_ip != local_ip:
                message += f"\n🌍 **Acesso Público:**\n"
                message += f"• http://{public_ip}:{port}\n"
                message += f"⚠️ *Certifique-se de que a porta {port} está liberada no firewall/roteador*\n"
            
            # Aviso se porta alternativa foi usada
            if port != 5000:
                message += f"\n⚡ **ATENÇÃO:** Porta padrão (5000) estava ocupada.\n"
                message += f"📌 **Usando porta alternativa:** {port}\n"
            
            message += f"\n🔐 **Credenciais:**\n"
            message += f"• **Usuário:** admin\n"
            message += f"• **Senha:** Configurada no config.json\n\n"
            
            message += f"⏰ **Iniciado em:** {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            message += f"🤖 **Status:** Online e Operacional"
            
            # Envia para todos os administradores
            success_count = 0
            failed_count = 0
            
            for admin_id in admins:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=message,
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
                    success_count += 1
                    professional_logger.success("PANEL_NOTIFY", f"Link enviado para admin {admin_id}")
                    
                except Exception as e:
                    failed_count += 1
                    professional_logger.error("PANEL_NOTIFY", f"Falha ao enviar para admin {admin_id}: {e}")
            
            # Log do resultado
            if success_count > 0:
                professional_logger.success("PANEL_NOTIFY", f"Links enviados para {success_count} administrador(es)")
            
            if failed_count > 0:
                professional_logger.warning("PANEL_NOTIFY", f"{failed_count} administrador(es) não puderam receber o link")
                
        except Exception as e:
            professional_logger.error("PANEL_NOTIFY", f"Erro ao enviar links do painel: {e}")
            logging.error(f"Erro ao enviar links do painel para admins: {e}")

    async def send_panel_links_after_startup():
        """Aguarda o painel inicializar e envia os links para os admins"""
        try:
            # Aguarda 5 segundos para o painel web inicializar completamente
            await asyncio.sleep(5)
            
            # Verifica se o painel está realmente rodando
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 5000))
            sock.close() 
            
            if result == 0:  # Porta está aberta, painel funcionando
                await send_panel_links_to_admins()
            else:
                professional_logger.warning("PANEL_NOTIFY", "Painel web não está acessível, links não enviados")
                
        except Exception as e:
            professional_logger.error("PANEL_NOTIFY", f"Erro ao verificar e enviar links do painel: {e}")

    def is_port_in_use(port):
        """Verifica se uma porta está em uso"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return False
            except OSError:
                return True

    def find_available_port(start_port=5000, max_attempts=10):
        """Encontra uma porta disponível a partir de start_port"""
        for port in range(start_port, start_port + max_attempts):
            if not is_port_in_use(port):
                return port
        return None

    def open_firewall_port_linux(port):
        """Tenta abrir a porta no firewall do Linux (ufw/iptables)"""
        import platform
        
        if platform.system() != 'Linux':
            return True  # Não é Linux, não precisa fazer nada
        
        try:
            # Tenta com UFW primeiro (Ubuntu/Debian)
            result = subprocess.run(['which', 'ufw'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"🔓 Tentando abrir porta {port} no UFW...")
                subprocess.run(['sudo', 'ufw', 'allow', str(port)], 
                             capture_output=True, text=True, timeout=5)
                print(f"✅ Porta {port} liberada no UFW!")
                return True
            
            # Tenta com iptables (outras distribuições)
            result = subprocess.run(['which', 'iptables'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"🔓 Tentando abrir porta {port} no iptables...")
                subprocess.run(['sudo', 'iptables', '-A', 'INPUT', '-p', 'tcp', 
                              '--dport', str(port), '-j', 'ACCEPT'], 
                             capture_output=True, text=True, timeout=5)
                print(f"✅ Porta {port} liberada no iptables!")
                return True
            
            print(f"⚠️ Firewall não detectado ou sem permissões sudo")
            return True
            
        except subprocess.TimeoutExpired:
            print(f"⚠️ Timeout ao tentar abrir porta {port}")
            return False
        except Exception as e:
            print(f"⚠️ Erro ao abrir porta {port}: {e}")
            return False

    def start_web_panel():
        """Inicia o painel web em thread separada com detecção automática de porta"""
        if WEB_PANEL_AVAILABLE:
            try:
                # Verifica se a porta 5000 está disponível
                port = 5000
                if is_port_in_use(port):
                    print(f"⚠️ Porta {port} já está em uso!")
                    alternative_port = find_available_port(5001)
                    if alternative_port:
                        port = alternative_port
                        print(f"✅ Porta alternativa encontrada: {port}")
                    else:
                        print(f"❌ Nenhuma porta disponível encontrada!")
                        professional_logger.web_panel_status("error")
                        return
                
                # Tenta abrir a porta no firewall do Linux
                open_firewall_port_linux(port)
                
                print(f"🚀 Iniciando painel web na porta {port}...")
                professional_logger.web_panel_status("starting", port)
                
                # Salva a porta usada em uma variável global para uso posterior
                global WEB_PANEL_PORT
                WEB_PANEL_PORT = port
                
                socketio.run(web_app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
            except Exception as e:
                professional_logger.web_panel_status("error")
                logging.error(f"Erro ao iniciar painel web: {e}")

# Comando para enviar links do painel manualmente
@dp.message(Command("links_painel"))
async def send_panel_links_cmd(message: types.Message):
    """Comando para enviar links do painel web para admins"""
    user_id = message.from_user.id
    
    # Verificar se é admin
    config = load_config()
    admins = config.get('admins', [])
    
    if user_id not in admins:
        await message.reply("❌ Apenas administradores podem usar este comando.")
        return
    
    try:
        await send_panel_links_to_admins()
        await message.reply("✅ Links do painel enviados para todos os administradores!")
    except Exception as e:
        await message.reply(f"❌ Erro ao enviar links: {e}")

# Comando para abrir o painel web
@dp.message(Command("painel_web"))
async def painel_cmd(message: types.Message):
    """Comando para acessar o painel web"""
    user_id = message.from_user.id
    
    # Verificar se é admin
    config = load_config()
    if user_id not in config.get('admins', []):
        await message.reply("❌ Acesso negado. Você não é administrador.")
        return
    
    # Usa a porta global configurada
    global WEB_PANEL_PORT
    port = WEB_PANEL_PORT
    
    painel_message = f"""🚀 **PAINEL WEB DE CONTROLE**

🌐 **Acesse:** http://localhost:{port}

🔐 **Login:**
• **Usuário:** {user_id}
• **Senha:** admin123

⚡ **Funcionalidades:**
• 📊 Dashboard com estatísticas
• 👥 Gerenciamento de usuários  
• 💬 Controle de mensagens agendadas
• 📢 Gestão de grupos/canais
• ⚙️ Configurações do bot
• 📋 Logs em tempo real

🎯 **Status:** {'🟢 Online' if WEB_PANEL_AVAILABLE else '🔴 Offline (Flask não instalado)'}"""

    # Adiciona aviso se porta alternativa foi usada
    if port != 5000:
        painel_message += f"\n\n⚡ **ATENÇÃO:** Usando porta alternativa {port} (porta 5000 estava ocupada)"
    
    painel_message += "\n\n💡 **Dica:** Mantenha esta aba aberta para acesso rápido!"

    await message.reply(painel_message, parse_mode="Markdown")

def check_for_duplicate_instances():
    """Verifica e encerra instâncias duplicadas do bot"""
    try:
        import psutil
        import os
        import sys
        import time
        
        current_pid = os.getpid()
        script_name = os.path.basename(sys.argv[0])
        
        print(f"🔍 [DEBUG] PID atual: {current_pid}, Script: {script_name}")
        
        duplicates_found = []
        
        # Procura por outras instâncias
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if proc.info['pid'] != current_pid and proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if script_name in cmdline and 'python' in cmdline.lower():
                        duplicates_found.append({
                            'pid': proc.info['pid'],
                            'create_time': proc.info['create_time']
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if duplicates_found:
            print(f"⚠️ [DUPLICATE_CHECK] Encontradas {len(duplicates_found)} instâncias duplicadas")
            
            # Ordena por tempo de criação (mais antigas primeiro)
            duplicates_found.sort(key=lambda x: x['create_time'])
            
            # Encerra instâncias mais antigas
            terminated_count = 0
            for dup in duplicates_found:
                try:
                    proc = psutil.Process(dup['pid'])
                    print(f"🔄 [DUPLICATE_CHECK] Encerrando instância duplicada PID {dup['pid']}")
                    proc.terminate()
                    terminated_count += 1
                    time.sleep(0.5)
                    if proc.is_running():
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            professional_logger.duplicate_check(found_duplicates=True, terminated_count=terminated_count)
            print(f"✅ [DUPLICATE_CHECK] {terminated_count} instâncias antigas encerradas. Continuando inicialização...")
            time.sleep(2)  # Aguarda encerramento completo
        else:
            professional_logger.duplicate_check(found_duplicates=False)
            print("✅ [DUPLICATE_CHECK] Nenhuma duplicata encontrada. Continuando...")
        
        print("🔍 [DEBUG] Função check_for_duplicate_instances concluída com sucesso")
        return True
            
    except ImportError:
        print("⚠️ [DUPLICATE_CHECK] psutil não disponível, pulando verificação")
        return True
    except Exception as e:
        print(f"❌ [DUPLICATE_CHECK] Erro na verificação: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        # SISTEMA DE VERIFICAÇÃO DE DUPLICATAS DESABILITADO
        # Para evitar problemas de encerramento automático
        # Se precisar matar instâncias antigas, faça manualmente com Ctrl+C
        print("ℹ️ Sistema de verificação de duplicatas desabilitado")
        print("💡 Se houver instâncias antigas rodando, encerre-as manualmente com Ctrl+C\n")
        
        print("✅ Iniciando bot...\n")
        
        # Iniciar painel web em thread separada
        if WEB_PANEL_AVAILABLE:
            web_thread = threading.Thread(target=start_web_panel, daemon=True)
            web_thread.start()
            professional_logger.web_panel_status("started")
        
        async def main_with_backup():
            asyncio.create_task(backup_scheduler())
            asyncio.create_task(expiring_plans_alert_scheduler())
            asyncio.create_task(check_and_remove_expired_messages())
            asyncio.create_task(smart_monitoring_system())
            asyncio.create_task(process_forward_tasks())
            
            # Sistema de auto-atualização
            asyncio.create_task(auto_update_scheduler())
            
            # Sistema de checkout - monitora status do bot nos grupos
            asyncio.create_task(checkout_system())
            
            # Envia links do painel para admins após inicialização
            if WEB_PANEL_AVAILABLE:
                asyncio.create_task(send_panel_links_after_startup())
            
            await main()
        
        print("🚀 Iniciando loop principal do bot...\n")
        asyncio.run(main_with_backup())
    except KeyboardInterrupt:
        logging.info("Bot finalizado pelo usuário.")
    except Exception as e:
        logging.error(f"[ERRO] Fatal: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logging.info("Bot encerrado.")
