

from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
import os
import json
import shutil
from config import SESSIONS_DIR, CONFIG_FILE, API_ID, API_HASH
from logger import log_info, log_error, log_warning
from data_store import atomic_write_json, load_json_file

class SessionManager:
    def __init__(self, sessions_dir=None, config_file=None):
        # Usa diretórios customizados ou padrão
        self.sessions_dir = sessions_dir or SESSIONS_DIR
        self.config_file = config_file or CONFIG_FILE
        self.data_dir = os.path.dirname(self.config_file) or os.getcwd()
        
        self.sessions = []
        self._sessions_cache = None  # Cache para evitar recarregar sempre
        self._cache_timestamp = 0
        self.load_sessions()
    
    def load_sessions(self, force_reload=False):
        """Carrega lista de sessões salvas com cache"""
        import time
        
        # Se tem cache válido (menos de 5 segundos), usa ele
        if not force_reload and self._sessions_cache is not None:
            current_time = time.time()
            if current_time - self._cache_timestamp < 5:
                self.sessions = self._sessions_cache
                return self.sessions
        
        if os.path.exists(self.config_file):
            data = load_json_file(self.config_file, {})
            sessions = data.get('sessions', [])

            # Adiciona campos novos se não existirem
            for session in sessions:
                if 'status' not in session:
                    session['status'] = 'active'  # active, flood, disconnected
                if 'flood_until' not in session:
                    session['flood_until'] = None
                if 'last_used' not in session:
                    session['last_used'] = None
                if 'total_added' not in session:
                    session['total_added'] = 0

            self.sessions = sessions

            # Atualiza status de flood e salva se algum prazo antigo expirou.
            if self._update_flood_status(sessions):
                self.sessions = sessions
                self.save_sessions()

            # Atualiza cache
            self._sessions_cache = sessions.copy()
            self._cache_timestamp = time.time()
        else:
            self.sessions = []
            
        return self.sessions
    
    def _update_flood_status(self, sessions):
        """Atualiza o status de flood das sessões"""
        from datetime import datetime
        flood_file = os.path.join(self.data_dir, 'session_floods.json')
        floods = {}
        changed = False
        floods_changed = False
        
        try:
            if os.path.exists(flood_file):
                floods = load_json_file(flood_file, {})
            
            now = datetime.now()
            
            for session in sessions:
                session_name = session.get('session_name', '')

                flood_until_str = floods.get(session_name) or session.get('flood_until')
                if not flood_until_str:
                    continue

                try:
                    flood_until = datetime.fromisoformat(flood_until_str)
                except ValueError:
                    if session.get('status') == 'flood':
                        session['status'] = 'active'
                        session['flood_until'] = None
                        changed = True
                    if session_name in floods:
                        floods.pop(session_name, None)
                        floods_changed = True
                    continue

                if now < flood_until:
                    if session.get('status') != 'flood' or session.get('flood_until') != flood_until_str:
                        session['status'] = 'flood'
                        session['flood_until'] = flood_until_str
                        changed = True
                else:
                    if session.get('status') == 'flood' or session.get('flood_until'):
                        session['status'] = 'active'
                        session['flood_until'] = None
                        changed = True
                    if session_name in floods:
                        floods.pop(session_name, None)
                        floods_changed = True
            
            # Salva floods atualizados
            if floods_changed or not os.path.exists(flood_file):
                atomic_write_json(flood_file, floods)
                
            return changed
        except json.JSONDecodeError as e:
            # Arquivo JSON corrompido, recria vazio
            log_warning(f'⚠️ Arquivo session_floods.json corrompido, recriando: {e}')
            try:
                atomic_write_json(flood_file, {})
            except:
                pass
        except Exception as e:
            log_warning(f'⚠️ Erro ao atualizar floods: {e}')
        
        return changed

    def get_session_flood_until(self, session_name):
        """Retorna o datetime de flood ativo pela fonte da verdade: session_floods.json."""
        from datetime import datetime
        if not session_name:
            return None

        flood_file = os.path.join(self.data_dir, 'session_floods.json')
        try:
            floods = load_json_file(flood_file, {}) if os.path.exists(flood_file) else {}
            flood_until_str = floods.get(session_name)
            if not flood_until_str:
                for session in self.sessions:
                    if session.get('session_name') == session_name:
                        flood_until_str = session.get('flood_until')
                        break
            if not flood_until_str:
                return None

            flood_until = datetime.fromisoformat(flood_until_str)
            if datetime.now() < flood_until:
                return flood_until
            return None
        except Exception:
            return None

    def is_session_flooded(self, session_name):
        """True se a sessão ainda está em quarentena."""
        return self.get_session_flood_until(session_name) is not None
    
    def save_sessions(self):
        """Salva lista de sessões preservando outras configurações"""
        self._update_flood_status(self.sessions)

        # Carrega dados existentes
        data = {}
        if os.path.exists(self.config_file):
            try:
                data = load_json_file(self.config_file, {})
                # Log para debug
                if 'api_credentials' in data:
                    log_info(f"✅ Preservando {len(data['api_credentials'])} API(s) ao salvar sessões")
            except Exception as e:
                log_warning(f"Erro ao carregar config existente: {e}")
                data = {}
        
        # Atualiza apenas as sessões, preservando o resto
        data['sessions'] = self.sessions
        
        # Salva de volta
        atomic_write_json(self.config_file, data)
        
        # Invalida cache
        self._sessions_cache = None
        
        log_info(f"💾 Sessões salvas: {len(self.sessions)} sessão(ões)")
    
    def invalidate_cache(self):
        """Invalida o cache de sessões forçando reload na próxima chamada"""
        self._sessions_cache = None
        self._cache_timestamp = 0
    
    def add_session(self, phone, api_id, api_hash):
        """Adiciona uma nova sessão"""
        session_name = phone.replace('+', '').replace(' ', '')
        session_path = os.path.join(self.sessions_dir, session_name)
        
        try:
            client = TelegramClient(session_path, api_id, api_hash)
            client.connect()
            
            if not client.is_user_authorized():
                client.send_code_request(phone)
                print(f'\n📱 Código enviado para {phone}')
                code = input('Digite o código recebido: ')
                
                try:
                    client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    password = input('Digite a senha de verificação em duas etapas: ')
                    client.sign_in(password=password)
            
            me = client.get_me()
            
            session_info = {
                'phone': phone,
                'session_name': session_name,
                'user_id': me.id,
                'username': me.username or 'Sem username',
                'first_name': me.first_name or '',
                'active': True
            }
            
            self.sessions.append(session_info)
            self.save_sessions()
            
            client.disconnect()
            
            print(f'✅ Sessão adicionada: {me.first_name} (@{me.username})')
            return True
            
        except Exception as e:
            print(f'❌ Erro ao adicionar sessão: {e}')
            return False
    
    def list_sessions(self):
        """Lista todas as sessões"""
        if not self.sessions:
            print('\n⚠️  Nenhuma sessão cadastrada')
            return
        
        print('\n📋 Sessões cadastradas:')
        print('-' * 60)
        for i, session in enumerate(self.sessions, 1):
            status = '🟢' if session.get('active') else '🔴'
            print(f"{i}. {status} {session['first_name']} (@{session['username']})")
            print(f"   📞 {session['phone']}")
        print('-' * 60)
    
    def get_active_sessions(self):
        """Retorna apenas sessões aprovadas para uso automático."""
        from datetime import datetime

        self.load_sessions(force_reload=True)
        
        active = []
        for session in self.sessions:
            if not session.get('active', True):
                continue

            flood_until = self.get_session_flood_until(session.get('session_name', ''))
            if flood_until:
                session['status'] = 'flood'
                session['flood_until'] = flood_until.isoformat()
                continue

            if session.get('status', 'active') not in ('active', 'flood'):
                continue
            
            # Verifica se está em flood
            if session.get('status') == 'flood' and session.get('flood_until'):
                flood_until = datetime.fromisoformat(session['flood_until'])
                if datetime.now() < flood_until:
                    # Ainda em flood, pula
                    continue
                else:
                    # Flood expirou, marca como ativa
                    session['status'] = 'active'
                    session['flood_until'] = None
            
            if session.get('status', 'active') == 'active':
                active.append(session)
        
        return active
    
    def get_flood_info(self, session_name):
        """Retorna informações sobre o flood de uma sessão"""
        from datetime import datetime

        flood_until = self.get_session_flood_until(session_name)
        if flood_until:
            remaining = flood_until - datetime.now()
            hours = remaining.total_seconds() // 3600
            minutes = (remaining.total_seconds() % 3600) // 60
            return {
                'in_flood': True,
                'flood_until': flood_until.strftime('%d/%m/%Y %H:%M'),
                'remaining_hours': int(hours),
                'remaining_minutes': int(minutes),
                'unknown_until': False,
                'recommended_action': 'O sistema libera automaticamente quando o prazo terminar.'
            }
        
        for session in self.sessions:
            if session.get('session_name') == session_name:
                if session.get('status') != 'flood':
                    return {'in_flood': False}

                if session.get('flood_until'):
                    flood_until = datetime.fromisoformat(session['flood_until'])
                    now = datetime.now()
                    
                    if now < flood_until:
                        remaining = flood_until - now
                        hours = remaining.total_seconds() // 3600
                        minutes = (remaining.total_seconds() % 3600) // 60
                        
                        return {
                            'in_flood': True,
                            'flood_until': flood_until.strftime('%d/%m/%Y %H:%M'),
                            'remaining_hours': int(hours),
                            'remaining_minutes': int(minutes),
                            'unknown_until': False,
                            'recommended_action': 'O sistema libera automaticamente quando o prazo terminar.'
                        }

                    return {
                        'in_flood': False,
                        'expired': True,
                        'flood_until': flood_until.strftime('%d/%m/%Y %H:%M'),
                        'recommended_action': 'O sistema vai liberar automaticamente ao sincronizar as sessões.'
                    }

                return {
                    'in_flood': True,
                    'flood_until': None,
                    'remaining_hours': None,
                    'remaining_minutes': None,
                    'unknown_until': True,
                    'recommended_action': 'Sem prazo informado. Não use automaticamente; valide manualmente antes de reativar.'
                }
        
        return {'in_flood': False}
    
    def toggle_session(self, index):
        """Ativa/desativa uma sessão"""
        if 0 <= index < len(self.sessions):
            self.sessions[index]['active'] = not self.sessions[index].get('active', True)
            self.save_sessions()
            return True
        return False
    
    def remove_session(self, index):
        """Remove uma sessão"""
        if 0 <= index < len(self.sessions):
            session = self.sessions.pop(index)
            self.save_sessions()
            
            # Remove arquivo de sessão
            session_path = os.path.join(self.sessions_dir, session['session_name'] + '.session')
            if os.path.exists(session_path):
                os.remove(session_path)
            
            print(f'✅ Sessão removida: {session["first_name"]}')
            return True
        return False
    
    def remove_all_sessions(self):
        """Remove todas as sessões de uma vez"""
        try:
            total = len(self.sessions)
            
            if total == 0:
                return False
            
            log_info(f'🗑️ Removendo {total} sessão(ões)...')
            
            # Remove todos os arquivos .session
            removed_count = 0
            for session in self.sessions:
                session_path = os.path.join(self.sessions_dir, session['session_name'] + '.session')
                if os.path.exists(session_path):
                    try:
                        os.remove(session_path)
                        removed_count += 1
                        log_info(f'  ✅ Removido: {session["first_name"]} (@{session.get("username", "sem username")})')
                    except Exception as e:
                        log_error(f'  ❌ Erro ao remover {session["first_name"]}: {e}')
            
            # Limpa a lista de sessões
            self.sessions = []
            self.save_sessions()
            
            log_info(f'✅ Total removido: {removed_count}/{total} arquivos')
            
            return True
            
        except Exception as e:
            log_error(f'❌ Erro ao remover todas as sessões: {e}')
            return False

    def import_session_file(self, session_file_path, api_id, api_hash, validate_online=False):
        """Importa um arquivo .session e valida se está ativo"""
        try:
            # Nome do arquivo sem extensão
            session_name = os.path.basename(session_file_path).replace('.session', '')

            # Bloqueia duplicadas pelo nome antes de copiar/validar.
            existing_names = {str(s.get('session_name', '')).lower() for s in self.sessions}
            if session_name.lower() in existing_names:
                log_info(f"⏭️ Sessão {session_name} já existe, pulando")
                return {
                    'success': False,
                    'name': session_name,
                    'error': 'Já cadastrada'
                }
            
            # Caminho de destino
            dest_path = os.path.join(self.sessions_dir, session_name + '.session')
            copied_to_dest = False
            
            # Se o arquivo não está no destino, copia
            if session_file_path != dest_path:
                if os.path.exists(session_file_path):
                    shutil.copy2(session_file_path, dest_path)
                    copied_to_dest = True
                else:
                    return {
                        'success': False,
                        'name': session_name,
                        'error': 'Arquivo não encontrado'
                    }
            
            # Verifica se o arquivo existe e tem tamanho válido
            if not os.path.exists(dest_path):
                return {
                    'success': False,
                    'name': session_name,
                    'error': 'Arquivo não encontrado no destino'
                }
            
            file_size = os.path.getsize(dest_path)
            if file_size < 100:
                return {
                    'success': False,
                    'name': session_name,
                    'error': f'Arquivo muito pequeno ({file_size} bytes)'
                }
            
            # Validação básica do SQLite
            import sqlite3
            phone = session_name
            username = session_name
            first_name = session_name
            user_id = abs(hash(session_name)) % 1000000000
            
            try:
                conn = sqlite3.connect(dest_path)
                cursor = conn.cursor()
                
                # Verifica se tem a tabela sessions
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
                if not cursor.fetchone():
                    conn.close()
                    return {
                        'success': False,
                        'name': session_name,
                        'error': 'Arquivo não é uma sessão válida do Telegram'
                    }
                
                # Tenta pegar dados da sessão
                try:
                    cursor.execute("SELECT dc_id, server_address, port, auth_key FROM sessions")
                    session_data = cursor.fetchone()
                    if not session_data or not session_data[3]:  # auth_key vazio
                        conn.close()
                        return {
                            'success': False,
                            'name': session_name,
                            'error': 'Sessão sem dados de autenticação'
                        }
                except:
                    pass
                
                conn.close()
                
            except Exception as e:
                log_error(f"❌ Erro ao ler SQLite {session_name}: {e}")
                return {
                    'success': False,
                    'name': session_name,
                    'error': f'Erro ao ler arquivo: {str(e)}'
                }
            
            # Validação online se solicitado
            if validate_online:
                try:
                    import asyncio
                    from telethon import TelegramClient
                    
                    # Cria um novo event loop para esta thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def validate():
                        try:
                            # Normaliza a sessão para o formato esperado pela versão atual do Telethon.
                            from downgrade_sessions import downgrade_session
                            session_file = dest_path
                            
                            try:
                                test_conn = sqlite3.connect(session_file)
                                test_cursor = test_conn.cursor()
                                test_cursor.execute("PRAGMA table_info(update_state)")
                                columns = test_cursor.fetchall()
                                test_conn.close()
                                
                                if len(columns) == 6:
                                    log_info(f"🔄 Convertendo sessão para formato compatível: {session_name}")
                                    success, msg = downgrade_session(session_file)
                                    if not success:
                                        log_warning(f"⚠️ Falha ao converter {session_name}: {msg}")
                                    else:
                                        log_info(f"✅ Conversão concluída: {session_name} - {msg}")
                            except Exception as normalize_error:
                                log_warning(f"⚠️ Não foi possível verificar formato da sessão {session_name}: {normalize_error}")
                            
                            # Conecta e valida
                            session_path = dest_path.replace('.session', '')
                            client = TelegramClient(session_path, api_id, api_hash)
                            try:
                                await client.connect()
                                
                                me = await client.get_me()
                            except Exception as connect_error:
                                error_msg = str(connect_error)
                                try:
                                    await client.disconnect()
                                except:
                                    pass

                                if 'update_state has 6 columns but 5 values were supplied' in error_msg:
                                    log_info(f"🔄 Ajustando formato após erro do Telethon: {session_name}")
                                    success, msg = downgrade_session(session_file)
                                    if not success:
                                        return {'valid': False, 'error': f'Falha ao ajustar sessão: {msg}'}

                                    client = TelegramClient(session_path, api_id, api_hash)
                                    await client.connect()
                                    me = await client.get_me()
                                else:
                                    raise
                            finally:
                                try:
                                    await client.disconnect()
                                except:
                                    pass
                            
                            if me:
                                return {
                                    'valid': True,
                                    'phone': me.phone if hasattr(me, 'phone') and me.phone else session_name,
                                    'username': me.username if me.username else session_name,
                                    'first_name': me.first_name if me.first_name else session_name,
                                    'user_id': me.id
                                }
                            else:
                                return {'valid': False, 'error': 'Não autorizada'}
                        except Exception as e:
                            return {'valid': False, 'error': str(e)}
                    
                    validation_result = loop.run_until_complete(validate())
                    loop.close()
                    
                    if validation_result.get('valid'):
                        phone = validation_result['phone']
                        username = validation_result['username']
                        first_name = validation_result['first_name']
                        user_id = validation_result['user_id']

                        # Bloqueia a mesma conta mesmo que venha com outro nome de arquivo.
                        existing_duplicate = next((
                            s for s in self.sessions
                            if str(s.get('user_id')) == str(user_id)
                            or (phone and str(s.get('phone')) == str(phone))
                        ), None)
                        if existing_duplicate:
                            log_info(
                                f"⏭️ Conta já cadastrada, pulando {session_name}: "
                                f"{existing_duplicate.get('session_name')}"
                            )
                            if copied_to_dest and os.path.exists(dest_path):
                                try:
                                    os.remove(dest_path)
                                except Exception as cleanup_error:
                                    log_warning(f"⚠️ Não consegui remover duplicada {dest_path}: {cleanup_error}")
                            return {
                                'success': False,
                                'name': session_name,
                                'error': 'Conta já cadastrada em outra sessão'
                            }

                        log_info(f"✅ Sessão validada: {first_name} ({phone})")
                    else:
                        log_warning(f"⚠️ Sessão não autorizada: {session_name} - {validation_result.get('error', 'Erro desconhecido')}")
                        return {
                            'success': False,
                            'name': session_name,
                            'error': f"Não autorizada: {validation_result.get('error', 'Erro desconhecido')}"
                        }
                        
                except Exception as e:
                    log_error(f"❌ Erro ao validar {session_name}: {e}")
                    return {
                        'success': False,
                        'name': session_name,
                        'error': f'Erro na validação: {str(e)}'
                    }
            
            # Adiciona à lista
            session_info = {
                'phone': phone,
                'session_name': session_name,
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'name': first_name,
                'active': True,
                'status': 'active'
            }
            
            # Verifica se já existe
            existing = next((s for s in self.sessions if s['session_name'] == session_name), None)
            if existing:
                log_info(f"⏭️ Sessão {session_name} já existe, pulando")
                if copied_to_dest and os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except Exception as cleanup_error:
                        log_warning(f"⚠️ Não consegui remover duplicada {dest_path}: {cleanup_error}")
                return {
                    'success': False,
                    'name': session_name,
                    'error': 'Já cadastrada'
                }
            
            self.sessions.append(session_info)
            log_info(f"✅ Sessão importada: {first_name} ({phone})")
            
            return {
                'success': True,
                'name': session_name,
                'user_info': f"{first_name} ({phone})",
                'session_info': session_info
            }
            
        except Exception as e:
            log_error(f"Erro ao importar {session_file_path}: {e}")
            return {
                'success': False,
                'name': os.path.basename(session_file_path),
                'error': str(e)
            }
    
    def import_multiple_sessions(self, session_files, api_id, api_hash, validate_online=True, delay_between=0, progress_callback=None):
        """Importa múltiplas sessões e vincula apenas as validadas."""
        results = []
        active_count = 0
        inactive_count = 0
        
        total = len(session_files)
        log_info(f'📦 Importando e validando {total} sessões...')
        if validate_online:
            log_info('🔐 Validação automática ligada - apenas sessões aprovadas serão vinculadas')
        
        for idx, session_file in enumerate(session_files, 1):
            session_name = os.path.basename(session_file).replace('.session', '')
            
            if idx % 10 == 0 or idx == total:
                log_info(f'⏳ [{idx}/{total}] Importando: {session_name}')
            
            result = self.import_session_file(session_file, api_id, api_hash, validate_online=validate_online)
            results.append(result)
            
            if result['success']:
                active_count += 1
                if active_count % 25 == 0:
                    self.save_sessions()
                    log_info(f'💾 Salvamento parcial: {active_count} sessões aprovadas gravadas')
            else:
                inactive_count += 1

            if progress_callback:
                try:
                    progress_callback({
                        'current': idx,
                        'total': total,
                        'session_name': session_name,
                        'active': active_count,
                        'inactive': inactive_count,
                        'success': bool(result.get('success')),
                        'error': result.get('error')
                    })
                except Exception:
                    pass

            if delay_between and idx < total:
                import time
                time.sleep(float(delay_between))
        
        # Salva todas as sessões de uma vez no final
        if active_count > 0:
            self.save_sessions()
            log_info(f'💾 {active_count} sessões salvas no config')
        
        log_info(f'✅ Importação concluída: {active_count} aprovadas, {inactive_count} recusadas/puladas')
        
        return {
            'success': True,
            'total': len(session_files),
            'active': active_count,
            'inactive': inactive_count,
            'results': results
        }
    
    def scan_and_import_sessions(self, api_id, api_hash):
        """Escaneia a pasta de sessões e importa as que não estão no config"""
        try:
            if not os.path.exists(self.sessions_dir):
                return {'success': False, 'error': 'Diretório de sessões não existe'}
            
            # Lista todos os arquivos .session na pasta
            session_files = []
            for file in os.listdir(self.sessions_dir):
                if file.endswith('.session'):
                    session_files.append(os.path.join(self.sessions_dir, file))
            
            if not session_files:
                return {'success': True, 'imported': 0, 'message': 'Nenhuma sessão encontrada na pasta'}
            
            # Pega nomes das sessões já cadastradas
            existing_names = {s['session_name'] for s in self.sessions}
            
            # Filtra apenas as que não estão cadastradas
            new_sessions = []
            for file_path in session_files:
                session_name = os.path.basename(file_path).replace('.session', '')
                if session_name not in existing_names:
                    new_sessions.append(file_path)
            
            if not new_sessions:
                return {'success': True, 'imported': 0, 'message': 'Todas as sessões já estão cadastradas'}
            
            # Importa as novas sessões
            log_info(f'🔍 Encontradas {len(new_sessions)} sessões não cadastradas')
            result = self.import_multiple_sessions(new_sessions, api_id, api_hash, validate_online=True)
            
            return {
                'success': True,
                'imported': result['active'],
                'failed': result['inactive'],
                'message': f'{result["active"]} sessões importadas com sucesso'
            }
            
        except Exception as e:
            log_error(f'Erro ao escanear sessões: {e}')
            return {'success': False, 'error': str(e)}
