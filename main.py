import os
import json
import time
from session_manager import SessionManager
from extractor import MemberExtractor
from adder import MemberAdder
from config import CONFIG_FILE, DATA_DIR

class TelegramAutomation:
    def __init__(self):
        self.session_manager = SessionManager()
        self.api_id = None
        self.api_hash = None
        self.load_api_config()
    
    def load_api_config(self):
        """Carrega configurações da API"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                self.api_id = data.get('api_id')
                self.api_hash = data.get('api_hash')
    
    def save_api_config(self):
        """Salva configurações da API"""
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
        
        data['api_id'] = self.api_id
        data['api_hash'] = self.api_hash
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    
    def configure_api(self):
        """Configura API ID e Hash"""
        print('\n🔧 Configuração da API do Telegram')
        print('Obtenha suas credenciais em: https://my.telegram.org/apps')
        print('-' * 60)
        
        api_id = input('API ID: ').strip()
        api_hash = input('API Hash: ').strip()
        
        if api_id and api_hash:
            self.api_id = int(api_id)
            self.api_hash = api_hash
            self.save_api_config()
            print('✅ API configurada com sucesso!')
        else:
            print('❌ Configuração cancelada')
    
    def menu_sessions(self):
        """Menu de gerenciamento de sessões"""
        while True:
            print('\n' + '='*60)
            print('📱 GERENCIAMENTO DE SESSÕES')
            print('='*60)
            print('1. Adicionar nova sessão')
            print('2. Listar sessões')
            print('3. Ativar/Desativar sessão')
            print('4. Remover sessão')
            print('0. Voltar')
            print('-' * 60)
            
            choice = input('Escolha: ').strip()
            
            if choice == '1':
                if not self.api_id or not self.api_hash:
                    print('\n⚠️  Configure a API primeiro!')
                    self.configure_api()
                    continue
                
                phone = input('\nTelefone (com código do país, ex: +5511999999999): ')
                self.session_manager.add_session(phone, self.api_id, self.api_hash)
                
            elif choice == '2':
                self.session_manager.list_sessions()
                
            elif choice == '3':
                self.session_manager.list_sessions()
                try:
                    idx = int(input('\nNúmero da sessão: ')) - 1
                    if self.session_manager.toggle_session(idx):
                        print('✅ Status alterado!')
                except:
                    print('❌ Número inválido')
                    
            elif choice == '4':
                self.session_manager.list_sessions()
                try:
                    idx = int(input('\nNúmero da sessão para remover: ')) - 1
                    confirm = input('Confirma remoção? (s/n): ')
                    if confirm.lower() == 's':
                        self.session_manager.remove_session(idx)
                except:
                    print('❌ Número inválido')
                    
            elif choice == '0':
                break
    
    def menu_extract(self):
        """Menu de extração de membros"""
        print('\n' + '='*60)
        print('🔍 EXTRAÇÃO DE MEMBROS')
        print('='*60)
        
        sessions = self.session_manager.get_active_sessions()
        if not sessions:
            print('⚠️  Nenhuma sessão ativa disponível')
            return
        
        print('\nSessões disponíveis:')
        for i, s in enumerate(sessions, 1):
            print(f"{i}. {s['first_name']} (@{s['username']})")
        
        try:
            idx = int(input('\nEscolha a sessão: ')) - 1
            session = sessions[idx]
        except:
            print('❌ Sessão inválida')
            return
        
        group_link = input('Link/Username do grupo para extrair: ').strip()
        
        if not group_link:
            print('❌ Link inválido')
            return
        
        extractor = MemberExtractor(self.api_id, self.api_hash)
        extractor.extract_members(session, group_link)
    
    def menu_add(self):
        """Menu de adição de membros"""
        print('\n' + '='*60)
        print('➕ ADIÇÃO DE MEMBROS')
        print('='*60)
        
        sessions = self.session_manager.get_active_sessions()
        if not sessions:
            print('⚠️  Nenhuma sessão ativa disponível')
            return
        
        extractor = MemberExtractor(self.api_id, self.api_hash)
        pending = extractor.get_pending_members()
        
        if not pending:
            print('⚠️  Nenhum membro pendente. Extraia membros primeiro!')
            return
        
        print(f'\n📊 Membros pendentes: {len(pending)}')
        print(f'📱 Sessões ativas: {len(sessions)}')
        
        target_group = input('\nLink/Username do grupo alvo: ').strip()
        if not target_group:
            print('❌ Link inválido')
            return
        
        try:
            members_per_session = int(input('Membros por sessão (padrão 50): ') or 50)
            delay_between_adds = int(input('Delay entre adições em segundos (padrão 2): ') or 2)
            delay_between_sessions = int(input('Delay entre sessões em segundos (padrão 60): ') or 60)
        except:
            print('❌ Valores inválidos')
            return
        
        print('\n' + '='*60)
        print('🚀 INICIANDO PROCESSO DE ADIÇÃO')
        print('='*60)
        
        adder = MemberAdder(self.api_id, self.api_hash)
        total_added = 0
        
        for i, session in enumerate(sessions, 1):
            print(f'\n[{i}/{len(sessions)}] Processando sessão...')
            
            added = adder.add_members(
                session,
                target_group,
                members_per_session,
                delay_between_adds
            )
            
            total_added += added
            
            # Verifica se ainda há membros pendentes
            pending = extractor.get_pending_members()
            if not pending:
                print('\n✅ Todos os membros foram processados!')
                break
            
            # Delay entre sessões
            if i < len(sessions):
                print(f'\n⏳ Aguardando {delay_between_sessions}s antes da próxima sessão...')
                time.sleep(delay_between_sessions)
        
        print('\n' + '='*60)
        print(f'✅ PROCESSO FINALIZADO')
        print(f'📊 Total adicionado: {total_added} membros')
        print('='*60)
    
    def main_menu(self):
        """Menu principal"""
        while True:
            print('\n' + '='*60)
            print('🤖 TELEGRAM AUTOMATION SYSTEM')
            print('='*60)
            print('1. Gerenciar Sessões')
            print('2. Extrair Membros')
            print('3. Adicionar Membros')
            print('4. Configurar API')
            print('5. Status do Sistema')
            print('0. Sair')
            print('-' * 60)
            
            choice = input('Escolha: ').strip()
            
            if choice == '1':
                self.menu_sessions()
            elif choice == '2':
                self.menu_extract()
            elif choice == '3':
                self.menu_add()
            elif choice == '4':
                self.configure_api()
            elif choice == '5':
                self.show_status()
            elif choice == '0':
                print('\n👋 Até logo!')
                break
    
    def show_status(self):
        """Mostra status do sistema"""
        print('\n' + '='*60)
        print('📊 STATUS DO SISTEMA')
        print('='*60)
        
        print(f'API ID: {"✅ Configurado" if self.api_id else "❌ Não configurado"}')
        print(f'API Hash: {"✅ Configurado" if self.api_hash else "❌ Não configurado"}')
        
        sessions = self.session_manager.sessions
        active_sessions = self.session_manager.get_active_sessions()
        print(f'\nSessões: {len(sessions)} total, {len(active_sessions)} ativas')
        
        extractor = MemberExtractor(self.api_id, self.api_hash)
        all_members = extractor.load_members()
        pending = extractor.get_pending_members()
        added = len(all_members) - len(pending)
        
        print(f'\nMembros extraídos: {len(all_members)}')
        print(f'Membros adicionados: {added}')
        print(f'Membros pendentes: {len(pending)}')
        print('='*60)

if __name__ == '__main__':
    app = TelegramAutomation()
    app.main_menu()
