# TiranoGio_App/core/banco_dados.py

import sqlite3
import os
import json

class GerenciadorBancoDados:
    def __init__(self, db_path="tiranogio_data.db"):
        self.db_path = db_path
        
        # A MÁGICA: O sistema continua achando que é o mesmo dicionário de antes
        self.config_cnc = {
            "maquina": {},
            "ferramentas": []
        }
        self.pos_processadores = {}
        
        self.carregar_dados_sqlite()
        self.carregar_pos_processadores()

    def conectar(self):
        return sqlite3.connect(self.db_path)

    def carregar_dados_sqlite(self):
        """Lê do banco blindado e monta o dicionário em memória para a UI"""
        if not os.path.exists(self.db_path):
            return

        with self.conectar() as conn:
            conn.row_factory = sqlite3.Row # Permite acessar as colunas pelo nome
            cursor = conn.cursor()
            
            # 1. Carrega as Configurações da Máquina
            cursor.execute("SELECT * FROM config_maquina WHERE id = 1")
            maq_db = cursor.fetchone()
            if maq_db:
                self.config_cnc["maquina"] = dict(maq_db)
                
            # 2. Carrega as Ferramentas
            cursor.execute("SELECT * FROM ferramentas")
            ferramentas_db = cursor.fetchall()
            
            self.config_cnc["ferramentas"] = []
            for f in ferramentas_db:
                f_dict = dict(f)
                # O banco usa 'id_ferramenta', mas o sistema antigo espera 'id'
                f_dict["id"] = f_dict.pop("id_ferramenta")
                self.config_cnc["ferramentas"].append(f_dict)

    def salvar_config_cnc(self):
        """Desconstrói o dicionário e salva de volta no SQLite (Inviolável)"""
        with self.conectar() as conn:
            cursor = conn.cursor()
            
            # 1. Salva a Máquina
            maq = self.config_cnc.get("maquina", {})
            if maq:
                cursor.execute('''
                    UPDATE config_maquina SET 
                        sobrecorte_mm = ?, angulo_rampa_graus = ?, z_seguranca_add = ?, 
                        usar_tabs = ?, tab_largura = ?, tab_espessura = ?
                    WHERE id = 1
                ''', (
                    maq.get("sobrecorte_mm", 0.5), maq.get("angulo_rampa_graus", 15.0),
                    maq.get("z_seguranca_add", 15.0), int(maq.get("usar_tabs", 1)),
                    maq.get("tab_largura", 5.0), maq.get("tab_espessura", 2.0)
                ))

            # 2. Salva as Ferramentas
            ferramentas = self.config_cnc.get("ferramentas", [])
            cursor.execute("DELETE FROM ferramentas") # Limpa para regravar
            
            for f in ferramentas:
                cursor.execute('''
                    INSERT INTO ferramentas 
                    (id_ferramenta, cone, tipo, min_d, max_d, z_desce, rpm, mergulho, corte)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    f.get("id", "Desc"), f.get("cone", "T1"), f.get("tipo", "corte"),
                    float(f.get("min_d", 0.0)), float(f.get("max_d", 0.0)), str(f.get("z_desce", "passante")),
                    int(f.get("rpm", 18000)), int(f.get("mergulho", 3000)), int(f.get("corte", 8000))
                ))
            conn.commit()

    def carregar_pos_processadores(self):
        """Mantém a leitura temporária do JSON de pós-processadores"""
        caminho = "pos_processadores.json"
        if os.path.exists(caminho):
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    self.pos_processadores = json.load(f)
            except Exception as e:
                print(f"Erro ao carregar pos_processadores: {e}")

    def buscar_ferramenta(self, tipo_desejado, diametro_alvo=None):
        """Motor de busca de fresas usado pelo gerador de G-Code"""
        melhor_ferramenta = None
        for f in self.config_cnc.get("ferramentas", []):
            if f.get("tipo") == tipo_desejado:
                if diametro_alvo:
                    min_d = float(f.get("min_d", 0))
                    max_d = float(f.get("max_d", 0))
                    if min_d <= diametro_alvo <= max_d:
                        melhor_ferramenta = f
                        break
                else:
                    melhor_ferramenta = f
                    break
        return melhor_ferramenta