# TiranoGio_App/ui/editor_cad_avancado.py

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import uuid
import math

class EditorCADAvancado:
    def __init__(self, app_core, uid_alvo):
        self.app = app_core
        self.root = app_core.root
        self.uid_alvo = uid_alvo

        # Localiza a peça ativa na chapa em memória
        self.peca_alvo = next((p for p in self.app.chapas_editaveis[self.app.indice_chapa_atual] 
                               if p.get("tipo") != "metadados" and p["uid"] == uid_alvo), None)
        
        if not self.peca_alvo:
            messagebox.showerror("Erro", "Peça não localizada na chapa ativa.")
            return

        self.rid = self.peca_alvo["rid"]
        self.w_real = float(self.rid.get("w_real", 0))
        self.h_real = float(self.rid.get("h_real", 0))
        self.esta_rotacionada = self.peca_alvo.get("is_rotated", False)

        # Garante as estruturas de dados necessárias
        if "furos" not in self.rid: self.rid["furos"] = []
        if "rasgos" not in self.rid: self.rid["rasgos"] = []
        if "pontos_perimetro" not in self.rid:
            self.rid["pontos_perimetro"] = [
                {"x": 0.0, "y": 0.0, "tem_fita": False},
                {"x": self.w_real, "y": 0.0, "tem_fita": False},
                {"x": self.w_real, "y": self.h_real, "tem_fita": False},
                {"x": 0.0, "y": self.h_real, "tem_fita": False}
            ]

        # Normalização de rasgos legados (H/V)
        for r in self.rid["rasgos"]:
            if "Dir" not in r:
                r_len = float(r.get("Length", 0))
                r["Dir"] = "H" if abs(r_len - self.w_real) < 2.0 else "V"

        # Dimensões de visualização no palco CAD
        self.w_vista = self.h_real if self.esta_rotacionada else self.w_real
        self.h_vista = self.w_real if self.esta_rotacionada else self.h_real

        # Estado interno do ambiente CAD/CAM
        self.estado_cad = {
            "escala": 1.0, "ox": 0, "oy": 0,
            "tipo_sel": None, "idx_sel": None,
            "snap_x": None, "snap_y": None,
            "em_arraste": False,
            "mouse_x_ant": 0, "mouse_y_ant": 0,
            "grid_intervalo": 10.0,
            "usar_grid_snap": True,
            "modo_desenho": "NENHUM"  # NENHUM, PERIMETRO, OFFSET, FILLET
        }

        self.construir_interface()

    def _rot_pt(self, px, py):
        return (py, self.w_real - px) if self.esta_rotacionada else (px, py)

    def _unrot_pt(self, nx, ny):
        return (self.w_real - ny, nx) if self.esta_rotacionada else (nx, ny)

    def construir_interface(self):
        self.janela_ed = ctk.CTkToplevel(self.root)
        self.janela_ed.title(f"CAD/CAM PRO 2D - {self.rid.get('nome', 'Peça')} ({self.w_real:.0f} x {self.h_real:.0f})")
        self.janela_ed.geometry("1250x780")
        self.janela_ed.grab_set()

        # Painel esquerdo de configurações e ferramentas
        self.f_esq = ctk.CTkFrame(self.janela_ed, width=430, corner_radius=0)
        self.f_esq.pack(side="left", fill="y", padx=5, pady=5)
        self.f_esq.pack_propagate(False)

        # Painel direito do Canvas
        self.f_dir = ctk.CTkFrame(self.janela_ed, fg_color="#121212", corner_radius=10)
        self.f_dir.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self.canvas_cad = tk.Canvas(self.f_dir, bg="#121212", highlightthickness=0)
        self.canvas_cad.pack(fill="both", expand=True, padx=10, pady=10)

        # Controle Global de Grid Superior
        f_grid_ctrl = ctk.CTkFrame(self.f_esq, fg_color="transparent")
        f_grid_ctrl.pack(fill="x", padx=15, pady=5)
        self.sw_grid = ctk.CTkSwitch(f_grid_ctrl, text="Malha Magnética (Snap 10mm)", progress_color="#00E676", font=ctk.CTkFont(size=11), command=self.desenhar_cad)
        self.sw_grid.select()
        self.sw_grid.pack(side="left")

        # Inicialização do Bloco de Abas Operacionais
        self.tabs = ctk.CTkTabview(self.f_esq)
        self.tabs.configure(segmented_button_fg_color="#1E1E1E", segmented_button_selected_color="#00796B")
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)

        self.t_geometria = self.tabs.add("📐 Geometria")
        self.t_fita = self.tabs.add("📼 Fita")
        self.t_furos = self.tabs.add("🕳️ Furações")
        self.t_rasgos = self.tabs.add("➖ Rasgos")

        # Preenche os módulos operacionais de cada aba
        self.configurar_aba_geometria()
        self.configurar_aba_fita()
        self.configurar_aba_furos()
        self.configurar_aba_rasgos()

        # Botão de persistência na parte inferior
        ctk.CTkButton(self.f_esq, text="💾 APLICAR ALTERAÇÕES NA CHAPA", fg_color="#00796B", hover_color="#004D40", height=42, font=ctk.CTkFont(weight="bold"), command=self.salvar_edicoes).pack(side="bottom", fill="x", padx=15, pady=15)

        # Binds do Canvas de Trabalho
        self.canvas_cad.bind("<Configure>", self.desenhar_cad)
        self.canvas_cad.bind("<ButtonPress-1>", self.cad_mouse_press)
        self.canvas_cad.bind("<B1-Motion>", self.cad_mouse_drag)
        self.canvas_cad.bind("<ButtonRelease-1>", self.cad_mouse_release)

        # Inicializa as listas dinâmicas e o desenho
        self.sync_listas()
        self.desenhar_cad()

        # =========================================================
    # ABA 1: GEOMETRIA, PRANCHETA VETORIAL e MODIFICADORES
    # =========================================================
    def configurar_aba_geometria(self):
        lbl_info = ctk.CTkLabel(self.t_geometria, text="FERRAMENTAS VETORIAIS", font=ctk.CTkFont(weight="bold", size=13), text_color="#00E676")
        lbl_info.pack(pady=10)

        f_botoes = ctk.CTkFrame(self.t_geometria, fg_color="transparent")
        f_botoes.pack(fill="x", padx=10, pady=5)

        self.btn_desenhar = ctk.CTkButton(f_botoes, text="✏️ Desenho Livre (MDF)", fg_color="#455A64", hover_color="#37474F", command=self.alternar_modo_desenho)
        self.btn_desenhar.pack(fill="x", pady=4)

        ctk.CTkButton(f_botoes, text="🔳 Resetar p/ Retângulo Padrão", fg_color="#b71c1c", hover_color="#7f0000", command=self.resetar_geometria).pack(fill="x", pady=4)

        f_modificadores = ctk.CTkFrame(self.t_geometria, fg_color="#1A1A1A", corner_radius=8)
        f_modificadores.pack(fill="both", expand=True, padx=10, pady=10)

        lbl_titulo_mod = ctk.CTkLabel(f_modificadores, text="📐 MODIFICADORES DE PERÍMETRO", font=ctk.CTkFont(weight="bold", size=11), text_color="#00796B")
        lbl_titulo_mod.pack(anchor="w", padx=15, pady=(10, 5))

        # Controles para o OFFSET / MOLDURA
        ctk.CTkLabel(f_modificadores, text="Distância / Largura da Moldura (mm):", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=15, pady=(10, 2))
        self.v_offset_dist = tk.StringVar(value="20.0")
        ctk.CTkEntry(f_modificadores, textvariable=self.v_offset_dist, height=28).pack(fill="x", padx=15, pady=2)

        f_off_btns = ctk.CTkFrame(f_modificadores, fg_color="transparent")
        f_off_btns.pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(f_off_btns, text="🔲 Vazar Moldura Interna", fg_color="#00796B", hover_color="#004D40", height=30, command=self.aplicar_moldura_vazada).pack(fill="x", padx=15, pady=2)

        # Controles para o FILLET INDIVIDUAL
        ctk.CTkLabel(f_modificadores, text="Raio do Canto Selecionado (mm):", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=15, pady=(15, 2))
        self.v_fillet_raio = tk.StringVar(value="30.0")
        self.e_fillet = ctk.CTkEntry(f_modificadores, textvariable=self.v_fillet_raio, height=28)
        self.e_fillet.pack(fill="x", padx=15, pady=2)
        
        self.lbl_canto_ativo = ctk.CTkLabel(f_modificadores, text="Clique em um ponto vermelho no canvas para arredondar", font=ctk.CTkFont(size=10, slant="italic"), text_color="#9E9E9E")
        self.lbl_canto_ativo.pack(pady=5)
        
        self.btn_aplicar_fillet = ctk.CTkButton(f_modificadores, text="⭕ Arredondar Canto Selecionado", fg_color="#E65100", hover_color="#BF360C", height=32, font=ctk.CTkFont(weight="bold"), command=self.aplicar_fillet_individual, state="disabled")
        self.btn_aplicar_fillet.pack(fill="x", padx=15, pady=5)

    # =========================================================
    # INTELIGÊNCIA GEOMÉTRICA (MOLDURAS E FILLET UNITÁRIO)
    # =========================================================
    def aplicar_moldura_vazada(self):
        """Calcula a retração paralela e injeta como janela interna de descarte CNC."""
        try:
            distancia = float(self.v_offset_dist.get())
        except ValueError:
            messagebox.showerror("Erro", "Insira um valor numérico válido.")
            return

        pontos_originais = self.rid["pontos_perimetro"]
        n = len(pontos_originais)
        if n < 3: return

        vazado_interno = []
        for i in range(n):
            p_ant = pontos_originais[(i - 1) % n]
            p_at = pontos_originais[i]
            p_prox = pontos_originais[(i + 1) % n]

            v1x, v1y = p_at["x"] - p_ant["x"], p_at["y"] - p_ant["y"]
            l1 = math.hypot(v1x, v1y) or 1.0
            n1x, n1y = -v1y / l1, v1x / l1

            v2x, v2y = p_prox["x"] - p_at["x"], p_prox["y"] - p_at["y"]
            l2 = math.hypot(v2x, v2y) or 1.0
            n2x, n2y = -v2y / l2, v2x / l2

            bx, by = n1x + n2x, n1y + n2y
            lb = math.hypot(bx, by) or 1.0
            bx, by = bx / lb, by / lb

            cos_a = bx * n1x + by * n1y
            fator = 1.0 / cos_a if cos_a != 0 else 1.0

            # Deslocamento interno negativo
            vazado_interno.append({
                "x": round(p_at["x"] - bx * distancia * fator, 1),
                "y": round(p_at["y"] - by * distancia * fator, 1)
            })

        # Inicializa a lista de janelas internas se não existir no modelo
        if "vetores_internos" not in self.rid:
            self.rid["vetores_internos"] = []
        
        self.rid["vetores_internos"].append(vazado_interno)
        messagebox.showinfo("Sucesso", "Moldura interna gerada! O miolo será descartado como janela no G-Code.")
        self.desenhar_cad()

    def preparar_fillet_canto(self, idx_canto):
        self.estado_cad["idx_canto_fillet"] = idx_canto
        self.lbl_canto_ativo.configure(text=f"Canto selecionado: Vértice nº {idx_canto + 1}", text_color="#00E676")
        self.btn_aplicar_fillet.configure(state="normal")

    def aplicar_fillet_individual(self):
        """Arredonda exclusivamente o vértice selecionado pelo operador."""
        idx = self.estado_cad.get("idx_canto_fillet")
        if idx is None: return

        try:
            raio = float(self.v_fillet_raio.get())
        except ValueError:
            messagebox.showerror("Erro", "Insira um valor válido para o raio.")
            return

        pontos = self.rid["pontos_perimetro"]
        n = len(pontos)
        if n < 3: return

        p_ant = pontos[(idx - 1) % n]
        p_at = pontos[idx]
        p_prox = pontos[(idx + 1) % n]

        v1x, v1y = p_ant["x"] - p_at["x"], p_ant["y"] - p_at["y"]
        d1 = math.hypot(v1x, v1y)
        v2x, v2y = p_prox["x"] - p_at["x"], p_prox["y"] - p_at["y"]
        d2 = math.hypot(v2x, v2y)

        if d1 == 0 or d2 == 0: return

        v1x, v1y = v1x / d1, v1y / d1
        v2x, v2y = v2x / d2, v2y / d2

        angulo = math.acos(max(-1.0, min(1.0, v1x * v2x + v1y * v2y)))
        dist_tangencia = raio / math.tan(angulo / 2.0)

        # Ajuste de salvaguarda de tamanho
        if dist_tangencia > min(d1, d2) / 2.0:
            dist_tangencia = min(d1, d2) / 2.0
            raio = dist_tangencia * math.tan(angulo / 2.0)

        pt1_x = p_at["x"] + v1x * dist_tangencia
        pt1_y = p_at["y"] + v1y * dist_tangencia
        pt2_x = p_at["x"] + v2x * dist_tangencia
        pt2_y = p_at["y"] + v2y * dist_tangencia

        nx, ny = v1x + v2x, v1y + v2y
        ln = math.hypot(nx, ny) or 1.0
        nx, ny = nx / ln, ny / ln
        
        cx = p_at["x"] + nx * (raio / math.sin(angulo / 2.0))
        cy = p_at["y"] + ny * (raio / math.sin(angulo / 2.0))

        ang_inicio = math.atan2(pt1_y - cy, pt1_x - cx)
        ang_fim = math.atan2(pt2_y - cy, pt2_x - cx)

        diff = ang_fim - ang_inicio
        if diff > math.pi: diff -= 2 * math.pi
        elif diff < -math.pi: diff += 2 * math.pi

        segmentos_arco = 6
        pontos_interpolados = []
        for j in range(segmentos_arco + 1):
            t = j / segmentos_arco
            a = ang_inicio + diff * t
            pontos_interpolados.append({
                "x": round(cx + raio * math.cos(a), 1),
                "y": round(cy + raio * math.sin(a), 1),
                "tem_fita": p_at.get("tem_fita", False)
            })

        # Substitui o ponto original pela curva gerada
        novos_pontos = pontos[:idx] + pontos_interpolados + pontos[idx+1:]
        self.rid["pontos_perimetro"] = novos_pontos
        
        self.btn_aplicar_fillet.configure(state="disabled")
        self.lbl_canto_ativo.configure(text="Arredondamento aplicado! Selecione outro canto.", text_color="#9E9E9E")
        self.estado_cad["idx_canto_fillet"] = None
        self.desenhar_cad()

    def alternar_modo_desenho(self):
        if self.estado_cad["modo_desenho"] == "PERIMETRO":
            self.estado_cad["modo_desenho"] = "NENHUM"
            self.btn_desenhar.configure(fg_color="#455A64", text="✏️ Desenho Livre (MDF)")
        else:
            self.estado_cad["modo_desenho"] = "PERIMETRO"
            self.btn_desenhar.configure(fg_color="#00796B", text="🟢 Clique no Canvas para Desenhar")
            self.rid["pontos_perimetro"] = [] # Limpa para nova captura nos testes
            self.desenhar_cad()

    def resetar_geometria(self):
        self.estado_cad["modo_desenho"] = "NENHUM"
        self.btn_desenhar.configure(fg_color="#455A64", text="✏️ Desenho Livre (MDF)")
        self.rid["pontos_perimetro"] = [
            {"x": 0.0, "y": 0.0, "tem_fita": False},
            {"x": self.w_real, "y": 0.0, "tem_fita": False},
            {"x": self.w_real, "y": self.h_real, "tem_fita": False},
            {"x": 0.0, "y": self.h_real, "tem_fita": False}
        ]
        self.desenhar_cad()

    # =========================================================
    # ABA 2: GERENCIAMENTO DE FITAS DE BORDA
    # =========================================================
    def configurar_aba_fita(self):
        self.v_base = tk.BooleanVar(value=self.rid["pontos_perimetro"][0].get("tem_fita", False) if len(self.rid["pontos_perimetro"]) > 0 else False)
        self.v_dir = tk.BooleanVar(value=self.rid["pontos_perimetro"][1].get("tem_fita", False) if len(self.rid["pontos_perimetro"]) > 1 else False)
        self.v_topo = tk.BooleanVar(value=self.rid["pontos_perimetro"][2].get("tem_fita", False) if len(self.rid["pontos_perimetro"]) > 2 else False)
        self.v_esq = tk.BooleanVar(value=self.rid["pontos_perimetro"][3].get("tem_fita", False) if len(self.rid["pontos_perimetro"]) > 3 else False)

        f_fitas = ctk.CTkFrame(self.t_fita, fg_color="transparent")
        f_fitas.pack(pady=20)
        
        lbl_topo = "Topo (Y Máx) [Vis. Dir]" if self.esta_rotacionada else "Topo (Y Máx)"
        lbl_esq = "Esq (X=0) [Vis. Topo]" if self.esta_rotacionada else "Esq (X=0)"
        lbl_dir = "Dir (X Máx) [Vis. Base]" if self.esta_rotacionada else "Dir (X Máx)"
        lbl_base = "Base (Y=0) [Vis. Esq]" if self.esta_rotacionada else "Base (Y=0)"

        ctk.CTkCheckBox(f_fitas, text=lbl_topo, variable=self.v_topo, command=self.update_fitas).grid(row=0, column=1, pady=15)
        ctk.CTkCheckBox(f_fitas, text=lbl_esq, variable=self.v_esq, command=self.update_fitas).grid(row=1, column=0, padx=10)
        ctk.CTkCheckBox(f_fitas, text=lbl_dir, variable=self.v_dir, command=self.update_fitas).grid(row=1, column=2, padx=10)
        ctk.CTkCheckBox(f_fitas, text=lbl_base, variable=self.v_base, command=self.update_fitas).grid(row=2, column=1, pady=15)

    def update_fitas(self):
        if len(self.rid["pontos_perimetro"]) >= 4:
            self.rid["pontos_perimetro"][0]["tem_fita"] = self.v_base.get()
            self.rid["pontos_perimetro"][1]["tem_fita"] = self.v_dir.get()
            self.rid["pontos_perimetro"][2]["tem_fita"] = self.v_topo.get()
            self.rid["pontos_perimetro"][3]["tem_fita"] = self.v_esq.get()
            self.desenhar_cad()

    # =========================================================
    # ABA 3: USINAGEM DE FUROS (CAM)
    # =========================================================
    def configurar_aba_furos(self):
        self.frame_scroll_f = ctk.CTkScrollableFrame(self.t_furos, height=160, fg_color="#121212", border_width=1, border_color="#2D2D2D")
        self.frame_scroll_f.pack(fill="x", pady=5)
        self.lista_botoes_furos = []

        f_in_f = ctk.CTkFrame(self.t_furos, fg_color="transparent")
        f_in_f.pack(fill="x", pady=10)
        self.vx, self.vy, self.vd = tk.StringVar(), tk.StringVar(), tk.StringVar()
        
        ctk.CTkEntry(f_in_f, textvariable=self.vx, width=60, placeholder_text="X").grid(row=0, column=0, padx=2)
        ctk.CTkEntry(f_in_f, textvariable=self.vy, width=60, placeholder_text="Y").grid(row=0, column=1, padx=2)
        ctk.CTkEntry(f_in_f, textvariable=self.vd, width=60, placeholder_text="Ø").grid(row=0, column=2, padx=2)

        ctk.CTkButton(f_in_f, text="➕", width=40, fg_color="#388E3C", hover_color="#2E7D32", command=self.add_furo).grid(row=0, column=3, padx=5)
        ctk.CTkButton(f_in_f, text="🗑️", width=40, fg_color="#D32F2F", hover_color="#B71C1C", command=self.del_furo).grid(row=0, column=4, padx=5)

        self.e_fx, self.e_fy, self.e_fd = f_in_f.winfo_children()[0], f_in_f.winfo_children()[1], f_in_f.winfo_children()[2]
        for entry in [self.e_fx, self.e_fy, self.e_fd]:
            entry.bind("<KeyRelease>", self.aplicar_digitacao)

    def add_furo(self):
        self.rid["furos"].append({"X": 50.0, "Y": 50.0, "Diameter": 35.0, "Depth": "passante"})
        self.sync_listas()
        self.desenhar_cad()

    def del_furo(self):
        if self.estado_cad["tipo_sel"] == "furo" and self.estado_cad["idx_sel"] is not None:
            self.rid["furos"].pop(self.estado_cad["idx_sel"])
            self.estado_cad["idx_sel"] = None
            self.sync_listas()
            self.desenhar_cad()

    # =========================================================
    # ABA 4: USINAGEM DE RASGOS / CANAIS (CAM)
    # =========================================================
    def configurar_aba_rasgos(self):
        self.frame_scroll_r = ctk.CTkScrollableFrame(self.t_rasgos, height=160, fg_color="#121212", border_width=1, border_color="#2D2D2D")
        self.frame_scroll_r.pack(fill="x", pady=5)
        self.lista_botoes_rasgos = []

        f_in_r = ctk.CTkFrame(self.t_rasgos, fg_color="transparent")
        f_in_r.pack(fill="x", pady=10)
        self.rx, self.ry, self.rw, self.rl, self.rdir = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(value="V")
        
        ctk.CTkEntry(f_in_r, textvariable=self.rx, width=50, placeholder_text="X").grid(row=0, column=0, padx=2)
        ctk.CTkEntry(f_in_r, textvariable=self.ry, width=50, placeholder_text="Y").grid(row=0, column=1, padx=2)
        ctk.CTkComboBox(f_in_r, variable=self.rdir, values=["V", "H"], width=55).grid(row=0, column=2, padx=2)
        ctk.CTkEntry(f_in_r, textvariable=self.rw, width=50, placeholder_text="Esp").grid(row=1, column=0, pady=5)
        ctk.CTkEntry(f_in_r, textvariable=self.rl, width=50, placeholder_text="Comprimento").grid(row=1, column=1, columnspan=2, sticky="we", padx=2)

        ctk.CTkButton(f_in_r, text="➕", width=40, fg_color="#388E3C", hover_color="#2E7D32", command=self.add_rasgo).grid(row=1, column=3, padx=2)
        ctk.CTkButton(f_in_r, text="🗑️", width=40, fg_color="#D32F2F", hover_color="#B71C1C", command=self.del_rasgo).grid(row=1, column=4, padx=2)

        self.e_rx, self.e_ry, self.e_rw, self.e_rl = f_in_r.winfo_children()[0], f_in_r.winfo_children()[1], f_in_r.winfo_children()[3], f_in_r.winfo_children()[4]
        for entry in [self.e_rx, self.e_ry, self.e_rw, self.e_rl]:
            entry.bind("<KeyRelease>", self.aplicar_digitacao)
        self.rdir.trace_add("write", lambda *args: self.aplicar_digitacao(None))

    def add_rasgo(self):
        self.rid["rasgos"].append({"X": 15.0, "Y": 0.0, "Width": 6.0, "Length": self.h_real, "Dir": "V"})
        self.sync_listas()
        self.desenhar_cad()

    def del_rasgo(self):
        if self.estado_cad["tipo_sel"] == "rasgo" and self.estado_cad["idx_sel"] is not None:
            self.rid["rasgos"].pop(self.estado_cad["idx_sel"])
            self.estado_cad["idx_sel"] = None
            self.sync_listas()
            self.desenhar_cad()

    # =========================================================
    # CORE ENGINE: SINCRONIZAÇÃO E RENDERIZAÇÃO 2D
    # =========================================================
    def sync_listas(self):
        for btn in self.lista_botoes_furos: btn.destroy()
        self.lista_botoes_furos.clear()
        for i, f in enumerate(self.rid["furos"]):
            txt = f"🕳️ Furo {i+1}: X={f.get('X',0):.1f} | Y={f.get('Y',0):.1f} | Ø={f.get('Diameter',5)}"
            bg_c = "#1E73BE" if self.estado_cad["tipo_sel"] == "furo" and self.estado_cad["idx_sel"] == i else "transparent"
            b = ctk.CTkButton(self.frame_scroll_f, text=txt, anchor="w", fg_color=bg_c, text_color="#E0E0E0", height=28, command=lambda idx=i: self.selecionar_item("furo", idx))
            b.pack(fill="x", pady=1)
            self.lista_botoes_furos.append(b)

        for btn in self.lista_botoes_rasgos: btn.destroy()
        self.lista_botoes_rasgos.clear()
        for i, r in enumerate(self.rid["rasgos"]):
            txt = f"➖ {r.get('Dir','V')}: X={r.get('X',0):.1f}, Y={r.get('Y',0):.1f} | E:{r.get('Width',6)} C:{r.get('Length',0)}"
            bg_c = "#D9A74A" if self.estado_cad["tipo_sel"] == "rasgo" and self.estado_cad["idx_sel"] == i else "transparent"
            b = ctk.CTkButton(self.frame_scroll_r, text=txt, anchor="w", fg_color=bg_c, text_color="#E0E0E0", height=28, command=lambda idx=i: self.selecionar_item("rasgo", idx))
            b.pack(fill="x", pady=1)
            self.lista_botoes_rasgos.append(b)

    def selecionar_item(self, tipo, idx):
        self.estado_cad["tipo_sel"], self.estado_cad["idx_sel"] = tipo, idx
        if tipo == "furo":
            self.tabs.set("🕳️ Furações")
            f = self.rid["furos"][idx]
            self.vx.set(str(f.get("X", 0.0)))
            self.vy.set(str(f.get("Y", 0.0)))
            self.vd.set(str(f.get("Diameter", 5.0)))
        elif tipo == "rasgo":
            self.tabs.set("➖ Rasgos")
            r = self.rid["rasgos"][idx]
            self.rx.set(str(r.get("X", 0.0)))
            self.ry.set(str(r.get("Y", 0.0)))
            self.rw.set(str(r.get("Width", 6.0)))
            self.rl.set(str(r.get("Length", self.h_real)))
            self.rdir.set(r.get("Dir", "V"))
        self.sync_listas()
        self.desenhar_cad()

    def aplicar_digitacao(self, e):
        if self.estado_cad["idx_sel"] is None: return
        i = self.estado_cad["idx_sel"]
        try:
            if self.estado_cad["tipo_sel"] == "furo" and i < len(self.rid["furos"]):
                self.rid["furos"][i].update({"X": float(self.vx.get()), "Y": float(self.vy.get()), "Diameter": float(self.vd.get())})
            elif self.estado_cad["tipo_sel"] == "rasgo" and i < len(self.rid["rasgos"]):
                self.rid["rasgos"][i].update({"X": float(self.rx.get()), "Y": float(self.ry.get()), "Width": float(self.rw.get()), "Length": float(self.rl.get()), "Dir": self.rdir.get()})
            self.desenhar_cad()
            self.sync_listas()
        except ValueError:
            pass

    def desenhar_cad(self, event=None):
        self.canvas_cad.delete("all")
        cw, ch = self.canvas_cad.winfo_width(), self.canvas_cad.winfo_height()
        if cw < 50: return

        escala = min((cw - 100) / self.w_vista, (ch - 100) / self.h_vista)
        self.estado_cad["escala"] = escala
        ox = (cw - (self.w_vista * escala)) / 2
        oy = (ch - (self.h_vista * escala)) / 2
        self.estado_cad["ox"], self.estado_cad["oy"] = ox, oy
        y_base_tela = oy + (self.h_vista * escala)

        # RENDER DA MALHA MAGNÉTICA (GRID BACKGROUND)
        step = self.estado_cad["grid_intervalo"]
        for gx in range(0, int(self.w_vista) + 1, int(step)):
            fx = ox + (gx * escala)
            self.canvas_cad.create_line(fx, oy, fx, y_base_tela, fill="#1F1F1F", width=1)
        for gy in range(0, int(self.h_vista) + 1, int(step)):
            fy = y_base_tela - (gy * escala)
            self.canvas_cad.create_line(ox, fy, ox + (self.w_vista * escala), fy, fill="#1F1F1F", width=1)

        # RENDER DO POLÍGONO DA GEOMETRIA DO MDF
        if self.rid["pontos_perimetro"]:
            coords_base = []
            for pt in self.rid["pontos_perimetro"]:
                tx, ty = self._rot_pt(pt['x'], pt['y'])
                coords_base.extend([ox + (tx * escala), y_base_tela - (ty * escala)])
            
            if len(coords_base) >= 4:
                self.canvas_cad.create_polygon(coords_base, fill="#E6C280", outline="#444", width=2)

        # RENDER DA FITA DE BORDA (LINHAS VERMELHAS)
        for i in range(min(4, len(self.rid["pontos_perimetro"]))):
            p1 = self.rid["pontos_perimetro"][i]
            if p1.get("tem_fita"):
                p2 = self.rid["pontos_perimetro"][(i+1) % len(self.rid["pontos_perimetro"])]
                tx1, ty1 = self._rot_pt(p1['x'], p1['y'])
                tx2, ty2 = self._rot_pt(p2['x'], p2['y'])
                self.canvas_cad.create_line(ox + (tx1 * escala), y_base_tela - (ty1 * escala), 
                                            ox + (tx2 * escala), y_base_tela - (ty2 * escala), fill="#D32F2F", width=6)

        # RENDER DE RASGOS
        for i, r in enumerate(self.rid["rasgos"]):
            rx, ry = r.get("X", 0.0), r.get("Y", 0.0)
            rw = r.get("Width", 6.0)
            r_dir = r.get("Dir", "V")
            rl = r.get("Length", self.h_real if r_dir == "V" else self.w_real)

            cantos = [(rx, ry), (rx+rw, ry), (rx+rw, ry+rl), (rx, ry+rl)] if r_dir == "V" else [(rx, ry), (rx+rl, ry), (rx+rl, ry+rw), (rx, ry+rw)]
            coords_r = []
            for cx, cy in cantos:
                tx, ty = self._rot_pt(cx, cy)
                coords_r.extend([ox + (tx * escala), y_base_tela - (ty * escala)])

            cor_r = "#FFEB3B" if self.estado_cad["tipo_sel"] == "rasgo" and self.estado_cad["idx_sel"] == i else "#795548"
            self.canvas_cad.create_polygon(coords_r, fill=cor_r, outline="#222", tags=("op", f"rasgo_{i}"))

        # RENDER DE FUROS
        for i, f in enumerate(self.rid["furos"]):
            tx, ty = self._rot_pt(f.get("X", 0.0), f.get("Y", 0.0))
            cx = ox + (tx * escala)
            cy = y_base_tela - (ty * escala)
            raio_px = max((f.get("Diameter", 5.0) / 2) * escala, 4)

            cor_f = "#00B0FF" if self.estado_cad["tipo_sel"] == "furo" and self.estado_cad["idx_sel"] == i else "#00E676"
            self.canvas_cad.create_oval(cx - raio_px, cy - raio_px, cx + raio_px, cy + raio_px, fill=cor_f, outline="#111", width=2, tags=("op", f"furo_{i}"))

        # GUIAS AUTOMÁTICAS DO SNAP MAGNÉTICO
        if self.estado_cad["snap_x"] is not None:
            sx = ox + (self.estado_cad["snap_x"] * escala)
            self.canvas_cad.create_line(sx, 0, sx, ch, fill="#00E5FF", dash=(4,4), width=1)
        if self.estado_cad["snap_y"] is not None:
            sy = y_base_tela - (self.estado_cad["snap_y"] * escala)
            self.canvas_cad.create_line(0, sy, cw, sy, fill="#FF1744", dash=(4,4), width=1)

        self.canvas_cad.tag_raise("op")

        # RENDERIZADOR DE ALVOS/BOLINHAS PARA CAD/FILLET INDIVIDUAL
        if self.rid["pontos_perimetro"] and self.estado_cad["modo_desenho"] == "NENHUM":
            for idx, pt in enumerate(self.rid["pontos_perimetro"]):
                tx, ty = self._rot_pt(pt['x'], pt['y'])
                cx = ox + (tx * escala)
                cy = y_base_tela - (ty * escala)
                
                # Se for o canto selecionado, pinta de azul, senão vermelho industrial
                cor_sel = "#00E676" if self.estado_cad.get("idx_canto_fillet") == idx else "#D32F2F"
                self.canvas_cad.create_oval(cx-5, cy-5, cx+5, cy+5, fill=cor_sel, outline="#FFF", width=1, tags=("op", f"canto_{idx}"))
                
    # =========================================================
    # EVENTOS MOUSE (ARRANSTE DO CAM E CAPTURA DE VÉRTICES CAD)
    # =========================================================
    def cad_mouse_press(self, e):
        escala = self.estado_cad["escala"]
        ox, oy = self.estado_cad["ox"], self.estado_cad["oy"]
        y_base_tela = oy + (self.h_vista * escala)

        # Captura clique nos marcadores visuais (Bolinhas de Canto)
        item = self.canvas_cad.find_withtag("current")
        if item:
            tags = self.canvas_cad.gettags(item[0])
            tag_canto = next((t for t in tags if t.startswith("canto_")), None)
            if tag_canto:
                idx_canto = int(tag_canto.split("_")[1])
                self.preparar_fillet_canto(idx_canto)
                return

        if self.estado_cad["modo_desenho"] == "PERIMETRO":
            click_x_mm = (e.x - ox) / escala
            click_y_mm = (y_base_tela - e.y) / escala

            if self.sw_grid.get():
                grid = self.estado_cad["grid_intervalo"]
                click_x_mm = round(click_x_mm / grid) * grid
                click_y_mm = round(click_y_mm / grid) * grid

            self.rid["pontos_perimetro"].append({"x": click_x_mm, "y": click_y_mm, "tem_fita": False})
            self.desenhar_cad()
            return

        # Arrasto padrão de furos/rasgos do CAM existente
        if item:
            tags = self.canvas_cad.gettags(item[0])
            tag_op = next((t for t in tags if t.startswith("furo_") or t.startswith("rasgo_")), None)
            if tag_op:
                partes = tag_op.split("_")
                self.selecionar_item(partes[0], int(partes[1]))
                self.estado_cad["em_arraste"] = True
                self.estado_cad["mouse_x_ant"] = e.x
                self.estado_cad["mouse_y_ant"] = e.y

    def cad_mouse_drag(self, e):
        if not self.estado_cad["em_arraste"] or self.estado_cad["idx_sel"] is None: return
        tipo, i = self.estado_cad["tipo_sel"], self.estado_cad["idx_sel"]
        escala = self.estado_cad["escala"]

        dx_vis_mm = (e.x - self.estado_cad["mouse_x_ant"]) / escala
        dy_vis_mm = -(e.y - self.estado_cad["mouse_y_ant"]) / escala

        operacao = self.rid["furos"][i] if tipo == "furo" else self.rid["rasgos"][i]
        orig_x = float(operacao.get("X", 0.0))
        orig_y = float(operacao.get("Y", 0.0))

        vis_x, vis_y = self._rot_pt(orig_x, orig_y)
        novo_vis_x = vis_x + dx_vis_mm
        novo_vis_y = vis_y + dy_vis_mm

        if self.sw_grid.get():
            grid = self.estado_cad["grid_intervalo"]
            novo_vis_x = round(novo_vis_x / grid) * grid
            novo_vis_y = round(novo_vis_y / grid) * grid
            self.estado_cad["snap_x"] = novo_vis_x
            self.estado_cad["snap_y"] = novo_vis_y
        else:
            self.estado_cad["snap_x"], self.estado_cad["snap_y"] = None, None

        novo_vis_x = max(0.0, min(novo_vis_x, self.w_vista))
        novo_vis_y = max(0.0, min(novo_vis_y, self.h_vista))

        novo_orig_x, novo_orig_y = self._unrot_pt(novo_vis_x, novo_vis_y)

        if tipo == "furo":
            self.rid["furos"][i]["X"], self.rid["furos"][i]["Y"] = round(novo_orig_x, 1), round(novo_orig_y, 1)
            self.vx.set(str(self.rid["furos"][i]["X"]))
            self.vy.set(str(self.rid["furos"][i]["Y"]))
        else:
            self.rid["rasgos"][i]["X"], self.rid["rasgos"][i]["Y"] = round(novo_orig_x, 1), round(novo_orig_y, 1)
            self.rx.set(str(self.rid["rasgos"][i]["X"]))
            self.ry.set(str(self.rid["rasgos"][i]["Y"]))

        self.estado_cad["mouse_x_ant"] = e.x
        self.estado_cad["mouse_y_ant"] = e.y
        self.desenhar_cad()

    def cad_mouse_release(self, e):
        self.estado_cad["em_arraste"] = False
        self.estado_cad["snap_x"], self.estado_cad["snap_y"] = None, None
        self.desenhar_cad()
        self.sync_listas()

    def salvar_edicoes(self):
        # Desliga o modo desenho se estiver ativo
        self.estado_cad["modo_desenho"] = "NENHUM"
        # Executa o pipeline de salvamento idêntico ao core do programa original
        self.app.salvar_estado_historico()
        self.app.graficos.desenhar_chapa()
        self.janela_ed.destroy()