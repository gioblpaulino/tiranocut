# TiranoGio_App/core/hodometro.py

import json
import os

class HodometroFerramentas:
    """Gaveta responsável por gerenciar o desgaste (em metros lineares) das ferramentas da CNC."""
    
    def __init__(self, app_core):
        self.app = app_core
        self.arquivo_db = "config_ferramentas.json"
        self.ferramentas = self.carregar_db()

    def carregar_db(self):
        # Se o arquivo já existe, carrega a quilometragem atual
        if os.path.exists(self.arquivo_db):
            with open(self.arquivo_db, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        # Se for a primeira vez, cria o banco de dados zerado
        dados_iniciais = {
            "fresa_corte_6mm": {
                "nome": "Fresa de Corte 6mm (UP/DOWN)", 
                "metros_rodados": 0.0, 
                "vida_util_max": 3000.0 # Ajuste isso de acordo com o fabricante da sua fresa
            },
            "broca_5mm": {
                "nome": "Broca de Furação Frontal 5mm", 
                "metros_rodados": 0.0, 
                "vida_util_max": 1500.0
            }
        }
        self.salvar_db(dados_iniciais)
        return dados_iniciais

    def salvar_db(self, dados=None):
        if dados is None:
            dados = self.ferramentas
        with open(self.arquivo_db, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4)

    def registrar_corte_projeto(self):
        """Lê o projeto atual na memória, calcula o perímetro e adiciona ao desgaste."""
        metros_cortados = 0.0
        
        # Soma o perímetro de todas as peças carregadas na tela
        for material, lista_pecas in self.app.lotes_por_material.items():
            for peca in lista_pecas:
                w = getattr(peca, 'dim_x_csv', getattr(peca, 'largura', 0))
                h = getattr(peca, 'dim_y_csv', getattr(peca, 'altura', 0))
                
                # Fórmula do perímetro convertido para metros lineares
                perimetro_metros = ((w + h) * 2) / 1000.0
                metros_cortados += perimetro_metros
                
        # Adiciona a quilometragem na fresa principal e salva
        if "fresa_corte_6mm" in self.ferramentas:
            self.ferramentas["fresa_corte_6mm"]["metros_rodados"] += metros_cortados
            self.salvar_db()
            
        return metros_cortados