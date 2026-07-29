"""
Sistema de Criação de Sessões via Telefone e Código
"""

import asyncio
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
from logger import log_info, log_error, log_warning

class SessionCreator:
    def __init__(self, api_id, api_hash, phone, sessions_dir):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.sessions_dir = sessions_dir
        self.client = None
        self.phone_code_hash = None
        self.loop = asyncio.new_event_loop()  # Cria loop dedicado
        self.thread = None
        
    def run_in_loop(self, coro):
        """Executa uma coroutine no loop dedicado desta sessão"""
        if not self.loop.is_running():
            # Inicia o loop em uma thread se ainda não está rodando
            import threading
            def run_loop():
                asyncio.set_event_loop(self.loop)
                self.loop.run_forever()
            
            self.thread = threading.Thread(target=run_loop, daemon=True)
            self.thread.start()
        
        # Agenda a coroutine no loop
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=30)
    
    async def send_code(self):
        """Envia código de verificação para o telefone"""
        try:
            # Cria nome da sessão
            session_name = self.phone.replace('+', '').replace(' ', '').replace('-', '')
            session_path = os.path.join(self.sessions_dir, session_name)
            
            # Cria cliente
            self.client = TelegramClient(session_path, self.api_id, self.api_hash)
            await self.client.connect()
            
            # Envia código
            result = await self.client.send_code_request(self.phone)
            self.phone_code_hash = result.phone_code_hash
            
            log_info(f"✅ Código enviado para {self.phone}")
            return True, "Código enviado com sucesso!"
            
        except PhoneNumberInvalidError:
            log_error(f"Número de telefone inválido: {self.phone}")
            return False, "Número de telefone inválido"
        except Exception as e:
            log_error(f"Erro ao enviar código: {e}")
            return False, str(e)
    
    async def verify_code(self, code):
        """Verifica o código e cria a sessão"""
        try:
            if not self.client:
                return False, "Cliente não conectado. Envie o código primeiro."
            
            if not self.phone_code_hash:
                return False, "Código não foi enviado. Envie o código primeiro."
            
            # Tenta fazer login com o código
            try:
                await self.client.sign_in(self.phone, code, phone_code_hash=self.phone_code_hash)
                
                # Garante que está conectado antes de pegar info
                if not self.client.is_connected():
                    await self.client.connect()
                
                # Sucesso! Pega informações do usuário
                me = await self.client.get_me()
                log_info(f"✅ Login bem-sucedido: {me.first_name} ({self.phone})")
                
                # Prepara dados do usuário
                user_data = {
                    'phone': self.phone,
                    'name': f"{me.first_name or ''} {me.last_name or ''}".strip(),
                    'username': me.username or '',
                    'user_id': me.id
                }
                
                # Desconecta
                await self.client.disconnect()
                
                return True, user_data
                
            except SessionPasswordNeededError:
                # Conta tem verificação em 2 fatores - NÃO desconecta
                log_warning(f"Conta {self.phone} tem senha 2FA")
                return False, "2FA_REQUIRED"
                
            except PhoneCodeInvalidError:
                log_error(f"Código inválido para {self.phone}")
                return False, "Código inválido"
                
        except Exception as e:
            log_error(f"Erro ao verificar código: {e}")
            return False, str(e)
    
    async def verify_password(self, password):
        """Verifica senha 2FA"""
        try:
            if not self.client:
                return False, "Sessão não iniciada"
            
            await self.client.sign_in(password=password)
            
            # Garante que está conectado antes de pegar info
            if not self.client.is_connected():
                await self.client.connect()
            
            # Sucesso! Pega informações do usuário
            me = await self.client.get_me()
            log_info(f"✅ Login 2FA bem-sucedido: {me.first_name} ({self.phone})")
            
            # Prepara dados do usuário
            user_data = {
                'phone': self.phone,
                'name': f"{me.first_name or ''} {me.last_name or ''}".strip(),
                'username': me.username or '',
                'user_id': me.id
            }
            
            await self.client.disconnect()
            
            return True, user_data
            
        except Exception as e:
            log_error(f"Erro ao verificar senha 2FA: {e}")
            return False, str(e)
    
    async def cancel(self):
        """Cancela o processo de criação"""
        try:
            if self.client:
                await self.client.disconnect()
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)
            return True
        except:
            return False


# Dicionário global para armazenar sessões em criação com seus loops
active_session_creators = {}

def get_session_creator(session_id):
    """Pega um SessionCreator"""
    return active_session_creators.get(session_id)

def set_session_creator(session_id, creator):
    """Armazena um SessionCreator"""
    active_session_creators[session_id] = creator

def remove_session_creator(session_id):
    """Remove um SessionCreator"""
    if session_id in active_session_creators:
        del active_session_creators[session_id]
