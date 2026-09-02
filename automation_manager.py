import json
import os
from datetime import datetime, timedelta
from config import DATA_DIR
from data_store import atomic_write_json, load_json_file

class AutomationManager:
    def __init__(self, data_dir=None):
        # Usa diretório customizado ou padrão
        self.data_dir = data_dir or DATA_DIR
        self.config_file = os.path.join(self.data_dir, 'automation_config.json')
        self.load_config()
    
    def load_config(self):
        """Carrega configurações de automação"""
        if os.path.exists(self.config_file):
            self.config = load_json_file(self.config_file, {
                'groups': [],
                'daily_limits': {},
                'warming_enabled': False,
                'warming_interval': 10
            })
        else:
            self.config = {
                'groups': [],  # Lista de grupos para encher
                'daily_limits': {},  # Limites diários por grupo
                'warming_enabled': False,  # Aquecimento ativo
                'warming_interval': 10  # Minutos entre mensagens
            }
            self.save_config()
    
    def save_config(self, preserve_disk_tasks=True):
        """Salva configurações"""
        if preserve_disk_tasks:
            self._preserve_disk_tasks()
        self._remove_deleted_tasks()
        self._preserve_manual_pauses()
        atomic_write_json(self.config_file, self.config)

    def get_next_task_id(self):
        """Retorna um ID único mesmo após tarefas antigas serem removidas."""
        task_ids = [
            int(task.get('id') or 0)
            for task in self.config.get('groups', [])
            if str(task.get('id') or '').isdigit()
        ]
        deleted_task_ids = [
            int(task_id)
            for task_id in self.config.get('deleted_task_ids', [])
            if str(task_id).isdigit()
        ]
        task_ids.extend(deleted_task_ids)
        return (max(task_ids) + 1) if task_ids else 1

    def _parse_datetime(self, value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None

    def _preserve_disk_tasks(self):
        """Evita que uma instância antiga apague tarefas criadas por outra request/thread."""
        if not os.path.exists(self.config_file):
            return

        try:
            disk_config = load_json_file(self.config_file, {})
            deleted_task_ids = {
                int(task_id)
                for task_id in disk_config.get('deleted_task_ids', [])
                if str(task_id).isdigit()
            }
            if deleted_task_ids:
                memory_deleted = set(self.config.get('deleted_task_ids', []))
                memory_deleted.update(deleted_task_ids)
                self.config['deleted_task_ids'] = sorted(memory_deleted)

            disk_tasks = [
                task
                for task in disk_config.get('groups', [])
                if task.get('id') is not None and int(task.get('id')) not in deleted_task_ids
            ]
            if not disk_tasks:
                return

            memory_tasks = self.config.setdefault('groups', [])
            memory_ids = {
                task.get('id')
                for task in memory_tasks
                if task.get('id') is not None
            }

            missing_tasks = [
                task for task in disk_tasks
                if task.get('id') not in memory_ids
            ]
            if missing_tasks:
                memory_tasks.extend(missing_tasks)
                memory_tasks.sort(key=lambda task: int(task.get('id') or 0))
        except Exception:
            return

    def _preserve_manual_pauses(self):
        """Impede que uma thread antiga sobrescreva uma pausa manual salva no disco."""
        if not os.path.exists(self.config_file):
            return

        try:
            disk_config = load_json_file(self.config_file, {})
            disk_tasks = {
                task.get('id'): task
                for task in disk_config.get('groups', [])
                if task.get('id') is not None
            }

            for task in self.config.get('groups', []):
                task_id = task.get('id')
                disk_task = disk_tasks.get(task_id)
                if not disk_task:
                    continue

                if disk_task.get('status') != 'paused' or task.get('status') != 'active':
                    continue

                pause_at = self._parse_datetime(disk_task.get('pause_requested_at'))
                run_at = self._parse_datetime(task.get('current_run_started_at'))
                if pause_at and (not run_at or pause_at >= run_at):
                    task['status'] = 'paused'
                    task['pause_requested_at'] = disk_task.get('pause_requested_at')
                    task['pause_reason'] = disk_task.get('pause_reason', 'Pausada manualmente')
        except Exception:
            return

    def _remove_deleted_tasks(self):
        """Mantém tarefas removidas fora do arquivo mesmo se uma thread antiga salvar depois."""
        deleted_task_ids = {
            int(task_id)
            for task_id in self.config.get('deleted_task_ids', [])
            if str(task_id).isdigit()
        }
        if not deleted_task_ids:
            return

        self.config['groups'] = [
            task
            for task in self.config.get('groups', [])
            if int(task.get('id') or 0) not in deleted_task_ids
        ]
        self.config['deleted_task_ids'] = sorted(deleted_task_ids)

    def delete_task(self, task_id):
        """Remove uma tarefa e registra o ID para evitar reaparecimento por saves atrasados."""
        task_id = int(task_id)
        self.load_config()
        before = len(self.config.get('groups', []))
        self.config['groups'] = [
            task for task in self.config.get('groups', [])
            if int(task.get('id') or 0) != task_id
        ]
        deleted_task_ids = {
            int(existing_id)
            for existing_id in self.config.get('deleted_task_ids', [])
            if str(existing_id).isdigit()
        }
        deleted_task_ids.add(task_id)
        self.config['deleted_task_ids'] = sorted(deleted_task_ids)
        self.save_config(preserve_disk_tasks=False)
        return len(self.config.get('groups', [])) < before
    
    def add_group_task(
        self,
        group_link,
        target_members,
        daily_limit=50,
        selected_sessions=None,
        members_per_session=25,
        target_groups=None,
        delay_between_adds=5,
        delay_between_sessions=90,
        delay_between_adds_min=None,
        delay_between_adds_max=None,
        delay_between_sessions_min=None,
        delay_between_sessions_max=None,
        group_interaction_enabled=True
    ):
        """Adiciona grupo à fila de tarefas - SUPORTA MÚLTIPLOS GRUPOS"""
        task = {
            'id': self.get_next_task_id(),
            'group_link': group_link,
            'target_groups': target_groups or [group_link],  # NOVO: Lista de grupos
            'target_members': target_members,
            'daily_limit': daily_limit,
            'members_per_session': members_per_session,
            'delay_between_adds': delay_between_adds,
            'delay_between_sessions': delay_between_sessions,
            'delay_between_adds_min': delay_between_adds_min if delay_between_adds_min is not None else delay_between_adds,
            'delay_between_adds_max': delay_between_adds_max if delay_between_adds_max is not None else delay_between_adds,
            'delay_between_sessions_min': delay_between_sessions_min if delay_between_sessions_min is not None else delay_between_sessions,
            'delay_between_sessions_max': delay_between_sessions_max if delay_between_sessions_max is not None else delay_between_sessions,
            'group_interaction_enabled': group_interaction_enabled,
            'added_today': 0,
            'last_reset': datetime.now().isoformat(),
            'status': 'pending',  # pending, active, completed, paused
            'total_added': 0,
            'selected_sessions': selected_sessions or []  # Sessões dedicadas a esta tarefa
        }
        self.config['groups'].append(task)
        self.save_config()
        return task
    
    def get_active_tasks(self):
        """Retorna tarefas ativas"""
        return [g for g in self.config['groups'] if g['status'] in ['pending', 'active']]
    
    def update_task_progress(self, task_id, added_count):
        """Atualiza progresso de uma tarefa"""
        for group in self.config['groups']:
            if group['id'] == task_id:
                group['added_today'] += added_count
                group['total_added'] += added_count
                
                # Verifica se atingiu o limite diário
                if group['added_today'] >= group['daily_limit']:
                    group['status'] = 'paused'
                
                # Verifica se completou
                if group['total_added'] >= group['target_members']:
                    group['status'] = 'completed'
                
                break
        self.save_config()
    
    def reset_daily_limits(self):
        """Reseta limites diários (executar a cada 25 horas)"""
        now = datetime.now()
        
        for group in self.config['groups']:
            last_reset = datetime.fromisoformat(group['last_reset'])
            
            # Se passou 25 horas
            if (now - last_reset).total_seconds() >= 25 * 3600:
                group['added_today'] = 0
                group['last_reset'] = now.isoformat()
                
                # Reativa se estava pausada
                if group['status'] == 'paused' and group['total_added'] < group['target_members']:
                    group['status'] = 'active'
        
        self.save_config()
    
    def split_members(self, members, parts):
        """Divide lista de membros em partes"""
        chunk_size = len(members) // parts
        remainder = len(members) % parts
        
        result = []
        start = 0
        
        for i in range(parts):
            # Adiciona 1 extra nas primeiras 'remainder' partes
            end = start + chunk_size + (1 if i < remainder else 0)
            result.append(members[start:end])
            start = end
        
        return result
    
    def mark_session_flood(self, session_name):
        """Marca sessão em flood por 3 dias"""
        flood_until = datetime.now() + timedelta(days=3)
        return {
            'status': 'flood',
            'flood_until': flood_until.isoformat()
        }
    
    def check_flood_status(self, session):
        """Verifica se sessão ainda está em flood"""
        if session.get('status') == 'flood' and session.get('flood_until'):
            flood_until = datetime.fromisoformat(session['flood_until'])
            if datetime.now() >= flood_until:
                return {'status': 'active', 'flood_until': None}
        return None
    
    def get_active_task_sessions(self):
        """Retorna lista de índices de sessões que estão em tarefas ativas"""
        blocked_sessions = []
        for task in self.config['groups']:
            if task['status'] == 'active':
                blocked_sessions.extend(task.get('selected_sessions', []))
        return list(set(blocked_sessions))  # Remove duplicatas

    def get_reserved_task_sessions(self):
        """Retorna sessões reservadas por tarefas que ainda não terminaram."""
        reserved_sessions = []
        for task in self.config['groups']:
            if task.get('status') in ['pending', 'active', 'paused']:
                reserved_sessions.extend(task.get('selected_sessions', []))
        return list(set(reserved_sessions))
    
    def is_session_in_active_task(self, session_index):
        """Verifica se uma sessão está sendo usada em uma tarefa ativa"""
        active_sessions = self.get_active_task_sessions()
        return session_index in active_sessions
