#!/usr/bin/env python3
"""
Script para forçar atualização manual do contador de uma tarefa
"""
import json
import sys
import os
import glob

def update_task_counter_for_user(username, task_id, added_today, total_added):
    """Atualiza manualmente o contador de uma tarefa de um usuário específico"""
    
    # Procura o arquivo do usuário
    possible_paths = [
        f'users/{username}/data/automation_config.json',
        f'web_app/users/{username}/data/automation_config.json',
    ]
    
    config_file = None
    for path in possible_paths:
        if os.path.exists(path):
            config_file = path
            break
    
    if not config_file:
        print(f'\n❌ Arquivo não encontrado para usuário: {username}')
        print(f'\n💡 Procurei em:')
        for path in possible_paths:
            print(f'   - {path}')
        print()
        return False
    
    print(f'\n📁 Arquivo encontrado: {config_file}')
    
    try:
        # Lê o arquivo de configuração
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Procura a tarefa (pode estar em 'tasks' ou 'groups')
        task_found = False
        tasks_list = config.get('tasks', []) or config.get('groups', [])
        
        for task in tasks_list:
            if task['id'] == task_id:
                task_found = True
                old_today = task.get('added_today', 0)
                old_total = task.get('total_added', 0)
                
                # Atualiza os contadores
                task['added_today'] = added_today
                task['total_added'] = total_added
                
                print(f'\n✅ Tarefa #{task_id} atualizada!')
                print(f'   Grupo: {task.get("group_link", "N/A")}')
                print(f'   Hoje: {old_today} → {added_today}')
                print(f'   Total: {old_total} → {total_added}')
                break
        
        if not task_found:
            print(f'\n❌ Tarefa #{task_id} não encontrada!')
            print(f'\n💡 Tarefas disponíveis:')
            for task in tasks_list:
                print(f'   - Tarefa #{task["id"]}: {task.get("group_link", "N/A")}')
            return False
        
        # Salva o arquivo
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f'\n💾 Arquivo salvo: {config_file}')
        print(f'\n💡 Recarregue a página para ver as mudanças!\n')
        return True
        
    except Exception as e:
        print(f'\n❌ Erro: {e}\n')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print('\n🔧 ATUALIZAÇÃO MANUAL DE CONTADOR DE TAREFA\n')
    print('=' * 60)
    
    # Se não passou argumentos, lista os usuários e tarefas
    if len(sys.argv) == 1:
        print('\n📋 LISTANDO USUÁRIOS E TAREFAS:\n')
        
        # Procura todos os arquivos de configuração
        configs = glob.glob('users/*/data/automation_config.json')
        configs.extend(glob.glob('web_app/users/*/data/automation_config.json'))
        
        if not configs:
            print('❌ Nenhum arquivo de configuração encontrado!\n')
            sys.exit(1)
        
        for config_path in configs:
            username = config_path.split(os.sep)[1] if 'users' in config_path else 'unknown'
            print(f'\n👤 Usuário: {username}')
            print(f'   📁 Arquivo: {config_path}')
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                tasks = config.get('tasks', []) or config.get('groups', [])
                if tasks:
                    print(f'   📋 Tarefas:')
                    for task in tasks:
                        print(f'      - Tarefa #{task["id"]}: {task.get("group_link", "N/A")}')
                        print(f'        Hoje: {task.get("added_today", 0)}/{task.get("daily_limit", 0)}')
                        print(f'        Total: {task.get("total_added", 0)}/{task.get("target_members", 0)}')
                else:
                    print(f'   ⚠️  Sem tarefas')
            except Exception as e:
                print(f'   ❌ Erro ao ler: {e}')
        
        print('\n' + '=' * 60)
        print('\nUso: python force_update_task.py <username> <task_id> <added_today> <total_added>')
        print('\nExemplo:')
        print('  python force_update_task.py itachidev 1 50 150')
        print('  (Atualiza tarefa #1 do usuário itachidev para 50 hoje e 150 total)\n')
        sys.exit(0)
    
    if len(sys.argv) != 5:
        print('\nUso: python force_update_task.py <username> <task_id> <added_today> <total_added>')
        print('\nExemplo:')
        print('  python force_update_task.py itachidev 1 50 150')
        print('  (Atualiza tarefa #1 do usuário itachidev para 50 hoje e 150 total)')
        print('\nPara listar usuários e tarefas, execute sem argumentos:')
        print('  python force_update_task.py\n')
        sys.exit(1)
    
    username = sys.argv[1]
    task_id = int(sys.argv[2])
    added_today = int(sys.argv[3])
    total_added = int(sys.argv[4])
    
    print(f'\n👤 Usuário: {username}')
    print(f'📋 Tarefa: #{task_id}')
    print(f'   Hoje: {added_today}')
    print(f'   Total: {total_added}\n')
    
    update_task_counter_for_user(username, task_id, added_today, total_added)
