import asyncio
import random
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.sessions import SQLiteSession
from datetime import datetime
import os
import shutil
import tempfile
import traceback
from config import SESSIONS_DIR

# Classe ReadOnlySession para evitar erro de update_state
class ReadOnlySession(SQLiteSession):
    def set_update_state(self, entity_id, state):
        """Override para não salvar update state"""
        pass
    
    def save(self):
        """Override para não salvar mudanças"""
        pass

class WarmingBot:
    def __init__(self, api_id, api_hash):
        self.api_id = api_id
        self.api_hash = api_hash
        self.running = False
        self.log_file = 'warming_debug.log'
        
        # Mensagens aleatórias
        self.messages = [
            "Bom dia! ☀️",
            "Boa tarde! 🌤️",
            "Boa noite! 🌙",
            "Tudo bem? 😊",
            "Como estão? 👋",
            "Ótimo dia a todos! ✨",
            "Que dia maravilhoso! 🌟",
            "Feliz dia! 🎉",
            "Ótima semana! 💪",
            "Bora lá! 🚀",
            "E aí, pessoal? 😄",
            "Fala galera! 👊",
            "Salve! 🤙",
            "Beleza? 😎",
            "Tudo certo? ✌️",
            "Opa! 👀",
            "Show! 🎸",
            "Top! 🔝",
            "Massa! 😁",
            "Legal! 👍",
            "Valeu! 🙏",
            "Obrigado! 💙",
            "Tmj! 🤝",
            "Partiu! 🏃",
            "Vamos! 💨",
            "Sucesso! 🌈",
            "Força! 💯",
            "Foco! 🎯",
            "Gás! ⚡",
            "Energia! 🔋"
        ]
        
        # Stickers (IDs de exemplo - você pode adicionar mais)
        self.stickers = [
            "👍", "❤️", "🔥", "⭐", "✨", 
            "💯", "🎉", "🚀", "💪", "😊",
            "👏", "🙌", "✅", "💙", "🌟",
            "🎊", "🎈", "🌺", "🌸", "🌼"
        ]
    
    def log(self, message):
        """Escreve log em arquivo TXT"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}\n"
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message)
        except Exception as e:
            print(f"Erro ao escrever log: {e}")
        
        # Também imprime no console
        print(log_message.strip())
    
    async def ensure_in_group(self, session_info, group_link):
        """Garante que a sessão está no grupo"""
        self.log(f"=== ENSURE_IN_GROUP INICIADO ===")
        self.log(f"Sessao: {session_info.get('first_name', 'Unknown')} ({session_info.get('session_name', 'Unknown')})")
        self.log(f"Grupo: {group_link}")
        
        # Garante que o nome da sessão tem a extensão .session
        session_name = session_info['session_name']
        if not session_name.endswith('.session'):
            session_name += '.session'
        
        session_path = os.path.join(SESSIONS_DIR, session_name)
        self.log(f"Session path: {session_path}")
        self.log(f"Session file exists: {os.path.exists(session_path)}")
        
        # Cria cópia temporária da sessão para evitar database lock
        temp_dir = tempfile.gettempdir()
        temp_session = os.path.join(temp_dir, f"warming_{session_name}")
        self.log(f"Temp session path: {temp_session}")
        
        try:
            # Copia arquivos da sessão
            self.log("Copiando arquivos da sessao...")
            if os.path.exists(session_path):
                shutil.copy2(session_path, temp_session)
                self.log("Arquivo principal copiado")
            else:
                self.log(f"ERRO: Arquivo de sessao nao existe: {session_path}")
                return False, "Arquivo de sessão não encontrado"
                
            if os.path.exists(session_path + '-journal'):
                shutil.copy2(session_path + '-journal', temp_session + '-journal')
                self.log("Arquivo journal copiado")
        except Exception as e:
            self.log(f"ERRO ao copiar sessao: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            return False, f"Erro ao copiar sessão: {str(e)}"
        
        client = None
        try:
            self.log("Criando TelegramClient com ReadOnlySession...")
            # Usa ReadOnlySession para evitar erro de update_state
            session = ReadOnlySession(temp_session)
            client = TelegramClient(session, self.api_id, self.api_hash)
            
            self.log("Conectando...")
            await client.connect()
            self.log("Conectado!")
            
            self.log("Verificando autorizacao...")
            is_authorized = await client.is_user_authorized()
            self.log(f"Autorizado: {is_authorized}")
            
            if not is_authorized:
                await client.disconnect()
                self.log("Sessao nao autorizada - desconectando")
                return False, "Sessão não autorizada"
            
            # Pega o grupo
            self.log(f"Buscando entidade do grupo: {group_link}")
            try:
                group = await client.get_entity(group_link)
                self.log(f"Grupo encontrado: {group.title if hasattr(group, 'title') else 'Unknown'}")
                self.log(f"Grupo ID: {group.id}")
            except Exception as e:
                self.log(f"ERRO ao buscar grupo: {str(e)}")
                self.log(f"Traceback: {traceback.format_exc()}")
                await client.disconnect()
                return False, f"Grupo não encontrado: {str(e)}"
            
            # Verifica se está no grupo
            self.log("Verificando se esta no grupo...")
            try:
                perms = await client.get_permissions(group, 'me')
                self.log(f"Permissoes obtidas: {perms}")
                await client.disconnect()
                self.log("Ja esta no grupo - desconectando")
                return True, "Já está no grupo"
            except Exception as e:
                self.log(f"Nao esta no grupo (esperado): {str(e)}")
                # Não está no grupo, tenta entrar
                try:
                    self.log("Tentando entrar no grupo...")
                    
                    # Detecta se é link privado
                    clean_link = group.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '')
                    
                    if 'joinchat' in group or '+' in group:
                        # Grupo privado
                        from telethon.tl.functions.messages import ImportChatInviteRequest
                        invite_hash = clean_link.split('/')[-1].replace('+', '')
                        self.log(f"Entrando em grupo privado com hash: {invite_hash}")
                        await client(ImportChatInviteRequest(invite_hash))
                    else:
                        # Grupo público
                        await client(JoinChannelRequest(clean_link))
                    
                    self.log("Comando de entrada enviado")
                    await asyncio.sleep(2)
                    self.log("Aguardou 2 segundos")
                    await client.disconnect()
                    self.log("Entrou no grupo com sucesso!")
                    return True, "Entrou no grupo com sucesso"
                except Exception as e2:
                    self.log(f"ERRO ao entrar no grupo: {str(e2)}")
                    self.log(f"Traceback: {traceback.format_exc()}")
                    await client.disconnect()
                    return False, f"Erro ao entrar: {str(e2)}"
            
        except Exception as e:
            self.log(f"ERRO GERAL: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            try:
                if client:
                    await client.disconnect()
                    self.log("Cliente desconectado apos erro")
            except:
                pass
            return False, f"Erro: {str(e)}"
        finally:
            # Remove arquivos temporários
            self.log("Limpando arquivos temporarios...")
            try:
                if os.path.exists(temp_session):
                    os.remove(temp_session)
                    self.log("Temp session removido")
                if os.path.exists(temp_session + '-journal'):
                    os.remove(temp_session + '-journal')
                    self.log("Temp journal removido")
            except Exception as e:
                self.log(f"Erro ao remover temporarios: {str(e)}")
            
            self.log(f"=== ENSURE_IN_GROUP FINALIZADO ===\n")
    
    async def send_warming_message(self, session_info, group_link):
        """Envia mensagem de aquecimento"""
        self.log(f"=== SEND_WARMING_MESSAGE INICIADO ===")
        self.log(f"Sessao: {session_info.get('first_name', 'Unknown')} ({session_info.get('session_name', 'Unknown')})")
        self.log(f"Grupo: {group_link}")
        
        # Garante que o nome da sessão tem a extensão .session
        session_name = session_info['session_name']
        if not session_name.endswith('.session'):
            session_name += '.session'
        
        session_path = os.path.join(SESSIONS_DIR, session_name)
        self.log(f"Session path completo: {session_path}")
        self.log(f"Arquivo existe: {os.path.exists(session_path)}")
        
        # Cria cópia temporária da sessão para evitar database lock
        # IMPORTANTE: Adiciona o número aleatório ANTES da extensão .session
        temp_dir = tempfile.gettempdir()
        random_id = random.randint(1000, 9999)
        session_name_without_ext = session_name.replace('.session', '')
        temp_session = os.path.join(temp_dir, f"warming_{session_name_without_ext}_{random_id}.session")
        self.log(f"Temp session: {temp_session}")
        
        try:
            # Copia arquivos da sessão
            self.log("Copiando arquivos...")
            if os.path.exists(session_path):
                shutil.copy2(session_path, temp_session)
                self.log("Arquivo principal copiado")
            else:
                self.log(f"ERRO: Arquivo nao existe: {session_path}")
                return False
                
            if os.path.exists(session_path + '-journal'):
                shutil.copy2(session_path + '-journal', temp_session + '-journal')
                self.log("Arquivo journal copiado")
        except Exception as e:
            self.log(f"ERRO ao copiar: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            return False
        
        client = None
        try:
            self.log("Criando cliente com ReadOnlySession...")
            # Usa ReadOnlySession para evitar erro de update_state
            session = ReadOnlySession(temp_session)
            client = TelegramClient(session, self.api_id, self.api_hash)
            
            self.log("Conectando...")
            await client.connect()
            self.log("Conectado!")
            
            self.log("Verificando autorizacao...")
            if not await client.is_user_authorized():
                self.log("Nao autorizado - abortando")
                await client.disconnect()
                return False
            self.log("Autorizado!")
            
            # Pega o grupo
            self.log(f"Buscando grupo: {group_link}")
            try:
                group = await client.get_entity(group_link)
                self.log(f"Grupo encontrado: {group.title if hasattr(group, 'title') else 'Unknown'}")
            except Exception as e:
                self.log(f"ERRO ao buscar grupo: {str(e)}")
                self.log(f"Traceback: {traceback.format_exc()}")
                await client.disconnect()
                return False
            
            # Verifica se está no grupo
            self.log("Verificando participacao no grupo...")
            try:
                perms = await client.get_permissions(group, 'me')
                self.log(f"Esta no grupo! Permissoes: {perms}")
            except Exception as e:
                self.log(f"Nao esta no grupo: {str(e)}")
                # Não está no grupo, tenta entrar
                try:
                    self.log("Tentando entrar...")
                    
                    # Detecta se é link privado
                    clean_link = group_link.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '')
                    
                    if 'joinchat' in group_link or '+' in group_link:
                        # Grupo privado
                        from telethon.tl.functions.messages import ImportChatInviteRequest
                        invite_hash = clean_link.split('/')[-1].replace('+', '')
                        self.log(f"Entrando em grupo privado com hash: {invite_hash}")
                        await client(ImportChatInviteRequest(invite_hash))
                    else:
                        # Grupo público
                        await client(JoinChannelRequest(clean_link))
                    await asyncio.sleep(2)
                    self.log("Entrou no grupo!")
                except Exception as e2:
                    self.log(f"ERRO ao entrar: {str(e2)}")
                    self.log(f"Traceback: {traceback.format_exc()}")
                    await client.disconnect()
                    return False
            
            # Escolhe mensagem
            use_text = random.choice([True, False])
            if use_text:
                message = random.choice(self.messages)
                self.log(f"Enviando mensagem de texto: {message}")
            else:
                message = random.choice(self.stickers)
                self.log(f"Enviando emoji: {message}")
            
            # Envia mensagem
            self.log("Enviando mensagem...")
            await client.send_message(group, message)
            self.log("Mensagem enviada com sucesso!")
            
            await client.disconnect()
            self.log("Desconectado!")
            return True
            
        except Exception as e:
            self.log(f"ERRO GERAL: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            try:
                if client:
                    await client.disconnect()
            except:
                pass
            return False
        finally:
            # Remove arquivos temporários
            self.log("Limpando temporarios...")
            try:
                if os.path.exists(temp_session):
                    os.remove(temp_session)
                if os.path.exists(temp_session + '-journal'):
                    os.remove(temp_session + '-journal')
                self.log("Temporarios removidos")
            except Exception as e:
                self.log(f"Erro ao limpar: {str(e)}")
            
            self.log(f"=== SEND_WARMING_MESSAGE FINALIZADO ===\n")
    
    async def start_warming(self, sessions, groups, interval_minutes=10):
        """Inicia aquecimento automático"""
        self.running = True
        
        while self.running:
            for session in sessions:
                if session.get('status') != 'active':
                    continue
                
                for group in groups:
                    try:
                        await self.send_warming_message(session, group['group_link'])
                        print(f"✅ Aquecimento: {session['first_name']} em {group['group_link']}")
                    except:
                        pass
                    
                    # Delay aleatório entre 5-15 minutos
                    delay = random.randint(5, 15) * 60
                    await asyncio.sleep(delay)
            
            # Aguarda intervalo configurado
            await asyncio.sleep(interval_minutes * 60)
    
    def stop_warming(self):
        """Para o aquecimento"""
        self.running = False
