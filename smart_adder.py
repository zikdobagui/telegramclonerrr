"""
Smart Adder - Sistema Inteligente de Adição com Aquecimento
Autor: Kiro AI
Data: 31/01/2026

Funcionalidades:
1. Sessão entra no grupo destino
2. Manda mensagens para se aquecer (parecer humano)
3. Adiciona membros (meta: 200/dia por grupo)
4. Durante delays, interage no grupo
5. Após concluir, SAI do grupo
"""

from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import SendMessageRequest
from telethon.errors import (
    PeerFloodError, UserPrivacyRestrictedError,
    UserNotMutualContactError, UserChannelsTooMuchError,
    FloodWaitError
)
import time
import json
import os
import asyncio
import shutil
import tempfile
import logging
import sys
import random
import re
from datetime import datetime, timedelta
from config import SESSIONS_DIR, MEMBERS_FILE
from logger import log_error, log_info, log_warning
from data_store import atomic_write_json, load_json_file

# Suprime warnings
logging.getLogger('telethon').setLevel(logging.ERROR)

# Carrega mensagens de aquecimento do arquivo JSON
def load_warming_messages():
    """Carrega mensagens naturais do arquivo JSON"""
    try:
        messages_file = os.path.join(os.path.dirname(__file__), 'warming_messages.json')
        with open(messages_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Combina todas as categorias de mensagens
        all_messages = []
        
        # Adiciona mensagens por horário
        hour = datetime.now().hour
        if 5 <= hour < 12:
            all_messages.extend(data['horarios']['manha'])
        elif 12 <= hour < 18:
            all_messages.extend(data['horarios']['tarde'])
        else:
            all_messages.extend(data['horarios']['noite'])
        
        # Adiciona outras categorias
        all_messages.extend(data['saudacoes'])
        all_messages.extend(data['perguntas_gerais'])
        all_messages.extend(data['comentarios_positivos'])
        all_messages.extend(data['conversas_casuais'])
        all_messages.extend(data['expressoes_brasileiras'])
        
        return all_messages, data
    except Exception as e:
        log_warning(f"Erro ao carregar mensagens personalizadas: {e}")
        # Fallback para mensagens padrão
        return [
            "Olá pessoal! 👋",
            "Boa tarde! Como estão?",
            "Alguém online? 😊",
            "Tudo bem com vocês?",
            "Oi gente! 🙂",
            "E aí, tudo certo?",
            "Olá! Alguém pode me ajudar?",
            "Boa noite! 🌙",
            "Bom dia! ☀️",
            "Opa, tudo bem?",
        ], None

WARMING_MESSAGES, WARMING_DATA = load_warming_messages()

def emit_log(message, log_type='info', socketio=None):
    """Helper para emitir logs"""
    if socketio:
        if socketio == 'task':
            from app import socketio as app_socketio
            app_socketio.emit('task_log', {'message': message, 'type': log_type})
        elif hasattr(socketio, 'emit'):
            socketio.emit('log', {'message': message, 'type': log_type})
    print(message)
    sys.stdout.flush()

class SmartAdder:
    def __init__(self, api_id, api_hash, data_dir=None, members_file=None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.data_dir = data_dir
        self.members_file = members_file or MEMBERS_FILE
        self.last_result = {'status': 'idle', 'reason': ''}

    def _set_last_result(self, status, reason):
        self.last_result = {'status': status, 'reason': reason}

    def get_last_result(self):
        return self.last_result or {'status': 'unknown', 'reason': 'Sem detalhe registrado'}

    def _is_disconnected_error(self, error):
        error_msg = str(error).lower()
        return (
            'cannot send requests while disconnected' in error_msg
            or 'disconnected' in error_msg and 'cannot send requests' in error_msg
        )

    def _record_member_result(self, task_data, member, session_info, status, observation):
        if not task_data:
            return
        entry = {
            'time': __import__('datetime').datetime.now().isoformat(timespec='seconds'),
            'member_id': member.get('id'),
            'member_name': member.get('first_name') or member.get('name') or member.get('username') or 'Usuário',
            'member_username': member.get('username') or '',
            'account': session_info.get('first_name') or session_info.get('phone') or session_info.get('session_name') or '',
            'account_username': session_info.get('username') or '',
            'phone': session_info.get('phone') or '',
            'session_name': session_info.get('session_name') or '',
            'status': status,
            'observation': observation
        }

        results = task_data.setdefault('member_results', [])
        results.append(entry)
        task_data['member_results'] = results[-1000:]

        automation_manager = task_data.get('automation_manager')
        task_id = task_data.get('task_id')
        if automation_manager and task_id:
            try:
                automation_manager.load_config()
                for group in automation_manager.config.get('groups', []):
                    if group.get('id') == task_id:
                        saved_results = group.setdefault('member_results', [])
                        saved_results.append(entry)
                        group['member_results'] = saved_results[-1000:]
                        stats_key = entry.get('session_name') or entry.get('phone') or entry.get('account') or 'desconhecida'
                        session_stats = group.setdefault('session_stats', {})
                        stat = session_stats.setdefault(stats_key, {
                            'added_count': 0,
                            'failed_count': 0,
                            'last_status': 'idle',
                            'last_observation': ''
                        })
                        if status == 'adicionado':
                            stat['added_count'] = int(stat.get('added_count') or 0) + 1
                        elif status == 'falha':
                            stat['failed_count'] = int(stat.get('failed_count') or 0) + 1
                        stat['last_status'] = status
                        stat['last_observation'] = observation
                        stat['last_seen'] = entry['time']
                        break
                automation_manager.save_config()
                task_data['member_results_persisted'] = True
            except Exception as persist_error:
                print(f'⚠️ Erro ao salvar resultado de membro da tarefa #{task_id}: {persist_error}')
    
    def get_source_group(self):
        """Retorna o grupo de origem dos membros"""
        from config import DATA_DIR
        export_file = os.path.join(self.data_dir or DATA_DIR, 'members_export.json')
        
        if os.path.exists(export_file):
            try:
                data = load_json_file(export_file, {})
                return data.get('source_group_link')
            except:
                pass
        return None
    
    def load_members(self):
        """Carrega membros do arquivo"""
        if os.path.exists(self.members_file):
            return load_json_file(self.members_file, [])
        return []
    
    def save_members(self, members):
        """Salva membros no arquivo"""
        atomic_write_json(self.members_file, members, indent=2)
    
    def mark_session_flood(self, session_name, flood_until):
        """Marca uma sessão como em FLOOD"""
        from config import DATA_DIR
        flood_file = os.path.join(self.data_dir or DATA_DIR, 'session_floods.json')
        
        # Carrega floods existentes
        floods = {}
        if os.path.exists(flood_file):
            try:
                floods = load_json_file(flood_file, {})
            except:
                floods = {}
        
        # Adiciona/atualiza flood
        floods[session_name] = flood_until.isoformat()
        
        # Salva
        atomic_write_json(flood_file, floods, indent=2)

    def _get_flood_wait_seconds(self, error):
        """Extrai o tempo de espera de um FloodWaitError ou da mensagem do Telethon."""
        seconds = getattr(error, 'seconds', None)
        if seconds is not None:
            try:
                return max(1, int(seconds))
            except (TypeError, ValueError):
                pass

        match = re.search(r'A wait of (\d+) seconds is required', str(error), re.IGNORECASE)
        if match:
            return max(1, int(match.group(1)))
        return None

    def _quarantine_session(self, session_info, seconds, status, reason, socketio=None):
        """Coloca a sessao em cooldown para o agendador nao tentar de novo em loop."""
        session_name = session_info.get('session_name')
        if not session_name:
            self._set_last_result(status, reason)
            return

        flood_until = datetime.now() + timedelta(seconds=max(1, int(seconds)))
        flood_until_iso = flood_until.isoformat()
        self.mark_session_flood(session_name, flood_until)
        session_info['status'] = 'flood'
        session_info['flood_until'] = flood_until_iso
        self._set_last_result(status, reason)
        emit_log(
            f'Sessao {session_name} em cooldown ate {flood_until.strftime("%d/%m/%Y %H:%M:%S")}',
            'warning',
            socketio
        )

    def _quarantine_from_error(self, session_info, error, socketio=None):
        """Retorna True quando o erro deve bloquear a sessao temporariamente."""
        error_type = type(error).__name__
        error_msg = str(error)
        wait_seconds = self._get_flood_wait_seconds(error)

        if wait_seconds:
            wait_minutes = max(1, wait_seconds // 60)
            reason = f'Flood temporario: aguardar {wait_minutes} min ({wait_seconds}s)'
            emit_log(f'FLOOD TEMPORARIO: precisa esperar {wait_seconds}s', 'warning', socketio)
            self._quarantine_session(session_info, wait_seconds, 'flood_wait', reason, socketio)
            return True

        if error_type == 'AuthKeyDuplicatedError' or 'authorization key' in error_msg.lower():
            reason = 'Sessao invalida/duplicada: arquivo usado em dois IPs ao mesmo tempo'
            emit_log('Sessao invalida/duplicada. Ela foi bloqueada por 7 dias.', 'error', socketio)
            self._quarantine_session(session_info, 7 * 24 * 3600, 'auth_key_duplicated', reason, socketio)
            return True

        return False

    def _get_existing_cooldown(self, session_info):
        """Consulta session_floods.json antes de qualquer conexão Telegram."""
        session_name = session_info.get('session_name')
        if not session_name:
            return None

        from config import DATA_DIR
        flood_file = os.path.join(self.data_dir or DATA_DIR, 'session_floods.json')
        try:
            floods = load_json_file(flood_file, {}) if os.path.exists(flood_file) else {}
            flood_until_str = floods.get(session_name) or session_info.get('flood_until')
            if not flood_until_str:
                return None
            flood_until = datetime.fromisoformat(flood_until_str)
            now = datetime.now()
            if now >= flood_until:
                return None
            return {
                'until': flood_until,
                'seconds': max(1, int((flood_until - now).total_seconds()))
            }
        except Exception:
            return None
    
    async def _leave_group(self, client, entity, socketio):
        """Sai do grupo"""
        try:
            from telethon.tl.functions.channels import LeaveChannelRequest
            await client(LeaveChannelRequest(entity))
            emit_log(f'✅ Saiu do grupo: {entity.title}', 'success', socketio)
        except Exception as e:
            emit_log(f'⚠️ Erro ao sair do grupo: {str(e)[:50]}', 'warning', socketio)
    
    def add_members_smart(
        self,
        session_info,
        target_group,
        members_per_session,
        daily_limit=200,
        socketio=None,
        task_data=None,
        delay_between_adds=5,
        delay_between_adds_max=None,
        group_interaction_enabled=True
    ):
        """
        Adiciona membros de forma inteligente com aquecimento
        
        Args:
            session_info: Informações da sessão
            target_group: Grupo destino
            members_per_session: Quantos membros adicionar nesta sessão
            daily_limit: Limite diário total do grupo (padrão: 200)
            socketio: Socket para logs em tempo real
            task_data: Dados da tarefa (task_id, added_today, total_added, etc) para atualizar em tempo real
        """
        self._set_last_result('running', 'Processando sessão')
        cooldown = self._get_existing_cooldown(session_info)
        if cooldown:
            minutes = max(1, cooldown['seconds'] // 60)
            self._set_last_result('flood_wait', f'Sessao em quarentena: aguardar {minutes} min')
            emit_log(
                f'Sessao {session_info.get("session_name")} em quarentena; pulando ate {cooldown["until"].strftime("%d/%m/%Y %H:%M:%S")}',
                'warning',
                socketio
            )
            return 0

        emit_log(f'🧠 [SMART ADDER] Iniciando adição inteligente', 'info', socketio)
        emit_log(f'👤 Sessão: {session_info["first_name"]}', 'info', socketio)
        emit_log(f'🎯 Grupo: {target_group}', 'info', socketio)
        emit_log(f'📊 Meta desta sessão: {members_per_session} membros', 'info', socketio)
        emit_log(f'📈 Limite diário do grupo: {daily_limit} membros', 'info', socketio)
        add_delay_min = max(1, int(delay_between_adds or 1))
        add_delay_max = max(add_delay_min, int(delay_between_adds_max if delay_between_adds_max is not None else add_delay_min))
        if add_delay_min == add_delay_max:
            emit_log(f'⏱️ Delay entre adições: {add_delay_min}s', 'info', socketio)
        else:
            emit_log(f'⏱️ Delay entre adições: {add_delay_min}-{add_delay_max}s', 'info', socketio)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self._add_smart_async(
                    session_info,
                    target_group,
                    members_per_session,
                    daily_limit,
                    socketio,
                    task_data,
                    delay_between_adds,
                    delay_between_adds_max,
                    group_interaction_enabled
                )
            )
            return result
        finally:
            loop.close()
    
    async def _add_smart_async(
        self,
        session_info,
        target_group,
        members_per_session,
        daily_limit,
        socketio,
        task_data=None,
        delay_between_adds=5,
        delay_between_adds_max=None,
        group_interaction_enabled=True
    ):
        """Adição inteligente assíncrona"""
        session_path = session_info.get('session_path')

        cooldown = self._get_existing_cooldown(session_info)
        if cooldown:
            minutes = max(1, cooldown['seconds'] // 60)
            self._set_last_result('flood_wait', f'Sessao em quarentena: aguardar {minutes} min')
            emit_log(
                f'Sessao {session_info.get("session_name")} em quarentena; nao vou conectar antes de {cooldown["until"].strftime("%d/%m/%Y %H:%M:%S")}',
                'warning',
                socketio
            )
            return 0
        
        if not session_path:
            # Fallback para o método antigo
            session_path = os.path.join(SESSIONS_DIR, session_info['session_name'])

        add_delay_min = max(1, int(delay_between_adds or 1))
        add_delay_max = max(add_delay_min, int(delay_between_adds_max if delay_between_adds_max is not None else add_delay_min))
        
        # Usa sessão diretamente (mesmo método da validação)
        added_count = 0  # Declara aqui para estar disponível no except
        try:
            from telethon import TelegramClient
            
            client = TelegramClient(
                session_path,
                self.api_id,
                self.api_hash
            )
            
            emit_log('🔌 Conectando ao Telegram...', 'info', socketio)
            await client.connect()
            
            if not await client.is_user_authorized():
                emit_log('❌ Sessão não autorizada', 'error', socketio)
                return 0
            
            emit_log('✅ Sessão autorizada', 'success', socketio)
            
            # PASSO 1: Entra no grupo destino
            emit_log('📥 PASSO 1: Entrando no grupo destino...', 'info', socketio)
            emit_log(f'🔗 Link original: {target_group}', 'info', socketio)
            
            clean_link = target_group.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '').strip().strip('/')
            emit_log(f'🔗 Link processado: {clean_link}', 'info', socketio)
            
            target_entity = None
            
            try:
                if 'joinchat' in target_group or '+' in target_group:
                    # Grupo privado
                    from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
                    invite_hash = clean_link.split('/')[-1].replace('+', '')
                    emit_log(f'🔐 Grupo privado detectado (hash: {invite_hash})', 'info', socketio)
                    
                    try:
                        result = await client(ImportChatInviteRequest(invite_hash))
                        await asyncio.sleep(2)
                        if hasattr(result, 'chats') and result.chats:
                            target_entity = result.chats[0]
                            emit_log(f'✅ Entrou no grupo privado: {target_entity.title}', 'success', socketio)
                    except Exception as private_error:
                        if self._quarantine_from_error(session_info, private_error, socketio):
                            return 0

                        private_error_msg = str(private_error)
                        already_participant = (
                            'already a participant' in private_error_msg.lower()
                            or type(private_error).__name__ == 'UserAlreadyParticipantError'
                        )
                        if already_participant:
                            emit_log('✅ A sessão já participa desse grupo privado', 'success', socketio)
                            try:
                                invite_info = await client(CheckChatInviteRequest(invite_hash))
                                if hasattr(invite_info, 'chat') and invite_info.chat:
                                    target_entity = invite_info.chat
                                    emit_log(f'✅ Grupo privado resolvido: {target_entity.title}', 'success', socketio)
                            except Exception as check_error:
                                emit_log(f'⚠️ Não consegui resolver pelo convite: {check_error}', 'warning', socketio)
                        else:
                            emit_log(f'❌ Erro ao entrar no grupo privado: {private_error}', 'error', socketio)

                        # Tenta pegar o grupo mesmo assim (pode já estar nele)
                        if not target_entity:
                            try:
                                target_entity = await client.get_entity(target_group)
                                emit_log(f'✅ Já estava no grupo: {target_entity.title}', 'success', socketio)
                            except:
                                raise Exception(f"Não foi possível acessar grupo privado: {private_error}")
                else:
                    # Grupo público
                    emit_log(f'🌐 Grupo público detectado', 'info', socketio)
                    
                    # Tenta primeiro pegar sem entrar (pode já estar nele)
                    try:
                        target_entity = await client.get_entity('@' + clean_link)
                        emit_log(f'✅ Grupo encontrado: {target_entity.title}', 'success', socketio)
                        
                        # Verifica se está no grupo
                        try:
                            perms = await client.get_permissions(target_entity, 'me')
                            if perms and perms.is_chat:
                                emit_log(f'✅ Já está no grupo!', 'success', socketio)
                            else:
                                emit_log(f'⚠️ Não está no grupo, entrando...', 'warning', socketio)
                                from telethon.tl.functions.channels import JoinChannelRequest
                                await client(JoinChannelRequest('@' + clean_link))
                                await asyncio.sleep(2)
                                emit_log(f'✅ Entrou no grupo!', 'success', socketio)
                        except:
                            # Tenta entrar
                            emit_log(f'🚪 Tentando entrar no grupo...', 'info', socketio)
                            from telethon.tl.functions.channels import JoinChannelRequest
                            await client(JoinChannelRequest('@' + clean_link))
                            await asyncio.sleep(2)
                            emit_log(f'✅ Entrou no grupo!', 'success', socketio)
                            
                    except Exception as get_error:
                        emit_log(f'⚠️ Grupo não encontrado ({get_error}), tentando entrar...', 'warning', socketio)
                        # Tenta entrar
                        try:
                            from telethon.tl.functions.channels import JoinChannelRequest
                            await client(JoinChannelRequest('@' + clean_link))
                            await asyncio.sleep(2)
                            target_entity = await client.get_entity('@' + clean_link)
                            emit_log(f'✅ Entrou no grupo: {target_entity.title}', 'success', socketio)
                        except Exception as join_error:
                            emit_log(f'❌ Erro ao entrar: {join_error}', 'error', socketio)
                            raise Exception(f"Não foi possível entrar no grupo: {join_error}")
                
                if not target_entity:
                    raise Exception(f"Não foi possível acessar o grupo: {target_group}")
                
                emit_log(f'✅ Grupo acessado: {target_entity.title}', 'success', socketio)
                
            except Exception as entry_error:
                emit_log(f'❌ ERRO ao entrar no grupo: {entry_error}', 'error', socketio)
                emit_log(f'🔍 Tipo do erro: {type(entry_error).__name__}', 'error', socketio)
                
                # Mostra o erro completo para debug
                import traceback
                error_trace = traceback.format_exc()
                emit_log(f'📋 Traceback completo:', 'error', socketio)
                for line in error_trace.split('\n'):
                    if line.strip():
                        emit_log(f'   {line}', 'error', socketio)
                
                raise
            
            emit_log(f'✅ Entrou no grupo: {target_entity.title}', 'success', socketio)
            
            # PASSO 2: Teste/aquecimento opcional
            if group_interaction_enabled:
                emit_log('🔥 PASSO 2: TESTE - Verificando se consegue enviar mensagem...', 'info', socketio)
            else:
                emit_log('⏭️ Interação no grupo desligada pelo painel', 'info', socketio)
            
            can_send_messages = False
            warming_group_used = None
            
            if group_interaction_enabled:
                try:
                # Tenta enviar uma mensagem de teste
                    test_message = random.choice(WARMING_MESSAGES)
                    await client.send_message(target_entity, test_message)
                    can_send_messages = True
                    warming_group_used = target_entity
                    emit_log(f'✅ TESTE PASSOU: Consegue enviar mensagens no grupo destino!', 'success', socketio)
                    emit_log(f'💬 Mensagem de teste: "{test_message}"', 'info', socketio)
                    await asyncio.sleep(3)  # Aguarda um pouco
                except Exception as test_error:
                    error_msg = str(test_error)
                    
                    emit_log(f'⚠️ TESTE: NÃO consegue enviar mensagens no grupo destino', 'warning', socketio)
                    emit_log(f'⚠️ Erro: {error_msg}', 'warning', socketio)
                    
                    # Verifica se é erro de permissão de mensagem (não impede adicionar membros)
                    if "CHAT_SEND_PLAIN_FORBIDDEN" in error_msg or "CHAT_SEND_MEDIA_FORBIDDEN" in error_msg:
                        emit_log(f'💡 Grupo restringe mensagens de texto/mídia', 'info', socketio)
                        emit_log(f'✅ MAS isso NÃO impede adicionar membros!', 'success', socketio)
                        emit_log(f'➡️ Pulando aquecimento e tentando adicionar direto...', 'info', socketio)
                        # Permite continuar sem aquecimento
                        can_send_messages = True  # Marca como OK para continuar
                        warming_group_used = None  # Sem aquecimento
                    else:
                        # Tenta usar grupo de aquecimento alternativo
                        emit_log(f'🔄 Tentando usar grupo de aquecimento alternativo...', 'info', socketio)
                        
                        # Carrega configuração do grupo de aquecimento
                        from config import CONFIG_FILE
                        warming_group_link = None
                        
                        if os.path.exists(CONFIG_FILE):
                            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                                config_data = json.load(f)
                                warming_group_link = config_data.get('warming_group')
                        
                        if warming_group_link:
                            emit_log(f'🔥 Grupo de aquecimento configurado: {warming_group_link}', 'info', socketio)
                            
                            try:
                            # Entra no grupo de aquecimento
                                clean_warming = warming_group_link.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '').strip().strip('/')
                                
                                if 'joinchat' in warming_group_link or '+' in warming_group_link:
                                    from telethon.tl.functions.messages import ImportChatInviteRequest
                                    invite_hash = clean_warming.split('/')[-1].replace('+', '')
                                    result = await client(ImportChatInviteRequest(invite_hash))
                                    await asyncio.sleep(2)
                                    if hasattr(result, 'chats') and result.chats:
                                        warming_entity = result.chats[0]
                                else:
                                    try:
                                        warming_entity = await client.get_entity('@' + clean_warming)
                                    except:
                                        from telethon.tl.functions.channels import JoinChannelRequest
                                        await client(JoinChannelRequest('@' + clean_warming))
                                        await asyncio.sleep(2)
                                        warming_entity = await client.get_entity('@' + clean_warming)
                                
                                emit_log(f'✅ Entrou no grupo de aquecimento: {warming_entity.title}', 'success', socketio)
                                
                                # Tenta enviar mensagem no grupo de aquecimento
                                test_message = random.choice(WARMING_MESSAGES)
                                await client.send_message(warming_entity, test_message)
                                can_send_messages = True
                                warming_group_used = warming_entity
                                emit_log(f'✅ SUCESSO: Consegue enviar no grupo de aquecimento!', 'success', socketio)
                                emit_log(f'💬 Mensagem: "{test_message}"', 'info', socketio)
                                emit_log(f'💡 Sessão vai aquecer no grupo alternativo e depois adicionar no destino', 'info', socketio)
                                await asyncio.sleep(3)
                                
                            except Exception as warming_error:
                                emit_log(f'⚠️ Erro no grupo de aquecimento: {warming_error}', 'warning', socketio)
                                emit_log(f'💡 Sessão muito nova - não consegue enviar mensagens em nenhum grupo', 'warning', socketio)
                                emit_log(f'✅ MAS vamos tentar adicionar membros mesmo assim!', 'success', socketio)
                                emit_log(f'💡 Adicionar membros usa permissão diferente de enviar mensagens', 'info', socketio)
                                # Permite continuar sem aquecimento
                                can_send_messages = True
                                warming_group_used = None
                        else:
                            emit_log(f'⚠️ Nenhum grupo de aquecimento configurado', 'warning', socketio)
                            emit_log(f'✅ Tentando adicionar membros sem aquecimento...', 'success', socketio)
                            # Permite continuar sem aquecimento
                            can_send_messages = True
                            warming_group_used = None
            
            # PASSO 3: Aquecimento (se conseguiu enviar mensagens)
            if warming_group_used:
                emit_log('🔥 PASSO 3: Aquecimento adicional...', 'info', socketio)
                
                if warming_group_used == target_entity:
                    emit_log('💬 Aquecendo no grupo destino...', 'info', socketio)
                else:
                    emit_log('💬 Aquecendo no grupo alternativo...', 'info', socketio)
                
                warming_count = random.randint(1, 3)  # Mais 1-3 mensagens (já mandou 1 no teste)
                emit_log(f'💬 Enviando mais {warming_count} mensagens de aquecimento...', 'info', socketio)
                
                # Decide se usa sequência natural ou mensagens aleatórias
                use_sequence = random.choice([True, False]) and WARMING_DATA
                
                if use_sequence and WARMING_DATA:
                    # Usa uma sequência natural de mensagens
                    sequence = random.choice(WARMING_DATA['sequencias_naturais'])
                    messages_to_send = sequence[:warming_count]
                    emit_log(f'🎭 Usando sequência natural de mensagens', 'info', socketio)
                else:
                    # Usa mensagens aleatórias
                    messages_to_send = [random.choice(WARMING_MESSAGES) for _ in range(warming_count)]
                
                for i, message in enumerate(messages_to_send, 1):
                    try:
                        await client.send_message(warming_group_used, message)
                        emit_log(f'✅ Mensagem {i}/{len(messages_to_send)}: "{message}"', 'success', socketio)
                        
                        # Às vezes adiciona um emoji como reação (mais natural)
                        if WARMING_DATA and random.random() < 0.3:  # 30% de chance
                            await asyncio.sleep(random.randint(1, 3))
                            emoji = random.choice(WARMING_DATA['reacoes'])
                            try:
                                await client.send_message(warming_group_used, emoji)
                                emit_log(f'😊 Reação: {emoji}', 'info', socketio)
                            except:
                                pass  # Ignora se não conseguir enviar emoji
                        
                        # Delay entre mensagens (5-15 segundos) - mais natural
                        delay = random.randint(5, 15)
                        emit_log(f'⏳ Aguardando {delay}s...', 'info', socketio)
                        await asyncio.sleep(delay)
                    except Exception as msg_error:
                        emit_log(f'⚠️ Erro ao enviar mensagem: {msg_error}', 'warning', socketio)
                        # Continua mesmo se não conseguir enviar mensagens
                        break
                
                emit_log('✅ Aquecimento concluído!', 'success', socketio)
            else:
                emit_log('⚠️ PASSO 3: Pulando aquecimento (sem permissão para mensagens)', 'warning', socketio)
                emit_log('💡 Tentando adicionar membros direto...', 'info', socketio)
            
            # PASSO 4: Carrega membros para adicionar
            emit_log('📋 PASSO 4: Carregando membros...', 'info', socketio)
            
            members = self.load_members()
            pending = [m for m in members if not m.get('added', False)]
            
            if not pending:
                emit_log('⚠️ Nenhum membro pendente', 'warning', socketio)
                self._set_last_result('no_pending_members', 'Nenhum membro pendente no arquivo de membros')
                # Sai do grupo antes de retornar
                await self._leave_group(client, target_entity, socketio)
                return 0
            
            max_attempts = min(len(pending), max(members_per_session + 5, members_per_session * 5))
            to_add = pending[:max_attempts]
            emit_log(f'📊 {len(pending)} membros disponíveis; meta desta sessão: {members_per_session}', 'info', socketio)
            if max_attempts > members_per_session:
                emit_log(f'🔎 Vou testar até {max_attempts} registro(s) para encontrar membros válidos', 'info', socketio)
            
            # PASSO 4.5: ENTRA NO GRUPO DE ORIGEM para atualizar access_hash
            emit_log('🔄 PASSO 4.5: Entrando no grupo de origem para atualizar dados...', 'info', socketio)
            
            source_group = self.get_source_group()
            members_with_id = [m for m in to_add if m.get('id')]
            
            if source_group and members_with_id:
                emit_log(f'📊 {len(members_with_id)} membro(s) com ID detectado(s)', 'info', socketio)
                emit_log(f'� Entrando no grupo de origem: {source_group}', 'info', socketio)
                
                try:
                    # Entra no grupo de origem
                    clean_source = source_group.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '').strip().strip('/')
                    
                    source_entity = None
                    if 'joinchat' in source_group or '+' in source_group:
                        # Grupo privado
                        from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
                        invite_hash = clean_source.split('/')[-1].replace('+', '')
                        try:
                            result = await client(ImportChatInviteRequest(invite_hash))
                            await asyncio.sleep(2)
                            if hasattr(result, 'chats') and result.chats:
                                source_entity = result.chats[0]
                        except Exception as source_invite_error:
                            if 'already a participant' in str(source_invite_error).lower():
                                invite_info = await client(CheckChatInviteRequest(invite_hash))
                                if hasattr(invite_info, 'chat') and invite_info.chat:
                                    source_entity = invite_info.chat
                            else:
                                raise
                    elif clean_source.lstrip('-').isdigit():
                        from telethon.tl.types import PeerChannel
                        numeric_id = int(clean_source)
                        if str(numeric_id).startswith('-100'):
                            numeric_id = int(str(numeric_id)[4:])
                        try:
                            source_entity = await client.get_entity(PeerChannel(numeric_id))
                        except Exception:
                            source_entity = await client.get_entity(int(clean_source))
                    else:
                        # Grupo público
                        try:
                            source_entity = await client.get_entity('@' + clean_source)
                        except:
                            from telethon.tl.functions.channels import JoinChannelRequest
                            await client(JoinChannelRequest('@' + clean_source))
                            await asyncio.sleep(2)
                            source_entity = await client.get_entity('@' + clean_source)
                    
                    if source_entity:
                        emit_log(f'✅ Entrou no grupo de origem: {source_entity.title}', 'success', socketio)
                        emit_log(f'🔄 Atualizando entidades/access_hash de {len(members_with_id)} membro(s)...', 'info', socketio)
                        
                        # Pega todos os membros do grupo de origem
                        emit_log(f'📥 Baixando lista de membros do grupo de origem...', 'info', socketio)
                        source_members = await client.get_participants(source_entity, limit=None)
                        emit_log(f'✅ {len(source_members)} membros baixados', 'success', socketio)
                        
                        # Cria um dicionário ID -> User para busca rápida
                        source_members_dict = {user.id: user for user in source_members}
                        
                        # Atualiza access_hash dos membros sem username
                        updated_count = 0
                        for member in members_with_id:
                            if member['id'] in source_members_dict:
                                source_user = source_members_dict[member['id']]
                                if hasattr(source_user, 'access_hash'):
                                    member['access_hash'] = source_user.access_hash
                                    updated_count += 1
                        
                        emit_log(f'✅ Access_hash atualizado: {updated_count}/{len(members_with_id)}', 'success', socketio)
                        
                        # NÃO SAI do grupo de origem - precisa estar nele para adicionar membros sem username
                        emit_log(f'� Mantendo conexão com grupo de origem para adicionar membros...', 'info', socketio)
                    
                except Exception as e:
                    if self._quarantine_from_error(session_info, e, socketio):
                        return 0

                    emit_log(f'⚠️ Erro ao acessar grupo de origem: {str(e)[:80]}', 'warning', socketio)
                    emit_log(f'💡 Continuando sem atualizar access_hash...', 'warning', socketio)
            elif not source_group:
                emit_log(f'⚠️ Grupo de origem não configurado', 'warning', socketio)
                emit_log(f'💡 Configure em "Membros" > "Grupo de Origem"', 'warning', socketio)
            else:
                emit_log(f'✅ Membros desta rodada não precisam atualizar ID/access_hash', 'success', socketio)
            
            # PASSO 5: Adiciona membros com interações durante delays
            emit_log('👥 PASSO 5: Adicionando membros...', 'info', socketio)
            
            # added_count já foi declarado no início da função
            
            for idx, member in enumerate(to_add, 1):
                try:
                    if added_count >= members_per_session:
                        break

                    # Delay antes de processar
                    await asyncio.sleep(2)
                    
                    # Busca o usuário
                    user_to_add = None
                    member_name = member.get('first_name', 'Usuário')
                    has_username = bool(member.get('username'))
                    
                    emit_log(f'🔍 [{idx}/{len(to_add)}] Processando: {member_name}', 'info', socketio)
                    
                    # MÉTODO 1: Tenta pelo username (mais confiável)
                    if has_username:
                        try:
                            if not client.is_connected():
                                raise ConnectionError('Cannot send requests while disconnected')
                            user_to_add = await client.get_entity(member['username'])
                            emit_log(f'✅ Encontrado por @{member["username"]}', 'success', socketio)
                        except Exception as e:
                            if self._is_disconnected_error(e):
                                raise
                            emit_log(f'⚠️ Username não encontrado: {str(e)[:60]}', 'warning', socketio)
                    
                    # MÉTODO 2: Tenta pelo ID (se não achou por username)
                    if not user_to_add and member.get('id'):
                        try:
                            if not client.is_connected():
                                raise ConnectionError('Cannot send requests while disconnected')
                            user_to_add = await client.get_entity(member['id'])
                            emit_log(f'✅ Encontrado por ID: {member["id"]}', 'success', socketio)
                        except Exception as e:
                            if self._is_disconnected_error(e):
                                raise
                            emit_log(f'⚠️ Não encontrado por ID: {str(e)[:60]}', 'warning', socketio)
                    
                    # MÉTODO 3: Usa InputPeerUser como último recurso (se tiver access_hash)
                    if not user_to_add and member.get('id') and member.get('access_hash'):
                        try:
                            if not client.is_connected():
                                raise ConnectionError('Cannot send requests while disconnected')
                            emit_log(f'🔄 Usando ID + access_hash como último recurso', 'info', socketio)
                            from telethon.tl.types import InputPeerUser
                            user_to_add = InputPeerUser(int(member['id']), int(member['access_hash']))
                        except Exception as e:
                            if self._is_disconnected_error(e):
                                raise
                            emit_log(f'⚠️ InputPeerUser falhou: {str(e)[:60]}', 'warning', socketio)
                    
                    if not user_to_add:
                        emit_log(f'❌ Não foi possível encontrar: {member_name}', 'error', socketio)
                        emit_log(f'💡 ID sozinho não basta; precisa username ou access_hash válido visto pela sessão', 'warning', socketio)
                        self._set_last_result('member_not_found', f'Não foi possível localizar o membro "{member_name}" com username, ID ou access_hash válido')
                        self._record_member_result(task_data, member, session_info, 'falha', self.last_result['reason'])
                        member['added'] = True
                        continue
                    
                    # Delay antes de adicionar
                    await asyncio.sleep(3)
                    
                    # Adiciona
                    try:
                        if not client.is_connected():
                            raise ConnectionError('Cannot send requests while disconnected')
                        await client(InviteToChannelRequest(target_entity, [user_to_add]))
                        
                        # INCREMENTA IMEDIATAMENTE após sucesso
                        added_count += 1
                        member['added'] = True
                        
                        name = member.get('first_name', 'Usuário')
                        username_info = f"(@{member['username']})" if member.get('username') else "(sem username)"
                        id_info = f"ID: {member.get('id', 'N/A')}"
                        emit_log(f'✅ [{added_count}/{len(to_add)}] Adicionado: {name} {username_info} [{id_info}]', 'success', socketio)
                        emit_log(f'📊 [DEBUG] added_count atual: {added_count}', 'info', socketio)
                        self._record_member_result(task_data, member, session_info, 'adicionado', 'Adicionado ao grupo de destino')
                        
                        # EMITE EVENTO PARA ATUALIZAR FRONTEND EM TEMPO REAL
                        if task_data and socketio and hasattr(socketio, 'emit'):
                            task_data['added_today'] += 1
                            task_data['total_added'] += 1
                            
                            # SALVA NO ARQUIVO IMEDIATAMENTE usando o automation_manager correto
                            if 'automation_manager' in task_data:
                                try:
                                    automation_manager = task_data['automation_manager']
                                    
                                    # Recarrega para pegar valores atuais
                                    automation_manager.load_config()
                                    
                                    # Atualiza a tarefa no arquivo
                                    for group in automation_manager.config.get('groups', []):
                                        if group['id'] == task_data['task_id']:
                                            group['added_today'] = task_data['added_today']
                                            group['total_added'] = task_data['total_added']
                                            break
                                    
                                    # Salva o arquivo
                                    automation_manager.save_config()
                                    print(f'💾 Arquivo salvo: {automation_manager.config_file}')
                                    print(f'   added_today={task_data["added_today"]}, total={task_data["total_added"]}')
                                except Exception as save_error:
                                    print(f'⚠️ Erro ao salvar arquivo: {save_error}')
                            
                            # Usa o socketio passado como parâmetro
                            socketio.emit('task_progress', {
                                'task_id': task_data['task_id'],
                                'added_today': task_data['added_today'],
                                'total_added': task_data['total_added'],
                                'target_members': task_data['target_members'],
                                'daily_limit': task_data['daily_limit'],
                                'status': 'adding'
                            })
                            print(f'📡 Evento task_progress emitido: added_today={task_data["added_today"]}, total={task_data["total_added"]}')

                        if task_data and task_data.get('force_rotate_after_each_add'):
                            remaining = [m for m in members if not m.get('added', False)]
                            self.save_members(remaining)
                            emit_log('🔄 Rotação 1x1: 1 membro adicionado, trocando para a próxima sessão...', 'success', socketio)
                            try:
                                await self._leave_group(client, target_entity, socketio)
                            finally:
                                await client.disconnect()
                            self._set_last_result('success', 'Sessão adicionou 1 membro e liberou a rotação')
                            return added_count
                        
                    except Exception as add_error:
                        add_error_msg = str(add_error)
                        if "Invalid object ID for a user" in add_error_msg:
                            emit_log(f'⚠️ ID/access_hash inválido para convite, pulando membro...', 'warning', socketio)
                            self._set_last_result('invalid_user_id', 'ID/access_hash inválido para convite. O registro foi removido do arquivo e a próxima tentativa continua.')
                            self._record_member_result(task_data, member, session_info, 'falha', self.last_result['reason'])
                            member['added'] = True
                            continue

                        # Se der erro ao adicionar, relança a exceção para o tratamento externo
                        raise add_error
                    
                    # INTERAÇÃO DURANTE DELAY - Manda mensagem aleatória a cada 3-5 adições (mais natural)
                    if group_interaction_enabled and added_count % random.randint(3, 5) == 0:
                        try:
                            # Escolhe tipo de interação
                            interaction_type = random.choice(['message', 'emoji', 'reaction'])
                            
                            if interaction_type == 'emoji' and WARMING_DATA:
                                # Apenas um emoji
                                interaction_msg = random.choice(WARMING_DATA['reacoes'])
                            elif interaction_type == 'reaction' and WARMING_DATA:
                                # Comentário positivo ou confirmação
                                category = random.choice(['comentarios_positivos', 'confirmacoes', 'respostas_contextuais'])
                                interaction_msg = random.choice(WARMING_DATA[category])
                            else:
                                # Mensagem casual
                                if WARMING_DATA:
                                    interaction_msg = random.choice(
                                        WARMING_DATA['comentarios_positivos'] + 
                                        WARMING_DATA['conversas_casuais'] +
                                        WARMING_DATA['reacoes']
                                    )
                                else:
                                    # Fallback
                                    interaction_msg = random.choice([
                                        "Legal! 👍",
                                        "Interessante...",
                                        "Concordo!",
                                        "Verdade!",
                                        "😊",
                                        "👏",
                                    ])
                            
                            await client.send_message(target_entity, interaction_msg)
                            emit_log(f'💬 Interação: "{interaction_msg}"', 'info', socketio)
                        except:
                            pass  # Não para se não conseguir interagir
                    
                    delay_seconds = random.randint(add_delay_min, add_delay_max)
                    emit_log(f'⏳ Aguardando {delay_seconds}s antes da próxima adição...', 'info', socketio)
                    await asyncio.sleep(delay_seconds)
                    
                except PeerFloodError:
                    emit_log('🚫 FLOOD detectado! Sessão bloqueada por 3 dias.', 'error', socketio)
                    self._set_last_result('peer_flood', 'FLOOD detectado. Sessão foi colocada em quarentena por 3 dias')
                    from datetime import datetime, timedelta
                    flood_until = datetime.now() + timedelta(days=3)
                    self.mark_session_flood(session_info['session_name'], flood_until)
                    break
                
                except FloodWaitError as e:
                    # Erro de flood temporário - precisa esperar X segundos
                    wait_seconds = e.seconds
                    wait_minutes = wait_seconds // 60
                    
                    emit_log(f'⏰ FLOOD TEMPORÁRIO: Precisa esperar {wait_minutes} minutos ({wait_seconds}s)', 'error', socketio)
                    emit_log(f'🔄 Pulando para próxima sessão...', 'warning', socketio)
                    self._quarantine_session(
                        session_info,
                        wait_seconds,
                        'flood_wait',
                        f'Flood temporario: aguardar {wait_minutes} min ({wait_seconds}s)',
                        socketio
                    )
                    break
                
                except Exception as e:
                    error_msg = str(e)
                    error_type = type(e).__name__
                    error_text = error_msg.lower()

                    if self._is_disconnected_error(e):
                        emit_log('🔌 Sessão desconectou do Telegram. Encerrando esta sessão e parando a repetição de erros.', 'error', socketio)
                        self._quarantine_session(
                            session_info,
                            30 * 60,
                            'disconnected',
                            'Sessão desconectou do Telegram durante a adição; aguardando 30 min antes de tentar de novo',
                            socketio
                        )
                        self._record_member_result(task_data, member, session_info, 'falha', self.last_result['reason'])
                        break
                    
                    # Ignora erros de TypeNotFoundError (problema de versão do Telethon)
                    if "TypeNotFoundError" in str(type(e).__name__) or "Could not find a matching Constructor ID" in error_msg:
                        # Erro de protocolo - ignora e continua
                        continue
                    
                    # Tratamento específico de erros
                    if "can't write" in error_msg.lower() or "ChatWriteForbiddenError" in error_msg:
                        emit_log(f'❌ ERRO: Sem permissão para adicionar membros neste grupo!', 'error', socketio)
                        emit_log(f'💡 Possíveis causas:', 'warning', socketio)
                        emit_log(f'   1. Sessão não é admin e grupo restringe adições', 'warning', socketio)
                        emit_log(f'   2. Sessão é muito nova (menos de 24h no grupo)', 'warning', socketio)
                        emit_log(f'   3. Grupo tem proteção anti-spam ativa', 'warning', socketio)
                        emit_log(f'💡 Solução: Torne esta sessão ADMIN do grupo', 'warning', socketio)
                        self._set_last_result('write_forbidden', 'Sessão sem permissão para adicionar/escrever no grupo. Torne a sessão admin ou revise permissões do grupo')
                        self._record_member_result(task_data, member, session_info, 'falha', self.last_result['reason'])
                        # Para esta sessão mas não marca como erro fatal
                        break
                    
                    elif "UserPrivacyRestrictedError" in error_type or "privacy" in error_text:
                        emit_log(f'⚠️ Privacidade restrita, pulando...', 'warning', socketio)
                        self._set_last_result('user_privacy_restricted', 'Membro recusado por configuração de privacidade')
                        self._record_member_result(task_data, member, session_info, 'falha', self.last_result['reason'])
                        member['added'] = True
                        continue
                    
                    elif "UserNotMutualContactError" in error_type or "not mutual contact" in error_text:
                        emit_log(f'⚠️ Não é contato mútuo, pulando...', 'warning', socketio)
                        self._set_last_result('not_mutual_contact', 'Membro não é contato mútuo da sessão')
                        self._record_member_result(task_data, member, session_info, 'falha', self.last_result['reason'])
                        member['added'] = True
                        continue
                    
                    elif (
                        "UserChannelsTooMuchError" in error_type
                        or "too many channels" in error_text
                        or "too many channels/supergroups" in error_text
                    ):
                        emit_log(f'⚠️ Usuário já está em muitos canais/supergrupos, pulando...', 'warning', socketio)
                        self._set_last_result('user_channels_too_much', 'Membro já participa de muitos grupos/canais')
                        self._record_member_result(task_data, member, session_info, 'falha', self.last_result['reason'])
                        member['added'] = True
                        continue
                    
                    else:
                        emit_log(f'❌ Erro: {error_msg}', 'error', socketio)
                        self._set_last_result(type(e).__name__, error_msg[:220])
                        self._record_member_result(task_data, member, session_info, 'falha', self.last_result['reason'])
                        member['added'] = True
                        continue
            
            # Salva progresso
            remaining = [m for m in members if not m.get('added', False)]
            self.save_members(remaining)
            
            removed_count = len(members) - len(remaining)
            if removed_count > 0:
                emit_log(f'🗑️ Removidos {removed_count} membros do arquivo', 'info', socketio)
            
            # PASSO 6: SAI DO GRUPO após concluir
            if client and client.is_connected():
                emit_log('🚪 PASSO 6: Saindo do grupo...', 'info', socketio)
                await self._leave_group(client, target_entity, socketio)
                await client.disconnect()
                await asyncio.sleep(1)
            else:
                emit_log('🔌 Sessão já estava desconectada; saída do grupo ignorada nesta rodada.', 'warning', socketio)
            
            print(f'\n🎯🎯🎯 [SMART_ADDER] ANTES DO RETURN 🎯🎯🎯')
            print(f'added_count = {added_count}')
            print(f'Tipo: {type(added_count)}')
            print(f'🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯\n')
            
            emit_log(f'✅ Sessão finalizada: {added_count} membros adicionados', 'success', socketio)
            emit_log(f'🔄 Retornando added_count={added_count}', 'info', socketio)
            if added_count > 0:
                self._set_last_result('success', f'Sessão adicionou {added_count} membro(s)')
            elif self.last_result.get('status') == 'running':
                self._set_last_result('zero_added', 'Sessão processou a rodada, mas nenhum membro foi aceito pelo Telegram')
            return added_count
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__

            if self._quarantine_from_error(session_info, e, socketio):
                try:
                    if client and client.is_connected():
                        await client.disconnect()
                        await asyncio.sleep(0.5)
                except:
                    pass
                return added_count
            
            emit_log(f'❌ ERRO na sessão: {error_msg}', 'error', socketio)
            emit_log(f'🔍 Tipo do erro: {error_type}', 'error', socketio)
            emit_log(f'📊 Mas conseguiu adicionar {added_count} membros antes do erro', 'warning', socketio)
            
            # Mostra traceback completo para debug
            import traceback
            error_trace = traceback.format_exc()
            emit_log(f'📋 Traceback completo:', 'error', socketio)
            for line in error_trace.split('\n')[-10:]:  # Últimas 10 linhas
                if line.strip():
                    emit_log(f'   {line}', 'error', socketio)
            
            # Tratamento específico de erros gerais
            if "can't write" in error_msg.lower() or "ChatWriteForbiddenError" in error_msg:
                emit_log(f'💡 Causa: Sessão sem permissão para escrever no grupo', 'warning', socketio)
                emit_log(f'💡 Solução: Torne esta sessão ADMIN do grupo', 'warning', socketio)
                self._set_last_result('write_forbidden', 'Sessão sem permissão para escrever/adicionar no grupo')
            elif "ChatAdminRequiredError" in error_msg:
                emit_log(f'💡 Causa: Apenas admins podem adicionar membros', 'warning', socketio)
                emit_log(f'💡 Solução: Torne esta sessão ADMIN do grupo', 'warning', socketio)
                self._set_last_result('admin_required', 'Grupo exige admin para adicionar membros')
            elif "UserBannedInChannelError" in error_msg:
                emit_log(f'💡 Causa: Sessão está BANIDA do grupo', 'warning', socketio)
                emit_log(f'💡 Solução: Use outra sessão', 'warning', socketio)
                self._set_last_result('session_banned_in_group', 'Sessão está banida no grupo destino')
            elif "ChannelPrivateError" in error_msg:
                emit_log(f'💡 Causa: Grupo é privado', 'warning', socketio)
                emit_log(f'💡 Solução: Adicione esta sessão ao grupo primeiro', 'warning', socketio)
                self._set_last_result('private_group', 'Grupo privado/inacessível para esta sessão')
            else:
                self._set_last_result(error_type, error_msg[:220])
            
            try:
                if client and client.is_connected():
                    await client.disconnect()
                    await asyncio.sleep(0.5)
            except:
                pass
            
            # RETORNA added_count MESMO SE DEU ERRO (membros já foram adicionados)
            emit_log(f'🔄 Retornando added_count={added_count} (apesar do erro)', 'info', socketio)
            return added_count
        finally:
            await asyncio.sleep(1)
            try:
                await client.disconnect()
            except:
                pass
