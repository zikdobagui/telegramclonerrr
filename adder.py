from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
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
from datetime import datetime
from config import SESSIONS_DIR, MEMBERS_FILE
from logger import log_error, log_info, log_warning
from data_store import atomic_write_json, load_json_file

# Suprime warnings de reconexão do Telethon
logging.getLogger('telethon').setLevel(logging.ERROR)

def emit_log(message, log_type='info', socketio=None):
    """Helper para emitir logs - detecta automaticamente qual aba"""
    if socketio:
        if socketio == 'task':
            # Importa aqui para evitar circular import
            from app import socketio as app_socketio
            app_socketio.emit('task_log', {'message': message, 'type': log_type})
        elif socketio == 'extract':
            from app import socketio as app_socketio
            app_socketio.emit('extract_log', {'message': message, 'type': log_type})
        elif socketio == 'add':
            from app import socketio as app_socketio
            app_socketio.emit('add_log', {'message': message, 'type': log_type})
        elif hasattr(socketio, 'emit'):
            # É o objeto socketio real
            socketio.emit('log', {'message': message, 'type': log_type})
    else:
        print(message)

def emit_extract_log(message, log_type='info'):
    """Emite log apenas para aba Extrair"""
    socketio.emit('extract_log', {'message': message, 'type': log_type})

def emit_add_log(message, log_type='info'):
    """Emite log apenas para aba Adicionar"""
    socketio.emit('add_log', {'message': message, 'type': log_type})

def emit_task_log(message, log_type='info'):
    """Emite log apenas para aba Tarefas"""
    socketio.emit('task_log', {'message': message, 'type': log_type})

class MemberAdder:
    def __init__(self, api_id, api_hash, data_dir=None, members_file=None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.data_dir = data_dir
        self.members_file = members_file or MEMBERS_FILE

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
    
    def add_members(self, session_info, target_group, members_per_session, delay, socketio=None):
        """Adiciona membros em um grupo usando uma sessão"""
        cooldown = self._get_existing_cooldown(session_info)
        if cooldown:
            minutes = max(1, cooldown['seconds'] // 60)
            emit_log(
                f'Sessão {session_info.get("session_name")} em quarentena; pulando por ~{minutes} min.',
                'warning',
                socketio
            )
            return 0

        # FORÇA FLUSH IMEDIATO
        import threading
        thread_name = threading.current_thread().name
        sys.stdout.write(f'\n🔵 [ADD_MEMBERS] ===== INICIANDO ===== (Thread: {thread_name})\n')
        sys.stdout.flush()
        
        # EMITE LOG PARA INTERFACE
        if socketio:
            emit_log(f'🔵 Iniciando adição para {session_info["first_name"]}', 'info', socketio)
        
        sys.stdout.write(f'🔵 [ADD_MEMBERS] Sessão: {session_info["first_name"]}\n')
        sys.stdout.flush()
        sys.stdout.write(f'🔵 [ADD_MEMBERS] Grupo: {target_group}\n')
        sys.stdout.flush()
        sys.stdout.write(f'🔵 [ADD_MEMBERS] Membros: {members_per_session}\n')
        sys.stdout.flush()
        sys.stdout.write(f'🔵 [ADD_MEMBERS] Delay: {delay}\n')
        sys.stdout.flush()
        
        # Cria um novo event loop para esta thread
        sys.stdout.write(f'🔵 [ADD_MEMBERS] Criando event loop...\n')
        sys.stdout.flush()
        
        if socketio:
            emit_log(f'⚙️ Criando event loop...', 'info', socketio)
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            sys.stdout.write(f'🔵 [ADD_MEMBERS] Event loop criado!\n')
            sys.stdout.flush()
            
            if socketio:
                emit_log(f'✅ Event loop criado', 'success', socketio)
        except Exception as loop_error:
            sys.stdout.write(f'🔴 [ADD_MEMBERS] ERRO ao criar loop: {loop_error}\n')
            sys.stdout.flush()
            
            if socketio:
                emit_log(f'❌ Erro ao criar event loop: {loop_error}', 'error', socketio)
            return 0
        
        try:
            sys.stdout.write(f'🔵 [ADD_MEMBERS] Executando _add_async...\n')
            sys.stdout.flush()
            
            if socketio:
                emit_log(f'🔄 Processando membros...', 'info', socketio)
            
            result = loop.run_until_complete(self._add_async(session_info, target_group, members_per_session, delay, socketio))
            
            sys.stdout.write(f'🔵 [ADD_MEMBERS] _add_async completou! Resultado: {result}\n')
            sys.stdout.flush()
            
            if socketio:
                emit_log(f'✅ Processamento completo! Resultado: {result}', 'success', socketio)
            
            return result
        except Exception as e:
            sys.stdout.write(f'🔴 [ADD_MEMBERS] ERRO: {e}\n')
            sys.stdout.flush()
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            
            if socketio:
                emit_log(f'❌ Erro: {e}', 'error', socketio)
            
            return 0
        finally:
            sys.stdout.write(f'🔵 [ADD_MEMBERS] Fechando loop...\n')
            sys.stdout.flush()
            try:
                loop.close()
                sys.stdout.write(f'🔵 [ADD_MEMBERS] Loop fechado!\n')
                sys.stdout.flush()
            except Exception as close_error:
                sys.stdout.write(f'🔴 [ADD_MEMBERS] Erro ao fechar loop: {close_error}\n')
                sys.stdout.flush()
            sys.stdout.write(f'🔵 [ADD_MEMBERS] ===== FINALIZADO =====\n\n')
            sys.stdout.flush()
    
    async def _add_async(self, session_info, target_group, members_per_session, delay, socketio=None):
        """Adição assíncrona"""
        sys.stdout.write(f'🟢 [_ADD_ASYNC] ===== INICIANDO ASYNC =====\n')
        sys.stdout.flush()
        
        if socketio:
            emit_log(f'📥 Preparando para adicionar membros...', 'info', socketio)
        
        session_path = session_info.get('session_path')
        
        if not session_path:
            # Fallback para o método antigo
            session_path = os.path.join(SESSIONS_DIR, session_info['session_name'])
        
        sys.stdout.write(f'🟢 [_ADD_ASYNC] Session path: {session_path}\n')
        sys.stdout.flush()
        
        # Cria uma cópia temporária da sessão
        sys.stdout.write(f'🟢 [_ADD_ASYNC] Criando diretório temporário...\n')
        sys.stdout.flush()
        
        temp_dir = tempfile.mkdtemp()
        temp_session = os.path.join(temp_dir, 'temp_session')
        
        sys.stdout.write(f'🟢 [_ADD_ASYNC] Temp session: {temp_session}\n')
        sys.stdout.flush()
        
        try:
            # Copia o arquivo de sessão
            print(f'🟢 [_ADD_ASYNC] Copiando arquivo de sessão...')
            if os.path.exists(session_path + '.session'):
                shutil.copy2(session_path + '.session', temp_session + '.session')
                print(f'🟢 [_ADD_ASYNC] Arquivo de sessão copiado')
            else:
                print(f'🔴 [_ADD_ASYNC] Arquivo de sessão não encontrado!')
            
            from telethon import TelegramClient
            from telethon.sessions import SQLiteSession
            
            # Cria uma sessão customizada que não salva updates
            class ReadOnlySession(SQLiteSession):
                def set_update_state(self, *args, **kwargs):
                    pass  # Não faz nada
                
                def save(self):
                    pass  # Não salva
            
            print(f'🟢 [_ADD_ASYNC] Criando TelegramClient...')
            client = TelegramClient(
                ReadOnlySession(temp_session), 
                self.api_id, 
                self.api_hash
            )
            print(f'🟢 [_ADD_ASYNC] TelegramClient criado, conectando...')
            
            if socketio:
                emit_log(f'🔌 Conectando ao Telegram...', 'info', socketio)
            
            await client.connect()
            print(f'🟢 [_ADD_ASYNC] Conectado!')
            
            if socketio:
                emit_log(f'✅ Conectado ao Telegram', 'success', socketio)
            
            print(f'🟢 [_ADD_ASYNC] Verificando autorização...')
            if not await client.is_user_authorized():
                print(f'🔴 [_ADD_ASYNC] Sessão não autorizada!')
                if socketio:
                    emit_log(f'❌ Sessão não autorizada', 'error', socketio)
                return 0
            
            print(f'🟢 [_ADD_ASYNC] Sessão autorizada, continuando...')
            if socketio:
                emit_log(f'✅ Sessão autorizada', 'success', socketio)
            
            print(f'\n👤 Usando: {session_info["first_name"]} (@{session_info["username"]})')
            
            # Carrega membros pendentes
            print(f'🟢 [_ADD_ASYNC] Carregando membros...')
            if socketio:
                emit_log(f'📋 Carregando lista de membros...', 'info', socketio)
            
            members = self.load_members()
            pending = [m for m in members if not m.get('added', False)]
            print(f'🟢 [_ADD_ASYNC] {len(pending)} membros pendentes')
            
            if not pending:
                print('⚠️  Nenhum membro pendente para adicionar')
                if socketio:
                    emit_log(f'⚠️ Nenhum membro pendente', 'warning', socketio)
                return 0
            
            if socketio:
                emit_log(f'📊 {len(pending)} membros disponíveis', 'info', socketio)
            
            # Pega o grupo de origem dos membros (se tiver salvo)
            print(f'🟢 [_ADD_ASYNC] Buscando grupo de origem...')
            source_group = self.get_source_group()
            source_entity = None
            
            # Entra no grupo de origem para atualizar access_hash
            if source_group:
                print(f'🟢 [_ADD_ASYNC] Grupo de origem encontrado: {source_group}')
                if socketio:
                    emit_log(f'📥 Entrando no grupo de origem...', 'info', socketio)
                
                try:
                    print(f'📥 Entrando no grupo de origem para atualizar dados...')
                    try:
                        print(f'🟢 [_ADD_ASYNC] Tentando get_entity...')
                        source_entity = await client.get_entity(source_group)
                        print(f'🟢 [_ADD_ASYNC] get_entity OK!')
                    except Exception as get_error:
                        print(f'🟢 [_ADD_ASYNC] get_entity falhou: {get_error}, tentando entrar...')
                        # Tenta entrar
                        clean_link = source_group.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '')
                        if 'joinchat' in source_group or '+' in source_group:
                            from telethon.tl.functions.messages import ImportChatInviteRequest
                            invite_hash = clean_link.split('/')[-1].replace('+', '')
                            print(f'🟢 [_ADD_ASYNC] Entrando via ImportChatInviteRequest...')
                            await client(ImportChatInviteRequest(invite_hash))
                        else:
                            from telethon.tl.functions.channels import JoinChannelRequest
                            print(f'🟢 [_ADD_ASYNC] Entrando via JoinChannelRequest...')
                            await client(JoinChannelRequest(clean_link))
                        print(f'🟢 [_ADD_ASYNC] Tentando get_entity novamente...')
                        source_entity = await client.get_entity(source_group)
                        print(f'🟢 [_ADD_ASYNC] get_entity OK após entrar!')
                    
                    print(f'✅ Entrou no grupo de origem: {source_entity.title}')
                    if socketio:
                        emit_log(f'✅ Entrou no grupo de origem: {source_entity.title}', 'success', socketio)
                    
                    # Atualiza access_hash dos membros pendentes
                    print('🔄 Atualizando dados dos membros...')
                    if socketio:
                        emit_log(f'🔄 Atualizando dados dos membros...', 'info', socketio)
                    
                    to_add = pending[:members_per_session]
                    
                    print(f'🟢 [_ADD_ASYNC] Atualizando access_hash de {len(to_add)} membros...')
                    for idx, member in enumerate(to_add):
                        try:
                            user = await client.get_entity(member['id'])
                            member['access_hash'] = user.access_hash
                            if idx % 5 == 0:
                                print(f'🟢 [_ADD_ASYNC] Atualizado {idx+1}/{len(to_add)}...')
                        except:
                            pass
                    print(f'🟢 [_ADD_ASYNC] Atualização de access_hash completa!')
                    if socketio:
                        emit_log(f'✅ Dados atualizados', 'success', socketio)
                    
                except Exception as e:
                    print(f'⚠️  Não foi possível entrar no grupo de origem: {e}')
                    if socketio:
                        emit_log(f'⚠️ Não foi possível entrar no grupo de origem', 'warning', socketio)
            else:
                print(f'🟢 [_ADD_ASYNC] Nenhum grupo de origem configurado')
            
            # Pega o grupo alvo e entra se necessário
            print(f'🟢 [_ADD_ASYNC] Processando grupo destino...')
            if socketio:
                emit_log(f'🎯 Acessando grupo destino...', 'info', socketio)
            
            target = None
            is_member = False
            
            try:
                print(f'🟢 [_ADD_ASYNC] Tentando get_entity do grupo destino...')
                target = await client.get_entity(target_group)
                print(f'🟢 [_ADD_ASYNC] get_entity OK: {target.title}')
                
                # Verifica se realmente está no grupo
                try:
                    print(f'🟢 [_ADD_ASYNC] Verificando permissões...')
                    await client.get_permissions(target, 'me')
                    is_member = True
                    print(f'✅ Já está no grupo destino: {target.title}')
                except:
                    is_member = False
                    print(f'⚠️  Não está no grupo destino: {target.title}')
                    
            except Exception as get_error:
                print(f'⚠️  Grupo não encontrado ({get_error}), tentando entrar...')
            
            # Se não está no grupo, tenta entrar
            if not is_member:
                print(f'📥 Entrando no grupo destino...')
                try:
                    # Limpa e processa o link
                    clean_link = target_group.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '').strip()
                    
                    # Remove barra final se existir
                    if clean_link.endswith('/'):
                        clean_link = clean_link[:-1]
                    
                    print(f'🔗 Link processado: {clean_link}')
                    
                    if 'joinchat' in target_group or '+' in target_group:
                        # Grupo privado
                        from telethon.tl.functions.messages import ImportChatInviteRequest
                        invite_hash = clean_link.split('/')[-1].replace('+', '')
                        print(f'🔐 Entrando em grupo privado (hash: {invite_hash})...')
                        await client(ImportChatInviteRequest(invite_hash))
                    else:
                        # Grupo público
                        from telethon.tl.functions.channels import JoinChannelRequest
                        print(f'🌐 Entrando em grupo público: {clean_link}')
                        await client(JoinChannelRequest(clean_link))
                    
                    print(f'🟢 [_ADD_ASYNC] Aguardando 2s após entrar...')
                    await asyncio.sleep(2)  # Aguarda entrar
                    print('✅ Entrou no grupo destino com sucesso!')
                    if socketio:
                        emit_log(f'✅ Entrou no grupo destino', 'success', socketio)
                    
                    print(f'🟢 [_ADD_ASYNC] Pegando entity novamente...')
                    target = await client.get_entity(target_group)
                    print(f'🟢 [_ADD_ASYNC] Entity obtida!')
                except Exception as join_error:
                    print(f'❌ Erro ao entrar no grupo destino: {join_error}')
                    if socketio:
                        emit_log(f'❌ Erro ao entrar no grupo destino: {join_error}', 'error', socketio)
                    return 0
            
            print(f'🎯 Grupo destino: {target.title}')
            if socketio:
                emit_log(f'🎯 Grupo destino: {target.title}', 'success', socketio)
            
            print(f'🟢 [_ADD_ASYNC] Iniciando loop de adição...')
            if socketio:
                emit_log(f'🔄 Iniciando adição de membros...', 'info', socketio)
            
            added_count = 0
            to_add = pending[:members_per_session]
            print(f'🟢 [_ADD_ASYNC] Processando {len(to_add)} membros...')
            if socketio:
                emit_log(f'📊 Processando {len(to_add)} membros', 'info', socketio)
            
            for idx, member in enumerate(to_add, 1):
                print(f'🟢 [_ADD_ASYNC] Membro {idx}/{len(to_add)}: {member.get("first_name", "Unknown")}')
                try:
                    user_to_add = None
                    
                    # DELAY ANTES DE PROCESSAR CADA MEMBRO (evita flood)
                    print(f'🟢 [_ADD_ASYNC] Aguardando 2s antes de processar...')
                    await asyncio.sleep(2)
                    
                    # Tenta buscar o usuário de diferentes formas
                    member_name = member.get('first_name', 'Usuário')
                    
                    # MÉTODO 1: Por username
                    if member.get('username'):
                        try:
                            user_to_add = await client.get_entity(member['username'])
                            print(f'📍 Encontrado por username: @{member["username"]}')
                            if socketio:
                                emit_log(f'📍 Encontrado: @{member["username"]}', 'info', socketio)
                        except Exception as e:
                            print(f'⚠️ Username @{member["username"]} não encontrado: {str(e)[:50]}')
                    
                    # MÉTODO 2: Por ID + access_hash
                    if not user_to_add and member.get('id') and member.get('access_hash'):
                        try:
                            from telethon.tl.types import InputPeerUser
                            user_to_add = InputPeerUser(member['id'], member['access_hash'])
                            print(f'📍 Usando ID direto: {member_name} (ID: {member["id"]})')
                            if socketio:
                                emit_log(f'📍 Usando ID: {member_name}', 'info', socketio)
                        except Exception as e:
                            print(f'⚠️ Erro ao criar InputPeerUser: {str(e)[:50]}')
                    
                    # MÉTODO 3: Tenta buscar pelo ID (atualiza access_hash)
                    if not user_to_add and member.get('id'):
                        try:
                            print(f'🔄 Tentando atualizar dados de {member_name}...')
                            user_to_add = await client.get_entity(member['id'])
                            
                            # Atualiza o access_hash
                            if hasattr(user_to_add, 'access_hash'):
                                member['access_hash'] = user_to_add.access_hash
                                print(f'✅ Dados atualizados: {member_name}')
                                if socketio:
                                    emit_log(f'✅ Dados atualizados: {member_name}', 'success', socketio)
                        except Exception as e:
                            print(f'⚠️ Não conseguiu atualizar: {str(e)[:50]}')
                    
                    if not user_to_add:
                        print(f'❌ Não encontrado: {member_name} (ID: {member.get("id", "N/A")})')
                        if socketio:
                            emit_log(f'❌ Não encontrado: {member_name}', 'warning', socketio)
                        member['added'] = True
                        continue
                    
                    if not user_to_add:
                        print(f'⚠️  Usuário não encontrado, pulando...')
                        member['added'] = True
                        continue
                    
                    # DELAY ANTES DE ADICIONAR (evita flood)
                    await asyncio.sleep(3)
                    
                    # Adiciona o usuário ao grupo
                    add_success = False
                    try:
                        await client(InviteToChannelRequest(
                            target,
                            [user_to_add]
                        ))
                        add_success = True  # Se chegou aqui, adicionou com sucesso
                        print(f'✅ InviteToChannelRequest executado com sucesso')
                    except Exception as invite_error:
                        error_msg = str(invite_error)
                        
                        # Erro específico: tentando adicionar em chat comum
                        if "Cannot cast InputPeerChat" in error_msg:
                            print(f'⚠️  Erro: Grupo destino é um chat comum, não um canal/supergrupo')
                            print(f'💡 Solução: Use um supergrupo ao invés de chat comum')
                            member['added'] = True
                            continue
                        # Outros erros específicos que não devem parar o loop
                        elif "USER_PRIVACY_RESTRICTED" in error_msg:
                            print(f'⚠️  Privacidade restrita, pulando...')
                            member['added'] = True
                            continue
                        elif "USER_NOT_MUTUAL_CONTACT" in error_msg:
                            print(f'⚠️  Não é contato mútuo, pulando...')
                            member['added'] = True
                            continue
                        elif "USER_CHANNELS_TOO_MUCH" in error_msg:
                            print(f'⚠️  Usuário em muitos grupos, pulando...')
                            member['added'] = True
                            continue
                        else:
                            # Outros erros, re-lança para o except externo
                            raise
                    
                    # Se adicionou com sucesso, registra
                    if add_success:
                        added_count += 1
                        member['added'] = True
                        
                        name = member.get('first_name', 'Usuário')
                        username_info = f"(@{member['username']})" if member.get('username') else ""
                        emit_log(f'✅ [{added_count}/{members_per_session}] Adicionado: {name} {username_info}', 'success', socketio)
                        print(f'✅ Registrado: {name} {username_info}')
                    
                    # DELAY FINAL ENTRE ADIÇÕES (configurável)
                    await asyncio.sleep(delay)
                    
                except PeerFloodError:
                    print(f'\n⚠️  FLOOD! Sessão {session_info["first_name"]} bloqueada temporariamente')
                    
                    # Marca sessão em FLOOD por 3 dias (72 horas)
                    from datetime import datetime, timedelta
                    flood_until = datetime.now() + timedelta(days=3)
                    self.mark_session_flood(session_info['session_name'], flood_until)
                    
                    print(f'🕐 Sessão bloqueada até: {flood_until.strftime("%d/%m/%Y %H:%M")}')
                    print(f'💡 Pulando para próxima sessão...')
                    
                    # Salva o progresso removendo membros já adicionados
                    remaining_members = [m for m in members if not m.get('added', False)]
                    self.save_members(remaining_members)
                    removed_count = len(members) - len(remaining_members)
                    if removed_count > 0:
                        print(f'🗑️  Removidos {removed_count} membros do arquivo')
                    break  # Sai do loop de membros, mas retorna para continuar com próxima sessão
                    
                except UserPrivacyRestrictedError:
                    print(f'⚠️  Privacidade restrita, pulando...')
                    member['added'] = True
                    
                except UserNotMutualContactError:
                    print(f'⚠️  Não é contato mútuo, pulando...')
                    member['added'] = True
                    
                except UserChannelsTooMuchError:
                    print(f'⚠️  Usuário em muitos grupos, pulando...')
                    member['added'] = True
                    
                except FloodWaitError as e:
                    wait_seconds = e.seconds
                    wait_minutes = wait_seconds // 60
                    wait_hours = wait_minutes // 60
                    
                    if wait_hours > 0:
                        print(f'\n⏳ FLOOD: Aguardar {wait_hours}h {wait_minutes % 60}min')
                    elif wait_minutes > 0:
                        print(f'\n⏳ FLOOD: Aguardar {wait_minutes} minutos')
                    else:
                        print(f'\n⏳ FLOOD: Aguardar {wait_seconds} segundos')
                    
                    # Se for mais de 1 hora, marca a sessão em flood
                    if wait_seconds > 3600:
                        from datetime import datetime, timedelta
                        flood_until = datetime.now() + timedelta(seconds=wait_seconds)
                        self.mark_session_flood(session_info['session_name'], flood_until)
                        print(f'🕐 Sessão bloqueada até: {flood_until.strftime("%d/%m/%Y %H:%M")}')
                        print(f'💡 Pulando para próxima sessão...')
                        break
                    else:
                        # Se for pouco tempo, aguarda
                        await asyncio.sleep(wait_seconds)
                    
                except Exception as e:
                    error_msg = str(e)
                    
                    # Erros específicos
                    if "can't write" in error_msg.lower() or "chat write forbidden" in error_msg.lower():
                        print(f'❌ Sem permissão para adicionar membros neste grupo!')
                        print(f'💡 Solução: Torne esta conta admin do grupo ou use um grupo onde membros podem adicionar pessoas.')
                        break  # Para de tentar adicionar
                    
                    print(f'❌ Erro: {e}')
                    member['added'] = True
                    continue
            
            # Salva progresso final - Remove membros adicionados
            print(f'🟢 [_ADD_ASYNC] Salvando progresso...')
            remaining_members = [m for m in members if not m.get('added', False)]
            self.save_members(remaining_members)
            print(f'🟢 [_ADD_ASYNC] Progresso salvo!')
            
            removed_count = len(members) - len(remaining_members)
            if removed_count > 0:
                print(f'🗑️  Removidos {removed_count} membros do arquivo (já adicionados)')
            
            # SAI DO GRUPO DESTINO antes de desconectar
            if added_count > 0:  # Só sai se adicionou pelo menos 1 membro
                print(f'🚪 [_ADD_ASYNC] Saindo do grupo destino...')
                try:
                    from telethon.tl.functions.channels import LeaveChannelRequest
                    await client(LeaveChannelRequest(target))
                    await asyncio.sleep(2)  # Aguarda sair
                    print(f'✅ Saiu do grupo destino com sucesso!')
                    emit_log(f'🚪 Sessão saiu do grupo destino', 'info', socketio)
                except Exception as leave_error:
                    print(f'⚠️  Erro ao sair do grupo: {leave_error}')
                    # Não é crítico, continua mesmo se falhar
            
            # Desconecta corretamente
            print(f'🟢 [_ADD_ASYNC] Desconectando cliente...')
            try:
                if client.is_connected():
                    await client.disconnect()
                    await asyncio.sleep(0.5)  # Aguarda cleanup
                    print(f'🟢 [_ADD_ASYNC] Cliente desconectado!')
            except Exception as disc_error:
                print(f'🔴 [_ADD_ASYNC] Erro ao desconectar: {disc_error}')
            
            if added_count > 0:
                print(f'\n✅ Sessão finalizou: {added_count} membros adicionados')
            else:
                print(f'\n⚠️  Sessão finalizou: Nenhum membro adicionado (FLOOD ou sem permissão)')
            
            print(f'🟢 [_ADD_ASYNC] Retornando {added_count}')
            return added_count
            
        except Exception as e:
            print(f'\n❌ Erro na sessão: {e}')
            import traceback
            print(f'🔴 [_ADD_ASYNC] Traceback completo:')
            traceback.print_exc()
            
            # Desconecta em caso de erro
            print(f'🟢 [_ADD_ASYNC] Tentando desconectar após erro...')
            try:
                if client and client.is_connected():
                    await client.disconnect()
                    await asyncio.sleep(0.5)
                    print(f'🟢 [_ADD_ASYNC] Desconectado após erro!')
            except Exception as disc_error:
                print(f'🔴 [_ADD_ASYNC] Erro ao desconectar: {disc_error}')
            
            print(f'🟢 [_ADD_ASYNC] Retornando 0 após erro')
            return 0
        finally:
            # Aguarda um pouco antes de limpar
            print(f'🟢 [_ADD_ASYNC] Finally block - aguardando 1s...')
            await asyncio.sleep(1)
            
            # Remove arquivos temporários
            print(f'🟢 [_ADD_ASYNC] Removendo arquivos temporários...')
            try:
                shutil.rmtree(temp_dir)
                print(f'🟢 [_ADD_ASYNC] Arquivos temporários removidos!')
            except Exception as rm_error:
                print(f'🔴 [_ADD_ASYNC] Erro ao remover temp: {rm_error}')
            
            print(f'🟢 [_ADD_ASYNC] Finally block completo!')
    
    def save_members(self, members):
        """Salva membros"""
        atomic_write_json(self.members_file, members)
    
    def load_members(self):
        """Carrega membros"""
        if os.path.exists(self.members_file):
            return load_json_file(self.members_file, [])
        return []

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
                pass
        
        # Adiciona/atualiza flood
        floods[session_name] = flood_until.isoformat()
        
        # Salva
        atomic_write_json(flood_file, floods)
    
    def add_members_with_session(self, session_info, target_group, members, delay_between_adds=3, socketio=None):
        """Adiciona membros usando uma sessão específica (para tarefas)"""
        cooldown = self._get_existing_cooldown(session_info)
        if cooldown:
            minutes = max(1, cooldown['seconds'] // 60)
            emit_log(
                f'Sessão {session_info.get("session_name")} em quarentena; pulando por ~{minutes} min.',
                'warning',
                socketio
            )
            return 0

        # Ao invés de manipular arquivos, passa os membros diretamente para o método async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self._add_members_direct(session_info, target_group, members, delay_between_adds, socketio)
            )
            return result
        finally:
            loop.close()
    
    async def _add_members_direct(self, session_info, target_group, members, delay, socketio):
        """Adiciona membros diretamente sem manipular arquivos"""
        session_path = session_info.get('session_path')
        
        if not session_path:
            # Fallback para o método antigo
            session_path = os.path.join(SESSIONS_DIR, session_info['session_name'])
        
        # Cria cópia temporária
        temp_dir = tempfile.mkdtemp()
        temp_session = os.path.join(temp_dir, 'temp_session')
        
        try:
            if os.path.exists(session_path + '.session'):
                shutil.copy2(session_path + '.session', temp_session + '.session')
            
            from telethon import TelegramClient
            from telethon.sessions import SQLiteSession
            
            class ReadOnlySession(SQLiteSession):
                def set_update_state(self, *args, **kwargs):
                    pass
                def save(self):
                    pass
            
            client = TelegramClient(
                ReadOnlySession(temp_session),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            if not await client.is_user_authorized():
                emit_log('❌ Sessão não autorizada', 'error', socketio)
                return 0
            
            # Entra no grupo de origem para atualizar dados
            emit_log('📥 Entrando no grupo de origem para atualizar dados...', 'info', socketio)
            
            from extractor import MemberExtractor
            extractor = MemberExtractor(self.api_id, self.api_hash)
            source_group = extractor.get_source_group()
            
            if source_group:
                try:
                    source_entity = await client.get_entity(source_group)
                    emit_log(f'✅ Entrou no grupo de origem: {source_entity.title}', 'success', socketio)
                except:
                    emit_log(f'⚠️  Não foi possível entrar no grupo de origem: {str(e)}', 'warning', socketio)
            
            # Entra no grupo destino
            emit_log('📥 Entrando no grupo destino...', 'info', socketio)
            
            clean_link = target_group.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '').strip().strip('/')
            emit_log(f'🔗 Link processado: {clean_link}', 'info', socketio)
            
            target_entity = None
            
            if 'joinchat' in target_group or '+' in target_group:
                from telethon.tl.functions.messages import ImportChatInviteRequest
                invite_hash = clean_link.split('/')[-1].replace('+', '')
                result = await client(ImportChatInviteRequest(invite_hash))
                await asyncio.sleep(2)
                if hasattr(result, 'chats') and result.chats:
                    target_entity = result.chats[0]
            else:
                try:
                    target_entity = await client.get_entity('@' + clean_link)
                    emit_log(f'✅ Encontrado: @{clean_link}', 'success', socketio)
                except:
                    from telethon.tl.functions.channels import JoinChannelRequest
                    emit_log(f'🌐 Entrando em grupo público: {clean_link}', 'info', socketio)
                    await client(JoinChannelRequest('@' + clean_link))
                    await asyncio.sleep(2)
                    target_entity = await client.get_entity('@' + clean_link)
                    emit_log(f'✅ Entrou no grupo destino com sucesso!', 'success', socketio)
            
            if not target_entity:
                raise Exception(f"Não foi possível entrar no grupo: {target_group}")
            
            emit_log(f'🎯 Grupo destino: {target_entity.title}', 'success', socketio)
            
            # Adiciona membros
            added_count = 0
            
            for member in members:
                try:
                    # Tenta por username primeiro
                    user_to_add = None
                    
                    if member.get('username'):
                        try:
                            user_to_add = await client.get_entity(member['username'])
                            emit_log(f'📍 Encontrado por username: @{member["username"]}', 'info', socketio)
                        except:
                            pass
                    
                    if not user_to_add and member.get('id') and member.get('access_hash'):
                        try:
                            from telethon.tl.types import InputPeerUser
                            user_to_add = InputPeerUser(member['id'], member['access_hash'])
                        except:
                            pass
                    
                    if not user_to_add:
                        emit_log(f'⚠️  Não foi possível encontrar {member.get("first_name")}: {member.get("id")}', 'warning', socketio)
                        continue
                    
                    # Adiciona
                    await client(InviteToChannelRequest(target_entity, [user_to_add]))
                    
                    # Verifica se realmente adicionou
                    await asyncio.sleep(2)
                    try:
                        is_member = await client.get_permissions(target_entity, user_to_add)
                        if is_member and is_member.is_chat:
                            added_count += 1
                            name = member.get('first_name', 'Usuário')
                            username_info = f"(@{member['username']})" if member.get('username') else ""
                            emit_log(f'✅ [{added_count}/{len(members)}] Adicionado: {name} {username_info}', 'success', socketio)
                        else:
                            emit_log(f'⚠️  FALSO POSITIVO: {member.get("first_name")} - Telegram rejeitou', 'warning', socketio)
                    except:
                        added_count += 1
                        name = member.get('first_name', 'Usuário')
                        username_info = f"(@{member['username']})" if member.get('username') else ""
                        emit_log(f'✅ [{added_count}/{len(members)}] Adicionado: {name} {username_info}', 'success', socketio)
                    
                    await asyncio.sleep(delay)
                    
                except PeerFloodError:
                    emit_log('🚫 FLOOD detectado! Sessão bloqueada por 3 dias.', 'error', socketio)
                    from datetime import datetime, timedelta
                    flood_until = datetime.now() + timedelta(days=3)
                    self.mark_session_flood(session_info['session_name'], flood_until)
                    break
                    
                except Exception as e:
                    emit_log(f'❌ Erro: {str(e)}', 'error', socketio)
                    continue
            
            await client.disconnect()
            await asyncio.sleep(1)
            
            return added_count
            
        except Exception as e:
            emit_log(f'❌ Erro na sessão: {str(e)}', 'error', socketio)
            return 0
        finally:
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    async def _add_with_session_async(self, session_info, target_group, members, delay_between_adds, socketio):
        """Adiciona membros de forma assíncrona"""
        session_path = session_info.get('session_path')
        
        if not session_path:
            # Fallback para o método antigo
            session_path = os.path.join(SESSIONS_DIR, session_info['session_name'])
        
        # Cria cópia temporária
        temp_dir = tempfile.mkdtemp()
        temp_session = os.path.join(temp_dir, 'temp_session')
        
        try:
            if os.path.exists(session_path + '.session'):
                shutil.copy2(session_path + '.session', temp_session + '.session')
            
            from telethon import TelegramClient
            from telethon.sessions import SQLiteSession
            
            class ReadOnlySession(SQLiteSession):
                def set_update_state(self, *args, **kwargs):
                    pass
                def save(self):
                    pass
            
            client = TelegramClient(
                ReadOnlySession(temp_session),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            if not await client.is_user_authorized():
                if socketio:
                    socketio.emit('log', {'message': f'❌ Sessão não autorizada', 'type': 'error'})
                return 0
            
            # Entra no grupo destino - SEMPRE processa o link corretamente
            if socketio:
                socketio.emit('log', {'message': f'🔐 Processando grupo destino...', 'type': 'info'})
            
            # Limpa e processa o link
            clean_link = target_group.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '').strip().strip('/')
            
            if socketio:
                socketio.emit('log', {'message': f'🔗 Link processado: {clean_link}', 'type': 'info'})
            
            target_entity = None
            
            if 'joinchat' in target_group or '+' in target_group:
                # Grupo privado
                from telethon.tl.functions.messages import ImportChatInviteRequest
                invite_hash = clean_link.split('/')[-1].replace('+', '')
                if socketio:
                    socketio.emit('log', {'message': f'🔐 Entrando em grupo privado (hash: {invite_hash})...', 'type': 'info'})
                try:
                    result = await client(ImportChatInviteRequest(invite_hash))
                    await asyncio.sleep(2)
                    if hasattr(result, 'chats') and result.chats:
                        target_entity = result.chats[0]
                except Exception as e:
                    # Pode já estar no grupo
                    if socketio:
                        socketio.emit('log', {'message': f'ℹ️ Tentando pegar grupo privado...', 'type': 'info'})
                    try:
                        target_entity = await client.get_entity(target_group)
                    except:
                        raise Exception(f"Não foi possível acessar grupo privado: {str(e)}")
            else:
                # Grupo público - tenta múltiplos formatos
                if socketio:
                    socketio.emit('log', {'message': f'🌐 Acessando grupo público...', 'type': 'info'})
                
                # Tenta com @username
                try:
                    target_entity = await client.get_entity('@' + clean_link)
                    if socketio:
                        socketio.emit('log', {'message': f'✅ Encontrado: @{clean_link}', 'type': 'success'})
                except:
                    # Tenta entrar com JoinChannelRequest
                    try:
                        from telethon.tl.functions.channels import JoinChannelRequest
                        if socketio:
                            socketio.emit('log', {'message': f'🚪 Entrando em @{clean_link}...', 'type': 'info'})
                        await client(JoinChannelRequest('@' + clean_link))
                        await asyncio.sleep(2)
                        target_entity = await client.get_entity('@' + clean_link)
                        if socketio:
                            socketio.emit('log', {'message': f'✅ Entrou com sucesso!', 'type': 'success'})
                    except Exception as e:
                        if socketio:
                            socketio.emit('log', {'message': f'❌ Erro ao entrar: {str(e)}', 'type': 'error'})
                        raise Exception(f"Não foi possível entrar no grupo: {str(e)}")
            
            if not target_entity:
                raise Exception(f"Não foi possível acessar o grupo: {target_group}")
            
            if socketio:
                socketio.emit('log', {'message': f'📍 Grupo destino: {target_entity.title}', 'type': 'success'})
            
            # Verifica se está no grupo e tem permissões
            try:
                my_permissions = await client.get_permissions(target_entity, 'me')
                
                if socketio:
                    socketio.emit('log', {'message': f'Verificando permissoes no grupo...', 'type': 'info'})
                
                # Verifica se é membro do grupo
                if not my_permissions or not my_permissions.is_chat:
                    if socketio:
                        socketio.emit('log', {'message': f'Sessao nao esta no grupo, entrando...', 'type': 'warning'})
                    
                    # Força entrada no grupo
                    clean_link = target_group.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '').strip().strip('/')
                    from telethon.tl.functions.channels import JoinChannelRequest
                    await client(JoinChannelRequest('@' + clean_link))
                    await asyncio.sleep(3)
                    
                    # Verifica novamente
                    my_permissions = await client.get_permissions(target_entity, 'me')
                    if socketio:
                        socketio.emit('log', {'message': f'Entrou no grupo com sucesso!', 'type': 'success'})
                
                # Verifica se pode adicionar membros
                if my_permissions.is_admin:
                    if socketio:
                        socketio.emit('log', {'message': f'Sessao e ADMIN no grupo', 'type': 'success'})
                elif hasattr(target_entity, 'default_banned_rights') and target_entity.default_banned_rights:
                    if target_entity.default_banned_rights.invite_users:
                        if socketio:
                            socketio.emit('log', {'message': f'AVISO: Grupo restringe adicao de membros por nao-admins', 'type': 'warning'})
                    else:
                        if socketio:
                            socketio.emit('log', {'message': f'Grupo permite adicao de membros', 'type': 'success'})
                else:
                    if socketio:
                        socketio.emit('log', {'message': f'Grupo permite adicao de membros', 'type': 'success'})
                        
            except Exception as perm_error:
                if socketio:
                    socketio.emit('log', {'message': f'Erro ao verificar permissoes: {str(perm_error)}', 'type': 'warning'})
            
            added_count = 0
            members_to_remove = []  # Lista de membros para remover do arquivo
            
            # Adiciona membros
            for member in members:
                try:
                    # Verifica se usuário já está no grupo
                    try:
                        is_participant = await client.get_permissions(target_entity, member.get('id'))
                        if is_participant:
                            if socketio:
                                socketio.emit('log', {
                                    'message': f'⏭️ Já no grupo: {member.get("first_name", "Unknown")} - REMOVENDO DO ARQUIVO',
                                    'type': 'info'
                                })
                            
                            # Marca para remoção IMEDIATA
                            members_to_remove.append(member)
                            
                            # Remove do arquivo AGORA
                            all_members = self.load_members()
                            all_members = [m for m in all_members if m.get('id') != member.get('id')]
                            self.save_members(all_members)
                            
                            if socketio:
                                socketio.emit('log', {
                                    'message': f'🗑️ Removido do arquivo: {member.get("first_name", "Unknown")}',
                                    'type': 'success'
                                })
                            
                            continue
                    except:
                        # Não está no grupo, pode adicionar
                        pass
                    
                    # Tenta adicionar
                    user_to_add = None
                    
                    # PRIORIDADE 1: Tenta por username
                    if member.get('username'):
                        try:
                            user_to_add = await client.get_entity(member['username'])
                            if socketio:
                                socketio.emit('log', {'message': f'✅ Resolvido por username: @{member["username"]}', 'type': 'info'})
                        except:
                            pass
                    
                    # PRIORIDADE 2: Usa ID + access_hash diretamente
                    if not user_to_add and member.get('id') and member.get('access_hash'):
                        try:
                            from telethon.tl.types import InputPeerUser
                            user_to_add = InputPeerUser(member['id'], member['access_hash'])
                            if socketio:
                                socketio.emit('log', {'message': f'✅ Resolvido por ID+hash: {member.get("first_name")}', 'type': 'info'})
                        except Exception as e:
                            if socketio:
                                socketio.emit('log', {'message': f'⚠️ Falha ID+hash: {str(e)}', 'type': 'warning'})
                    
                    # PRIORIDADE 3: Entra no grupo de origem para pegar o usuário
                    if not user_to_add and member.get('id'):
                        try:
                            # Pega o link do grupo de origem
                            from extractor import MemberExtractor
                            api_id, api_hash = self.api_id, self.api_hash
                            extractor = MemberExtractor(api_id, api_hash)
                            source_group = extractor.get_source_group()
                            
                            if source_group:
                                if socketio:
                                    socketio.emit('log', {'message': f'🔄 Entrando no grupo de origem para resolver: {member.get("first_name")}', 'type': 'info'})
                                
                                # Entra no grupo de origem
                                try:
                                    source_entity = await client.get_entity(source_group)
                                except:
                                    # Tenta entrar
                                    clean_source = source_group.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '').strip().strip('/')
                                    try:
                                        source_entity = await client.get_entity('@' + clean_source)
                                    except:
                                        from telethon.tl.functions.channels import JoinChannelRequest
                                        await client(JoinChannelRequest('@' + clean_source))
                                        await asyncio.sleep(2)
                                        source_entity = await client.get_entity('@' + clean_source)
                                
                                # Agora busca o usuário no grupo de origem
                                async for participant in client.iter_participants(source_entity, limit=None):
                                    if participant.id == member.get('id'):
                                        user_to_add = participant
                                        if socketio:
                                            socketio.emit('log', {'message': f'✅ Encontrado no grupo de origem: {member.get("first_name")}', 'type': 'success'})
                                        break
                        except Exception as source_error:
                            if socketio:
                                socketio.emit('log', {'message': f'⚠️ Erro ao buscar no grupo de origem: {str(source_error)}', 'type': 'warning'})
                    
                    if not user_to_add:
                        if socketio:
                            socketio.emit('log', {'message': f'❌ Não foi possível resolver: {member.get("first_name", "Unknown")}', 'type': 'error'})
                        member['added'] = True
                        continue
                    
                    # Adiciona ao grupo
                    await client(InviteToChannelRequest(target_entity, [user_to_add]))
                    
                    added_count += 1
                    member['added'] = True
                    
                    if socketio:
                        socketio.emit('log', {
                            'message': f'✅ Adicionado: {member.get("first_name", "Unknown")} (@{member.get("username", "sem username")})',
                            'type': 'success'
                        })
                    
                    # Delay
                    await asyncio.sleep(delay_between_adds)
                    
                except PeerFloodError:
                    if socketio:
                        socketio.emit('log', {'message': f'🚫 FLOOD detectado! Sessão bloqueada por 3 dias.', 'type': 'error'})
                    
                    from datetime import datetime, timedelta
                    flood_until = datetime.now() + timedelta(days=3)
                    self.mark_session_flood(session_info['session_name'], flood_until)
                    break
                
                except Exception as e:
                    import traceback
                    error_msg = str(e)
                    error_trace = traceback.format_exc()
                    error_type = type(e).__name__
                    
                    # Log no arquivo
                    log_error(f"ERRO AO ADICIONAR MEMBRO: {error_msg}")
                    log_error(f"TIPO: {error_type}")
                    
                    # Tratamento específico por tipo de erro
                    
                    # 1. ChatWriteForbiddenError - Sem permissão
                    if "ChatWriteForbiddenError" in error_type or "can't write" in error_msg.lower():
                        if socketio:
                            socketio.emit('log', {
                                'message': f'ERRO: Sessao sem permissao no grupo. Pode ser: 1) Sessao nao esta no grupo, 2) Sessao e muito nova, 3) Grupo restringe adicoes',
                                'type': 'error'
                            })
                        # Para esta sessão
                        break
                    
                    # 2. FROZEN_METHOD_INVALID - Conta congelada
                    elif "FROZEN_METHOD_INVALID" in error_msg or "FloodError" in error_type:
                        if socketio:
                            socketio.emit('log', {
                                'message': f'ERRO: Conta CONGELADA pelo Telegram. Nao pode adicionar membros temporariamente.',
                                'type': 'error'
                            })
                        # Marca como flood
                        from datetime import datetime, timedelta
                        flood_until = datetime.now() + timedelta(days=3)
                        self.mark_session_flood(session_info['session_name'], flood_until)
                        break
                    
                    # 3. UserIdInvalidError - ID inválido
                    elif "UserIdInvalidError" in error_type or "Invalid object ID" in error_msg:
                        if socketio:
                            socketio.emit('log', {
                                'message': f'ERRO: ID do usuario invalido. Access_hash pode estar expirado. Tentando buscar no grupo de origem...',
                                'type': 'warning'
                            })
                        # Marca como adicionado para não tentar novamente com este método
                        member['added'] = True
                        continue
                    
                    # 4. Outros erros
                    else:
                        if socketio:
                            socketio.emit('log', {
                                'message': f'ERRO DESCONHECIDO: {error_type}: {error_msg}',
                                'type': 'error'
                            })
                        member['added'] = True
                        continue
                    
                except FloodWaitError as e:
                    wait_seconds = e.seconds
                    if socketio:
                        socketio.emit('log', {'message': f'⏳ FLOOD: Aguardar {wait_seconds}s', 'type': 'warning'})
                    
                    if wait_seconds > 3600:
                        from datetime import datetime, timedelta
                        flood_until = datetime.now() + timedelta(seconds=wait_seconds)
                        self.mark_session_flood(session_info['session_name'], flood_until)
                        break
                    else:
                        await asyncio.sleep(wait_seconds)
                        
                except Exception as e:
                    if socketio:
                        socketio.emit('log', {'message': f'❌ Erro: {str(e)}', 'type': 'error'})
                    member['added'] = True
                    continue
            
            # Salva progresso
            all_members = self.load_members()
            remaining = [m for m in all_members if not m.get('added', False)]
            self.save_members(remaining)
            
            # Desconecta corretamente
            try:
                if client.is_connected():
                    await client.disconnect()
                    await asyncio.sleep(0.5)  # Aguarda cleanup
            except:
                pass
            
            return added_count
            
        except Exception as e:
            if socketio:
                socketio.emit('log', {'message': f'❌ Erro na sessão: {str(e)}', 'type': 'error'})
            
            # Desconecta em caso de erro
            try:
                if client and client.is_connected():
                    await client.disconnect()
                    await asyncio.sleep(0.5)
            except:
                pass
            
            return 0
        finally:
            # Aguarda um pouco antes de limpar
            await asyncio.sleep(1)
            
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
