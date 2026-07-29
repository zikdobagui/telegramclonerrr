"""
Script para migrar sessões antigas do Telethon para o novo formato SQLite
Corrige o erro: "table update_state has 6 columns but 5 values were supplied"
"""

import sqlite3
import os
import shutil
from pathlib import Path

def migrate_session(session_path):
    """Migra uma sessão do formato antigo para o novo"""
    try:
        # Faz backup
        backup_path = session_path + '.backup'
        shutil.copy2(session_path, backup_path)
        
        # Aguarda um pouco para garantir que o arquivo não está em uso
        import time
        time.sleep(0.3)
        
        # Conecta ao banco com timeout maior
        conn = sqlite3.connect(session_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Verifica se a tabela update_state existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='update_state'")
        if not cursor.fetchone():
            conn.close()
            os.remove(backup_path)
            return True, "Tabela update_state não existe (sessão já está no formato correto)"
        
        # Pega a estrutura atual da tabela
        cursor.execute("PRAGMA table_info(update_state)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Se já tem 6 colunas, não precisa migrar
        if len(column_names) == 6:
            conn.close()
            os.remove(backup_path)
            return True, "Sessão já está no formato correto"
        
        # Pega os dados atuais
        cursor.execute("SELECT * FROM update_state")
        old_data = cursor.fetchall()
        
        # Remove a tabela antiga
        cursor.execute("DROP TABLE update_state")
        
        # Cria a nova tabela com 6 colunas (formato novo do Telethon)
        cursor.execute("""
            CREATE TABLE update_state (
                id INTEGER PRIMARY KEY,
                pts INTEGER NOT NULL,
                qts INTEGER NOT NULL,
                date INTEGER NOT NULL,
                seq INTEGER NOT NULL,
                unread_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        
        # Migra os dados antigos para o novo formato
        if old_data:
            for row in old_data:
                # Se tinha 5 colunas, adiciona unread_count=0 como 6ª coluna
                if len(row) == 5:
                    new_row = list(row) + [0]  # Adiciona unread_count=0
                else:
                    new_row = row
                
                cursor.execute("""
                    INSERT INTO update_state (id, pts, qts, date, seq, unread_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, new_row)
        
        # Salva as mudanças
        conn.commit()
        conn.close()
        
        # Aguarda um pouco antes de remover o backup
        time.sleep(0.2)
        
        # Remove o backup se deu tudo certo
        os.remove(backup_path)
        
        return True, "Migração bem-sucedida"
        
    except sqlite3.OperationalError as e:
        # Se o banco está bloqueado, retorna erro específico
        if 'locked' in str(e).lower():
            # Tenta restaurar o backup
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, session_path)
                    os.remove(backup_path)
                except:
                    pass
            return False, "Banco de dados em uso - tente novamente"
        
        # Restaura o backup para outros erros
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, session_path)
            os.remove(backup_path)
        
        return False, f"Erro SQLite: {str(e)}"
        
    except Exception as e:
        # Restaura o backup se algo deu errado
        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, session_path)
                os.remove(backup_path)
            except:
                pass
        
        return False, f"Erro na migração: {str(e)}"

def migrate_all_sessions(sessions_dir):
    """Migra todas as sessões em um diretório"""
    sessions_dir = Path(sessions_dir)
    
    if not sessions_dir.exists():
        return {'success': False, 'error': 'Diretório não encontrado'}
    
    # Encontra todos os arquivos .session
    session_files = list(sessions_dir.glob('*.session'))
    
    if not session_files:
        return {'success': False, 'error': 'Nenhuma sessão encontrada'}
    
    results = {
        'total': len(session_files),
        'migrated': 0,
        'already_correct': 0,
        'failed': 0,
        'details': []
    }
    
    for session_file in session_files:
        session_name = session_file.stem
        success, message = migrate_session(str(session_file))
        
        if success:
            if 'já está no formato correto' in message:
                results['already_correct'] += 1
            else:
                results['migrated'] += 1
        else:
            results['failed'] += 1
        
        results['details'].append({
            'session': session_name,
            'success': success,
            'message': message
        })
    
    results['success'] = True
    return results

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: py migrate_sessions.py <diretório_das_sessões>")
        sys.exit(1)
    
    sessions_dir = sys.argv[1]
    
    print(f"🔄 Migrando sessões em: {sessions_dir}")
    print()
    
    results = migrate_all_sessions(sessions_dir)
    
    if results['success']:
        print(f"✅ Migração completa!")
        print(f"   Total: {results['total']} sessões")
        print(f"   ✅ Migradas: {results['migrated']}")
        print(f"   ℹ️  Já corretas: {results['already_correct']}")
        print(f"   ❌ Falhas: {results['failed']}")
        print()
        
        if results['failed'] > 0:
            print("Sessões com falha:")
            for detail in results['details']:
                if not detail['success']:
                    print(f"   ❌ {detail['session']}: {detail['message']}")
    else:
        print(f"❌ Erro: {results['error']}")
