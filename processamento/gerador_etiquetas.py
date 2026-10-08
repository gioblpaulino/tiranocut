# TiranoGio_App/processamento/gerador_etiquetas.py

import os
from io import BytesIO
from tkinter import filedialog, messagebox
import customtkinter as ctk
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

class GeradorEtiquetas:
    """Módulo unificado de expedição para etiquetas paramétricas Pimaco A4 e Zebra Térmica."""
    def __init__(self, app_core):
        self.app = app_core
        # Layout editável e dicionário dinâmico de chaves para substituição
        self.layout_parametros = {
            "template_linha_1": "Cliente: {cliente}",
            "template_linha_2": "Ambiente: {ambiente}",
            "template_linha_3": "Chapa: {chapa}",
            "template_linha_4": "Dimensão: {largura}x{altura}x{espessura}mm",
            "largura_zebra_mm": 100,
            "altura_zebra_mm": 50
        }

    def gerar_pdf_pimaco(self):
        if not self.app.chapas_globais:
            messagebox.showwarning("Aviso", "Processe o Nesting antes de exportar as etiquetas!")
            return

        arquivo_destino = filedialog.asksaveasfilename(
            title="Salvar PDF de Etiquetas Pimaco A4",
            defaultextension=".pdf",
            filetypes=[("Arquivo PDF", "*.pdf")]
        )
        if not arquivo_destino: return

        try:
            c = canvas.Canvas(arquivo_destino, pagesize=A4)
            largura_folha, altura_folha = A4
            
            margem_esq, margem_topo = 5.9 * mm, 12.5 * mm
            largura_etq, altura_etq = 99.1 * mm, 34.0 * mm
            colunas, linhas = 2, 8
            idx_col, idx_lin = 0, 0

            for material, lista_chapas in self.app.chapas_globais.items():
                for chapa_idx, chapa_dados in enumerate(lista_chapas):
                    pecas = [p for p in chapa_dados if p.get("tipo") != "metadados" and p.get("y", 9999) < self.app.area_util_y]
                    
                    for peca in pecas:
                        dados = peca["rid"]
                        x = margem_esq + (idx_col * largura_etq)
                        y = altura_folha - margem_topo - ((idx_lin + 1) * altura_etq)
                        
                        # Injeção dinâmica com base no nosso dicionário editável
                        valores_peca = {
                            "cliente": self.app.nome_cliente[:20],
                            "ambiente": self.app.nome_ambiente[:20],
                            "chapa": f"{material[:18]} (Chapa {chapa_idx+1})",
                            "largura": f"{dados.get('w_real', 0):.0f}",
                            "altura": f"{dados.get('h_real', 0):.0f}",
                            "espessura": dados.get("espessura", "15")
                        }

                        c.setFont("Helvetica-Bold", 8)
                        c.drawString(x + 4*mm, y + 28*mm, self.layout_parametros["template_linha_1"].format(**valores_peca))
                        c.setFont("Helvetica", 8)
                        c.drawString(x + 4*mm, y + 23*mm, self.layout_parametros["template_linha_2"].format(**valores_peca))
                        c.drawString(x + 4*mm, y + 18*mm, self.layout_parametros["template_linha_3"].format(**valores_peca))
                        c.setFont("Helvetica-Bold", 9)
                        c.drawString(x + 4*mm, y + 12*mm, self.layout_parametros["template_linha_4"].format(**valores_peca))
                        
                        # Código identificador visual simplificado
                        c.setFont("Helvetica-Bold", 12)
                        c.drawString(x + largura_etq - 25*mm, y + 12*mm, dados.get("id_visual", "#N/A"))

                        idx_col += 1
                        if idx_col >= colunas:
                            idx_col = 0
                            idx_lin += 1
                            if idx_lin >= linhas:
                                c.showPage()
                                idx_lin = 0
            c.save()
            messagebox.showinfo("Sucesso", "Etiquetas Pimaco A4 geradas com sucesso!")
            os.startfile(arquivo_destino)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na geração do PDF: {e}")

    def gerar_codigo_zebra_zpl(self):
        """Gera arquivo ZPL leve nativo para rolos térmicos industriais"""
        if not self.app.chapas_globais: return

        arquivo_destino = filedialog.asksaveasfilename(
            title="Salvar Código Térmico Zebra (ZPL)",
            defaultextension=".zpl",
            filetypes=[("Código Zebra", "*.zpl")]
        )
        if not arquivo_destino: return

        try:
            linhas_zpl = []
            for material, lista_chapas in self.app.chapas_globais.items():
                for chapa_idx, chapa_dados in enumerate(lista_chapas):
                    pecas = [p for p in chapa_dados if p.get("tipo") != "metadados" and p.get("y", 9999) < self.app.area_util_y]
                    
                    for peca in pecas:
                        dados = peca["rid"]
                        
                        valores_peca = {
                            "cliente": self.app.nome_cliente[:20],
                            "ambiente": self.app.nome_ambiente[:20],
                            "chapa": f"{material[:18]} - CH {chapa_idx+1}",
                            "largura": f"{dados.get('w_real', 0):.0f}",
                            "altura": f"{dados.get('h_real', 0):.0f}",
                            "espessura": dados.get("espessura", "15")
                        }

                        # Montagem do bloco de strings ZPL II estruturado por coordenadas de pixel
                        zpl = []
                        zpl.append("^XA") # Início do Bloco
                        zpl.append("^CF0,30") # Fonte de alta densidade
                        zpl.append(f"^FO50,40^FD{self.layout_parametros['template_linha_1'].format(**valores_peca)}^FS")
                        zpl.append(f"^FO50,80^FD{self.layout_parametros['template_linha_2'].format(**valores_peca)}^FS")
                        zpl.append(f"^FO50,120^FD{self.layout_parametros['template_linha_3'].format(**valores_peca)}^FS")
                        zpl.append(f"^FO50,160^BQN,2,4^FDQA,{dados.get('id_visual', '000')}^FS") # QR Code de Rastreio
                        zpl.append(f"^FO250,160^A0N,40,40^FD{dados.get('id_visual', '')}^FS")
                        zpl.append(f"^FO250,210^FD{self.layout_parametros['template_linha_4'].format(**valores_peca)}^FS")
                        zpl.append("^XZ") # Fim da etiqueta
                        
                        linhas_zpl.append("\n".join(zpl))

            with open(arquivo_destino, "w", encoding="utf-8") as f:
                f.write("\n".join(linhas_zpl))
            
            messagebox.showinfo("Zebra ZPL", "Arquivo de comandos térmicos exportado com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na exportação Zebra: {e}")