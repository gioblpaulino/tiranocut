import tkinter as tk
import math
import random

class MotorGrafico:
    """
    Renderização 2D (Chapa Horizontal), centralização responsiva
    e física de interação (arrastar, soltar, transferir, girar e zoom).
    """
    def __init__(self, app_core):
        self.app = app_core
        self.canvas = self.app.ui.canvas
        
        self.escala = 0.22 
        self.zoom_manual_aplicado = False
        self.offset_x = 20
        self.offset_y = 20
        self.peca_arrastada = None
        self.drag_data = {"x_mouse": 0, "y_mouse": 0, "delta_x_px": 0, "delta_y_px": 0, "orig_x_mdf": 0, "orig_y_mdf": 0}

    def farejar_peca_no_cofre(self, dados_rid, peca_nesting):
        cofre = getattr(self.app, 'cofre_pecas_originais', {})
        if not cofre: return None

        candidatos = [
            str(dados_rid.get("id_original", "")), str(dados_rid.get("id_peca", "")),
            str(dados_rid.get("id", "")), str(dados_rid.get("id_visual", "")),
            str(dados_rid.get("codigo", "")), str(dados_rid.get("item_code", "")),
            str(peca_nesting.get("uid", ""))
        ]
        candidatos_limpos = [c.strip() for c in candidatos if c and c.strip() not in ["None", "0", ""]]

        for cand in candidatos_limpos:
            if cand in cofre: return cofre[cand]
            cand_sem_hash = cand.replace('#', '')
            if cand_sem_hash in cofre: return cofre[cand_sem_hash]
            if f"#{cand_sem_hash}" in cofre: return cofre[f"#{cand_sem_hash}"]

        w_alvo = float(dados_rid.get("w_real", dados_rid.get("largura", dados_rid.get("w", 0))))
        desc_alvo = str(dados_rid.get("descricao") or dados_rid.get("nome") or "").strip().upper()

        for peca_cofre in cofre.values():
            id_obj = str(getattr(peca_cofre, 'id_peca', getattr(peca_cofre, 'id', ''))).strip()
            if id_obj in candidatos_limpos or id_obj.replace('#', '') in [c.replace('#', '') for c in candidatos_limpos]:
                return peca_cofre
            
            desc_obj = str(getattr(peca_cofre, 'descricao', '')).strip().upper()
            if desc_alvo and (desc_alvo == desc_obj or desc_alvo.endswith(desc_obj) or desc_obj.endswith(desc_alvo)):
                w_obj = float(getattr(peca_cofre, 'dim_x_csv', getattr(peca_cofre, 'largura', 0)))
                if abs(w_alvo - w_obj) < 1.0:
                    return peca_cofre
        return None

    def zoom_mouse(self, event):
        self.zoom_manual_aplicado = True
        if event.num == 4 or getattr(event, 'delta', 0) > 0: self.escala *= 1.1
        elif event.num == 5 or getattr(event, 'delta', 0) < 0: self.escala /= 1.1
        self.desenhar_chapa()

    def iniciar_arrasto(self, event):
        self.canvas.focus_set()
        if not self.app.chapas_editaveis: return
        canvas_x, canvas_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        item = self.canvas.find_withtag("current")
        if not item: return
        
        uid_alvo = next((t for t in self.canvas.gettags(item[0]) if t.startswith("uid_")), None)
        if not uid_alvo: return
        
        self.peca_arrastada = uid_alvo
        self.drag_data["x_mouse"] = canvas_x
        self.drag_data["y_mouse"] = canvas_y
        self.drag_data["delta_x_px"] = 0
        self.drag_data["delta_y_px"] = 0
        
        for peca in self.app.chapas_editaveis[self.app.indice_chapa_atual]:
            if peca.get("tipo") == "metadados": continue
            
            if peca["uid"] == self.peca_arrastada:
                self.drag_data["orig_x_mdf"], self.drag_data["orig_y_mdf"] = peca["x"], peca["y"]
                break
        
        self.canvas.tag_raise(self.peca_arrastada)

    def arrastar_peca(self, event):
        if not self.app.chapas_editaveis: return
        if self.peca_arrastada:
            canvas_x, canvas_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            dx, dy = canvas_x - self.drag_data["x_mouse"], canvas_y - self.drag_data["y_mouse"]
            self.canvas.move(self.peca_arrastada, dx, dy)
            self.drag_data["delta_x_px"] += dx
            self.drag_data["delta_y_px"] += dy
            self.drag_data["x_mouse"], self.drag_data["y_mouse"] = canvas_x, canvas_y

    def verificar_colisao(self, uid_alvo, x, y, w, h):
        if y < self.app.area_util_y:
            # Tolerância microscópica (epsilon) para permitir encaixes justos no arrasto manual
            if x < -0.1 or y < -0.1 or (x + w) > self.app.area_util_x + 0.1 or (y + h) > self.app.area_util_y + 0.1:
                return True
            
        if not self.app.chapas_editaveis:
            return False
        
        chapa_atual = self.app.chapas_editaveis[self.app.indice_chapa_atual]
        epsilon = 0.2  # Margem de segurança para evitar falsos positivos de sobreposição de pixels
        
        for peca in chapa_atual:
            if peca.get("tipo") == "metadados" or peca["uid"] == uid_alvo or peca["y"] >= self.app.area_util_y:
                continue
            
            px, py, pw, ph = peca["x"], peca["y"], peca["width"], peca["height"]
            
            # Checagem puramente geométrica de sobreposição de caixas (AABB)
            if (x < px + pw - epsilon and x + w > px + epsilon and y < py + ph - epsilon and y + h > py + epsilon):
                return True
        return False

    def soltar_peca(self, event):
        if not self.app.chapas_editaveis: return
        if self.peca_arrastada:
            dx_mm = self.drag_data["delta_x_px"] / self.escala
            dy_mm = self.drag_data["delta_y_px"] / self.escala
            chapa_atual = self.app.chapas_editaveis[self.app.indice_chapa_atual]
            
            peca_movida = next((p for p in chapa_atual if p.get("tipo") != "metadados" and p["uid"] == self.peca_arrastada), None)
            if not peca_movida: return
            
            self.app.salvar_estado_historico()
            
            novo_x, novo_y = peca_movida["x"] + dx_mm, peca_movida["y"] - dy_mm 
            w_movida, h_movida = peca_movida["width"], peca_movida["height"]

            # --- ENVIO PARA A ÁREA DE TRANSFERÊNCIA/ESTOQUE SE FOR JOGADA FORA DA TELA ---
            if novo_x > self.app.area_util_x + 80 or novo_x < -150 or novo_y > self.app.area_util_y + 120 or novo_y < -150:
                chapa_atual.remove(peca_movida)
                mat_atual = self.app.ui.combo_materiais.get()
                if mat_atual not in self.app.estoque_global_pecas: self.app.estoque_global_pecas[mat_atual] = []
                self.app.estoque_global_pecas[mat_atual].append(peca_movida)
                
                self.app.peca_destaque = None
                self.desenhar_chapa()
                self.app.atualizar_lista_estoque()
                self.peca_arrastada = None
                return

            # --- SISTEMA INTELIGENTE DE ANCORAGEM FACE A FACE ---
            snapped_x, snapped_y = novo_x, novo_y
            ancoras_x = [0, self.app.area_util_x - w_movida]
            ancoras_y = [0, self.app.area_util_y - h_movida]
            
            for outra in chapa_atual:
                if outra.get("tipo") == "metadados" or outra["uid"] == self.peca_arrastada or outra["y"] >= self.app.area_util_y: 
                    continue
                ox, oy, ow, oh = outra["x"], outra["y"], outra["width"], outra["height"]
                ancoras_x.extend([ox - w_movida, ox + ow, ox])
                ancoras_y.extend([oy - h_movida, oy + oh, oy])

            melhor_dist_x, melhor_dist_y = 20.0, 20.0
            snap_efetuado_x, snap_efetuado_y = False, False

            for ax in ancoras_x:
                if abs(novo_x - ax) < melhor_dist_x and not self.verificar_colisao(self.peca_arrastada, ax, novo_y, w_movida, h_movida):
                    melhor_dist_x, snapped_x = abs(novo_x - ax), ax
                    snap_efetuado_x = True

            for ay in ancoras_y:
                if abs(novo_y - ay) < melhor_dist_y and not self.verificar_colisao(self.peca_arrastada, snapped_x, ay, w_movida, h_movida):
                    melhor_dist_y, snapped_y = abs(novo_y - ay), ay
                    snap_efetuado_y = True

            # --- 🚀 RECURSO ULTRA UX: ALGORITMO DE AJUSTE AUTOMÁTICO DE NICHOS VAGOS ---
            # Se a peça ainda colidir na posição final (ou na posição solta), farejamos um encaixe perfeito num raio de 40mm
            if self.verificar_colisao(self.peca_arrastada, snapped_x, snapped_y, w_movida, h_movida):
                vago_encontrado = False
                # Varre em cruz expandindo o vetor de busca para encontrar folgas nas laterais
                for offsets in range(1, 41, 2):  # passos de 2mm para não pesar o processamento
                    for ox_dir, oy_dir in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (1,1), (-1,1), (1,-1)]:
                        test_x = snapped_x + (ox_dir * offsets)
                        test_y = snapped_y + (oy_dir * offsets)
                        if not self.verificar_colisao(self.peca_arrastada, test_x, test_y, w_movida, h_movida):
                            snapped_x, snapped_y = test_x, test_y
                            vago_encontrado = True
                            snap_efetuado_x = snap_efetuado_y = True
                            break
                    if vago_encontrado: 
                        break
                
                # Se mesmo expandindo o radar ela não couber em nenhum espaço, volta para a origem histórica
                if not vago_encontrado:
                    snapped_x, snapped_y = self.drag_data["orig_x_mdf"], self.drag_data["orig_y_mdf"]
                    snap_efetuado_x = snap_efetuado_y = False

            # Aplica o posicionamento final refinado
            peca_movida["x"], peca_movida["y"] = snapped_x, snapped_y
            self.desenhar_chapa()

            # --- RENDEREZAÇÃO DAS LINHAS-GUIA BASEADA NO ACIONAMENTO REAL DO SNAP ---
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            altura_chapa_px = self.app.chapa_altura * self.escala
            
            if snap_efetuado_x and melhor_dist_x < 20.0:
                self.canvas.create_line(self.offset_x + (snapped_x * self.escala), 0, self.offset_x + (snapped_x * self.escala), canvas_h, fill="#00E5FF", width=1, dash=(3, 3))
            if snap_efetuado_y and melhor_dist_y < 20.0:
                self.canvas.create_line(0, self.offset_y + altura_chapa_px - (snapped_y * self.escala), canvas_w, self.offset_y + altura_chapa_px - (snapped_y * self.escala), fill="#FF1744", width=1, dash=(3, 3))
            
            self.peca_arrastada = None

    def girar_peca_manual(self, event, hotkey=False):
        if not self.app.chapas_editaveis: return
        uid_alvo = None
        
        item = self.canvas.find_withtag("current")
        if item: uid_alvo = next((t for t in self.canvas.gettags(item[0]) if t.startswith("uid_")), None)
        elif hotkey and self.app.peca_destaque: uid_alvo = self.app.peca_destaque
        if not uid_alvo: return
        
        for peca in self.app.chapas_editaveis[self.app.indice_chapa_atual]:
            if peca.get("tipo") == "metadados" or peca["uid"] != uid_alvo: continue
            if peca["rid"].get("tem_veio", False): return
            
            self.app.salvar_estado_historico()
            old_w, old_h = peca["width"], peca["height"]
            peca["width"], peca["height"], peca["is_rotated"] = old_h, old_w, not peca["is_rotated"]
            
            if self.verificar_colisao(uid_alvo, peca["x"], peca["y"], peca["width"], peca["height"]):
                peca["width"], peca["height"], peca["is_rotated"] = old_w, old_h, not peca["is_rotated"]
            else: self.desenhar_chapa()
            break

    def deletar_peca_selecionada(self):
        if not self.app.chapas_editaveis: return
        uid_alvo = None
        
        item = self.canvas.find_withtag("current")
        if item: uid_alvo = next((t for t in self.canvas.gettags(item[0]) if t.startswith("uid_")), None)
        elif self.app.peca_destaque: uid_alvo = self.app.peca_destaque
        if not uid_alvo: return
        
        self.app.salvar_estado_historico()
        chapa_atual = self.app.chapas_editaveis[self.app.indice_chapa_atual]
        mat_atual = self.app.ui.combo_materiais.get()
        
        if mat_atual not in self.app.estoque_global_pecas: self.app.estoque_global_pecas[mat_atual] = []
        
        for peca in chapa_atual:
            if peca.get("tipo") == "metadados" or peca["uid"] != uid_alvo: continue
            chapa_atual.remove(peca)
            self.app.estoque_global_pecas[mat_atual].append(peca)
            self.app.peca_destaque = None
            
            self.desenhar_chapa()
            self.app.atualizar_lista_estoque()
            break

    def transformar_ponto_tela(self, px, py, w_real, girou, x_offset, y_offset):
        if girou: nx, ny = py, w_real - px
        else: nx, ny = px, py
        return x_offset + nx, y_offset + ny 

    def desenhar_chapa(self):
        self.canvas.delete("all")
        if not self.app.chapas_editaveis: return
        
        chapa_dados = self.app.chapas_editaveis[self.app.indice_chapa_atual]
        
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        # Centralização Dinâmica e Auto-Escala
        if canvas_w > 100 and not self.zoom_manual_aplicado:
            escala_x = (canvas_w - 60) / self.app.chapa_largura
            escala_y = (canvas_h - 60) / self.app.chapa_altura
            self.escala = min(escala_x, escala_y)
        
        largura_chapa_px = self.app.chapa_largura * self.escala
        altura_chapa_px = self.app.chapa_altura * self.escala
        
        self.offset_x = max((canvas_w - largura_chapa_px) / 2, 20) if canvas_w > 100 else 20
        self.offset_y = max((canvas_h - altura_chapa_px) / 2, 20) if canvas_h > 100 else 20
        
        ox, oy = self.offset_x, self.offset_y
        
        # Renderiza a chapa de MDF base
        self.canvas.create_rectangle(ox, oy, ox + largura_chapa_px, oy + altura_chapa_px, outline="#3A3A3A", width=2, fill="#F5DEB3")
        ref_px = self.app.refilo * self.escala
        self.canvas.create_rectangle(ox + ref_px, oy + ref_px, ox + largura_chapa_px - ref_px, oy + altura_chapa_px - ref_px, outline="#FF1744", dash=(5, 5), width=2)
        
        # --- IMPLEMENTAÇÃO UX: HUD DE ESCALA E TELEMETRIA OPERACIONAL ---
        info_hud = f"Zoom/Escala: {self.escala*100:.1f}%  |  Área Útil: {self.app.area_util_x:.0f}x{self.app.area_util_y:.0f} mm"
        self.canvas.create_text(25, canvas_h - 25, text=info_hud, anchor="w", font=("Arial", 10, "bold"), fill="#9E9E9E")

        for peca in chapa_dados:
            if peca.get("tipo") == "metadados": continue
            uid, dados = peca["uid"], peca["rid"]
            
            peca_intacta = self.farejar_peca_no_cofre(dados, peca)

            is_critica = getattr(peca_intacta, 'is_critica', False) if peca_intacta else dados.get("is_critica", False)
            tipo_alerta = getattr(peca_intacta, 'tipo_engrosso', 'NORMAL') if peca_intacta else dados.get("tipo_engrosso", "NORMAL")
            esp_alvo = getattr(peca_intacta, 'esp_alvo_engrosso', 30) if peca_intacta else dados.get("esp_alvo_engrosso", 30)

            x_mdf = peca["x"] + self.app.refilo + (self.app.gap_nesting / 2)
            y_mdf = peca["y"] + self.app.refilo + (self.app.gap_nesting / 2)
            girou = peca["is_rotated"]
            w_real = float(dados.get("w_real", dados.get("largura", 0)))
            h_real = float(dados.get("h_real", dados.get("altura", 0)))
            
            nome = dados.get("nome", "Peça")
            id_etiqueta = dados.get("id_visual", dados.get("id_etiqueta", ""))
            nome_limpo = nome.split("] ")[-1] if "] " in nome else nome
            
            draw_w, draw_h = (w_real, h_real) if not girou else (h_real, w_real)
            
            px1 = ox + (x_mdf * self.escala)
            py1 = oy + altura_chapa_px - ((y_mdf + draw_h) * self.escala)
            px2 = ox + ((x_mdf + draw_w) * self.escala)
            py2 = oy + altura_chapa_px - (y_mdf * self.escala)
            
            ct = f"{min(w_real, h_real):.1f}x{max(w_real, h_real):.1f}"
            if ct not in self.app.cores_por_tamanho: 
                self.app.cores_por_tamanho[ct] = f"#{random.randint(60, 180):02x}{random.randint(100, 200):02x}{random.randint(140, 240):02x}"
            
            tracejo_ativo = None
            if self.app.peca_destaque == uid:
                cor_fundo, cor_borda, largura_linha = ("yellow" if not self.app.modo_raiox else ""), "red", 4
            elif self.app.modo_raiox:
                cor_fundo, cor_borda, largura_linha = "", "#00E676", 2
            elif is_critica:
                cor_fundo, cor_borda, largura_linha, tracejo_ativo = "#FF5722", "#B71C1C", 3, (6, 3) 
            else:
                cor_fundo, cor_borda, largura_linha = self.app.cores_por_tamanho[ct], "#222", 1
            
            opcoes_desenho = {"fill": cor_fundo, "outline": cor_borda, "width": largura_linha, "tags": (uid, "peca_movivel")}
            if tracejo_ativo and self.app.peca_destaque != uid: opcoes_desenho["dash"] = tracejo_ativo

            coords = []
            for pt in dados.get("pontos_perimetro", []):
                tx, ty = self.transformar_ponto_tela(pt['x'], pt['y'], w_real, girou, x_mdf, y_mdf)
                coords.extend([ox + (tx * self.escala), oy + altura_chapa_px - (ty * self.escala)])
            
            if len(coords) >= 6: self.canvas.create_polygon(coords, **opcoes_desenho)
            else: self.canvas.create_rectangle(px1, py1, px2, py2, **opcoes_desenho)
            
            # --- IMPLEMENTAÇÃO UI: TEXTURIZAÇÃO VISUAL DE VEIOS DE MADEIRA ---
            if dados.get("tem_veio", False) and not self.app.modo_raiox:
                cor_veio = "#222222" if self.app.peca_destaque == uid else "#5A5A5A"
                if girou:
                    passo_v = abs(px2 - px1) / 5
                    for vi in range(1, 5):
                        vx_f = px1 + (vi * passo_v)
                        self.canvas.create_line(vx_f, py1 + 4, vx_f, py2 - 4, fill=cor_veio, width=1, dash=(2, 4), tags=(uid, "peca_movivel"))
                else:
                    passo_v = abs(py2 - py1) / 5
                    for vi in range(1, 5):
                        vy_f = py1 + (vi * passo_v)
                        self.canvas.create_line(px1 + 4, vy_f, px2 - 4, vy_f, fill=cor_veio, width=1, dash=(2, 4), tags=(uid, "peca_movivel"))

            vetores_int = getattr(peca_intacta, 'vetores_internos', dados.get("vetores_internos", []))
            for buraco in vetores_int:
                coords_buraco = []
                for pt in buraco:
                    tx, ty = self.transformar_ponto_tela(pt['x'], pt['y'], w_real, girou, x_mdf, y_mdf)
                    coords_buraco.extend([ox + (tx * self.escala), oy + altura_chapa_px - (ty * self.escala)])
                if coords_buraco: self.canvas.create_polygon(coords_buraco, fill="#F5DEB3", outline="#111", width=2, tags=(uid, "peca_movivel"))

            for i in range(len(dados.get("pontos_perimetro", []))):
                p1 = dados["pontos_perimetro"][i]
                if p1.get('tem_fita'):
                    p2 = dados["pontos_perimetro"][(i + 1) % len(dados["pontos_perimetro"])]
                    tx1, ty1 = self.transformar_ponto_tela(p1['x'], p1['y'], w_real, girou, x_mdf, y_mdf)
                    tx2, ty2 = self.transformar_ponto_tela(p2['x'], p2['y'], w_real, girou, x_mdf, y_mdf)
                    self.canvas.create_line(ox + (tx1 * self.escala), oy + altura_chapa_px - (ty1 * self.escala), ox + (tx2 * self.escala), oy + altura_chapa_px - (ty2 * self.escala), fill="red", width=3, tags=(uid, "peca_movivel"))

            for rasgo in dados.get("rasgos", []):
                try:
                    rx, ry, rw, rl = rasgo.get('X', 0), rasgo.get('Y', 0), rasgo.get('Width', 6), rasgo.get('Length', w_real)
                    if rasgo.get('Dir') == 'V':
                        tx1_r, ty1_r = self.transformar_ponto_tela(rx + (rw/2), ry, w_real, girou, x_mdf, y_mdf)
                        tx2_r, ty2_r = self.transformar_ponto_tela(rx + (rw/2), ry + rl, w_real, girou, x_mdf, y_mdf)
                    else:
                        tx1_r, ty1_r = self.transformar_ponto_tela(rx, ry + (rw/2), w_real, girou, x_mdf, y_mdf)
                        tx2_r, ty2_r = self.transformar_ponto_tela(rx + rl, ry + (rw/2), w_real, girou, x_mdf, y_mdf)
                    
                    cx1, cy1 = ox + (min(tx1_r, tx2_r) * self.escala), oy + altura_chapa_px - (max(ty1_r, ty2_r) * self.escala)
                    cx2, cy2 = ox + (max(tx1_r, tx2_r) * self.escala), oy + altura_chapa_px - (min(ty1_r, ty2_r) * self.escala)
                    self.canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="#8B4513", outline="", tags=(uid, "peca_movivel"))
                except Exception: pass

            for furo in dados.get("furos", []):
                try:
                    tx_f, ty_f = self.transformar_ponto_tela(furo['X'], furo['Y'], w_real, girou, x_mdf, y_mdf)
                    raio = max((furo.get('Diameter', 5)/2)*self.escala, 0.5)
                    fx, fy = ox + (tx_f * self.escala), oy + altura_chapa_px - (ty_f * self.escala)
                    self.canvas.create_oval(fx - raio, fy - raio, fx + raio, fy + raio, fill="#333", tags=(uid, "peca_movivel"))
                except Exception: pass

            if abs(px2 - px1) > 60 * self.escala and abs(py2 - py1) > 40 * self.escala:
                texto_exibicao = f"⚠️ {tipo_alerta} ({esp_alvo}mm)\n{id_etiqueta}\n{nome_limpo[:15]}\n{w_real:.0f}x{h_real:.0f}" if is_critica else f"{id_etiqueta}\n{nome_limpo[:15]}\n{w_real:.0f}x{h_real:.0f}"
                self.canvas.create_text((px1+px2)/2, (py1+py2)/2, text=texto_exibicao, font=("Arial", int(max(6, 11 * self.escala)), "bold"), fill="white", justify="center", tags=(uid, "peca_movivel"))

        self.canvas.tag_raise("peca_movivel")
        self.app.calcular_aproveitamento()