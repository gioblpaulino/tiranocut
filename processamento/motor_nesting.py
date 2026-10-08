import threading
import customtkinter as ctk
from rectpack import newPacker, PackingMode, PackingBin, SORT_LSIDE, MaxRectsBl

class MotorNesting:
    def __init__(self, app_core):
        self.app = app_core

    def processar(self):
        if not self.app.lotes_por_material: return
        
        self.app.chapas_globais.clear()
        
        self.janela_load = ctk.CTkToplevel(self.app.root)
        self.janela_load.title("Processando...")
        self.janela_load.geometry("400x150")
        self.janela_load.grab_set()
        self.janela_load.attributes("-topmost", True)
        
        ctk.CTkLabel(self.janela_load, text="⚙️ Otimizando o Plano de Corte...", font=ctk.CTkFont(weight="bold", size=14)).pack(pady=(20, 10))
        self.barra = ctk.CTkProgressBar(self.janela_load, mode="indeterminate", progress_color="#00E676")
        self.barra.pack(fill="x", padx=40, pady=10)
        self.barra.start()
        
        t = threading.Thread(target=self._tarefa_pesada)
        t.start()

    def _tarefa_pesada(self):
        try:
            uid_contador = 0
            for material, lista_pecas in self.app.lotes_por_material.items():
                lote_tem_veio = False
                for p in lista_pecas:
                    if isinstance(p, dict):
                        if p.get("rid", {}).get("tem_veio", False): lote_tem_veio = True
                    else:
                        if getattr(p, 'tem_veio', False): lote_tem_veio = True

                packer = newPacker(mode=PackingMode.Offline, bin_algo=PackingBin.BFF, 
                                   pack_algo=MaxRectsBl, sort_algo=SORT_LSIDE, rotation=not lote_tem_veio)
                
                for peca in lista_pecas:
                    if isinstance(peca, dict):
                        rid = peca.get("rid", {})
                        w_base = float(rid.get("w_real", 0))
                        h_base = float(rid.get("h_real", 0))
                        dados_desenho = rid
                    else:
                        w_base = float(getattr(peca, 'dim_x_csv', getattr(peca, 'largura', 0)))
                        h_base = float(getattr(peca, 'dim_y_csv', getattr(peca, 'altura', 0)))
                        dados_desenho = {
                            "id_original": getattr(peca, 'id_peca', ""), 
                            "id_etiqueta": f"#{getattr(peca, 'id_peca', '')}", 
                            "nome": getattr(peca, 'descricao', 'Peça'), 
                            "w_real": w_base, "h_real": h_base, 
                            "espessura": getattr(peca, 'espessura', 15.0), 
                            "furos": getattr(peca, 'furos', []), 
                            "rasgos": getattr(peca, 'rasgos', []), 
                            "pontos_perimetro": getattr(peca, 'pontos_perimetro', []), 
                            "tem_veio": getattr(peca, 'tem_veio', False), 
                            "material": material
                        }

                    larg_calc = int((w_base + self.app.gap_fresa) * 10)
                    alt_calc = int((h_base + self.app.gap_fresa) * 10)
                    
                    packer.add_rect(larg_calc, alt_calc, rid=dados_desenho)
                
                area_x_int = int(self.app.area_util_x * 10)
                area_y_int = int(self.app.area_util_y * 10)
                for _ in range(len(lista_pecas)): 
                    packer.add_bin(area_x_int, area_y_int)
                
                packer.pack() 

                chapas_deste_material = []
                for b in packer:
                    chapa_atual = []
                    max_x_alcancado, max_y_alcancado = 0, 0 

                    for rect in b:
                        rx, ry = rect.x / 10.0, rect.y / 10.0
                        rw, rh = rect.width / 10.0, rect.height / 10.0
                        girou_ia = rw != round(rect.rid["w_real"] + self.app.gap_fresa, 1)
                        
                        chapa_atual.append({
                            "uid": f"uid_{uid_contador}", "rid": rect.rid, 
                            "x": rx, "y": ry, "width": rw, "height": rh, "is_rotated": girou_ia
                        })
                        uid_contador += 1
                        
                        if (rx + rw) > max_x_alcancado: max_x_alcancado = rx + rw
                        if (ry + rh) > max_y_alcancado: max_y_alcancado = ry + rh
                    
                    if chapa_atual:
                        chapa_atual.append({
                            "tipo": "metadados", 
                            "limite_x_corte": max_x_alcancado,
                            "limite_y_corte": max_y_alcancado
                        })
                    chapas_deste_material.append(chapa_atual)
                
                self.app.chapas_globais[material] = chapas_deste_material

            self.app.root.after(0, self._finalizar_ui)
        except Exception as e:
            self.app.root.after(0, lambda err=e: self._erro_ui(err))

    def _finalizar_ui(self):
        contador_visual = 1
        for mat, chapas in self.app.chapas_globais.items():
            for chapa in chapas:
                pecas_validas = [p for p in chapa if p.get("tipo") != "metadados" and p["y"] < self.app.area_util_y]
                metadados_chapa = next((p for p in chapa if p.get("tipo") == "metadados"), None)
                
                # Mascara e indexa os IDs visuais das peças válidas
                pecas_validas.sort(key=lambda p: (p["y"], p["x"]))
                for p_dict in pecas_validas:
                    nome_bruto = p_dict["rid"].get("nome", "")
                    tag_modulo = ""
                    if "[" in nome_bruto and "]" in nome_bruto:
                        tag_modulo = nome_bruto[nome_bruto.find("["):nome_bruto.find("]") + 1] + " "
                    mascara_id = f"#{contador_visual} {tag_modulo}".strip()
                    p_dict["rid"]["id_visual"] = mascara_id
                    contador_visual += 1
                
                # 🚀 INJEÇÃO DINÂMICA: Se houver peças alocadas e metadados estruturais na chapa, 
                # calcula as sobras de guilhotina e salva no SQLite de forma 100% automatizada!
                if pecas_validas and metadados_chapa:
                    espessura_mdf = float(pecas_validas[0]["rid"].get("espessura", 15.0))
                    self.varrer_e_salvar_sobras_guilhotina(mat, espessura_mdf, metadados_chapa)
                    
                    # Se esta chapa veio do banco e foi de fato usada para corte, dá baixa automática
                    if "id_retalho_banco" in metadados_chapa:
                        id_consumido = metadados_chapa["id_retalho_banco"]
                        self.app.db.consumir_retalho_banco(id_consumido)
                        self.app.logger.info(f"Retalho ID {id_consumido} foi alocado com sucesso e consumido do cofre.")
        
        if hasattr(self, 'janela_load'):
            self.barra.stop()
            self.janela_load.destroy()

        materiais_disponiveis = list(self.app.chapas_globais.keys())
        if materiais_disponiveis:
            self.app.ui.combo_materiais.configure(values=materiais_disponiveis)
            self.app.ui.combo_materiais.set(materiais_disponiveis[0])
        self.app.mudar_material_preview()
        
        self.app.ui.btn_pdf.configure(state="normal")
        self.app.ui.btn_etiquetas.configure(state="normal")
        self.app.ui.btn_gcode.configure(state="normal")
        self.app.ui.lbl_status.configure(text="Plano Calculado com Sucesso!", text_color="#00E676")
        if hasattr(self.app, 'persistir_projeto_atual'):
            self.app.persistir_projeto_atual()

    def _erro_ui(self, erro):
        if hasattr(self, 'janela_load'):
            self.barra.stop()
            self.janela_load.destroy()
        from tkinter import messagebox
        messagebox.showerror("Erro Crítico", f"O algoritmo falhou:\n{erro}")
    
    def varrer_e_salvar_sobras_guilhotina(self, material, espessura, metadados_chapa):
        """
        Calcula as dimensões das sobras geradas pelos cortes em L da guilhotina
        e as salva no cofre do SQLite se passarem pelo filtro de área útil.
        """
        if not metadados_chapa: return

        # Recupera as dimensões máximas alcançadas pelas peças na chapa (em mm)
        limite_x = float(metadados_chapa.get("limite_x_corte", 0))
        limite_y = float(metadados_chapa.get("limite_y_corte", 0))
        possui_veio = bool(metadados_chapa.get("possui_veio", False))

        # Dimensões totais da matéria-prima ativa
        chapa_w = self.app.chapa_largura
        chapa_h = self.app.chapa_altura

        # Se nenhuma peça foi alocada ou ocupou a chapa inteira, aborta
        if limite_x == 0 or limite_y == 0: return

        # Recupera as diretrizes de tamanho mínimo configuradas pelo operador no SQLite
        min_x, min_y = self.app.db.obter_limites_retalho()

        # 1. Avalia o Retalho Lateral Direito (Faixa Vertical)
        largura_ret_lat = chapa_w - (limite_x + self.app.refilo)
        altura_ret_lat = chapa_h - (self.app.refilo * 2)

        if largura_ret_lat >= min_x and altura_ret_lat >= min_y:
            self.app.db.salvar_retalho_avulso(
                material=material,
                largura=largura_ret_lat,
                altura=altura_ret_lat,
                espessura=espessura,
                possui_veio=possui_veio
            )
            self.app.logger.info(f"Retalho Lateral gerado automaticamente: {largura_ret_lat:.0f}x{altura_ret_lat:.0f}mm ({material})")

        # 2. Avalia o Retalho Superior (Faixa Horizontal do Topo)
        # Para evitar sobreposição geométrica na quina superior direita, limitamos a largura até o corte da guilhotina lateral
        largura_ret_topo = limite_x if largura_ret_lat >= min_x else (chapa_w - (self.app.refilo * 2))
        altura_ret_topo = chapa_h - (limite_y + self.app.refilo)

        if largura_ret_topo >= min_x and altura_ret_topo >= min_y:
            self.app.db.salvar_retalho_avulso(
                material=material,
                largura=largura_ret_topo,
                altura=altura_ret_topo,
                espessura=espessura,
                possui_veio=possui_veio
            )
            self.app.logger.info(f"Retalho Superior gerado automaticamente: {largura_ret_topo:.0f}x{altura_ret_topo:.0f}mm ({material})")