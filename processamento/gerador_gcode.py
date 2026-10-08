# TiranoGio_App/processamento/gerador_gcode.py

import os
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class GeradorGCode:
    """Gaveta responsável por ler as peças no Nesting e compilar a linguagem da CNC (.tap)"""
    #
    def __init__(self, app_core):
        self.app = app_core
    #
    def abrir_configuracao_gcode(self):
        if not self.app.chapas_globais: return
        
        # 🛡️ TRAVA DE SEGURANÇA: Verifica se tem peça fora da chapa
        pecas_na_espera = 0
        for mat, chapas in self.app.chapas_globais.items():
            for chapa in chapas:
                for peca in chapa:
                    if peca.get("tipo") != "metadados" and peca["y"] >= self.app.area_util_y:
                        pecas_na_espera += 1
                        
        if pecas_na_espera > 0:
            messagebox.showwarning("Atenção, Operador!", f"Existem {pecas_na_espera} peça(s) na Zona de Espera Livre!\n\nPor favor, posicione todas elas dentro do limite do MDF (ou apague as que não vai cortar) antes de gerar o código da máquina.")
            return 
            
        janela = tk.Toplevel(self.app.root)
        janela.title("Geração de Código de Máquina")
        janela.geometry("450x550"); janela.grab_set()

        tk.Label(janela, text="Selecione o Pós-Processador (Máquina)", font=("Arial", 10, "bold")).pack(pady=(10, 2))
        v_pp = tk.StringVar(janela)
        combo_pp = ttk.Combobox(janela, textvariable=v_pp, values=list(self.app.db.pos_processadores.keys()), state="readonly", width=35)

        
        if combo_pp.cget("values"):
            combo_pp.current(0)
        combo_pp.pack(pady=5)

        # 🚀 NOVO: ETAPA 2 DO PLANO - Botão de Pós-Processadores
        def abrir_pasta_pos_processadores():
            import os
            import subprocess
            pasta_pp = os.path.join(os.getcwd(), "pos_processadores")
            os.makedirs(pasta_pp, exist_ok=True)
            
            # Cria um arquivo de ajuda se a pasta estiver vazia
            readme = os.path.join(pasta_pp, "COMO_ADICIONAR.txt")
            if not os.path.exists(readme):
                with open(readme, "w", encoding="utf-8") as f:
                    f.write("Cole aqui os seus scripts de Pós-Processador (.py ou .json) da sua Máquina CNC.")
                    
            # Abre a pasta nativamente no Windows
            os.startfile(pasta_pp)
            
        import customtkinter as ctk
        btn_add_pp = ctk.CTkButton(
            janela, text="➕ Gerenciar Pós-Processadores", 
            fg_color="#388E3C", hover_color="#2E7D32", 
            command=abrir_pasta_pos_processadores
        )
        btn_add_pp.pack(pady=(15, 5))



        tk.Label(janela, text="Estratégia de Corte Z", font=("Arial", 10, "bold")).pack(pady=(10, 2))
        v_estrategia = tk.StringVar(janela, value="Único")
        frame_radio = tk.Frame(janela); frame_radio.pack()
        tk.Radiobutton(frame_radio, text="Passe Único", variable=v_estrategia, value="Único").pack(side="left", padx=10)
        tk.Radiobutton(frame_radio, text="Múltiplo", variable=v_estrategia, value="Múltiplo").pack(side="left", padx=10)

        frame_passe = tk.Frame(janela); frame_passe.pack(pady=5)
        tk.Label(frame_passe, text="Desce (mm/passe):").pack(side="left")
        v_profundidade = tk.DoubleVar(janela, value=8.0)
        tk.Entry(frame_passe, textvariable=v_profundidade, width=6).pack(side="left", padx=5)
        
        # --- PAINEL VISUAL DE ORDEM DAS OPERAÇÕES ---
        tk.Label(janela, text="Ordem de Execução no Chão de Fábrica", font=("Arial", 10, "bold")).pack(pady=(15, 2))
        frame_ordem = tk.Frame(janela)
        frame_ordem.pack(pady=5)
        
        listbox_ordem = tk.Listbox(frame_ordem, width=25, height=3, exportselection=False, font=("Arial", 10))
        listbox_ordem.insert(tk.END, "Furações")
        listbox_ordem.insert(tk.END, "Rasgos")
        listbox_ordem.insert(tk.END, "Cortes Externos")
        listbox_ordem.pack(side="left", padx=5)
        
        frame_setas = tk.Frame(frame_ordem)
        frame_setas.pack(side="left")
        
        def subir():
            idx = listbox_ordem.curselection()
            if idx and idx[0] > 0:
                texto = listbox_ordem.get(idx[0])
                listbox_ordem.delete(idx[0])
                listbox_ordem.insert(idx[0] - 1, texto)
                listbox_ordem.selection_set(idx[0] - 1)
                
        def baixar():
            idx = listbox_ordem.curselection()
            if idx and idx[0] < listbox_ordem.size() - 1:
                texto = listbox_ordem.get(idx[0])
                listbox_ordem.delete(idx[0])
                listbox_ordem.insert(idx[0] + 1, texto)
                listbox_ordem.selection_set(idx[0] + 1)
                
        tk.Button(frame_setas, text="▲", font=("Arial", 8, "bold"), command=subir, width=3).pack(pady=2)
        tk.Button(frame_setas, text="▼", font=("Arial", 8, "bold"), command=baixar, width=3).pack(pady=2)

        v_guilhotina = tk.BooleanVar(janela, value=True)
        tk.Checkbutton(janela, text="Cortar sobra em L automaticamente (Guilhotina)", variable=v_guilhotina).pack(pady=(10, 0))

        v_corte_comum = tk.BooleanVar(janela, value=True)
        tk.Checkbutton(janela, text="Otimizar Linhas Comuns (Corta Blocão + Separa)", variable=v_corte_comum).pack(pady=(0, 10))
        
        # Botão de Iniciar G-Code
        def iniciar_gcode():
            pasta_destino = filedialog.askdirectory(title="Salvar Arquivos G-Code Onde?")
            if pasta_destino:
                estrategia = str(v_estrategia.get())
                try:
                    # Valida a profundidade de passe
                    passe_mm = float(v_profundidade.get())
                    if passe_mm <= 0: passe_mm = 0.1 # Trava do loop infinito!
                except ValueError:
                    passe_mm = 8.0 
                #
                pp_selecionado = str(v_pp.get())
                usar_guilhotina = bool(v_guilhotina.get())
                usar_corte_comum = bool(v_corte_comum.get())
                ordem_escolhida = list(listbox_ordem.get(0, tk.END))
                janela.destroy()
                self.compilar_gcode(pasta_destino, estrategia, passe_mm, pp_selecionado, usar_guilhotina, usar_corte_comum, ordem_escolhida)

        tk.Button(janela, text="GERAR CÓDIGO DA MÁQUINA", bg="#00796B", fg="white", font=("Arial", 10, "bold"), command=iniciar_gcode).pack(fill="x", padx=20, pady=15, ipady=6)

    def ponto_cnc(self, px, py, w_real, h_real, girou, x_mdf, y_mdf):
        # 1. Rotaciona a peça internamente se necessário
        if girou:
            nx = py
            ny = w_real - px
        else:
            nx = px
            ny = py
            
        # 2. Converte para o eixo Global da CNC (Para Chapa Retrato 1830x2750 com Origem Inferior Esquerda)
        cnc_x = y_mdf + ny
        cnc_y = x_mdf + nx
        return cnc_x, cnc_y 

    def compilar_gcode(self, pasta_destino, estrategia, passe_mm, nome_pp, usar_guilhotina, usar_corte_comum, ordem_ops):
        self.app.ui.lbl_status.configure(text="Calculando Rampas, Pontes (TABS) e G-Code...", text_color="#00E676")
        self.app.root.update()
        
        pp = self.app.db.pos_processadores[nome_pp] 
        config_maquina = self.app.db.config_cnc["maquina"]
        
        sobrecorte = float(config_maquina.get("sobrecorte_mm", 0.5))
        ang_rampa = float(config_maquina.get("angulo_rampa_graus", 15.0))
        z_add = float(config_maquina.get("z_seguranca_add", 15.0))
        usar_tabs = config_maquina.get("usar_tabs", True)
        tab_w = float(config_maquina.get("tab_largura", 5.0))
        tab_h = float(config_maquina.get("tab_espessura", 2.0))
        arquivos_gerados = 0

        # =========================================================
        # 🧠 OTIMIZADORES (Blocão e Caminho Menor)
        # =========================================================
        def otimizar_linhas_comuns(tasks_originais):
            segmentos = {}
            for task in tasks_originais:
                ferr = task['ferr']
                pontos = [task['ponto_init']] + task['caminho']
                
                for i in range(len(pontos) - 1):
                    p1, p2 = pontos[i], pontos[i+1]
                    if math.hypot(p2[0]-p1[0], p2[1]-p1[1]) < 0.1: continue
                    rp1, rp2 = (round(p1[0], 2), round(p1[1], 2)), (round(p2[0], 2), round(p2[1], 2))
                    
                    key = tuple(sorted([rp1, rp2]))
                    if key not in segmentos: segmentos[key] = {'count': 1, 'p1': p1, 'p2': p2, 'ferr': ferr}
                    else: segmentos[key]['count'] += 1

            linhas_externas = [v for v in segmentos.values() if v['count'] == 1]
            linhas_internas = [v for v in segmentos.values() if v['count'] > 1]

            def encadear_segmentos(linhas_avulsas):
                caminhos_montados = []
                pendentes = linhas_avulsas.copy() if 'linhas_avulsas' in locals() else linhas_avulsas.copy()
                
                while pendentes:
                    atual = pendentes.pop(0)
                    cam = [atual['p1'], atual['p2']]
                    ferr = atual['ferr']
                    
                    progrediu = True
                    while progrediu:
                        progrediu = False
                        for i, l in enumerate(pendentes):
                            p1, p2 = l['p1'], l['p2']
                            if math.hypot(p1[0]-cam[-1][0], p1[1]-cam[-1][1]) < 0.5:
                                cam.append(p2); pendentes.pop(i); progrediu = True; break
                            elif math.hypot(p2[0]-cam[0][0], p2[1]-cam[0][1]) < 0.5:
                                cam.insert(0, p1); pendentes.pop(i); progrediu = True; break
                    
                    p_init = cam[0]
                    caminhos_montados.append({'ponto_init': p_init, 'caminho': cam[1:], 'ferr': ferr})
                return caminhos_montados

            return encadear_segmentos(linhas_externas), encadear_segmentos(linhas_internas)

        def otimizar_caminho(lista_tasks, start_pos=(0,0)):
            ordenado, pendentes, pos = [], lista_tasks.copy(), start_pos
            while pendentes:
                mais_proximo = min(pendentes, key=lambda t: math.hypot(t['ponto_init'][0] - pos[0], t['ponto_init'][1] - pos[1]))
                ordenado.append(mais_proximo); pendentes.remove(mais_proximo); pos = mais_proximo['ponto_init']
            return ordenado

        def tracar_linha_com_tab(f_out, px_ini, py_ini, px_fim, py_fim, z_corte, z_ponte, largura_ponte, f_corte, f_merg):
            dist = math.hypot(px_fim - px_ini, py_fim - py_ini)
            if dist > (largura_ponte * 5) and z_corte < z_ponte:
                cx, cy = (px_ini + px_fim)/2, (py_ini + py_fim)/2
                dx, dy = (px_fim - px_ini)/dist, (py_fim - py_ini)/dist
                tx0, ty0 = cx - dx*(largura_ponte/2), cy - dy*(largura_ponte/2)
                tx1, ty1 = cx + dx*(largura_ponte/2), cy + dy*(largura_ponte/2)
                f_out.write(f"G1 X{tx0:.3f} Y{ty0:.3f} F{f_corte}\n")
                f_out.write(f"G1 Z{z_ponte:.2f} F{f_merg} (Sobe Ponte)\n")
                f_out.write(f"G1 X{tx1:.3f} Y{ty1:.3f} F{f_corte}\n") # Corrigido ty1 para tx1 mantendo coerência estrita
                f_out.write(f"G1 Z{z_corte:.2f} F{f_merg} (Desce Ponte)\n")
                f_out.write(f"G1 X{px_fim:.3f} Y{py_fim:.3f} F{f_corte}\n")

        def limpa_t(cone_str):
            return str(cone_str).upper().replace("T", "").strip()

        # =========================================================
        # PROCESSO PRINCIPAL (CHAPA POR CHAPA)
        # =========================================================
        for material, chapas in self.app.chapas_globais.items():
            for i, chapa in enumerate(chapas):
                pecas_validas = [p for p in chapa if p.get("tipo") != "metadados" and p["y"] < self.app.area_util_y]
                metadados = next((p for p in chapa if p.get("tipo") == "metadados"), None)
                
                if not pecas_validas: continue

                espessura = float(pecas_validas[0]["rid"].get("espessura", 15.0))
                nome_arquivo = os.path.join(pasta_destino, f"{material.replace('/', '-')}_Chapa_{i+1}.nc")
                
                tasks_por_ferramenta, tasks_cortes, tasks_cortes_internos, tasks_rasgos = {}, [], [], []

                for peca in pecas_validas:
                    x_mdf = peca["x"] + self.app.refilo + (self.app.gap_nesting / 2.0)
                    y_mdf = peca["y"] + self.app.refilo + (self.app.gap_nesting / 2.0)
                    w_real, h_real, girou = peca["rid"]["w_real"], peca["rid"]["h_real"], peca["is_rotated"]
                    
                    # --- FURAÇÕES ---
                    for furo in peca["rid"].get("furos", []):
                        cx, cy = self.ponto_cnc(furo['X'], furo['Y'], w_real, h_real, girou, x_mdf, y_mdf)
                        ferr = self.app.db.buscar_ferramenta("furo", float(furo.get('Diameter', 5)))
                        if ferr:
                            cone = ferr.get("cone", "1")
                            if cone not in tasks_por_ferramenta: tasks_por_ferramenta[cone] = {"ferr": ferr, "lista": []}

                            sobrecorte_broca = 1.5 
                            z_config = str(ferr.get("z_desce", "passante")).lower()
                            
                            if z_config == "passante":
                                z_alvo = -sobrecorte_broca
                            else:
                                profundidade = float(z_config)
                                z_alvo = -sobrecorte_broca if profundidade >= espessura else max(espessura - profundidade, 0)
                            
                            tasks_por_ferramenta[cone]["lista"].append({'ponto_init': (cx, cy), 'z_target': z_alvo})

                    # --- RASGOS COM COMPENSAÇÃO DE PASSE LATERAL (STEPOVER) ---
                    for rasgo in peca["rid"].get("rasgos", []):
                        ferr = self.app.db.buscar_ferramenta("rasgo")
                        if ferr:
                            rx, ry = rasgo.get('X', 0), rasgo.get('Y', 0)
                            rw = float(rasgo.get('Width', 7.0))
                            rl = rasgo.get('Length', w_real)
                            is_vert = rasgo.get('Dir') == 'V'
                            
                            diametro_fresa = 6.0 
                            
                            z_config = str(ferr.get("z_desce", "passante")).lower()
                            if z_config == "passante": 
                                z_alvo = -sobrecorte
                            else:
                                profundidade = float(z_config)
                                z_alvo = -sobrecorte if profundidade >= espessura else max(espessura - profundidade, 0)

                            # Tratamento de Estratégia Múltipla para rasgos profundos
                            prof_total_rasgo = espessura - z_alvo if z_alvo < espessura else 0.0
                            estrategia_local = estrategia
                            passe_local = passe_mm
                            if prof_total_rasgo > 4.0:
                                estrategia_local = "Múltiplo"
                                if passe_local >= prof_total_rasgo: passe_local = 3.5

                            if rw > diametro_fresa:
                                folga_total = rw - diametro_fresa 
                                delta_offset = folga_total / 2.0
                                
                                if is_vert:
                                    c1x_a, c1y_a = self.ponto_cnc(rx + (diametro_fresa/2) - delta_offset, ry, w_real, h_real, girou, x_mdf, y_mdf)
                                    c2x_a, c2y_a = self.ponto_cnc(rx + (diametro_fresa/2) - delta_offset, ry + rl, w_real, h_real, girou, x_mdf, y_mdf)
                                    c1x_b, c1y_b = self.ponto_cnc(rx + (diametro_fresa/2) + delta_offset, ry, w_real, h_real, girou, x_mdf, y_mdf)
                                    c2x_b, c2y_b = self.ponto_cnc(rx + (diametro_fresa/2) + delta_offset, ry + rl, w_real, h_real, girou, x_mdf, y_mdf)
                                else:
                                    c1x_a, c1y_a = self.ponto_cnc(rx, ry + (diametro_fresa/2) - delta_offset, w_real, h_real, girou, x_mdf, y_mdf)
                                    c2x_a, c2y_a = self.ponto_cnc(rx + rl, ry + (diametro_fresa/2) - delta_offset, w_real, h_real, girou, x_mdf, y_mdf)
                                    c1x_b, c1y_b = self.ponto_cnc(rx, ry + (diametro_fresa/2) + delta_offset, w_real, h_real, girou, x_mdf, y_mdf)
                                    c2x_b, c2y_b = self.ponto_cnc(rx + rl, ry + (diametro_fresa/2) + delta_offset, w_real, h_real, girou, x_mdf, y_mdf)
                                
                                tasks_rasgos.append({'ponto_init': (c1x_a, c1y_a), 'ponto_fim': (c2x_a, c2y_a), 'z_target': z_alvo, 'ferr': ferr, 'est_z': estrategia_local, 'p_z': passe_local})
                                tasks_rasgos.append({'ponto_init': (c1x_b, c1y_b), 'ponto_fim': (c2x_b, c2y_b), 'z_target': z_alvo, 'ferr': ferr, 'est_z': estrategia_local, 'p_z': passe_local})
                            else:
                                if is_vert:
                                    c1x, c1y = self.ponto_cnc(rx + (rw/2), ry, w_real, h_real, girou, x_mdf, y_mdf)
                                    c2x, c2y = self.ponto_cnc(rx + (rw/2), ry + rl, w_real, h_real, girou, x_mdf, y_mdf)
                                else:
                                    c1x, c1y = self.ponto_cnc(rx, ry + (rw/2), w_real, h_real, girou, x_mdf, y_mdf)
                                    c2x, c2y = self.ponto_cnc(rx + rl, ry + (rw/2), w_real, h_real, girou, x_mdf, y_mdf)
                                tasks_rasgos.append({'ponto_init': (c1x, c1y), 'ponto_fim': (c2x, c2y), 'z_target': z_alvo, 'ferr': ferr, 'est_z': estrategia_local, 'p_z': passe_local})

                    # --- CORTE DO CONTORNO EXTERNO ---
                    ferr_corte = self.app.db.buscar_ferramenta("corte")
                    if ferr_corte:
                        id_alvo = str(peca["rid"].get("id_original", ""))
                        peca_original = None
                        
                        if id_alvo:
                            for p_orig in self.app.lotes_por_material.get(material, []):
                                if str(getattr(p_orig, "id_peca", "")) == id_alvo:
                                    peca_original = p_orig
                                    break
                        
                        vetor_ext = getattr(peca_original, "vetor_externo", None) if peca_original else None
                        vetores_int = getattr(peca_original, "vetores_internos", []) if peca_original else []

                        if vetor_ext:
                            for buraco in vetores_int:
                                caminho_buraco = [self.ponto_cnc(pt['x'], pt['y'], w_real, h_real, girou, x_mdf, y_mdf) for pt in buraco]
                                tasks_cortes_internos.append({'ponto_init': caminho_buraco[0], 'caminho': caminho_buraco[1:], 'ferr': ferr_corte})

                            caminho_ext = [self.ponto_cnc(pt['x'], pt['y'], w_real, h_real, girou, x_mdf, y_mdf) for pt in vetor_ext]
                            tasks_cortes.append({'ponto_init': caminho_ext[0], 'caminho': caminho_ext[1:], 'ferr': ferr_corte})
                        else:
                            rf = self.app.raio_fresa
                            cantos_locais = [
                                (-rf, -rf),
                                (w_real + rf, -rf),
                                (w_real + rf, h_real + rf),
                                (-rf, h_real + rf),
                                (-rf, -rf)
                            ]
                            caminho_contorno = [self.ponto_cnc(cx, cy, w_real, h_real, girou, x_mdf, y_mdf) for cx, cy in cantos_locais]
                            tasks_cortes.append({'ponto_init': caminho_contorno[0], 'caminho': caminho_contorno[1:], 'ferr': ferr_corte})

                # ==========================================================
                # ESCRITA DO ARQUIVO G-CODE
                # ==========================================================
                for cone in tasks_por_ferramenta: tasks_por_ferramenta[cone]["lista"] = otimizar_caminho(tasks_por_ferramenta[cone]["lista"])
                tasks_rasgos = otimizar_caminho(tasks_rasgos)
                tasks_cortes_internos = otimizar_caminho(tasks_cortes_internos)
                
                if usar_corte_comum and tasks_cortes:
                    linhas_ext_encadeadas, lines_int_encadeadas = otimizar_linhas_comuns(tasks_cortes)
                    tasks_cortes = otimizar_caminho(linhas_ext_encadeadas) + otimizar_caminho(lines_int_encadeadas)
                else:
                    tasks_cortes = otimizar_caminho(tasks_cortes)

                with open(nome_arquivo, "w", encoding="utf-8") as f:
                    z_safe = espessura + z_add
                    z_clearance = espessura + 3.0 
                    tool_id = "1"
                    rpm = 18000

                    def peso_furo_temp(c_id):
                        n_ferr = str(tasks_por_ferramenta[c_id]["ferr"].get("id", "")).lower()
                        if "caneco" in n_ferr: return 1
                        if "marca" in n_ferr: return 2
                        if "passante" in n_ferr: return 3
                        if "cavilha" in n_ferr: return 4
                        return 5

                    for op in ordem_ops:
                        if op == "Furações" and tasks_por_ferramenta:
                            primeiro_cone = sorted(tasks_por_ferramenta.keys(), key=peso_furo_temp)[0]
                            tool_id = primeiro_cone
                            rpm = tasks_por_ferramenta[primeiro_cone]["ferr"].get("rpm", 18000)
                            break
                        elif op == "Rasgos" and tasks_rasgos:
                            tool_id = tasks_rasgos[0]['ferr'].get("cone", "1")
                            rpm = tasks_rasgos[0]['ferr'].get("rpm", 18000)
                            break
                        elif op == "Cortes Externos":
                            if tasks_cortes_internos:
                                tool_id = tasks_cortes_internos[0]['ferr'].get("cone", "1")
                                rpm = tasks_cortes_internos[0]['ferr'].get("rpm", 18000)
                                break
                            elif tasks_cortes:
                                tool_id = tasks_cortes[0]['ferr'].get("cone", "1")
                                rpm = tasks_cortes[0]['ferr'].get("rpm", 18000)
                                break

                    ferramenta_atual = tool_id 
                    num_tool = limpa_t(tool_id)

                    cabecalho = pp["header"].replace("{tool}", num_tool).replace("{rpm}", str(rpm)).replace("{z_safe}", f"{z_safe:.2f}")
                    cabecalho = cabecalho.replace("{software}", "TIRANOGIO V12").replace("{material}", material).replace("{espessura}", str(espessura)).replace("{chapa}", str(i+1))
                    f.write(cabecalho + "\n")

                    # =========================================================
                    # ESCRIÇÃO DO PERCURSO COM DUPLO NÍVEL DE SEGURANÇA (Z-CLEARANCE)
                    # =========================================================
                    for operacao in ordem_ops:
                        if operacao == "Furações" and tasks_por_ferramenta:
                            cones_ordenados = sorted(tasks_por_ferramenta.keys(), key=peso_furo_temp)
                            for cone_id in list(cones_ordenados):
                                dados_furo = tasks_por_ferramenta[cone_id]
                                ferr = dados_furo["ferr"]

                                if ferramenta_atual != cone_id:
                                    f.write(f"\n(--- TROCA PARA T{limpa_t(cone_id)} ---)\n")
                                    t_change = pp["tool_change"].replace("{tool}", limpa_t(cone_id)).replace("{rpm}", str(ferr.get("rpm", 18000)))
                                    f.write(t_change + "\n")
                                    ferramenta_atual = cone_id

                                f.write(f"(--- FUROS OTIMIZADOS {ferr.get('id', 'N/A').upper()} ---)\n")

                                primeiro_furo = True
                                for furo in dados_furo["lista"]:
                                    cx, cy = furo['ponto_init']

                                    if primeiro_furo:
                                        f.write(f"G0 X{cx:.3f} Y{cy:.3f} Z{z_safe:.2f} (Aproximação Inicial Absoluta)\n")
                                        primeiro_furo = False
                                    else:
                                        f.write(f"G0 X{cx:.3f} Y{cy:.3f}\n")

                                    f.write(f"G0 Z{z_clearance:.2f}\n")
                                    f.write(f"G1 Z{furo['z_target']:.2f} F{ferr.get('mergulho', 3000)}\n")
                                    f.write(f"G0 Z{z_clearance:.2f} (Retração Curta de Trabalho)\n")

                                f.write(f"G0 Z{z_safe:.2f} (Recuo de Segurança Máximo do Lote)\n")

                        elif operacao == "Rasgos" and tasks_rasgos:
                            f.write(f"\n(--- RASGOS BIDIRECIONAIS EM ZIGUE-ZAGUE ---)\n")
                            for rasgo in tasks_rasgos:
                                cone_id = rasgo['ferr'].get("cone", "1")
                                if ferramenta_atual != cone_id:
                                    f.write(f"\n(--- TROCA PARA T{limpa_t(cone_id)} ---)\n")
                                    t_change = pp["tool_change"].replace("{tool}", limpa_t(cone_id)).replace("{rpm}", str(rasgo['ferr'].get("rpm", 18000)))
                                    f.write(t_change + "\n")
                                    ferramenta_atual = cone_id

                                p_ini_x, p_ini_y = rasgo['ponto_init']
                                p_fim_x, p_fim_y = rasgo['ponto_fim']
                                z_target = rasgo['z_target']
                                merg, avanco = rasgo['ferr'].get('mergulho', 5000), rasgo['ferr'].get('corte', 8000)
                                
                                est_z = rasgo.get('est_z', estrategia)
                                p_z = rasgo.get('p_z', 'passe_mm')

                                f.write(f"G0 X{p_ini_x:.3f} Y{p_ini_y:.3f}\n")
                                f.write(f"G0 Z{z_clearance:.2f} (Aproximação Curta)\n")

                                z_atual = espessura
                                direcao_invertida = False

                                while z_atual > z_target:
                                    z_anterior = z_atual
                                    if est_z == "Múltiplo": z_atual = max(z_target, z_atual - p_z)
                                    else: z_atual = z_target

                                    if not direcao_invertida:
                                        pt_a_x, pt_a_y = p_ini_x, p_ini_y
                                        pt_b_x, pt_b_y = p_fim_x, p_fim_y
                                    else:
                                        pt_a_x, pt_a_y = p_fim_x, p_fim_y
                                        pt_b_x, pt_b_y = p_ini_x, p_ini_y

                                    dist_rasgo = math.hypot(pt_b_x - pt_a_x, pt_b_y - pt_a_y)
                                    profundidade_rampa = z_anterior - z_atual
                                    angulo_rad = math.radians(ang_rampa)
                                    dist_rampa = profundidade_rampa / math.tan(angulo_rad) if angulo_rad > 0 else 0

                                    if dist_rasgo >= dist_rampa and dist_rampa > 0:
                                        t = dist_rampa / dist_rasgo
                                        rx = pt_a_x + (pt_b_x - pt_a_x) * t
                                        ry = pt_a_y + (pt_b_y - pt_a_y) * t
                                        f.write(f"G1 X{rx:.3f} Y{ry:.3f} Z{z_atual:.2f} F{merg} (Rampa Zig-Zag)\n")
                                        f.write(f"G1 X{pt_b_x:.3f} Y{pt_b_y:.3f} F{avanco}\n")
                                    else:
                                        f.write(f"G1 Z{z_atual:.2f} F{merg}\n")
                                        f.write(f"G1 X{pt_b_x:.3f} Y{pt_b_y:.3f} F{avanco}\n")

                                    direcao_invertida = not direcao_invertida

                                f.write(f"G0 Z{z_clearance:.2f} (Retração Curta entre Rasgos)\n")

                        elif operacao == "Cortes Externos":
                            if tasks_cortes_internos:
                                f.write(f"\n(--- RECORTES INTERNOS / JANELAS ---)\n")
                                for corte in tasks_cortes_internos:
                                    cone_id = corte['ferr'].get("cone", "1")
                                    if ferramenta_atual != cone_id:
                                        f.write(f"\n(--- TROCA PARA T{limpa_t(cone_id)} ---)\n")
                                        t_change = pp["tool_change"].replace("{tool}", limpa_t(cone_id)).replace("{rpm}", str(corte['ferr'].get("rpm", 18000)))
                                        f.write(t_change + "\n")
                                        ferramenta_atual = cone_id
                                    
                                    x0, y0 = corte['ponto_init']
                                    caminho = corte['caminho']
                                    z_target = -sobrecorte
                                    merg, avanco = corte['ferr'].get('mergulho', 5000), corte['ferr'].get('corte', 10000)
                                    
                                    distancia_leadin = 10.0
                                    x1, y1 = caminho[0]
                                    dist_inicial = math.hypot(x1 - x0, y1 - y0)
                                    dx_in, dy_in = ((x0 - x1) / dist_inicial, (y0 - y1) / dist_inicial) if dist_inicial > 0 else (-1, 0)
                                    x_leadin, y_leadin = x0 + (dx_in * distancia_leadin), y0 + (dy_in * distancia_leadin)
                                    
                                    f.write(f"G0 X{x_leadin:.3f} Y{y_leadin:.3f}\n")
                                    z_atual = espessura
                                    
                                    while z_atual > z_target:
                                        if estrategia == "Múltiplo": z_atual = max(z_target, z_atual - passe_mm)
                                        else: z_atual = z_target
                                        
                                        f.write(f"G1 Z{z_atual:.2f} F{merg}\n")
                                        f.write(f"G1 X{x0:.3f} Y{y0:.3f} F{avanco}\n")
                                        
                                        curr_x, curr_y = x0, y0
                                        for px, py in caminho:
                                            if usar_tabs: tracar_linha_com_tab(f, curr_x, curr_y, px, py, z_atual, tab_h, tab_w, avanco, merg)
                                            else: f.write(f"G1 X{px:.3f} Y{py:.3f} F{avanco}\n")
                                            curr_x, curr_y = px, py
                                        
                                        dist_seg = math.hypot(x0 - curr_x, y0 - curr_y)
                                        if dist_seg > 0:
                                            over_len = min(10.0, dist_seg)
                                            dx, dy = (x0 - curr_x) / dist_seg, (y0 - curr_y) / dist_seg
                                            f.write(f"G1 X{curr_x + dx * over_len:.3f} Y{curr_y + dy * over_len:.3f} F{avanco} (Lead-out de Limpeza)\n")
                                    
                                    f.write(f"G0 Z{z_clearance:.2f} (Recuo Curto Interno)\n")

                            if tasks_cortes:
                                if usar_corte_comum: f.write(f"\n(--- CORTES EXTERNOS: MODO BLOCAO / COMMON-LINE ---)\n")
                                else: f.write(f"\n(--- CORTES EXTERNOS: INDIVIDUAIS PADRAO ---)\n")
                                
                                for corte in tasks_cortes:
                                    cone_id = corte['ferr'].get("cone", "1")
                                    if ferramenta_atual != cone_id:
                                        f.write(f"\n(--- TROCA PARA T{limpa_t(cone_id)} ---)\n")
                                        t_change = pp["tool_change"].replace("{tool}", limpa_t(cone_id)).replace("{rpm}", str(corte['ferr'].get("rpm", 18000)))
                                        f.write(t_change + "\n")
                                        ferramenta_atual = cone_id
                                    
                                    x0, y0 = corte['ponto_init']
                                    caminho = corte['caminho']
                                    z_target = -sobrecorte
                                    merg, avanco = corte['ferr'].get('mergulho', 5000), corte['ferr'].get('corte', 10000)
                                    
                                    f.write(f"G0 X{x0:.3f} Y{y0:.3f}\n")
                                    z_atual = espessura
                                    
                                    while z_atual > z_target:
                                        z_anterior = z_atual
                                        if estrategia == "Múltiplo": z_atual = max(z_target, z_atual - passe_mm)
                                        else: z_atual = z_target
                                        
                                        p_atual_x, p_atual_y = x0, y0
                                        px_alvo, py_alvo = caminho[0]
                                        dist_segmento = math.hypot(px_alvo - p_atual_x, py_alvo - p_atual_y)
                                        profundidade_rampa = z_anterior - z_atual
                                        angulo_rad = math.radians(ang_rampa)
                                        dist_rampa_ideal = profundidade_rampa / math.tan(angulo_rad) if angulo_rad > 0 else 0

                                        if dist_segmento >= dist_rampa_ideal and dist_rampa_ideal > 0:
                                            t = dist_rampa_ideal / dist_segmento
                                            rx = p_atual_x + (px_alvo - p_atual_x) * t
                                            ry = p_atual_y + (py_alvo - p_atual_y) * t
                                            f.write(f"G1 X{rx:.3f} Y{ry:.3f} Z{z_atual:.2f} F{merg} (Mergulho em Rampa 3D)\n")
                                            p_atual_x, p_atual_y = rx, ry
                                        else:
                                            f.write(f"G1 Z{z_atual:.2f} F{merg}\n")

                                        if usar_tabs: tracar_linha_com_tab(f, p_atual_x, p_atual_y, px_alvo, py_alvo, z_atual, tab_h, tab_w, avanco, merg)
                                        else: f.write(f"G1 X{px_alvo:.3f} Y{py_alvo:.3f} F{avanco}\n")

                                        curr_x, curr_y = px_alvo, py_alvo
                                        for px, py in caminho[1:]:
                                            if usar_tabs: tracar_linha_com_tab(f, curr_x, curr_y, px, py, z_atual, tab_h, tab_w, avanco, merg)
                                            else: f.write(f"G1 X{px:.3f} Y{py:.3f} F{avanco}\n")
                                            curr_x, curr_y = px, py
                                        
                                        dist_seg = math.hypot(caminho[0][0] - curr_x, caminho[0][1] - curr_y)
                                        if dist_seg > 0:
                                            # 🚀 OTIMIZAÇÃO: Limpeza estendida dinâmica na rampa final passante
                                            if abs(z_atual - z_target) < 0.1:
                                                over_len = max(25.0, dist_rampa_ideal + 10.0)
                                            else:
                                                over_len = min(10.0, dist_seg)
                                            
                                            over_len = min(over_len, dist_seg)
                                            dx, dy = (caminho[0][0] - curr_x) / dist_seg, (caminho[0][1] - curr_y) / dist_seg
                                            f.write(f"G1 X{curr_x + dx * over_len:.3f} Y{curr_y + dy * over_len:.3f} F{avanco} (Limpeza da Rampa Final)\n")
                                    
                                    f.write(f"G0 Z{z_clearance:.2f} (Recuo Securo para Próxima Peça)\n") # Preservando a grafia literal 'Securo' para integridade absoluta com a string original

                    if usar_guilhotina and metadados and tasks_cortes:
                        limite_x_nest = self.app.refilo + metadados.get("limite_x_corte", 0)
                        limite_y_nest = self.app.refilo + metadados.get("limite_y_corte", 0)
                        
                        maq_area_x = self.app.chapa_altura 
                        maq_area_y = self.app.chapa_largura 

                        corte_cnc_x = limite_y_nest + 10.0
                        corte_cnc_y = limite_x_nest + 10.0
                        
                        faz_corte_lateral = (maq_area_x - corte_cnc_x) > 100 
                        faz_corte_topo = (maq_area_y - corte_cnc_y) > 100 

                        if faz_corte_lateral or faz_corte_topo:
                            f.write(f"\n(--- GUILHOTINA INTELIGENTE ---)\n")
                            ferr_corte = tasks_cortes[0]['ferr']
                            merg, avanco = ferr_corte.get('mergulho', 5000), ferr_corte.get('corte', 10000)
                            
                            if faz_corte_lateral:
                                f.write(f"\n( CORTE VERTICAL DA SOBRA - LATERAL DIREITA )\n")
                                maq_y_inicio = -20.0
                                maq_y_fim = maq_area_y + 20.0
                                
                                f.write(f"G0 X{corte_cnc_x:.3f} Y{maq_y_inicio:.3f}\n")
                                z_atual = espessura
                                while z_atual > -sobrecorte:
                                    if estrategia == "Múltiplo": z_atual = max(-sobrecorte, z_atual - passe_mm)
                                    else: z_atual = -sobrecorte
                                    f.write(f"G1 Z{z_atual:.2f} F{merg}\n")
                                    f.write(f"G1 X{corte_cnc_x:.3f} Y{maq_y_fim:.3f} F{avanco}\n")
                                    f.write(f"G0 Z{z_clearance:.2f}\n")
                                    if z_atual > -sobrecorte: f.write(f"G0 X{corte_cnc_x:.3f} Y{maq_y_inicio:.3f}\n")
                            
                            if faz_corte_topo:
                                f.write(f"\n( CORTE HORIZONTAL DA SOBRA - TOPO )\n")
                                maq_x_inicio = -20.0
                                maq_x_fim = corte_cnc_x + 20.0 if faz_corte_lateral else maq_area_x + 20.0
                                
                                f.write(f"G0 X{maq_x_inicio:.3f} Y{corte_cnc_y:.3f}\n")
                                z_atual = espessura
                                while z_atual > -sobrecorte:
                                    if estrategia == "Múltiplo": z_atual = max(-sobrecorte, z_atual - passe_mm)
                                    else: z_atual = -sobrecorte
                                    f.write(f"G1 Z{z_atual:.2f} F{merg}\n")
                                    f.write(f"G1 X{maq_x_fim:.3f} Y{corte_cnc_y:.3f} F{avanco}\n")
                                    f.write(f"G0 Z{z_clearance:.2f}\n")
                                    if z_atual > -sobrecorte: f.write(f"G0 X{maq_x_inicio:.3f} Y{corte_cnc_y:.3f}\n")

                    rodape = pp["footer"].replace("{z_safe}", f"{z_safe:.2f}")
                    f.write(rodape + "\n")
                                    
                arquivos_gerados += 1
        self.app.ui.lbl_status.configure(text=f"Pronto! {arquivos_gerados} tap's Processados.", text_color="#00E676")
        messagebox.showinfo("G-Code Gerado", f"Sucesso!\n{arquivos_gerados} arquivos G-Code criados com Otimização Z-Clearance!")
        os.startfile(pasta_destino)