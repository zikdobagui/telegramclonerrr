from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest, JoinChannelRequest
from telethon.tl.types import ChannelParticipantsSearch
import json
import os
import asyncio
import shutil
import tempfile
import logging
from datetime import datetime, timedelta, timezone
from config import SESSIONS_DIR, MEMBERS_FILE
from data_store import atomic_write_json, load_json_file

# Suprime warnings de reconexão do Telethon
logging.getLogger('telethon').setLevel(logging.ERROR)

class MemberExtractor:
    def __init__(self, api_id, api_hash, data_dir=None, members_file=None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.data_dir = data_dir
        self.members_file = members_file or MEMBERS_FILE
        self.progress_callback = None

    def _normalize_group_id(self, value):
        """Converte IDs -100... para o ID interno usado pelas entidades."""
        text = str(value or '').strip()
        if not text:
            return None

        try:
            numeric = int(text)
        except Exception:
            return None

        if text.startswith('-100'):
            try:
                return int(text[4:])
            except Exception:
                return abs(numeric)

        return abs(numeric)
    
    def set_progress_callback(self, callback):
        """Define callback para progresso em tempo real"""
        self.progress_callback = callback
    
    def extract_members(self, session_info, group_link, filters=None):
        """Extrai membros de um grupo"""
        # Cria um novo event loop para esta thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(self._extract_async(session_info, group_link, filters or {}))
            return result
        finally:
            loop.close()
    
    async def _extract_async(self, session_info, group_link, filters=None):
        """Extração assíncrona"""
        filters = filters or {}
        # CORRIGIDO: Usa o caminho completo da sessão se fornecido
        if 'session_path' in session_info:
            session_path = session_info['session_path']
        else:
            # Fallback para o método antigo
            session_path = os.path.join(SESSIONS_DIR, session_info['session_name'])
        
        # Usa a sessão diretamente (mesmo método da validação)
        try:
            from telethon import TelegramClient
            
            # Conecta diretamente na sessão original (igual à validação)
            client = TelegramClient(
                session_path, 
                self.api_id, 
                self.api_hash
            )
            
            await client.connect()
            
            # TESTA SE A SESSÃO ESTÁ FUNCIONANDO
            try:
                if self.progress_callback:
                    self.progress_callback('info', '🔐 Testando sessão...')
                
                # Verifica se está autorizado
                if not await client.is_user_authorized():
                    if self.progress_callback:
                        self.progress_callback('error', '❌ SESSÃO NÃO AUTORIZADA')
                        self.progress_callback('error', '⚠️ Esta sessão precisa fazer login novamente')
                    return []
                
                me = await client.get_me()
                
                if not me:
                    if self.progress_callback:
                        self.progress_callback('error', '❌ SESSÃO INVÁLIDA: get_me() retornou None')
                    return []
                
                if self.progress_callback:
                    session_display = me.first_name or me.username or str(me.id)
                    self.progress_callback('success', f'✅ Sessão válida: {session_display} (ID: {me.id})')
                    self.progress_callback('info', f'🔍 Extraindo com: {session_display}')
                    
            except Exception as test_error:
                error_msg = str(test_error)
                
                if 'AUTH_KEY_UNREGISTERED' in error_msg or 'The key is not registered' in error_msg:
                    if self.progress_callback:
                        self.progress_callback('error', '❌ SESSÃO BANIDA/EXPIRADA')
                        self.progress_callback('error', '⚠️ Esta sessão foi desconectada pelo Telegram')
                        self.progress_callback('error', '💡 Você precisa criar uma nova sessão com este número')
                    return []
                elif 'USER_DEACTIVATED' in error_msg:
                    if self.progress_callback:
                        self.progress_callback('error', '❌ CONTA DESATIVADA')
                        self.progress_callback('error', '⚠️ Esta conta foi desativada pelo Telegram')
                    return []
                else:
                    if self.progress_callback:
                        self.progress_callback('error', f'❌ Erro ao testar sessão: {error_msg}')
                    return []
            
            # Limpa o link primeiro
            original_link = group_link.strip()
            clean_link = original_link
            clean_link = clean_link.replace('https://t.me/', '').replace('http://t.me/', '')
            clean_link = clean_link.replace('https://telegram.me/', '').replace('http://telegram.me/', '')
            clean_link = clean_link.replace('@', '').strip('/')
            
            if self.progress_callback:
                self.progress_callback('info', f'🔗 Link processado: {clean_link}')
            
            # Tenta pegar a entidade do grupo primeiro
            group = None
            last_error = None
            
            # Verifica se é um ID numérico (começa com -100)
            is_numeric_id = clean_link.startswith('-100') or (clean_link.replace('-', '').isdigit() and len(clean_link) > 5)
            
            if is_numeric_id:
                if self.progress_callback:
                    self.progress_callback('info', f'🔢 Detectado ID numérico: {clean_link}')
                try:
                    group = await client.get_entity(int(clean_link))
                    if self.progress_callback:
                        self.progress_callback('success', f'✅ Grupo encontrado por ID: {group.title}')
                except Exception as e:
                    last_error = str(e)
                    if self.progress_callback:
                        self.progress_callback('error', f'❌ Erro ao buscar por ID: {last_error}')

                if not group:
                    normalized_group_id = self._normalize_group_id(clean_link)
                    if self.progress_callback:
                        self.progress_callback('info', '🔎 Procurando esse ID nos diálogos da sessão...')
                        self.progress_callback('info', 'ℹ️ Para grupo privado, a sessão precisa estar no grupo ou ter o chat no cache.')

                    try:
                        async for dialog in client.iter_dialogs():
                            entity = dialog.entity
                            entity_id = getattr(entity, 'id', None)
                            dialog_id = getattr(dialog, 'id', None)
                            possible_ids = {
                                str(entity_id or ''),
                                f'-100{entity_id}' if entity_id else '',
                                str(dialog_id or '')
                            }

                            if str(normalized_group_id) in possible_ids or str(clean_link) in possible_ids:
                                group = entity
                                if self.progress_callback:
                                    title = getattr(dialog, 'title', None) or getattr(entity, 'title', None) or clean_link
                                    self.progress_callback('success', f'✅ Grupo privado encontrado nos diálogos: {title}')
                                break
                    except Exception as e:
                        last_error = str(e)
                        if self.progress_callback:
                            self.progress_callback('warning', f'⚠️ Busca por ID nos diálogos falhou: {last_error}')
            
            # Se não é ID ou falhou, tenta como username
            if not group:
                # Lista de tentativas em ordem
                attempts = [
                    ('Link direto', clean_link),
                    ('Com @', f'@{clean_link}'),
                    ('Com t.me/', f't.me/{clean_link}'),
                    ('Link original', original_link),
                ]
                
                # Se for link de convite privado
                if 'joinchat' in original_link or '+' in original_link:
                    if self.progress_callback:
                        self.progress_callback('info', '🔐 Detectado link de convite privado')
                    
                    try:
                        from telethon.tl.functions.messages import ImportChatInviteRequest
                        invite_hash = original_link.split('/')[-1].replace('+', '')
                        
                        if self.progress_callback:
                            self.progress_callback('info', f'� Entrando com hash: {invite_hash}')
                        
                        result = await client(ImportChatInviteRequest(invite_hash))
                        await asyncio.sleep(2)
                        
                        if hasattr(result, 'chats') and result.chats:
                            group = result.chats[0]
                            if self.progress_callback:
                                self.progress_callback('success', f'✅ Entrou no grupo: {group.title}')
                    except Exception as e:
                        last_error = str(e)
                        if self.progress_callback:
                            self.progress_callback('error', f'❌ Erro ao entrar no grupo privado: {last_error}')
                else:
                    # Grupo público - tenta diferentes formatos
                    for attempt_name, attempt_link in attempts:
                        try:
                            if self.progress_callback:
                                self.progress_callback('info', f'� Tentativa: {attempt_name} ({attempt_link})')
                            
                            group = await client.get_entity(attempt_link)
                            
                            if group:
                                if self.progress_callback:
                                    self.progress_callback('success', f'✅ Grupo encontrado: {group.title}')
                                break
                        except Exception as e:
                            last_error = str(e)
                            if self.progress_callback:
                                self.progress_callback('warning', f'⚠️ {attempt_name} falhou: {last_error}')
                            continue
                    
                    # Se não conseguiu com get_entity, tenta entrar primeiro
                    if not group:
                        if self.progress_callback:
                            self.progress_callback('info', '🔄 Tentando entrar no grupo antes de extrair...')
                        
                        for attempt_name, attempt_link in attempts:
                            try:
                                if self.progress_callback:
                                    self.progress_callback('info', f'🚪 Entrando via: {attempt_name}')
                                
                                await client(JoinChannelRequest(attempt_link))
                                await asyncio.sleep(2)
                                group = await client.get_entity(attempt_link)
                                
                                if group:
                                    if self.progress_callback:
                                        self.progress_callback('success', f'✅ Entrou e encontrou: {group.title}')
                                    break
                            except Exception as e:
                                last_error = str(e)
                                continue
                    
                    # Última tentativa: buscar nos diálogos (conversas)
                    if not group:
                        if self.progress_callback:
                            self.progress_callback('info', '🔍 Buscando grupo nas suas conversas...')
                        
                        try:
                            search_terms = [clean_link.lower(), original_link.lower()]
                            
                            async for dialog in client.iter_dialogs():
                                # Verifica se é um grupo/canal
                                if hasattr(dialog.entity, 'megagroup') or hasattr(dialog.entity, 'broadcast'):
                                    # Busca por título
                                    if any(term in dialog.title.lower() for term in search_terms):
                                        group = dialog.entity
                                        if self.progress_callback:
                                            self.progress_callback('success', f'✅ Grupo encontrado nas conversas: {dialog.title}')
                                        break
                                    
                                    # Busca por username
                                    if hasattr(dialog.entity, 'username') and dialog.entity.username:
                                        if any(term in dialog.entity.username.lower() for term in search_terms):
                                            group = dialog.entity
                                            if self.progress_callback:
                                                self.progress_callback('success', f'✅ Grupo encontrado nas conversas: {dialog.title}')
                                            break
                        except Exception as e:
                            last_error = str(e)
                            if self.progress_callback:
                                self.progress_callback('warning', f'⚠️ Busca em conversas falhou: {last_error}')
            
            if not group:
                error_msg = f"❌ Não foi possível acessar o grupo.\n\n"
                error_msg += f"📋 DICAS:\n"
                error_msg += f"• Verifique se o link/username está correto\n"
                error_msg += f"• Tente usar o ID numérico do grupo (ex: -1001234567890)\n"
                error_msg += f"• Para pegar o ID: encaminhe uma mensagem do grupo para @userinfobot\n"
                error_msg += f"• Certifique-se que você está no grupo\n"
                error_msg += f"• O username pode ter sido alterado\n\n"
                error_msg += f"🔴 Último erro: {last_error}"
                
                if self.progress_callback:
                    self.progress_callback('error', error_msg)
                
                raise Exception(error_msg)
            
            if self.progress_callback:
                self.progress_callback('success', f'📊 Grupo: {group.title}')
            
            # Pega lista de admins e dono
            if self.progress_callback:
                self.progress_callback('info', '🔍 Identificando admins e dono...')
            
            from telethon.tl.types import (
                ChannelParticipantAdmin, 
                ChannelParticipantCreator,
                ChatParticipantAdmin,
                ChatParticipantCreator,
                ChannelParticipantsAdmins
            )
            
            admin_ids = set()
            try:
                async def collect_admins():
                    found_admins = set()
                    async for participant in client.iter_participants(group, filter=ChannelParticipantsAdmins):
                        if hasattr(participant, 'participant'):
                            if isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator, ChatParticipantAdmin, ChatParticipantCreator)):
                                found_admins.add(participant.id)
                        else:
                            found_admins.add(participant.id)
                    return found_admins

                admin_ids = await asyncio.wait_for(collect_admins(), timeout=20)
            except Exception as admin_error:
                if self.progress_callback:
                    self.progress_callback('warning', f'⚠️ Não consegui listar admins diretamente: {str(admin_error)}')
                    self.progress_callback('info', 'ℹ️ Continuando extração sem bloquear por isso...')
            
            if self.progress_callback:
                self.progress_callback('info', f'🛡️ {len(admin_ids)} admins/dono identificados')
            
            all_participants = []
            
            if self.progress_callback:
                self.progress_callback('info', '📥 Iniciando extração de membros...')
                self.progress_callback('info', '💡 Para grupos grandes, pode levar alguns minutos...')
            
            # Tenta extrair todos os membros usando diferentes métodos
            try:
                count = 0
                seen_ids = set()  # Para evitar duplicatas
                
                # Método 1: Extração normal (pega até 10k)
                if self.progress_callback:
                    self.progress_callback('info', '🔄 Método 1: Extração direta...')
                
                offset = 0
                limit = 200
                page = 1

                while True:
                    if self.progress_callback:
                        self.progress_callback('info', f'📄 Buscando página {page} de membros... (offset {offset})')

                    try:
                        participants = await asyncio.wait_for(
                            client(GetParticipantsRequest(
                                channel=group,
                                filter=ChannelParticipantsSearch(''),
                                offset=offset,
                                limit=limit,
                                hash=0
                            )),
                            timeout=45
                        )
                    except asyncio.TimeoutError:
                        if self.progress_callback:
                            self.progress_callback('warning', '⏱️ Telegram demorou demais para responder essa página. Parando com o que já foi coletado.')
                        break
                    except Exception as page_error:
                        if self.progress_callback:
                            self.progress_callback('warning', f'⚠️ Não consegui buscar a página {page}: {str(page_error)}')
                        break

                    users = getattr(participants, 'users', []) or []
                    if not users:
                        if self.progress_callback:
                            self.progress_callback('info', '📭 Nenhum membro novo retornado nessa página.')
                        break

                    new_in_page = 0
                    for user in users:
                        if user.id not in seen_ids:
                            all_participants.append(user)
                            seen_ids.add(user.id)
                            count += 1
                            new_in_page += 1

                    if self.progress_callback:
                        total_hint = getattr(participants, 'count', None)
                        total_text = f' de ~{total_hint}' if total_hint else ''
                        self.progress_callback('info', f'📥 Página {page}: +{new_in_page} membros | Total: {count}{total_text}')

                    if len(users) < limit or new_in_page == 0:
                        break

                    offset += len(users)
                    page += 1
                    await asyncio.sleep(0.35)
                
                if self.progress_callback:
                    self.progress_callback('info', f'✅ Método 1 completo: {len(all_participants)} membros')
                
                # Se pegou menos de 10k, já tem todos
                if len(all_participants) < 10000:
                    if self.progress_callback:
                        self.progress_callback('success', f'✅ Extração completa! Total: {len(all_participants)} membros')
                else:
                    # Método 2: Busca por letras para pegar membros além dos 10k
                    if self.progress_callback:
                        self.progress_callback('info', '🔄 Método 2: Buscando membros adicionais por filtro...')
                    
                    # Busca por cada letra do alfabeto
                    search_queries = list('abcdefghijklmnopqrstuvwxyz') + list('0123456789')
                    
                    for query in search_queries:
                        try:
                            query_count = 0
                            async for user in client.iter_participants(group, search=query, limit=None):
                                if user.id not in seen_ids:
                                    all_participants.append(user)
                                    seen_ids.add(user.id)
                                    count += 1
                                    query_count += 1
                            
                            if query_count > 0 and self.progress_callback:
                                self.progress_callback('info', f'📥 Letra "{query}": +{query_count} novos | Total: {count}')
                            
                            await asyncio.sleep(0.5)  # Delay entre buscas
                            
                        except Exception as search_error:
                            # Ignora erros em buscas específicas
                            pass
                    
                    if self.progress_callback:
                        self.progress_callback('success', f'✅ Extração completa! Total: {len(all_participants)} membros')
                    
            except Exception as e:
                if self.progress_callback:
                    self.progress_callback('error', f'❌ Erro durante extração: {str(e)}')
                    self.progress_callback('info', f'ℹ️ Membros extraídos até o erro: {len(all_participants)}')
                # Continua com os membros que conseguiu extrair
            
            # Salva membros (filtrando bots, admins e dono)
            members_data = []
            filtered_count = 0
            user_filter_count = 0
            active_filters = self._describe_filters(filters)

            if active_filters and self.progress_callback:
                self.progress_callback('info', f'🔎 Filtros ativos: {", ".join(active_filters)}')
            
            for user in all_participants:
                # Ignora bots
                if user.bot:
                    filtered_count += 1
                    continue
                
                # Ignora deletados
                if user.deleted:
                    filtered_count += 1
                    continue
                
                # Ignora admins e dono
                if user.id in admin_ids:
                    filtered_count += 1
                    continue

                if not self._passes_member_filters(user, filters):
                    user_filter_count += 1
                    continue
                
                members_data.append({
                    'id': user.id,
                    'access_hash': user.access_hash,  # IMPORTANTE: Salva o access_hash
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone': user.phone,
                    'added': False
                })
            
            if self.progress_callback:
                self.progress_callback('warning', f'🚫 Filtrados: {filtered_count} (bots/admins/dono)')
                if user_filter_count:
                    self.progress_callback('warning', f'🔎 Removidos pelos filtros escolhidos: {user_filter_count}')
            
            self.save_members(members_data)
            
            # Exporta para arquivo
            self.export_to_file(members_data, group.title, group_link)
            
            await client.disconnect()
            
            if self.progress_callback:
                self.progress_callback('success', f'✅ Total extraído: {len(members_data)} membros válidos')
                self.progress_callback('success', f'💾 Arquivo exportado: members_export.json')
            
            return members_data
            
        except Exception as e:
            if self.progress_callback:
                self.progress_callback('error', f'❌ Erro: {str(e)}')
            return []
        finally:
            # Desconecta o cliente
            try:
                await client.disconnect()
            except:
                pass
    
    def save_members(self, members):
        """Salva membros extraídos"""
        atomic_write_json(self.members_file, members)
    
    def load_members(self):
        """Carrega membros salvos"""
        if os.path.exists(self.members_file):
            return load_json_file(self.members_file, [])
        return []

    def _describe_filters(self, filters):
        labels = {
            'active_7d': 'ativos 7 dias',
            'active_3d': 'ativos 3 dias',
            'online': 'online',
            'photo': 'com foto',
            'username': 'com username',
            'phone': 'com telefone'
        }
        return [label for key, label in labels.items() if filters.get(key)]

    def _passes_member_filters(self, user, filters):
        if not filters:
            return True

        if filters.get('username') and not user.username:
            return False

        if filters.get('phone') and not user.phone:
            return False

        if filters.get('photo') and not user.photo:
            return False

        status = getattr(user, 'status', None)

        if filters.get('online') and status.__class__.__name__ != 'UserStatusOnline':
            return False

        if filters.get('active_3d') and not self._was_recently_active(status, 3):
            return False

        if filters.get('active_7d') and not self._was_recently_active(status, 7):
            return False

        return True

    def _was_recently_active(self, status, days):
        if not status:
            return False

        status_name = status.__class__.__name__
        if status_name in ('UserStatusOnline', 'UserStatusRecently'):
            return True

        was_online = getattr(status, 'was_online', None)
        if not was_online:
            return False

        if was_online.tzinfo is None:
            was_online = was_online.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc) - was_online <= timedelta(days=days)
    
    def get_pending_members(self):
        """Retorna membros que ainda não foram adicionados"""
        members = self.load_members()
        return [m for m in members if not m.get('added', False)]
    
    def export_to_file(self, members, group_name, group_link=None):
        """Exporta membros para arquivo JSON"""
        from datetime import datetime
        
        export_data = {
            'group_name': group_name,
            'source_group_link': group_link,  # Salva o link do grupo de origem
            'extracted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_members': len(members),
            'members': members
        }
        
        # Salva no diretório data
        from config import DATA_DIR
        data_dir = self.data_dir or DATA_DIR
        os.makedirs(data_dir, exist_ok=True)
        export_file = os.path.join(data_dir, 'members_export.json')
        
        atomic_write_json(export_file, export_data)
        
        return export_file
    
    def split_members_into_batches(self, members, batch_count):
        """
        Divide membros em lotes (batches)
        
        Args:
            members: Lista de membros
            batch_count: Número de lotes para dividir
        
        Returns:
            Lista de lotes
        """
        if batch_count <= 0:
            batch_count = 1
        
        total = len(members)
        batch_size = total // batch_count
        remainder = total % batch_count
        
        batches = []
        start = 0
        
        for i in range(batch_count):
            # Adiciona 1 extra nos primeiros 'remainder' lotes
            end = start + batch_size + (1 if i < remainder else 0)
            batches.append(members[start:end])
            start = end
        
        return batches
    
    def export_batches_to_files(self, members, group_name, batch_count, group_link=None):
        """
        Exporta membros divididos em múltiplos arquivos
        
        Args:
            members: Lista de membros
            group_name: Nome do grupo
            batch_count: Número de arquivos para criar
            group_link: Link do grupo de origem
        
        Returns:
            Lista de caminhos dos arquivos criados
        """
        from datetime import datetime
        from config import DATA_DIR
        data_dir = self.data_dir or DATA_DIR
        os.makedirs(data_dir, exist_ok=True)
        
        # Divide em lotes
        batches = self.split_members_into_batches(members, batch_count)
        
        created_files = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for i, batch in enumerate(batches, 1):
            export_data = {
                'group_name': group_name,
                'source_group_link': group_link,
                'extracted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'batch_number': i,
                'total_batches': batch_count,
                'batch_size': len(batch),
                'total_members_extracted': len(members),
                'members': batch
            }
            
            # Nome do arquivo com número do lote
            filename = f'members_export_lote_{i}_de_{batch_count}_{timestamp}.json'
            export_file = os.path.join(data_dir, filename)
            
            atomic_write_json(export_file, export_data)
            
            created_files.append({
                'filename': filename,
                'path': export_file,
                'batch_number': i,
                'size': len(batch)
            })
        
        # Também salva um arquivo índice com informações de todos os lotes
        index_data = {
            'group_name': group_name,
            'source_group_link': group_link,
            'extracted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_members': len(members),
            'total_batches': batch_count,
            'batches': created_files
        }
        
        index_file = os.path.join(data_dir, f'members_export_index_{timestamp}.json')
        atomic_write_json(index_file, index_data)
        
        return created_files, index_file
    
    def get_source_group(self):
        """Retorna o grupo de origem dos membros"""
        from config import DATA_DIR
        data_dir = self.data_dir or DATA_DIR
        export_file = os.path.join(data_dir, 'members_export.json')
        
        if os.path.exists(export_file):
            try:
                data = load_json_file(export_file, {})
                return data.get('source_group_link')
            except:
                pass
        return None
