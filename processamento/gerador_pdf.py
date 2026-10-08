# TiranoGio_App/processamento/gerador_pdf.py

import os
import random
from tkinter import messagebox, filedialog
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors

class GeradorPDF:
    """Gaveta responsável por gerar o Mapa de Corte detalhado em PDF orientado em Paisagem."""
    def __init__(self, app_core):
        self.app = app_core

    def gerar_pdf(self):
        if not self.app.chapas_globais:
            messagebox.showwarning("Aviso", "Processe o Nesting antes de exportar o Mapa de Corte!")
            return

        # Abre o seletor para evitar travamentos de arquivo preso em memória
        arquivo_destino = filedialog.asksaveasfilename(
            title="Salvar Mapa de Corte em PDF",
            defaultextension=".pdf",
            filetypes=[("Arquivo PDF", "*.pdf")]
        )
        if not arquivo_destino: 
            return

        try:
            # Configura a página em modo horizontal (Landscape)
            c = pdf_canvas.Canvas(arquivo_destino, pagesize=landscape(A4))
            largura_pagina, altura_pagina = landscape(A4)
            
            # Margens de segurança operacionais
            margem_x, margem_y = 40, 60
            
            # Inversão do cálculo da escala para se adequar ao formato horizontal
            escala_pdf = min((largura_pagina - 80) / self.app.chapa_largura, (altura_pagina - 160) / self.app.chapa_altura)
            
            w_chapa_pdf = self.app.chapa_largura * escala_pdf
            h_chapa_pdf = self.app.chapa_altura * escala_pdf
            
            # Centraliza a chapa perfeitamente na largura útil da folha
            margem_x = (largura_pagina - w_chapa_pdf) / 2
            
            # Ordenação industrial: Chapas de 15mm primeiro, seguidas por 6mm e demais espessuras
            materiais_ordenados = sorted(self.app.chapas_globais.keys(), key=lambda m: 0 if "15" in m else 2 if "6" in m else 1)

            for material in materiais_ordenados:
                for i, chapa in enumerate(self.app.chapas_globais[material]):
                    
                    # --- CÁLCULO DE APROVEITAMENTO ---
                    area_chapa = self.app.area_util_x * self.app.area_util_y
                    area_ocupada = 0
                    for p in chapa:
                        if p.get("tipo") != "metadados" and p["y"] < self.app.area_util_y:
                            area_ocupada += (p["width"] * p["height"])
                    pct_aprov = (area_ocupada / area_chapa) * 100 if area_chapa > 0 else 0

                    # --- CABEÇALHO DA PÁGINA ---
                    c.setFont("Helvetica-Bold", 16)
                    c.setFillColor(colors.HexColor("#2C3E50"))
                    c.drawString(40, altura_pagina - 40, "Mapa de Corte - TiranoGio")
                    
                    c.setFont("Helvetica-Bold", 10)
                    c.setFillColor(colors.black)
                    c.drawString(40, altura_pagina - 60, f"Cliente: {self.app.nome_cliente}")
                    c.drawString(40, altura_pagina - 75, f"Ambiente: {self.app.nome_ambiente}")
                    
                    c.drawString(largura_pagina - 300, altura_pagina - 60, f"Material: {material}")
                    c.drawString(largura_pagina - 300, altura_pagina - 75, f"Chapa {i+1} de {len(self.app.chapas_globais[material])}")
                    
                    cor_aprov = colors.HexColor("#00E676") if pct_aprov > 75 else (colors.HexColor("#FF9800") if pct_aprov > 50 else colors.HexColor("#F44336"))
                    c.setFillColor(cor_aprov)
                    c.drawString(largura_pagina - 300, altura_pagina - 90, f"Aproveitamento: {pct_aprov:.1f}%")
                    
                    # --- FUNDO DO MDF BASE ---
                    c.setStrokeColor(colors.HexColor("#3A3A3A"))
                    c.setLineWidth(1.5)
                    c.setFillColorRGB(0.96, 0.93, 0.87) # Tom amadeirado claro realista
                    c.rect(margem_x, margem_y, w_chapa_pdf, h_chapa_pdf, fill=1, stroke=1)
                    
                    # Linha tracejada indicando o limite de refilo técnico
                    c.setStrokeColor(colors.HexColor("#E74C3C"))
                    c.setLineWidth(0.5)
                    c.setDash(4, 4) # Ativa o tracejado (4 pontos cheios, 4 vazios)
                    ref_pdf = self.app.refilo * escala_pdf
                    c.rect(margem_x + ref_pdf, margem_y + ref_pdf, w_chapa_pdf - (ref_pdf * 2), h_chapa_pdf - (ref_pdf * 2), fill=0, stroke=1)
                    c.setDash() # Retorna para linha contínua
                    
                    legenda_chapa = {}
                    
                    for peca in chapa:
                        if peca.get("tipo") == "metadados" or peca["y"] >= self.app.area_util_y: 
                            continue 

                        dados = peca["rid"]
                        # CORREÇÃO: Alterado de id_etiqueta para id_visual para casar com a estrutura do sistema
                        w_real, h_real, id_etiq, nome = dados["w_real"], dados["h_real"], dados["id_visual"], dados["nome"]
                        
                        ct = f"{min(w_real, h_real):.1f}x{max(w_real, h_real):.1f}"
                        if ct not in self.app.cores_por_tamanho: 
                            self.app.cores_por_tamanho[ct] = f"#{random.randint(80, 210):02x}{random.randint(110, 220):02x}{random.randint(140, 255):02x}"
                        cor_peca = self.app.cores_por_tamanho[ct]
                        
                        chave = f"{w_real:.0f}x{h_real:.0f}"
                        if chave not in legenda_chapa:
                            legenda_chapa[chave] = {"qtd": 0, "cor": cor_peca}
                        legenda_chapa[chave]["qtd"] += 1
                        
                        x_mdf = peca["x"] + self.app.refilo + (self.app.gap_nesting / 2)
                        y_mdf = peca["y"] + self.app.refilo + (self.app.gap_nesting / 2)
                        girou = peca["is_rotated"]
                        
                        # Coordenadas alinhadas com o plano horizontal do motor gráfico
                        pdf_x = margem_x + (x_mdf * escala_pdf)
                        pdf_y = margem_y + (y_mdf * escala_pdf)
                        pdf_w = peca["width"] * escala_pdf
                        pdf_h = peca["height"] * escala_pdf
                        
                        # 1. RENDERIZAÇÃO DA PEÇA (POLÍGONO OU RETÂNGULO)
                        poligono_coords = []
                        for pt in dados.get("pontos_perimetro", []):
                            tx, ty = self.app.graficos.transformar_ponto_tela(pt['x'], pt['y'], w_real, girou, peca["x"], peca["y"])
                            # Ajuste de translação para o posicionamento global real da chapa mestre
                            tx_global = tx + self.app.refilo + (self.app.gap_nesting / 2)
                            ty_global = ty + self.app.refilo + (self.app.gap_nesting / 2)
                            poligono_coords.extend([margem_x + (tx_global * escala_pdf), margem_y + (ty_global * escala_pdf)])
                        
                        c.setFillColor(colors.HexColor(cor_peca))
                        c.setStrokeColor(colors.HexColor("#2C3E50"))
                        c.setLineWidth(0.8)
                        
                        if len(poligono_coords) >= 6:
                            p = c.beginPath()
                            p.moveTo(poligono_coords[0], poligono_coords[1])
                            for k in range(2, len(poligono_coords), 2): 
                                p.lineTo(poligono_coords[k], poligono_coords[k+1])
                            p.close()
                            c.drawPath(p, fill=1, stroke=1)
                        else:
                            c.rect(pdf_x, pdf_y, pdf_w, pdf_h, fill=1, stroke=1)

                        # 2. FITAS DE BORDA (LINHAS VERMELHAS DESTAQUE)
                        c.setStrokeColor(colors.red)
                        c.setLineWidth(2)
                        for i_f in range(len(dados.get("pontos_perimetro", []))):
                            p1 = dados["pontos_perimetro"][i_f]
                            p2 = dados["pontos_perimetro"][(i_f + 1) % len(dados["pontos_perimetro"])]
                            if p1.get('tem_fita'):
                                # CORREÇÃO: Utiliza peca["x"] e peca["y"] em ambos os pontos para alinhar o plano local
                                tx1, ty1 = self.app.graficos.transformar_ponto_tela(p1['x'], p1['y'], w_real, girou, peca["x"], peca["y"])
                                tx2, ty2 = self.app.graficos.transformar_ponto_tela(p2['x'], p2['y'], w_real, girou, peca["x"], peca["y"])
                                
                                tx1_g = tx1 + self.app.refilo + (self.app.gap_nesting / 2)
                                ty1_g = ty1 + self.app.refilo + (self.app.gap_nesting / 2)
                                tx2_g = tx2 + self.app.refilo + (self.app.gap_nesting / 2)
                                ty2_g = ty2 + self.app.refilo + (self.app.gap_nesting / 2)
                                c.line(margem_x + tx1_g*escala_pdf, margem_y + ty1_g*escala_pdf, margem_x + tx2_g*escala_pdf, margem_y + ty2_g*escala_pdf)

                        # 3. RASGOS (USINAGENS MARRONS)
                        c.setFillColor(colors.HexColor("#8B4513"))
                        for rasgo in dados.get("rasgos", []):
                            try:
                                rx, ry = rasgo.get('X', 0), rasgo.get('Y', 0)
                                rw, rl = rasgo.get('Width', 6), rasgo.get('Length', w_real)
                                is_vert = rasgo.get('Dir') == 'V'
                                
                                tx1_r, ty1_r = self.app.graficos.transformar_ponto_tela(rx, ry, w_real, girou, peca["x"], peca["y"])
                                if is_vert:
                                    tx2_r, ty2_r = self.app.graficos.transformar_ponto_tela(rx + rw, ry + rl, w_real, girou, peca["x"], peca["y"])
                                else:
                                    tx1_r, ty1_r = self.app.graficos.transformar_ponto_tela(rx, ry, w_real, girou, peca["x"], peca["y"])
                                    tx2_r, ty2_r = self.app.graficos.transformar_ponto_tela(rx + rl, ry + rw, w_real, girou, peca["x"], peca["y"])
                                
                                cx1 = margem_x + ((min(tx1_r, tx2_r) + self.app.refilo + (self.app.gap_nesting/2)) * escala_pdf)
                                cy1 = margem_y + ((min(ty1_r, ty2_r) + self.app.refilo + (self.app.gap_nesting/2)) * escala_pdf)
                                cx2 = margem_x + ((max(tx1_r, tx2_r) + self.app.refilo + (self.app.gap_nesting/2)) * escala_pdf)
                                cy2 = margem_y + ((max(ty1_r, ty2_r) + self.app.refilo + (self.app.gap_nesting/2)) * escala_pdf)
                                c.rect(cx1, cy1, cx2 - cx1, cy2 - cy1, fill=1, stroke=0)
                            except Exception: 
                                pass

                        # 4. FUROS DE ALTA PRECISÃO
                        c.setFillColor(colors.HexColor("#2C3E50"))
                        for furo in dados.get("furos", []):
                            try:
                                tx_f, ty_f = self.app.graficos.transformar_ponto_tela(furo['X'], furo['Y'], w_real, girou, peca["x"], peca["y"])
                                tx_fg = tx_f + self.app.refilo + (self.app.gap_nesting / 2)
                                ty_fg = ty_f + self.app.refilo + (self.app.gap_nesting / 2)
                                raio = max((furo.get('Diameter', 5)/2)*escala_pdf, 0.6)
                                c.circle(margem_x + tx_fg*escala_pdf, margem_y + ty_fg*escala_pdf, raio, stroke=0, fill=1)
                            except Exception: 
                                pass
                        
                        # 5. GRAVAÇÃO DOS IDENTIFICADORES DAS PEÇAS
                        c.setFillColor(colors.white)
                        c.setFont("Helvetica-Bold", max(6, 10 * escala_pdf))
                        nome_limpo = nome.split("] ")[-1] if "] " in nome else nome
                        if pdf_w > 20 and pdf_h > 15:
                            c.drawCentredString(pdf_x + (pdf_w/2), pdf_y + (pdf_h/2) + 4, f"{id_etiq}")
                            c.setFont("Helvetica", max(5, 8 * escala_pdf))
                            c.drawCentredString(pdf_x + (pdf_w/2), pdf_y + (pdf_h/2) - 4, f"{nome_limpo[:12]}")
                            c.drawCentredString(pdf_x + (pdf_w/2), pdf_y + (pdf_h/2) - 11, f"{w_real:.0f}x{h_real:.0f}")

                    # --- GERAÇÃO AUTOMÁTICA DE TABELA DE LEGENDAS HORIZONTAIS ---
                    c.setFillColor(colors.black)
                    c.setFont("Helvetica-Bold", 9)
                    c.drawString(40, 42, "Especificações das Peças Desta Chapa:")
                    c.setFont("Helvetica", 8)
                    
                    y_item, coluna_x = 26, 40
                    for count, (chave, info) in enumerate(legenda_chapa.items()):
                        c.setFillColor(colors.HexColor(info["cor"]))
                        c.rect(coluna_x, y_item - 1, 8, 8, fill=1, stroke=1)
                        c.setFillColor(colors.black)
                        c.drawString(coluna_x + 12, y_item, f"{chave} (Qtd: {info['qtd']})")
                        
                        coluna_x += 125
                        if (count + 1) % 5 == 0:
                            coluna_x = 40
                            y_item -= 12
                     
                    c.showPage() 
            
            c.save()
            messagebox.showinfo("Sucesso", "Mapa de Corte PDF exportado com sucesso!")
            os.startfile(arquivo_destino)
            
        except Exception as e: 
            messagebox.showerror("Erro no PDF", f"Falha crítica ao compilar as páginas: {e}")