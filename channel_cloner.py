"""
Sistema de Clonagem de Canais do Telegram
Copia mensagens de um canal origem para um canal destino com edição
"""

import asyncio
import json
import os
import re
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from logger import log_info, log_error, log_warning
from data_store import atomic_write_json, load_json_file

class ChannelCloner:
    def __init__(self, api_id, api_hash, phone, session_path):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_path = session_path
        self.client = None
        self.active_clones = {}  # {clone_id: task}
        self.clone_configs = {}  # {clone_id: config}
        self.cloned_messages = {}  # {clone_id: set(message_ids)} - Anti-duplicação
        self.clones_file = None
        
    async def connect(self):
        """Conecta ao Telegram com retentativas de SQLite lock"""
        import sqlite3
        import asyncio
        
        # Se já estiver conectado e autorizado, apenas retorna
        if self.client and self.client.is_connected():
            try:
                if await self.client.is_user_authorized():
                    return True
            except:
                pass
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Antes de conectar com Telethon, tenta garantir que o SQLite está em modo WAL
                # e tem um timeout alto para evitar "database is locked"
                try:
                    db_file = self.session_path + '.session'
                    if os.path.exists(db_file):
                        conn = sqlite3.connect(db_file, timeout=20)
                        conn.execute("PRAGMA journal_mode=WAL")
                        conn.execute("PRAGMA busy_timeout=20000")
                        conn.close()
                except Exception as sqle:
                    log_warning(f"Aviso ao preparar SQLite (tentativa {attempt+1}): {sqle}")

                self.client = TelegramClient(self.session_path, self.api_id, self.api_hash)
                await self.client.connect()
                
                if not await self.client.is_user_authorized():
                    log_error("Sessão não autorizada")
                    return False
                
                log_info(f"✅ Conectado com sucesso: {self.phone}")
                return True
                
            except Exception as e:
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    log_warning(f"⚠️ Banco de dados travado, tentando novamente em {wait_time}s... ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    log_error(f"Erro ao conectar: {e}")
                    return False
        return False
    
    async def disconnect(self):
        """Desconecta do Telegram se não houver clones ativos"""
        if self.client and not self.active_clones:
            await self.client.disconnect()
            log_info(f"🔌 Cliente desconectado: {self.phone}")

    def _looks_like_markdown(self, text):
        """Detecta formatação simples que deve ser interpretada pelo Telegram."""
        if not text:
            return False
        return any(marker in text for marker in ('**', '__', '~~', '`'))

    def _strip_simple_formatting(self, text):
        """Remove marcadores simples para comparar pelo texto visivel."""
        if not text:
            return ''

        plain = str(text)
        for marker in ('**', '__', '~~', '`'):
            plain = plain.replace(marker, '')
        plain = re.sub(r'</?(?:b|strong|i|em|u|s|code|pre)>', '', plain, flags=re.IGNORECASE)
        return plain

    def _visible_index_map(self, text):
        """Mapeia indices do texto visivel para indices do texto com formatacao."""
        visible = []
        index_map = []
        i = 0
        while i < len(text):
            matched_marker = None
            for marker in ('**', '__', '~~', '`'):
                if text.startswith(marker, i):
                    matched_marker = marker
                    break

            if matched_marker:
                i += len(matched_marker)
                continue

            html_tag = re.match(r'</?(?:b|strong|i|em|u|s|code|pre)>', text[i:], flags=re.IGNORECASE)
            if html_tag:
                i += len(html_tag.group(0))
                continue

            visible.append(text[i])
            index_map.append(i)
            i += 1

        return ''.join(visible), index_map

    def _apply_wrapped_replacement(self, source, new_text):
        """Mantem wrappers quando o trecho substituido estava todo formatado."""
        wrappers = [
            ('**', '**'),
            ('__', '__'),
            ('~~', '~~'),
            ('`', '`'),
            ('<b>', '</b>'),
            ('<strong>', '</strong>'),
            ('<i>', '</i>'),
            ('<em>', '</em>'),
            ('<u>', '</u>'),
            ('<s>', '</s>'),
            ('<code>', '</code>'),
            ('<pre>', '</pre>'),
        ]

        lower_source = source.lower()
        lower_new = new_text.lower()
        for left, right in wrappers:
            if lower_source.startswith(left.lower()) and lower_source.endswith(right.lower()):
                if not (lower_new.startswith(left.lower()) and lower_new.endswith(right.lower())):
                    return f'{source[:len(left)]}{new_text}{source[len(source) - len(right):]}'
        return new_text

    def _replace_visible_text(self, text, old_text, new_text):
        """Substitui usando o texto visivel, ignorando marcadores de formatacao."""
        comparable_old = self._strip_simple_formatting(old_text)
        if not comparable_old:
            return text

        visible_text, index_map = self._visible_index_map(text)
        search_start = 0
        modified = text
        offset = 0

        while True:
            visible_pos = visible_text.find(comparable_old, search_start)
            if visible_pos == -1:
                break

            visible_end = visible_pos + len(comparable_old)
            original_start = index_map[visible_pos] + offset
            original_end = index_map[visible_end - 1] + 1 + offset

            # Inclui wrappers imediatamente ao redor do trecho visivel.
            for left, right in (('**', '**'), ('__', '__'), ('~~', '~~'), ('`', '`')):
                if (
                    original_start >= len(left)
                    and modified[original_start - len(left):original_start] == left
                    and modified[original_end:original_end + len(right)] == right
                ):
                    original_start -= len(left)
                    original_end += len(right)
                    break

            # Inclui marcadores que estejam dentro do trecho visivel, como
            # "Att. **FLOW**" ao buscar por "Att. FLOW".
            expanded = True
            while expanded:
                expanded = False
                current_source = modified[original_start:original_end]
                for marker in ('**', '__', '~~', '`'):
                    if (
                        original_start >= len(marker)
                        and modified[original_start - len(marker):original_start] == marker
                        and self._strip_simple_formatting(marker + current_source) == comparable_old
                    ):
                        original_start -= len(marker)
                        expanded = True
                        break

                    if (
                        modified.startswith(marker, original_end)
                        and self._strip_simple_formatting(current_source + marker) == comparable_old
                    ):
                        original_end += len(marker)
                        expanded = True
                        break

            replacement_source = modified[original_start:original_end]
            replacement = self._apply_wrapped_replacement(replacement_source, new_text)
            modified = modified[:original_start] + replacement + modified[original_end:]
            offset += len(replacement) - (original_end - original_start)
            search_start = visible_end

        return modified

    def _replace_preserving_markdown(self, text, old_text, new_text):
        """Substitui texto mesmo quando a origem vem com formatacao simples."""
        if not old_text:
            return text

        old_text = str(old_text)
        new_text = str(new_text)
        replacements = []

        markdown_wrappers = [('**', '**'), ('__', '__'), ('~~', '~~'), ('`', '`')]
        for left, right in markdown_wrappers:
            wrapped_old = f'{left}{old_text}{right}'
            wrapped_new = new_text
            if not (new_text.startswith(left) and new_text.endswith(right)):
                wrapped_new = f'{left}{new_text}{right}'
            replacements.append((wrapped_old, wrapped_new))

            if old_text.startswith(left) and old_text.endswith(right):
                inner_new = new_text
                if not (new_text.startswith(left) and new_text.endswith(right)):
                    inner_new = f'{left}{new_text}{right}'
                replacements.append((old_text, inner_new))

        replacements.append((old_text, new_text))

        modified = text
        for source, target in replacements:
            modified = modified.replace(source, target)
        return self._replace_visible_text(modified, old_text, new_text)
    
    def apply_text_modifications(self, text, config):
        """Aplica modificações no texto"""
        if not text:
            return text
        
        modified_text = text
        
        # Remove links se configurado
        if config.get('remove_links', False):
            # Remove URLs
            modified_text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', modified_text)
            # Remove @mentions
            if config.get('remove_mentions', False):
                modified_text = re.sub(r'@\w+', '', modified_text)
        
        # Substitui textos
        replacements = config.get('text_replacements', {})
        for old_text, new_text in replacements.items():
            modified_text = self._replace_preserving_markdown(modified_text, old_text, new_text)
        
        # Adiciona prefixo
        prefix = config.get('prefix', '')
        if prefix:
            modified_text = f"{prefix}\n\n{modified_text}"
        
        # Adiciona rodapé
        footer = config.get('footer', '')
        if footer:
            modified_text = f"{modified_text}\n\n{footer}"
        
        return modified_text.strip()

    def get_latest_clone_config(self, clone_id, fallback_config):
        """Busca a configuracao salva mais recente para evitar config antiga em memoria."""
        if not clone_id or not self.clones_file or not os.path.exists(self.clones_file):
            return fallback_config

        try:
            clones = load_json_file(self.clones_file, {'clones': []}).get('clones', [])
            latest = next((clone for clone in clones if clone.get('id') == clone_id), None)
            if not latest:
                return fallback_config

            return {
                'remove_links': latest.get('remove_links', fallback_config.get('remove_links', False)),
                'remove_mentions': latest.get('remove_mentions', fallback_config.get('remove_mentions', False)),
                'prefix': latest.get('prefix', fallback_config.get('prefix', '')),
                'footer': latest.get('footer', fallback_config.get('footer', '')),
                'text_replacements': latest.get('text_replacements', fallback_config.get('text_replacements', {}))
            }
        except Exception as e:
            log_warning(f"⚠️ Não consegui recarregar config da clonagem {clone_id}: {e}")
            return fallback_config
    
    async def clone_message(self, message, dest_channel, config, clone_id=None):
        """Clona uma mensagem para o canal destino"""
        try:
            # Verifica se já foi clonada (anti-duplicação)
            if clone_id:
                if clone_id not in self.cloned_messages:
                    self.cloned_messages[clone_id] = set()
                
                if message.id in self.cloned_messages[clone_id]:
                    log_info(f"⏭️ Mensagem ID {message.id} já foi clonada, pulando...")
                    return False
            
            log_info(f"🔄 Iniciando clonagem de mensagem ID {message.id}")
            
            # Pega o texto original
            original_text = message.text or message.message or ""
            log_info(f"� Texto original: {original_text[:50]}..." if len(original_text) > 50 else f"📝 Texto original: {original_text}")
            
            # Aplica modificações
            effective_config = self.get_latest_clone_config(clone_id, config)
            replacement_count = len(effective_config.get('text_replacements', {}) or {})
            log_info(f"🔁 Substituições carregadas: {replacement_count}")
            modified_text = self.apply_text_modifications(original_text, effective_config)
            log_info(f"✏️ Texto modificado: {modified_text[:50]}..." if len(modified_text) > 50 else f"✏️ Texto modificado: {modified_text}")
            
            # Se tem mídia, envia com a mídia
            parse_mode = 'md' if self._looks_like_markdown(modified_text) else None
            if message.media:
                log_info(f"🖼️ Mensagem tem mídia: {type(message.media).__name__}")
                if isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument)):
                    await self.client.send_file(
                        dest_channel,
                        message.media,
                        caption=modified_text if modified_text else None,
                        parse_mode=parse_mode
                    )
                    log_info(f"✅ Mensagem com mídia clonada para {dest_channel}")
                else:
                    # Outros tipos de mídia
                    await self.client.send_message(dest_channel, modified_text, parse_mode=parse_mode)
                    log_info(f"✅ Mensagem clonada (mídia não suportada)")
            else:
                # Apenas texto
                log_info(f"💬 Mensagem é apenas texto")
                if modified_text:
                    await self.client.send_message(dest_channel, modified_text, parse_mode=parse_mode)
                    log_info(f"✅ Mensagem de texto clonada para {dest_channel}")
                else:
                    log_warning(f"⚠️ Texto vazio, mensagem não enviada")
            
            # Marca como clonada
            if clone_id:
                self.cloned_messages[clone_id].add(message.id)
                log_info(f"✔️ Mensagem ID {message.id} marcada como clonada ({len(self.cloned_messages[clone_id])} total)")
            
            return True
        except Exception as e:
            log_error(f"Erro ao clonar mensagem: {e}")
            import traceback
            log_error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def get_last_message(self, channel_id):
        """Pega a última mensagem do canal"""
        try:
            log_info(f"🔍 Buscando última mensagem do canal: {channel_id}")
            
            # Tenta converter o ID se for string
            try:
                if isinstance(channel_id, str):
                    channel_id = int(channel_id)
            except:
                pass
            
            # Tenta pegar mensagens com timeout
            try:
                messages = await asyncio.wait_for(
                    self.client.get_messages(channel_id, limit=1),
                    timeout=10.0
                )
                
                if messages:
                    log_info(f"✅ Última mensagem encontrada: ID {messages[0].id}")
                    return messages[0]
                else:
                    log_warning(f"⚠️ Nenhuma mensagem encontrada no canal {channel_id}")
                    
            except asyncio.TimeoutError:
                log_error(f"⏱️ Timeout ao buscar mensagens do canal {channel_id}")
                log_error(f"💡 Verifique se a conta tem acesso ao canal e se o ID está correto")
                return None
                
            return None
            
        except Exception as e:
            log_error(f"Erro ao pegar última mensagem: {e}")
            import traceback
            log_error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def clone_last_message(self, source_channel, dest_channel, config, clone_id=None):
        """Clona a última mensagem do canal origem"""
        try:
            log_info(f"📋 Tentando clonar última mensagem de {source_channel} para {dest_channel}")
            last_msg = await self.get_last_message(source_channel)
            if last_msg:
                log_info(f"📤 Clonando mensagem ID {last_msg.id}")
                await self.clone_message(last_msg, dest_channel, config, clone_id)
                return last_msg.id
            else:
                log_warning(f"⚠️ Nenhuma mensagem para clonar")
            return None
        except Exception as e:
            log_error(f"Erro ao clonar última mensagem: {e}")
            return None
    
    async def start_monitoring(self, clone_id, source_channel, dest_channel, config):
        """Inicia monitoramento de novas mensagens"""
        try:
            # Converte IDs para inteiros se forem strings
            if isinstance(source_channel, str):
                try:
                    source_channel = int(source_channel)
                    log_info(f"� Canal origem convertido para int: {source_channel}")
                except ValueError:
                    pass  # Mantém como string se não for número
            
            if isinstance(dest_channel, str):
                try:
                    dest_channel = int(dest_channel)
                    log_info(f"🔢 Canal destino convertido para int: {dest_channel}")
                except ValueError:
                    pass  # Mantém como string se não for número
            
            log_info(f"🔄 Iniciando monitoramento: {source_channel} -> {dest_channel}")
            
            # Valida acesso aos canais
            log_info(f"🔐 Validando acesso aos canais...")
            try:
                # Tenta pegar info do canal origem
                source_entity = await asyncio.wait_for(
                    self.client.get_entity(source_channel),
                    timeout=10.0
                )
                log_info(f"✅ Acesso ao canal origem confirmado: {getattr(source_entity, 'title', 'Canal')}")
            except asyncio.TimeoutError:
                log_error(f"⏱️ Timeout ao acessar canal origem {source_channel}")
                return
            except Exception as e:
                log_error(f"❌ Erro ao acessar canal origem: {e}")
                return
            
            try:
                # Tenta pegar info do canal destino
                dest_entity = await asyncio.wait_for(
                    self.client.get_entity(dest_channel),
                    timeout=10.0
                )
                log_info(f"✅ Acesso ao canal destino confirmado: {getattr(dest_entity, 'title', 'Canal')}")
            except asyncio.TimeoutError:
                log_error(f"⏱️ Timeout ao acessar canal destino {dest_channel}")
                return
            except Exception as e:
                log_error(f"❌ Erro ao acessar canal destino: {e}")
                return
            
            # Clona a última mensagem primeiro
            last_msg_id = await self.clone_last_message(source_channel, dest_channel, config, clone_id)
            
            if last_msg_id:
                log_info(f"✅ Última mensagem clonada (ID: {last_msg_id})")
            else:
                log_warning(f"⚠️ Não foi possível clonar a última mensagem")
            
            # Registra handler para novas mensagens
            @self.client.on(events.NewMessage(chats=source_channel))
            async def handler(event):
                if clone_id in self.active_clones:
                    log_info(f"📨 Nova mensagem detectada no canal origem")
                    await self.clone_message(event.message, dest_channel, config, clone_id)
            
            # Mantém o monitoramento ativo
            while clone_id in self.active_clones:
                await asyncio.sleep(1)
            
            log_info(f"⏹️ Monitoramento parado: {clone_id}")
            
        except Exception as e:
            log_error(f"Erro no monitoramento: {e}")
            import traceback
            log_error(f"Traceback: {traceback.format_exc()}")
    
    async def start_clone(self, clone_id, source_channel, dest_channel, config):
        """Inicia uma clonagem"""
        try:
            if not await self.connect():
                return False
            
            # Salva config
            self.clone_configs[clone_id] = config
            
            # Cria task de monitoramento
            task = asyncio.create_task(
                self.start_monitoring(clone_id, source_channel, dest_channel, config)
            )
            
            self.active_clones[clone_id] = task
            
            log_info(f"✅ Clonagem iniciada: {clone_id}")
            return True
            
        except Exception as e:
            log_error(f"Erro ao iniciar clonagem: {e}")
            return False
    
    async def stop_clone(self, clone_id):
        """Para uma clonagem"""
        try:
            if clone_id in self.active_clones:
                # Remove do dicionário (isso para o loop)
                task = self.active_clones.pop(clone_id)
                task.cancel()
                
                # Remove config
                if clone_id in self.clone_configs:
                    del self.clone_configs[clone_id]
                
                # Limpa IDs de mensagens clonadas (opcional - comentar se quiser manter histórico)
                if clone_id in self.cloned_messages:
                    msg_count = len(self.cloned_messages[clone_id])
                    del self.cloned_messages[clone_id]
                    log_info(f"🗑️ Histórico de {msg_count} mensagens clonadas removido")
                
                log_info(f"⏹️ Clonagem parada: {clone_id}")
                
                # Se não houver mais clones ativos nesta sessão, desconecta
                if not self.active_clones:
                    await self.disconnect()
                    
                return True
            return False
        except Exception as e:
            log_error(f"Erro ao parar clonagem: {e}")
            return False
    
    def get_clone_stats(self, clone_id):
        """Retorna estatísticas de uma clonagem"""
        return {
            'active': clone_id in self.active_clones,
            'messages_cloned': len(self.cloned_messages.get(clone_id, set()))
        }
    
    def get_active_clones(self):
        """Retorna lista de clonagens ativas"""
        return list(self.active_clones.keys())
    
    def is_clone_active(self, clone_id):
        """Verifica se uma clonagem está ativa"""
        return clone_id in self.active_clones


class CloneManager:
    """Gerenciador de múltiplas clonagens"""
    
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.clones_file = os.path.join(data_dir, 'channel_clones.json')
        self.cloners = {}  # {session_name: ChannelCloner}
        self.init_clones_file()
    
    def init_clones_file(self):
        """Inicializa arquivo de clonagens"""
        if not os.path.exists(self.clones_file):
            atomic_write_json(self.clones_file, {'clones': []})
    
    def load_clones(self):
        """Carrega configurações de clonagens"""
        if os.path.exists(self.clones_file):
            data = load_json_file(self.clones_file, {'clones': []})
            return data.get('clones', [])
        return []
    
    def save_clones(self, clones):
        """Salva configurações de clonagens"""
        atomic_write_json(self.clones_file, {'clones': clones})
    
    def add_clone(self, clone_config):
        """Adiciona nova configuração de clonagem"""
        clones = self.load_clones()
        
        # Gera ID único
        clone_id = f"clone_{len(clones) + 1}_{int(datetime.now().timestamp())}"
        clone_config['id'] = clone_id
        clone_config['created_at'] = datetime.now().isoformat()
        clone_config['active'] = False
        
        clones.append(clone_config)
        self.save_clones(clones)
        
        return clone_id
    
    def remove_clone(self, clone_id):
        """Remove uma clonagem"""
        clones = self.load_clones()
        clones = [c for c in clones if c['id'] != clone_id]
        self.save_clones(clones)
    
    def update_clone_status(self, clone_id, active):
        """Atualiza status de uma clonagem"""
        clones = self.load_clones()
        for clone in clones:
            if clone['id'] == clone_id:
                clone['active'] = active
                break
        self.save_clones(clones)
    
    def get_cloner(self, session_name, api_id, api_hash, phone, session_path):
        """Pega ou cria um cloner para uma sessão"""
        if session_name not in self.cloners:
            self.cloners[session_name] = ChannelCloner(api_id, api_hash, phone, session_path)
        self.cloners[session_name].clones_file = self.clones_file
        return self.cloners[session_name]
