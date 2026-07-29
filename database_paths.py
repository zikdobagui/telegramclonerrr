#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Paths - Caminhos dos arquivos de dados
Centraliza todos os caminhos de arquivos usados pelo bot
"""

import os

# ============================================================================
# DIRETÓRIOS
# ============================================================================

# Diretório de dados
DATA_DIR = "data"

# Cria diretório se não existir
os.makedirs(DATA_DIR, exist_ok=True)

# ============================================================================
# ARQUIVOS DE CONFIGURAÇÃO
# ============================================================================

CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# ============================================================================
# ARQUIVOS DE DADOS DE USUÁRIOS
# ============================================================================

# Usuários registrados
REGISTERED_USERS_FILE = os.path.join(DATA_DIR, "registered_users.json")
USER_IDS_FILE = os.path.join(DATA_DIR, "user_ids.json")

# ============================================================================
# ARQUIVOS DE GRUPOS E CHATS
# ============================================================================

# IDs de chats/grupos
CHAT_IDS_FILE = os.path.join(DATA_DIR, "chat_ids.json")
FAILED_CHAT_IDS_FILE = os.path.join(DATA_DIR, "failed_chat_ids.json")

# ============================================================================
# ARQUIVOS DE MENSAGENS AGENDADAS
# ============================================================================

# Mensagens agendadas (planos ativos)
SCHEDULED_MESSAGES_FILE = os.path.join(DATA_DIR, "scheduled_messages.json")

# Planos expirados (arquivo)
EXPIRED_PLANS_FILE = os.path.join(DATA_DIR, "expired_plans.json")

# ============================================================================
# ARQUIVOS DE MEMBROS
# ============================================================================

# Membros adicionados
ADDED_BY_FILE = os.path.join(DATA_DIR, "added_by.json")

# ============================================================================
# ARQUIVOS DE LOGS
# ============================================================================

# Log do sistema
SYSTEM_LOG_FILE = os.path.join(DATA_DIR, "system.log")

# ============================================================================
# INICIALIZAÇÃO DOS ARQUIVOS
# ============================================================================

def initialize_files():
    """Cria arquivos vazios se não existirem"""
    
    # Arquivos que devem ser listas vazias
    list_files = [
        CHAT_IDS_FILE,
        FAILED_CHAT_IDS_FILE,
        SCHEDULED_MESSAGES_FILE,
        EXPIRED_PLANS_FILE,
    ]
    
    # Arquivos que devem ser dicionários vazios
    dict_files = [
        REGISTERED_USERS_FILE,
        USER_IDS_FILE,
        ADDED_BY_FILE,
    ]
    
    # Arquivo de configuração padrão
    default_config = {
        "admins": [],
        "bot_token": "",
        "api_id": "",
        "api_hash": "",
        "reference_channel": "",
        "log_channel": ""
    }
    
    import json
    
    # Cria arquivos de lista
    for file_path in list_files:
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    # Cria arquivos de dicionário
    for file_path in dict_files:
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    # Cria arquivo de configuração
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
    
    # Cria arquivo de log
    if not os.path.exists(SYSTEM_LOG_FILE):
        with open(SYSTEM_LOG_FILE, 'w', encoding='utf-8') as f:
            f.write("# System Log\n")

# Inicializa arquivos automaticamente ao importar
initialize_files()

# ============================================================================
# INFORMAÇÕES
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("📁 DATABASE PATHS - Caminhos dos Arquivos")
    print("=" * 60)
    print(f"\n📂 Diretório de dados: {DATA_DIR}")
    print(f"\n📋 Arquivos de configuração:")
    print(f"   • {CONFIG_FILE}")
    print(f"\n👥 Arquivos de usuários:")
    print(f"   • {REGISTERED_USERS_FILE}")
    print(f"   • {USER_IDS_FILE}")
    print(f"\n💬 Arquivos de grupos:")
    print(f"   • {CHAT_IDS_FILE}")
    print(f"   • {FAILED_CHAT_IDS_FILE}")
    print(f"\n📅 Arquivos de mensagens:")
    print(f"   • {SCHEDULED_MESSAGES_FILE}")
    print(f"   • {EXPIRED_PLANS_FILE}")
    print(f"\n📊 Arquivos de membros:")
    print(f"   • {ADDED_BY_FILE}")
    print(f"\n📝 Arquivos de logs:")
    print(f"   • {SYSTEM_LOG_FILE}")
    print("\n" + "=" * 60)
    print("✅ Todos os arquivos foram inicializados!")
    print("=" * 60)
