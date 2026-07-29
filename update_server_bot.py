#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT SERVER DE ATUALIZAÇÕES
Gerencia atualizações centralizadas para múltiplos bots clientes
Hospedado em: 135.148.144.90
"""

import os
import json
import asyncio
import hashlib
import zipfile
import shutil
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, jsonify, send_file
import threading

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

# Carrega configurações do arquivo config.json
def load_config():
    """Carrega configurações do arquivo config.json"""
    config_file = "config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Erro ao carregar config.json: {e}")
            return None
    return None

# Tenta carregar configurações
config = load_config()

if config:
    UPDATE_BOT_TOKEN = config.get('bot_token', '')
    ADMIN_IDS = config.get('admin_ids', [])
    HTTP_PORT = config.get('http_port', 8080)
    print(f"✅ Configurações carregadas do config.json")
else:
    # Valores padrão se não houver config.json
    UPDATE_BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    ADMIN_IDS = []
    HTTP_PORT = 8080
    print(f"⚠️ Usando configurações padrão (config.json não encontrado)")

# Validação
if not UPDATE_BOT_TOKEN or UPDATE_BOT_TOKEN == "SEU_TOKEN_AQUI":
    print("=" * 60)
    print("❌ ERRO: Token do bot não configurado!")
    print("=" * 60)
    print("\n📋 Para configurar:")
    print("1. Crie um arquivo config.json com:")
    print('''
{
  "bot_token": "SEU_TOKEN_DO_BOTFATHER",
  "admin_ids": [123456789],
  "http_port": 8080
}
''')
    print("\n2. Ou defina a variável de ambiente:")
    print("   export BOT_TOKEN='seu_token_aqui'")
    print("\n3. Reinicie o serviço:")
    print("   systemctl restart update-server")
    print("=" * 60)
    exit(1)

if not ADMIN_IDS:
    print("⚠️ AVISO: Nenhum admin configurado! Adicione IDs no config.json")

# Diretório de atualizações
UPDATES_DIR = "updates"
CURRENT_UPDATE_FILE = "current_update.json"

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

os.makedirs(UPDATES_DIR, exist_ok=True)

bot = Bot(token=UPDATE_BOT_TOKEN)
dp = Dispatcher()

# Flask app para servir atualizações via HTTP
app = Flask(__name__)

# ============================================================================
# ARMAZENAMENTO DE DADOS
# ============================================================================

def load_current_update():
    """Carrega informações da atualização atual"""
    if os.path.exists(CURRENT_UPDATE_FILE):
        with open(CURRENT_UPDATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_current_update(update_data):
    """Salva informações da atualização atual"""
    with open(CURRENT_UPDATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(update_data, f, ensure_ascii=False, indent=2)

def calculate_file_hash(filepath):
    """Calcula hash SHA256 do arquivo"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# ============================================================================
# ROTAS HTTP (para os bots clientes consultarem)
# ============================================================================

@app.route('/version', methods=['GET'])
def get_version():
    """Retorna informações da versão atual disponível"""
    update_data = load_current_update()
    if update_data:
        return jsonify({
            'version': update_data['version'],
            'download_url': f"http://135.148.144.90:{HTTP_PORT}/download",
            'changelog': update_data['changelog'],
            'release_date': update_data['release_date'],
            'file_hash': update_data['file_hash']
        })
    return jsonify({'error': 'No update available'}), 404

@app.route('/download', methods=['GET'])
def download_update():
    """Permite download do arquivo de atualização"""
    update_data = load_current_update()
    if update_data and os.path.exists(update_data['file_path']):
        return send_file(
            update_data['file_path'],
            as_attachment=True,
            download_name='bot_update.zip'
        )
    return jsonify({'error': 'Update file not found'}), 404

@app.route('/stats', methods=['GET'])
def get_stats():
    """Retorna estatísticas do servidor"""
    update_data = load_current_update()
    return jsonify({
        'server': 'Bot Update Server',
        'status': 'online',
        'current_version': update_data['version'] if update_data else 'None',
        'updates_available': update_data is not None
    })

# ============================================================================
# COMANDOS DO BOT TELEGRAM
# ============================================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Comando inicial"""
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Acesso negado. Este bot é apenas para administradores.")
        return
    
    await message.reply(
        "🤖 <b>Bot Server de Atualizações</b>\n\n"
        "Bem-vindo ao sistema centralizado de atualizações!\n\n"
        "<b>📋 Comandos disponíveis:</b>\n"
        "/enviar - Enviar nova atualização\n"
        "/status - Ver status atual\n"
        "/versao - Ver versão disponível\n"
        "/logs - Ver logs de atualizações\n\n"
        "<b>🌐 Servidor HTTP:</b>\n"
        f"http://135.148.144.90:{HTTP_PORT}\n\n"
        "<b>📡 Endpoints:</b>\n"
        "• /version - Info da versão\n"
        "• /download - Download da atualização\n"
        "• /stats - Estatísticas",
        parse_mode="HTML"
    )

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    """Mostra status do servidor"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    update_data = load_current_update()
    
    if update_data:
        status_text = (
            "✅ <b>Servidor Online</b>\n\n"
            f"<b>📦 Versão Atual:</b> {update_data['version']}\n"
            f"<b>📅 Data de Release:</b> {update_data['release_date']}\n"
            f"<b>📝 Changelog:</b>\n{update_data['changelog']}\n\n"
            f"<b>🔗 URL de Download:</b>\n"
            f"http://135.148.144.90:{HTTP_PORT}/download\n\n"
            f"<b>🔐 Hash SHA256:</b>\n<code>{update_data['file_hash'][:32]}...</code>"
        )
    else:
        status_text = "⚠️ Nenhuma atualização disponível no momento."
    
    await message.reply(status_text, parse_mode="HTML")

@dp.message(Command("versao"))
async def cmd_versao(message: types.Message):
    """Mostra versão atual"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    update_data = load_current_update()
    
    if update_data:
        await message.reply(
            f"📦 <b>Versão Disponível:</b> {update_data['version']}\n"
            f"📅 <b>Release:</b> {update_data['release_date']}",
            parse_mode="HTML"
        )
    else:
        await message.reply("⚠️ Nenhuma versão disponível.")

# Estado para armazenar dados temporários durante o envio
user_states = {}

@dp.message(Command("enviar"))
async def cmd_enviar(message: types.Message):
    """Inicia processo de envio de atualização"""
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Acesso negado.")
        return
    
    user_states[message.from_user.id] = {'step': 'waiting_version'}
    
    await message.reply(
        "📦 <b>Enviar Nova Atualização</b>\n\n"
        "Por favor, envie a <b>versão</b> da atualização.\n"
        "Exemplo: <code>2.8.0</code>\n\n"
        "Use /cancelar para cancelar.",
        parse_mode="HTML"
    )

@dp.message(Command("cancelar"))
async def cmd_cancelar(message: types.Message):
    """Cancela processo de envio"""
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
        await message.reply("❌ Processo cancelado.")
    else:
        await message.reply("ℹ️ Nenhum processo ativo.")

@dp.message(F.text)
async def handle_text(message: types.Message):
    """Processa respostas de texto durante o envio"""
    user_id = message.from_user.id
    
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    
    if state['step'] == 'waiting_version':
        # Salva versão
        state['version'] = message.text.strip()
        state['step'] = 'waiting_changelog'
        
        await message.reply(
            f"✅ Versão: <b>{state['version']}</b>\n\n"
            "Agora envie o <b>changelog</b> (descrição das mudanças).\n"
            "Exemplo:\n"
            "<code>- Corrigido bug de rate limit\n"
            "- Adicionado comando /cancelartodos\n"
            "- Melhorias de performance</code>",
            parse_mode="HTML"
        )
    
    elif state['step'] == 'waiting_changelog':
        # Salva changelog
        state['changelog'] = message.text.strip()
        state['step'] = 'waiting_file'
        
        await message.reply(
            "✅ Changelog salvo!\n\n"
            "Agora envie o <b>arquivo ZIP</b> com a atualização.\n\n"
            "⚠️ O arquivo deve conter:\n"
            "• bot.py (arquivo principal atualizado)\n"
            "• Outros arquivos necessários\n\n"
            "📤 Envie o arquivo agora:",
            parse_mode="HTML"
        )

@dp.message(F.document)
async def handle_document(message: types.Message):
    """Processa arquivo enviado"""
    user_id = message.from_user.id
    
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    
    if state['step'] != 'waiting_file':
        return
    
    # Verifica se é um arquivo ZIP
    if not message.document.file_name.endswith('.zip'):
        await message.reply("❌ Por favor, envie um arquivo ZIP.")
        return
    
    await message.reply("⏳ Processando arquivo...")
    
    try:
        # Download do arquivo
        file = await bot.get_file(message.document.file_id)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = os.path.join(UPDATES_DIR, f"update_{state['version']}_{timestamp}.zip")
        
        await bot.download_file(file.file_path, file_path)
        
        # Calcula hash
        file_hash = calculate_file_hash(file_path)
        
        # Salva informações da atualização
        update_data = {
            'version': state['version'],
            'changelog': state['changelog'],
            'release_date': datetime.now().isoformat(),
            'file_path': file_path,
            'file_hash': file_hash,
            'file_size': os.path.getsize(file_path),
            'uploaded_by': user_id
        }
        
        save_current_update(update_data)
        
        # Limpa estado
        del user_states[user_id]
        
        # Confirmação
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Ver Status", callback_data="view_status")],
            [InlineKeyboardButton(text="🔗 Copiar URL", callback_data="copy_url")]
        ])
        
        await message.reply(
            "✅ <b>Atualização publicada com sucesso!</b>\n\n"
            f"<b>📦 Versão:</b> {update_data['version']}\n"
            f"<b>📅 Data:</b> {update_data['release_date'][:19]}\n"
            f"<b>📝 Changelog:</b>\n{update_data['changelog']}\n\n"
            f"<b>📊 Arquivo:</b>\n"
            f"• Tamanho: {update_data['file_size'] / 1024:.2f} KB\n"
            f"• Hash: <code>{file_hash[:16]}...</code>\n\n"
            f"<b>🌐 URL de Download:</b>\n"
            f"<code>http://135.148.144.90:{HTTP_PORT}/download</code>\n\n"
            "Os bots clientes receberão a atualização automaticamente!",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        print(f"✅ Nova atualização publicada: v{update_data['version']}")
        
    except Exception as e:
        await message.reply(f"❌ Erro ao processar arquivo: {e}")
        print(f"❌ Erro: {e}")

@dp.callback_query(F.data == "view_status")
async def callback_view_status(callback: types.CallbackQuery):
    """Callback para ver status"""
    await callback.answer()
    await cmd_status(callback.message)

@dp.callback_query(F.data == "copy_url")
async def callback_copy_url(callback: types.CallbackQuery):
    """Callback para copiar URL"""
    await callback.answer(
        f"URL copiada: http://135.148.144.90:{HTTP_PORT}/download",
        show_alert=True
    )

# ============================================================================
# INICIALIZAÇÃO DO SERVIDOR
# ============================================================================

def run_flask():
    """Executa servidor Flask em thread separada"""
    app.run(host='0.0.0.0', port=HTTP_PORT, debug=False)

async def main():
    """Função principal"""
    print("=" * 60)
    print("🚀 BOT SERVER DE ATUALIZAÇÕES")
    print("=" * 60)
    print(f"🌐 Servidor HTTP: http://135.148.144.90:{HTTP_PORT}")
    print(f"📡 Endpoints disponíveis:")
    print(f"   • /version - Informações da versão")
    print(f"   • /download - Download da atualização")
    print(f"   • /stats - Estatísticas do servidor")
    print("=" * 60)
    print("✅ Servidor iniciado! Aguardando comandos...\n")
    
    # Inicia Flask em thread separada
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Inicia bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
