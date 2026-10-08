# TiranoGio_App/processamento/exportador_cortecloud.py

import json
from tkinter import filedialog, messagebox

class ExportadorCorteCloud:
    """Gaveta responsável por traduzir o lote de peças interno para o formato JSON estrito do CorteCloud/LeoCut."""
    def __init__(self, app_core):
        self.app = app_core

    def exportar_projeto_json(self):
        if not self.app.lotes_por_material:
            messagebox.showwarning("Sem Dados", "Não há nenhuma lista de peças carregada para exportar!")
            return

        nome_sugerido = f"Projeto_{self.app.nome_cliente.replace(' ', '_')}_CorteCloud.json"
        arquivo_destino = filedialog.asksaveasfilename(
            title="Salvar Arquivo para CorteCloud",
            defaultextension=".json",
            filetypes=[("Arquivos JSON", "*.json")],
            initialfile=nome_sugerido
        )

        if not arquivo_destino:
            return

        try:
            estrutura_corte_cloud = {
                "parts": []
            }

            for material, lista_pecas in self.app.lotes_por_material.items():
                for peca in lista_pecas:
                    
                    # Mapeamento oficial CorteCloud (Plano Cartesiano anti-horário):
                    # C1 (Segmento 0-1): Base / Inferior
                    # C2 (Segmento 2-3): Topo / Superior
                    # L1 (Segmento 3-0): Esquerda
                    # L2 (Segmento 1-2): Direita
                    fita_c1 = None 
                    fita_c2 = None 
                    fita_l1 = None 
                    fita_l2 = None 
                    
                    pts = peca.pontos_perimetro
                    if len(pts) >= 4:
                        fita_l1 = "Fita Padrão" if pts[0].get("tem_fita", False) else None  # pts[0] é o Esquerda -> L1
                        fita_l2 = "Fita Padrão" if pts[1].get("tem_fita", False) else None  # pts[1] é a Direita -> L2
                        fita_c1 = "Fita Padrão" if pts[2].get("tem_fita", False) else None  # pts[2] é a Base -> C1
                        fita_c2 = "Fita Padrão" if pts[3].get("tem_fita", False) else None  # pts[3] é a Topo -> C2

                    # Corpo principal da peça
                    item_json = {
                        "quantity": 1,
                        "c": peca.largura,  # Eixo X no CorteCloud
                        "l": peca.altura,   # Eixo Y no CorteCloud
                        "function": peca.descricao,
                        "complement": peca.id_peca,
                        "c1": fita_c1,
                        "l1": fita_l1,
                        "c2": fita_c2,
                        "l2": fita_l2,
                        "material": material
                    }

                    # Se a peça tiver furos, adiciona o bloco "machining"
                    if peca.furos:
                        brocas_verticais = []
                        for furo in peca.furos:
                            brocas_verticais.append({
                                "face": "i",
                                "bolthole": False,
                                "corner": 3,
                                "x": furo.get('X', 0.0),
                                "y": furo.get('Y', 0.0),
                                "depth": furo.get('Depth', peca.espessura), 
                                "diameter": furo.get('Diameter', 5.0)
                            })

                        item_json["machining"] = {
                            "x": peca.largura,
                            "y": peca.altura,
                            "z": peca.espessura,
                            "startSide": 0,
                            "furrowMachining": None,
                            "furrowMachiningPair": None,
                            "verticalDrills": brocas_verticais,
                            "horizontalDrills": []
                        }

                    estrutura_corte_cloud["parts"].append(item_json)

            with open(arquivo_destino, "w", encoding="utf-8") as f:
                json.dump(estrutura_corte_cloud, f, indent=2, ensure_ascii=False)

            self.app.ui.lbl_status.configure(text="JSON CorteCloud exportado com sucesso!", text_color="#00E676")
            messagebox.showinfo("Exportação Concluída", f"Arquivo gerado nos padrões do CorteCloud com sucesso!")
            
        except Exception as e:
            messagebox.showerror("Erro na Exportação", f"Falha ao gerar o JSON:\n{e}")
