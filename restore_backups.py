"""
Script para restaurar sessões dos backups criados pelo downgrade
"""

import os
import shutil
from pathlib import Path

def restore_session_backup(session_path):
    """Restaura uma sessão do backup"""
    backup_path = session_path + '.backup'
    
    if not os.path.exists(backup_path):
        return False, "Backup não encontrado"
    
    try:
        # Restaura o backup
        shutil.copy2(backup_path, session_path)
        
        # Remove o backup
        os.remove(backup_path)
        
        return True, "Backup restaurado com sucesso"
    except Exception as e:
        return False, f"Erro ao restaurar: {str(e)}"

def restore_all_backups(sessions_dir):
    """Restaura todos os backups em um diretório"""
    sessions_dir = Path(sessions_dir)
    
    if not sessions_dir.exists():
        return {'success': False, 'error': 'Diretório não encontrado'}
    
    # Encontra todos os arquivos .backup
    backup_files = list(sessions_dir.glob('*.session.backup'))
    
    if not backup_files:
        return {'success': False, 'error': 'Nenhum backup encontrado'}
    
    results = {
        'total': len(backup_files),
        'restored': 0,
        'failed': 0,
        'details': []
    }
    
    for backup_file in backup_files:
        # Remove o .backup do nome para pegar o caminho da sessão original
        session_path = str(backup_file)[:-7]  # Remove '.backup'
        session_name = Path(session_path).stem
        
        success, message = restore_session_backup(session_path)
        
        if success:
            results['restored'] += 1
        else:
            results['failed'] += 1
        
        results['details'].append({
            'session': session_name,
            'success': success,
            'message': message
        })
    
    results['success'] = True
    return results
