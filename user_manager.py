"""
Sistema de Gerenciamento de Usuários
Cada usuário tem suas próprias sessões, configurações e dados
"""

import os
import json
import hashlib
from datetime import datetime
from config import DATA_DIR
from data_store import atomic_write_json, load_json_file

class UserManager:
    def __init__(self):
        self.legacy_users_dir = "users"
        self.users_dir = os.environ.get("USERS_DIR", os.path.join(DATA_DIR, "users"))
        self.users_file = os.path.join(self.users_dir, "users.json")
        self.current_user = None
        self.init_users_system()
    
    def init_users_system(self):
        """Inicializa o sistema de usuários"""
        # Cria pasta de usuários
        os.makedirs(self.users_dir, exist_ok=True)

        legacy_users_file = os.path.join(self.legacy_users_dir, "users.json")
        if not os.path.exists(self.users_file) and os.path.exists(legacy_users_file):
            legacy_users = load_json_file(legacy_users_file, {'users': []})
            atomic_write_json(self.users_file, legacy_users)
        
        # Cria arquivo de usuários se não existir
        if not os.path.exists(self.users_file):
            default_users = {
                "users": [
                    {
                        "username": "admin",
                        "password": self.hash_password("admin123"),
                        "created_at": datetime.now().isoformat(),
                        "is_admin": True
                    }
                ]
            }
            atomic_write_json(self.users_file, default_users)
    
    def hash_password(self, password):
        """Cria hash da senha"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def load_users(self):
        """Carrega lista de usuários"""
        if os.path.exists(self.users_file):
            data = load_json_file(self.users_file, {'users': []})
            return data.get('users', [])
        return []
    
    def save_users(self, users):
        """Salva lista de usuários"""
        atomic_write_json(self.users_file, {'users': users})
    
    def authenticate(self, username, password):
        """Autentica usuário"""
        users = self.load_users()
        password_hash = self.hash_password(password)
        
        for user in users:
            if user['username'] == username and user['password'] == password_hash:
                self.current_user = username
                self.create_user_directories(username)
                return True
        return False
    
    def create_user(self, username, password, is_admin=False):
        """Cria novo usuário"""
        users = self.load_users()
        
        # Verifica se usuário já existe
        if any(u['username'] == username for u in users):
            return False, "Usuário já existe"
        
        # Adiciona novo usuário
        new_user = {
            "username": username,
            "password": self.hash_password(password),
            "created_at": datetime.now().isoformat(),
            "is_admin": is_admin
        }
        users.append(new_user)
        self.save_users(users)
        
        # Cria diretórios do usuário
        self.create_user_directories(username)
        
        return True, "Usuário criado com sucesso"
    
    def delete_user(self, username):
        """Remove usuário"""
        if username == "admin":
            return False, "Não é possível remover o admin"
        
        users = self.load_users()
        users = [u for u in users if u['username'] != username]
        self.save_users(users)
        
        # Remove diretórios do usuário
        import shutil
        user_dir = self.get_user_directory(username)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
        
        return True, "Usuário removido"
    
    def change_password(self, username, old_password, new_password):
        """Altera senha do usuário"""
        users = self.load_users()
        old_hash = self.hash_password(old_password)
        
        for user in users:
            if user['username'] == username and user['password'] == old_hash:
                user['password'] = self.hash_password(new_password)
                self.save_users(users)
                return True, "Senha alterada"
        
        return False, "Senha atual incorreta"
    
    def create_user_directories(self, username):
        """Cria estrutura de diretórios para o usuário"""
        user_dir = self.get_user_directory(username)
        
        # Cria pastas
        os.makedirs(os.path.join(user_dir, "sessions"), exist_ok=True)
        os.makedirs(os.path.join(user_dir, "data"), exist_ok=True)
        os.makedirs(os.path.join(user_dir, "exports"), exist_ok=True)
        os.makedirs(os.path.join(user_dir, "logs"), exist_ok=True)
        
        # Cria arquivos de configuração padrão
        data_dir = os.path.join(user_dir, "data")
        
        # config.json
        config_file = os.path.join(data_dir, "config.json")
        if not os.path.exists(config_file):
            default_config = {
                'api_credentials': [],
                'sessions': [],
                'current_api_index': 0
            }
            atomic_write_json(config_file, default_config)
        
        # members.json
        members_file = os.path.join(data_dir, "members.json")
        if not os.path.exists(members_file):
            atomic_write_json(members_file, [])
        
        # session_floods.json
        floods_file = os.path.join(data_dir, "session_floods.json")
        if not os.path.exists(floods_file):
            atomic_write_json(floods_file, {})
        
        # automation_config.json
        automation_file = os.path.join(data_dir, "automation_config.json")
        if not os.path.exists(automation_file):
            default_automation = {
                'groups': [],
                'daily_limits': {},
                'warming_enabled': False,
                'warming_interval': 10
            }
            atomic_write_json(automation_file, default_automation)
        
        # warming_groups.json
        warming_file = os.path.join(data_dir, "warming_groups.json")
        if not os.path.exists(warming_file):
            atomic_write_json(warming_file, [])
    
    def get_user_directory(self, username=None):
        """Retorna diretório do usuário"""
        if username is None:
            username = self.current_user
        return os.path.join(self.users_dir, username)
    
    def get_user_sessions_dir(self, username=None):
        """Retorna diretório de sessões do usuário"""
        return os.path.join(self.get_user_directory(username), "sessions")
    
    def get_user_data_dir(self, username=None):
        """Retorna diretório de dados do usuário"""
        return os.path.join(self.get_user_directory(username), "data")
    
    def get_user_exports_dir(self, username=None):
        """Retorna diretório de exports do usuário"""
        return os.path.join(self.get_user_directory(username), "exports")
    
    def get_user_logs_dir(self, username=None):
        """Retorna diretório de logs do usuário"""
        return os.path.join(self.get_user_directory(username), "logs")
    
    def is_admin(self, username=None):
        """Verifica se usuário é admin"""
        if username is None:
            username = self.current_user
        
        users = self.load_users()
        for user in users:
            if user['username'] == username:
                return user.get('is_admin', False)
        return False
    
    def list_users(self):
        """Lista todos os usuários (apenas para admin)"""
        users = self.load_users()
        return [
            {
                'username': u['username'],
                'created_at': u.get('created_at', 'N/A'),
                'is_admin': u.get('is_admin', False)
            }
            for u in users
        ]
    
    def logout(self):
        """Faz logout do usuário atual"""
        self.current_user = None
