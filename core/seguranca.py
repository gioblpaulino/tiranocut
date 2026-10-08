# TiranoGio_App/core/seguranca.py

import os
import subprocess
import hashlib
from tkinter import messagebox, simpledialog
import tkinter as tk

class GerenciadorLicenca:
    def __init__(self, salt_secreto="TiranoGio_SuperSecret_2026!@#"):
        # O Salt é a sua "assinatura". Se alguém tentar adivinhar a chave, não vai conseguir 
        # sem saber essa frase exata. NÃO MUDE ESSE TEXTO depois de gerar a primeira licença!
        self.salt = salt_secreto
        self.arquivo_licenca = "licenca.key"

    def obter_id_maquina(self):
        """Busca o UUID da Placa-Mãe (Funciona no Windows)"""
        try:
            # Comando PowerShell para ler a BIOS/Placa-Mãe (Difícil de fraudar)
            cmd = 'powershell.exe -Command "(Get-CimInstance -Class Win32_ComputerSystemProduct).UUID"'
            resultado = subprocess.check_output(cmd, shell=True, text=True)
            uid = resultado.strip()
            
            if not uid or "Ocorreu um erro" in uid:
                raise Exception("UUID não encontrado")
            return uid
        except Exception:
            # Fallback de emergência: Tenta ler o Serial do HD principal (C:)
            try:
                cmd_fallback = 'vol C:'
                resultado = subprocess.check_output(cmd_fallback, shell=True, text=True)
                uid_hd = resultado.strip().split("\n")[-1].strip()
                return uid_hd
            except:
                return "MAQUINA_DESCONHECIDA"

    def gerar_hash_esperado(self, maquina_id):
        """Mistura o ID da máquina com o seu Salt e gera o código da chave"""
        texto_base = f"{maquina_id}{self.salt}".encode('utf-8')
        # Cria um hash SHA-256 (Padrão ouro de segurança)
        hash_completo = hashlib.sha256(texto_base).hexdigest()
        # Retorna só os primeiros 20 caracteres para a chave não ficar gigante
        return hash_completo[:20].upper()

    def verificar_licenca(self):
        """Lê o arquivo licenca.key e cruza com a máquina atual"""
        maquina_id = self.obter_id_maquina()
        chave_esperada = self.gerar_hash_esperado(maquina_id)

        # Se o arquivo não existir, já barra na hora
        if not os.path.exists(self.arquivo_licenca):
            return False, maquina_id

        # Lê a chave que o cliente colocou na pasta
        try:
            with open(self.arquivo_licenca, 'r', encoding='utf-8') as f:
                chave_instalada = f.read().strip()
                
            if chave_instalada == chave_esperada:
                return True, maquina_id
            else:
                return False, maquina_id
        except Exception:
            return False, maquina_id