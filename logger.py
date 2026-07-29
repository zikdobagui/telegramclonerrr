"""
Sistema de Logging Centralizado
Todos os logs do sistema são salvos aqui para debug
"""

import logging
import os
from datetime import datetime
from config import DATA_DIR

class CentralLogger:
    def __init__(self):
        self.log_file = os.path.join(DATA_DIR, 'system.log')
        
        # Configura o logger
        self.logger = logging.getLogger('TelegramAutomation')
        self.logger.setLevel(logging.DEBUG)
        
        # Remove handlers existentes
        self.logger.handlers = []
        
        # Handler para arquivo
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formato dos logs
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def debug(self, message, module='SYSTEM'):
        """Log de debug"""
        self.logger.debug(f'[{module}] {message}')
    
    def info(self, message, module='SYSTEM'):
        """Log de informação"""
        self.logger.info(f'[{module}] {message}')
    
    def warning(self, message, module='SYSTEM'):
        """Log de aviso"""
        self.logger.warning(f'[{module}] {message}')
    
    def error(self, message, module='SYSTEM', exc_info=False):
        """Log de erro"""
        self.logger.error(f'[{module}] {message}', exc_info=exc_info)
    
    def critical(self, message, module='SYSTEM', exc_info=False):
        """Log crítico"""
        self.logger.critical(f'[{module}] {message}', exc_info=exc_info)
    
    def separator(self):
        """Adiciona separador visual"""
        self.logger.info('=' * 80)
    
    def section(self, title):
        """Inicia uma nova seção"""
        self.separator()
        self.logger.info(f'  {title}')
        self.separator()

# Instância global
central_logger = CentralLogger()

# Funções de conveniência
def log_debug(message, module='SYSTEM'):
    central_logger.debug(message, module)

def log_info(message, module='SYSTEM'):
    central_logger.info(message, module)

def log_warning(message, module='SYSTEM'):
    central_logger.warning(message, module)

def log_error(message, module='SYSTEM', exc_info=False):
    central_logger.error(message, module, exc_info)

def log_critical(message, module='SYSTEM', exc_info=False):
    central_logger.critical(message, module, exc_info)

def log_separator():
    central_logger.separator()

def log_section(title):
    central_logger.section(title)
