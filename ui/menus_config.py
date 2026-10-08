# TiranoGio_App/ui/menus_config.py

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

class MenusConfiguracao:
    """
    Gaveta que guarda as janelas de Setup Operacional e Biblioteca de Ferramentas.
    Comunica-se diretamente com o BancoDadosSQLite unificado para ler/salvar no banco blindado.
    """
    def __init__(self, app_core):
        self.app = app_core

    def abrir_setup_maquina(self):
        janela = tk.Toplevel(self.app.root)
        janela.title("Setup Operacional")
        janela.geometry("380x350")
        janela.grab_set()

        # Lê os dados diretos do banco SQLite unificado
        config = self.app.db.config_cnc["maquina"]
        
        v_sobre = tk.DoubleVar(value=config.get("sobrecorte_mm", 0.5))
        v_rampa = tk.DoubleVar(value=config.get("angulo_rampa_graus", 15.0))
        v_safe = tk.DoubleVar(value=config.get("z_seguranca_add", 15.0))
        v_usar_tabs = tk.BooleanVar(value=config.get("usar_tabs", True))
        v_tab_w = tk.DoubleVar(value=config.get("tab_largura", 5.0))
        v_tab_h = tk.DoubleVar(value=config.get("tab_espessura", 2.0))

        def cria_linha(pai, texto, var):
            f = tk.Frame(pai); f.pack(fill="x", padx=20, pady=2)
            tk.Label(f, text=texto).pack(side="left")
            tk.Entry(f, textvariable=var, width=8).pack(side="right")

        f_geral = tk.LabelFrame(janela, text=" Geral Z ")
        f_geral.pack(fill="x", padx=15, pady=5)
        cria_linha(f_geral, "Sobrecorte Passante (mm):", v_sobre)
        cria_linha(f_geral, "Ângulo da Rampa (Graus):", v_rampa)
        cria_linha(f_geral, "Z de Segurança (+mm):", v_safe)

        f_tabs = tk.LabelFrame(janela, text=" Pontes de Fixação (TABS) ")
        f_tabs.pack(fill="x", padx=15, pady=5)
        tk.Checkbutton(f_tabs, text="Ativar Pontes no Corte Final?", variable=v_usar_tabs).pack(anchor="w", padx=15)
        cria_linha(f_tabs, "Largura da Ponte (mm):", v_tab_w)
        cria_linha(f_tabs, "Espessura da Ponte Z (mm):", v_tab_h)

        def salvar_configs():
            self.app.db.config_cnc["maquina"].update({
                "sobrecorte_mm": v_sobre.get(), "angulo_rampa_graus": v_rampa.get(), 
                "z_seguranca_add": v_safe.get(), "usar_tabs": v_usar_tabs.get(), 
                "tab_largura": v_tab_w.get(), "tab_espessura": v_tab_h.get()
            })
            self.app.db.salvar_config_cnc()
            janela.destroy()
        
        tk.Button(janela, text="Salvar", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=salvar_configs).pack(fill="x", padx=20, pady=10)

    def abrir_gerenciador_ferramentas(self):
        janela = tk.Toplevel(self.app.root)
        janela.title("Gerenciador de Ferramentas & Hodômetro")
        janela.geometry("650x550")
        janela.configure(bg="#121212")
        janela.grab_set()

        # ==========================================
        # CRIANDO AS ABAS (TABS) MODERNAS
        # ==========================================
        estilo = ttk.Style()
        estilo.theme_use("default")
        estilo.configure("TNotebook", background="#121212", borderwidth=0)
        estilo.configure("TNotebook.Tab", background="#1E1E1E", foreground="white", font=("Arial", 10, "bold"), padding=[15, 5])
        estilo.map("TNotebook.Tab", background=[("selected", "#4CAF50")])

        abas = ttk.Notebook(janela)
        abas.pack(fill="both", expand=True, padx=10, pady=10)

        aba_parametros = tk.Frame(abas, bg="#121212")
        aba_hodometro = tk.Frame(abas, bg="#121212")

        abas.add(aba_parametros, text="⚙️ Parâmetros CNC")
        abas.add(aba_hodometro, text="📊 Hodômetro (Desgaste)")

        # ==========================================
        # ABA 1: PARÂMETROS CNC (Sincronizado com SQLite)
        # ==========================================
        tk.Label(aba_parametros, text="Setup de Avanço e Rotação (RPM)", font=("Arial", 14, "bold"), bg="#121212", fg="#4CAF50").pack(pady=10)

        colunas = ("ID", "Cone", "Tipo", "Mín", "Máx", "Z Desce", "RPM", "Mergulho", "Corte")
        tree = ttk.Treeview(aba_parametros, columns=colunas, show="headings", height=12)
        
        for c in colunas: 
            tree.heading(c, text=c)
            largura = 80 if c in ["RPM", "Mergulho", "Corte"] else 60
            tree.column(c, width=largura, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=5)

        def atualizar_lista():
            for i in tree.get_children(): tree.delete(i)
            # Garante leitura atualizada da memória do banco
            self.app.db.carregar_config_cnc()
            for f in self.app.db.config_cnc.get("ferramentas", []):
                tree.insert("", "end", values=(f.get("id",""), f.get("cone",""), f.get("tipo",""), f.get("min_d",""), f.get("max_d",""), f.get("z_desce",""), f.get("rpm",""), f.get("mergulho",""), f.get("corte","")))

        atualizar_lista()

        def salvar_ferramenta(f_edit=None, j_sec=None, dic_vars=None):
            nova = {
                "id": dic_vars["id"].get(), "cone": dic_vars["cone"].get(), "tipo": dic_vars["tipo"].get(), 
                "min_d": float(dic_vars["min"].get()), "max_d": float(dic_vars["max"].get()), 
                "z_desce": dic_vars["z"].get() if str(dic_vars["z"].get()).lower() == "passante" else float(dic_vars["z"].get()), 
                "rpm": int(dic_vars["rpm"].get()), "mergulho": int(dic_vars["merg"].get()), "corte": int(dic_vars["corte"].get())
            }
            if f_edit: 
                idx = self.app.db.config_cnc["ferramentas"].index(f_edit)
                self.app.db.config_cnc["ferramentas"][idx] = nova
            else: 
                self.app.db.config_cnc["ferramentas"].append(nova)
            
            self.app.db.salvar_config_cnc()
            atualizar_lista()
            j_sec.destroy()

        def form_ferramenta(f_edit=None):
            j_sec = tk.Toplevel(janela)
            j_sec.geometry("400x450")
            j_sec.grab_set()
            f = f_edit or {"id": "", "cone": "T", "tipo": "corte", "min_d": 0, "max_d": 0, "z_desce": "passante", "rpm": 18000, "mergulho": 3000, "corte": 8000}
            
            dic_vars = {
                "id": tk.StringVar(value=f.get("id", "")), "cone": tk.StringVar(value=f.get("cone", "T1")), "tipo": tk.StringVar(value=f.get("tipo", "corte")),
                "min": tk.StringVar(value=f.get("min_d", 0)), "max": tk.StringVar(value=f.get("max_d", 0)), "z": tk.StringVar(value=f.get("z_desce", "passante")),
                "rpm": tk.StringVar(value=f.get("rpm", 18000)), "merg": tk.StringVar(value=f.get("mergulho", 3000)), "corte": tk.StringVar(value=f.get("corte", 8000))
            }
            
            def campo(txt, var_key, box=False, vals=None):
                fr = tk.Frame(j_sec); fr.pack(fill="x", padx=20, pady=4)
                tk.Label(fr, text=txt, width=20, anchor="w").pack(side="left")
                if box: ttk.Combobox(fr, textvariable=dic_vars[var_key], values=vals or [], state="readonly").pack(fill="x", expand=True)
                else: tk.Entry(fr, textvariable=dic_vars[var_key]).pack(fill="x", expand=True)
            
            campo("ID (Ex: Caneco):", "id"); campo("Cone (Ex: T3):", "cone"); campo("Tipo:", "tipo", True, ["corte", "furo", "rasgo"])
            campo("Diâm Mínimo:", "min"); campo("Diâm Máximo:", "max"); campo("Z Desce:", "z")
            campo("Rotação:", "rpm"); campo("Vel. Mergulho:", "merg"); campo("Vel. Corte:", "corte")
            
            tk.Button(j_sec, text="Salvar", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=lambda: salvar_ferramenta(f_edit, j_sec, dic_vars)).pack(fill="x", padx=20, pady=20)

        def btn_editar():
            sel = tree.selection()
            if sel: form_ferramenta(self.app.db.config_cnc["ferramentas"][tree.index(sel[0])])
            
        def btn_excluir():
            sel = tree.selection()
            if sel: 
                del self.app.db.config_cnc["ferramentas"][tree.index(sel[0])]
                self.app.db.salvar_config_cnc()
                atualizar_lista()

        frame_botoes = tk.Frame(aba_parametros, bg="#121212")
        frame_botoes.pack(pady=10)

        tk.Button(frame_botoes, text="+ Nova Ferramenta", bg="#1976D2", fg="white", command=lambda: form_ferramenta()).pack(side="left", padx=5)
        tk.Button(frame_botoes, text="✏️ Editar", command=btn_editar).pack(side="left", padx=5)
        tk.Button(frame_botoes, text="🗑️ Excluir", bg="#D32F2F", fg="white", command=btn_excluir).pack(side="left", padx=5)

        # ==========================================
        # ABA 2: HODÔMETRO (Controle de Desgaste via SQLite)
        # ==========================================
        tk.Label(aba_hodometro, text="Monitoramento de Desgaste (m)", font=("Arial", 14, "bold"), bg="#121212", fg="#FF9800").pack(pady=10)

        frame_scroll = tk.Frame(aba_hodometro, bg="#121212")
        frame_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        canvas_hodo = tk.Canvas(frame_scroll, bg="#1E1E1E", highlightthickness=0)
        scroll_y = ttk.Scrollbar(frame_scroll, orient="vertical", command=canvas_hodo.yview)

        frame_lista_hodo = tk.Frame(canvas_hodo, bg="#1E1E1E")

        canvas_hodo.create_window((0, 0), window=frame_lista_hodo, anchor="nw", width=580)
        canvas_hodo.configure(yscrollcommand=scroll_y.set)

        canvas_hodo.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        frame_lista_hodo.bind("<Configure>", lambda e: canvas_hodo.configure(scrollregion=canvas_hodo.bbox("all")))

        def criar_comando_reset(id_ferramenta_alvo):
            """Função fábrica corrigida: executa o UPDATE direto no SQLite unificado"""
            def zerar_fresa():
                if messagebox.askyesno("Troca de Ferramenta", f"Você instalou uma nova ferramenta?\n\nIsso vai zerar a contagem de '{id_ferramenta_alvo}' para 0 metros. Confirma?"):
                    with self.app.db.conectar() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE ferramentas SET metros_rodados = 0.0 WHERE id_ferramenta = ?", (id_ferramenta_alvo,))
                        conn.commit()
                    janela.destroy()
                    self.abrir_gerenciador_ferramentas()
            return zerar_fresa

        # --- CARREGAMENTO DO HODÔMETRO DIRETO DO COFRE SQLITE ---
        with self.app.db.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_ferramenta, metros_rodados, tipo FROM ferramentas")
            lista_ferramentas_db = cursor.fetchall()

        for row in lista_ferramentas_db:
            id_f = row[0]
            rodados = row[1] or 0.0
            tipo_f = row[2]
            
            # Define limite padrão baseado no tipo de fresa
            limite = 3000.0 if tipo_f == "corte" else 1500.0
            porcentagem = (rodados / limite) * 100 if limite > 0 else 0
            
            frame_item = tk.Frame(frame_lista_hodo, bg="#2C2C2C", bd=1, relief="ridge")
            frame_item.pack(fill="x", padx=10, pady=8)
            
            frame_topo = tk.Frame(frame_item, bg="#2C2C2C")
            frame_topo.pack(fill="x", padx=10, pady=(10, 5))
            
            tk.Label(frame_topo, text=id_f, font=("Arial", 11, "bold"), bg="#2C2C2C", fg="#E0E0E0").pack(side="left")
            
            if porcentagem < 75: cor_texto = "#00E676"
            elif porcentagem < 95: cor_texto = "#FF9800"
            else: cor_texto = "#F44336"
            
            lbl_status = tk.Label(frame_topo, text=f"{rodados:.1f} m / {limite:.1f} m ({porcentagem:.1f}%)", font=("Arial", 10, "bold"), bg="#2C2C2C", fg=cor_texto)
            lbl_status.pack(side="right")
            
            barra = ttk.Progressbar(frame_item, length=400, mode='determinate')
            barra['value'] = min(porcentagem, 100) # Evita estouro visual na barra
            barra.pack(fill="x", padx=10, pady=5)
            
            tk.Button(
                frame_item, text="🔄 Trocar / Zerar", bg="#455A64", fg="white",
                font=("Arial", 9, "bold"), cursor="hand2",
                command=criar_comando_reset(id_f)
            ).pack(side="right", padx=10, pady=(0, 10))