# TiranoGio_App/core/logger.py

import logging
from logging.handlers import RotatingFileHandler
import os

class GerenciadorLogs:
    def __init__(self, pasta_logs="logs"):
        # Cria a pasta de logs se ela não existir
        if not os.path.exists(pasta_logs):
            os.makedirs(pasta_logs)
            
        arquivo_log = os.path.join(pasta_logs, "tiranogio_sistema.log")
        
        # Configura o Logger (Usa RotatingFileHandler para o arquivo não ficar gigante com o tempo, limite de 5MB)
        self.logger = logging.getLogger("TiranoGio")
        self.logger.setLevel(logging.DEBUG)
        
        # Evita duplicar logs se a classe for instanciada duas vezes
        if not self.logger.handlers:
            formato = logging.Formatter('%(asctime)s | [%(levelname)s] | %(filename)s:%(lineno)d | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            
            # Handler para o Arquivo (Gravando no PC do Cliente)
            file_handler = RotatingFileHandler(arquivo_log, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
            file_handler.setFormatter(formato)
            file_handler.setLevel(logging.ERROR) # Grava apenas ERROS e AVISOS no arquivo
            
            # Handler para o Console (Aparece no seu terminal do VSCode)
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formato)
            console_handler.setLevel(logging.DEBUG) # Mostra tudo no terminal
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
            
        self.logger.info("=== SISTEMA TIRANOGIO V12 INICIADO ===")

    def info(self, mensagem):
        self.logger.info(mensagem)

    def aviso(self, mensagem):
        self.logger.warning(mensagem)

    def erro(self, mensagem, exc_info=True):
        """Grava o erro com o rastro (traceback) completo para você achar o defeito"""
        self.logger.error(mensagem, exc_info=exc_info)