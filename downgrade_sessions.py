"""
Script para fazer downgrade de sessões do Telethon
Remove a 6ª coluna (unread_count) para funcionar com versões antigas
"""

import sqlite3
import os
import shutil
from pathlib import Path

def downgrade_session(session_path):
    """Faz downgrade de uma sessão do formato novo para o antigo"""
    try:
        # Faz backup
        backup_path = session_path + '.backup'
        shutil.copy2(session_path, backup_path)
        
        # Aguarda um pouco
        import time
        time.sleep(0.2)
        
        # Conecta ao banco
        conn = sqlite3.connect(session_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Verifica se a tabela update_state existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='update_state'")
        if not cursor.fetchone():
            conn.close()
            os.remove(backup_path)
            return True, "Tabela update_state não existe"
        
        # Pega a estrutura atual
        cursor.execute("PRAGMA table_info(update_state)")
        columns = cursor.fetchall()
        
        # Se já tem 5 colunas, não precisa fazer downgrade
        if len(columns) == 5:
            conn.close()
            os.remove(backup_path)
            return True, "Sessão já está no formato antigo (5 colunas)"
        
        # Se não tem 6 colunas, algo está errado
        if len(columns) != 6:
            conn.close()
            os.remove(backup_path)
            return False, f"Formato inesperado: {len(columns)} colunas"
        
        # Pega os dados atuais (apenas as primeiras 5 colunas)
        cursor.execute("SELECT id, pts, qts, date, seq FROM update_state")
        old_data = cursor.fetchall()
        
        # Remove a tabela antiga
        cursor.execute("DROP TABLE update_state")
        
        # Cria a nova tabela com 5 colunas (formato antigo do Telethon)
        cursor.execute("""
            CREATE TABLE update_state (
                id INTEGER PRIMARY KEY,
                pts INTEGER NOT NULL,
                qts INTEGER NOT NULL,
                date INTEGER NOT NULL,
                seq INTEGER NOT NULL
            )
        """)
        
        # Insere os dados
        if old_data:
            for row in old_data:
                cursor.execute("""
                    INSERT INTO update_state (id, pts, qts, date, seq)
                    VALUES (?, ?, ?, ?, ?)
                """, row)
        
        # Salva
        conn.commit()
        conn.close()
        
        time.sleep(0.2)
        os.remove(backup_path)
        
        return True, "Downgrade bem-sucedido (6 → 5 colunas)"
        
    except Exception as e:
        # Restaura backup
        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, session_path)
                os.remove(backup_path)
            except:
                pass
        
        return False, f"Erro: {str(e)}"

def downgrade_all_sessions(sessions_dir):
    """Faz downgrade de todas as sessões"""
    sessions_dir = Path(sessions_dir)
    
    if not sessions_dir.exists():
        return {'success': False, 'error': 'Diretório não encontrado'}
    
    session_files = list(sessions_dir.glob('*.session'))
    
    if not session_files:
        return {'success': False, 'error': 'Nenhuma sessão encontrada'}
    
    results = {
        'total': len(session_files),
        'downgraded': 0,
        'already_old': 0,
        'failed': 0,
        'details': []
    }
    
    for session_file in session_files:
        session_name = session_file.stem
        success, message = downgrade_session(str(session_file))
        
        if success:
            if 'já está no formato antigo' in message:
                results['already_old'] += 1
            else:
                results['downgraded'] += 1
        else:
            results['failed'] += 1
        
        results['details'].append({
            'session': session_name,
            'success': success,
            'message': message
        })
    
    results['success'] = True
    return results
