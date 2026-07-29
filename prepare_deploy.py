#!/usr/bin/env python3
"""
Script para preparar o projeto para deploy no Discloud
Cria um arquivo ZIP com apenas os arquivos necessários
"""

import os
import zipfile
import shutil
from datetime import datetime

def create_deployment_zip():
    """Cria arquivo ZIP para deploy"""
    
    # Nome do arquivo ZIP
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f'telegram_automation_deploy_{timestamp}.zip'
    
    # Arquivos e pastas para incluir
    include_files = [
        'app.py',
        'config.py',
        'logger.py',
        'session_manager.py',
        'extractor.py',
        'adder.py',
        'smart_adder.py',
        'automation_manager.py',
        'warming_bot.py',
        'requirements.txt',
        'discloud.config',
        'Procfile',
        '.discloudignore'
    ]
    
    include_folders = [
        'templates',
        'static',
        'sessions',  # Pasta vazia será criada
        'data'       # Pasta vazia será criada
    ]
    
    # Arquivos para excluir
    exclude_patterns = [
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '*.log',
        '.git',
        '.vscode',
        '*.md',
        'test_*.py',
        '*_test.py',
        '*.backup',
        '*.bak'
    ]
    
    print(f'📦 Criando arquivo de deploy: {zip_filename}')
    print('='*60)
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Adiciona arquivos individuais
        for file in include_files:
            if os.path.exists(file):
                zipf.write(file)
                print(f'✅ Adicionado: {file}')
            else:
                print(f'⚠️  Não encontrado: {file}')
        
        # Adiciona pastas
        for folder in include_folders:
            if os.path.exists(folder):
                for root, dirs, files in os.walk(folder):
                    # Remove pastas excluídas
                    dirs[:] = [d for d in dirs if d not in exclude_patterns]
                    
                    for file in files:
                        # Verifica se arquivo deve ser excluído
                        should_exclude = False
                        for pattern in exclude_patterns:
                            if pattern.startswith('*'):
                                if file.endswith(pattern[1:]):
                                    should_exclude = True
                                    break
                            elif pattern.endswith('*'):
                                if file.startswith(pattern[:-1]):
                                    should_exclude = True
                                    break
                            elif pattern in file:
                                should_exclude = True
                                break
                        
                        if not should_exclude:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path)
                            print(f'✅ Adicionado: {file_path}')
            else:
                # Cria pasta vazia no ZIP
                zipf.writestr(folder + '/', '')
                print(f'📁 Pasta criada: {folder}/')
    
    print('='*60)
    print(f'✅ Arquivo criado com sucesso: {zip_filename}')
    print(f'📊 Tamanho: {os.path.getsize(zip_filename) / 1024:.2f} KB')
    print()
    print('🚀 Próximos passos:')
    print('1. Acesse: https://discloud.app/dashboard')
    print('2. Faça upload do arquivo:', zip_filename)
    print('3. Aguarde o deploy completar')
    print('4. Acesse: https://telegram-clone-site.discloud.app')
    print()
    print('📖 Leia DEPLOY_DISCLOUD.md para mais informações')

if __name__ == '__main__':
    try:
        create_deployment_zip()
    except Exception as e:
        print(f'❌ Erro ao criar arquivo: {e}')
        import traceback
        traceback.print_exc()
