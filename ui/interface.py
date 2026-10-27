# TiranoGio_App/ui/interface.py

import tkinter as tk
import customtkinter as ctk
from PIL import Image

class InterfacePrincipal:
    def __init__(self, root, app_core):
        self.root = root
        self.app = app_core

        # Variáveis de Controle de Interface
        self.combo_materiais = None
        self.lbl_status = None
        self.lbl_paginacao = None
        self.btn_ant = None
        self.btn_prox = None
        self.btn_gcode = None
        self.btn_cortecloud = None
        self.btn_etiquetas = None
        self.btn_pdf = None
        self.btn_nesting = None
        self.canvas = None
        self.btn_json = None
        self.lista_pecas = None
        self.barra_aprov = None
        self.var_diam_fresa = tk.StringVar(value="6.0")
        self.var_folga_pecas = tk.StringVar(value="4.0")

        # 1. O PALCO MESTRE (Onde as telas vão se alternar)
        self.root.configure(fg_color="#121212")
        self.container_principal = ctk.CTkFrame(self.root, fg_color="#000000", corner_radius=0)
        self.container_principal.pack(fill="both", expand=True)

        # Inicia o software mostrando a Home Page
        self.construir_tela_inicial()

    def limpar_palco(self):
        """Destrói todos os widgets atuais do contêiner para trocar de tela limpo."""
        for widget in self.container_principal.winfo_children():
            widget.destroy()

    def construir_tela_inicial(self):
        self.limpar_palco()

        # Frame centralizado para o Dashboard
        frame_home = ctk.CTkFrame(self.container_principal, fg_color="transparent")
        frame_home.place(relx=0.5, rely=0.5, anchor="center")

        # Injeção da Logo
        try:
            img = Image.open("logo.png")
            logo = ctk.CTkImage(light_image=img, dark_image=img, size=(430, 430))
            ctk.CTkLabel(frame_home, text="", image=logo).pack(pady=(0, 0))
        except Exception:
            ctk.CTkLabel(frame_home, text="[ LOGO NÃO ENCONTRADA ]", text_color="red").pack(pady=(0, 20))

        # Título da Home
        ctk.CTkLabel(frame_home, text="Sistema CAM & Otimização de Corte", font=ctk.CTkFont(size=16), text_color="#9E9E9E").pack(pady=(0, 40))

        # GRID DE BOTÕES DE ENTRADA
        f_botoes = ctk.CTkFrame(frame_home, fg_color="transparent")
        f_botoes.pack(fill="x")

        btn_abrir = ctk.CTkButton(
            frame_home, text="📂 ABRIR PROJETO SALVO",
            font=ctk.CTkFont(weight="bold", size=14), height=50, width=250,
            fg_color="#455A64", hover_color="#37474F",
            command=self.abrir_modal_historico_clientes
        )
        btn_abrir.pack(pady=10)

        # Coluna 1: Criar do Zero
        f_col1 = ctk.CTkFrame(f_botoes, fg_color="transparent")
        f_col1.pack(side="left", padx=10)
        ctk.CTkLabel(f_col1, text="COMEÇAR NOVO PROJETO", font=ctk.CTkFont(weight="bold", size=12), text_color="#5C5C5C").pack(pady=(0, 10))
        
        ctk.CTkButton(
            f_col1, text="➕ Novo Projeto", font=ctk.CTkFont(weight="bold"), height=45, width=220,
            fg_color="#388E3C", hover_color="#2E7D32", command=self.app.iniciar_novo_projeto
        ).pack(pady=5)

        # Divisória visual
        ctk.CTkFrame(f_botoes, width=2, fg_color="#333").pack(side="left", fill="y", padx=20, pady=10)

        # Coluna 2: Importadores
        f_col2 = ctk.CTkFrame(f_botoes, fg_color="transparent")
        f_col2.pack(side="left", padx=10)
        ctk.CTkLabel(f_col2, text="IMPORTAR PROJETO", font=ctk.CTkFont(weight="bold", size=12), text_color="#5C5C5C").pack(pady=(0, 10))
        ctk.CTkButton(f_col2, text="🌐 Puxar do TiranoGio 3D", font=ctk.CTkFont(weight="bold"),height=40, width=220, fg_color="#7B1FA2", hover_color="#6A1B9A", command=self.app.puxar_modulo_servidor).pack(pady=5)
        ctk.CTkButton(f_col2, text="📄 Importar lista CSV", font=ctk.CTkFont(weight="bold"), height=40, width=220, fg_color="#455A64", hover_color="#37474F", command=lambda: self.app.iniciar_via_importacao('csv')).pack(pady=5)
        ctk.CTkButton(f_col2, text="📦 Importar dados JSON", font=ctk.CTkFont(weight="bold"), height=40, width=220, fg_color="#0288D1", hover_color="#0277BD", command=lambda: self.app.iniciar_via_importacao('json')).pack(pady=5)
        ctk.CTkButton(f_col2, text="📐 Importar vetores DXF", font=ctk.CTkFont(weight="bold"), height=40, width=220, fg_color="#546E7A", hover_color="#37474F", command=lambda: self.app.iniciar_via_importacao('dxf')).pack(pady=5)

    def construir_tela_projeto(self):
        self.limpar_palco()

        # ==========================================
        # 1. BARRA LATERAL (MENU PRINCIPAL) - Fixado no container_principal
        # ==========================================
        self.frame_lateral = ctk.CTkFrame(self.container_principal, width=280, corner_radius=0, fg_color="#1E1E1E")
        self.frame_lateral.pack(side="left", fill="y")
        self.frame_lateral.pack_propagate(False)

        # Cabeçalho Dinâmico do Cliente
        ctk.CTkLabel(self.frame_lateral, text=f"Cliente: {self.app.nome_cliente}", font=ctk.CTkFont(weight="bold", size=16), text_color="#FF9800").pack(pady=(20, 5))
        ctk.CTkButton(self.frame_lateral, text="⬅ Voltar ao Início", fg_color="transparent", text_color="#9E9E9E", border_width=1, border_color="#555", command=self.app.voltar_para_home).pack(pady=(0, 15), padx=20, fill="x")



        # --- SEÇÃO: PROCESSAMENTO ---
        self._criar_titulo_secao(self.frame_lateral, "OTIMIZAÇÃO")

        self.btn_nesting = ctk.CTkButton(self.frame_lateral, text="PROCESSAR NESTING", fg_color="#388E3C", hover_color="#2E7D32", height=40, font=ctk.CTkFont(weight="bold"), command=self.app.processar_nesting)
        self.btn_nesting.pack(fill="x", padx=20, pady=5)

        # 🚀 NOVO CONTROLADOR DE FLUXO: Checkbox para ativação opcional do estoque de retalhos
        self.var_usar_retalhos_banco = tk.BooleanVar(value=True)

        # Criação do checkbox substituindo 'progress_color' pelos parâmetros corretos de cor
        self.chk_usar_retalhos = ctk.CTkCheckBox(master=self.frame_lateral, text="Priorizar Retalhos do Cofre", variable=self.var_usar_retalhos_banco, font=ctk.CTkFont(size=11), fg_color="#00E676")
        self.chk_usar_retalhos.pack(anchor="w", padx=25, pady=(5, 10))

        frame_gap = ctk.CTkFrame(self.frame_lateral, fg_color="transparent")
        frame_gap.pack(fill="x", padx=20, pady=5)
        
        f_diam = ctk.CTkFrame(frame_gap, fg_color="transparent")
        f_diam.pack(fill="x", pady=2)
        ctk.CTkLabel(f_diam, text="Ø Fresa (mm):", text_color="#A0A0A0").pack(side="left")
        ctk.CTkEntry(f_diam, textvariable=self.var_diam_fresa, width=50, justify="center").pack(side="right")
        
        f_folga = ctk.CTkFrame(frame_gap, fg_color="transparent")
        f_folga.pack(fill="x", pady=2)
        ctk.CTkLabel(f_folga, text="Folga (Gap):", text_color="#A0A0A0").pack(side="left")
        ctk.CTkEntry(f_folga, textvariable=self.var_folga_pecas, width=50, justify="center").pack(side="right")

        # --- SEÇÃO: EXPORTAÇÃO ---
        self._criar_titulo_secao(self.frame_lateral, "MÁQUINA & EXPEDIÇÃO")

        self.btn_gcode = ctk.CTkButton(self.frame_lateral, text="⚙️ GERAR G-CODE CNC", fg_color="#00796B", hover_color="#00695C", state="disabled", command=self.app.abrir_configuracao_gcode)
        self.btn_gcode.pack(fill="x", padx=20, pady=5)
        self.btn_etiquetas = ctk.CTkButton(self.frame_lateral, text="🏷️ ETIQUETAS A4", fg_color="#1976D2", hover_color="#1565C0", state="disabled", command=self.app.exportar_etiquetas)
        self.btn_etiquetas.pack(fill="x", padx=20, pady=5)
        self.btn_cortecloud = ctk.CTkButton(self.frame_lateral, text="✈️ EXPORTAR JSON", fg_color="#FF5722", hover_color="#E64A19", command=self.app.exportar_cortecloud)
        self.btn_cortecloud.pack(fill="x", padx=20, pady=5)

        # --- LISTA INTERATIVA ---
        self._criar_titulo_secao(self.frame_lateral, "PEÇAS DA CHAPA ATUAL")

        frame_lista = ctk.CTkFrame(self.frame_lateral, fg_color="#121212", corner_radius=5)
        frame_lista.pack(fill="both", expand=True, padx=20, pady=(5, 10))

        self.lista_pecas = tk.Listbox(frame_lista, bg="#121212", fg="#E0E0E0", font=("Consolas", 9), bd=0, highlightthickness=0, selectbackground="#388E3C")
        self.lista_pecas.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        scroll_lista = ctk.CTkScrollbar(frame_lista, command=self.lista_pecas.yview)
        scroll_lista.pack(side="right", fill="y")
        self.lista_pecas.config(yscrollcommand=scroll_lista.set)

        self.lista_pecas.bind("<<ListboxSelect>>", self.app.destacar_peca_lista)

        self.lbl_status = ctk.CTkLabel(self.frame_lateral, text="Aguardando arquivos...", text_color="#757575", font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_status.pack(side="bottom", pady=10)

        # ==========================================
        # 2. ZONA DE ESPERA / ESTOQUE - Fixado no container_principal
        # ==========================================
        self.frame_estoque = ctk.CTkFrame(self.container_principal, width=220, fg_color="#1E1E1E", corner_radius=0)
        self.frame_estoque.pack(side="right", fill="y")
        self.frame_estoque.pack_propagate(False)

        self._criar_titulo_secao(self.frame_estoque, "ÁREA DE TRANSFERÊNCIA")

        self.btn_nova_peca = ctk.CTkButton(self.frame_estoque, text="+ Nova Peça Avulsa", fg_color="#388E3C", hover_color="#2E7D32", height=32, font=ctk.CTkFont(weight="bold"), command=self.app.abrir_criador_pecas)
        self.btn_nova_peca.pack(fill="x", padx=10, pady=(0, 5))

        self.lista_estoque = tk.Listbox(self.frame_estoque, bg="#121212", fg="#FF9800", font=("Consolas", 9), bd=0, highlightthickness=0, selectbackground="#5D4037")
        self.lista_estoque.pack(fill="both", expand=True, padx=10, pady=10)

        self.lista_estoque.bind("<Double-Button-1>", self.app.resgatar_peca_estoque)
        self.lista_estoque.bind("<<ListboxSelect>>", self.app.selecionar_bloco_estoque)

        ctk.CTkLabel(self.frame_estoque, text="Dê um duplo clique\npara voltar à chapa.", text_color="#757575", font=("Arial", 10)).pack(pady=10)

        # O Workspace - Fixado no container_principal
        frame_direita = ctk.CTkFrame(self.container_principal, fg_color="#121212")
        frame_direita.pack(side="left", fill="both", expand=True, padx=15, pady=15)

        # --- TOPO (Filtros e Visualização) ---
        frame_topo = ctk.CTkFrame(frame_direita, height=60, fg_color="#1E1E1E")
        frame_topo.pack(fill="x", pady=(0, 15))
        frame_topo.pack_propagate(False)

        ctk.CTkLabel(frame_topo, text="Material da Chapa:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15, pady=15)

        self.combo_materiais = ctk.CTkComboBox(frame_topo, state="readonly", width=250, command=self.app.mudar_material_preview)
        self.combo_materiais.pack(side="left", pady=15)
        
        self.btn_injetar_mdf = ctk.CTkButton(frame_topo, text="➕", width=35, height=28, fg_color="#00796B", hover_color="#004D40", font=("Arial", 12, "bold"),command=self.app.abrir_injetor_chapas_dinamico)
        self.btn_injetar_mdf.pack(side="left", padx=2)
        
        self.btn_deposito_retalhos = ctk.CTkButton(frame_topo, text="🪵 Retalhos", width=100, fg_color="#A0522D", hover_color="#8B4513", font=("Arial", 11, "bold"), command=self.app.abrir_gerenciador_retalhos_manual)
        self.btn_deposito_retalhos.pack(side="left", padx=5, pady=15)

        ctk.CTkButton(frame_topo, text="↩️", width=40, fg_color="#424242", hover_color="#616161", command=self.app.desfazer_acao).pack(side="left", padx=(15, 5), pady=15)
        ctk.CTkButton(frame_topo, text="↪️", width=40, fg_color="#424242", hover_color="#616161", command=self.app.refazer_acao).pack(side="left", pady=15)

        ctk.CTkButton(frame_topo, text="⚙️ Máquina CNC", width=120, fg_color="#424242", hover_color="#616161", command=self.app.abrir_setup_maquina).pack(side="right", padx=15, pady=15)
        ctk.CTkButton(frame_topo, text="🛠️ Fresas", width=100, fg_color="#5D4037", hover_color="#4E342E", command=self.app.abrir_gerenciador_ferramentas).pack(side="right", padx=5, pady=15)
        self.btn_pdf = ctk.CTkButton(frame_topo, text="📄 Preview", width=100, fg_color="#757575", state="disabled", command=self.app.gerar_pdf)
        self.btn_pdf.pack(side="right", padx=5, pady=15)

        self.btn_editor = ctk.CTkButton(frame_topo, text="✏️ Editor CAD", width=120, fg_color="#FBC02D", text_color="black", hover_color="#F9A825", font=ctk.CTkFont(weight="bold"), command=self.app.abrir_editor_operacoes)
        self.btn_editor.pack(side="right", padx=5, pady=15)

        self.btn_raiox = ctk.CTkButton(frame_topo, text="👁️ Raio-X", width=100, fg_color="#00838F", hover_color="#006064", command=self.app.alternar_raiox)
        self.btn_raiox.pack(side="right", padx=5, pady=15)

        # --- CANVAS (MESA DE CORTE) ---
        frame_canvas_container = ctk.CTkFrame(frame_direita, fg_color="#2B2B2B", corner_radius=10)
        frame_canvas_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(frame_canvas_container, bg="#2B2B2B", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)

        self.app.graficos.canvas = self.canvas

        self.canvas.bind("<Configure>", lambda e: self.app.graficos.desenhar_chapa())
        self.canvas.bind("<ButtonPress-1>", self.app.iniciar_arrasto)
        self.canvas.bind("<B1-Motion>", self.app.arrastar_peca)
        self.canvas.bind("<ButtonRelease-1>", self.app.soltar_peca)
        self.canvas.bind("<Button-3>", self.app.girar_peca_manual)
        self.canvas.bind("<MouseWheel>", self.app.zoom_mouse)

        self.canvas.bind("<ButtonPress-2>", lambda event: self.canvas.scan_mark(event.x, event.y))
        self.canvas.bind("<B2-Motion>", lambda event: self.canvas.scan_dragto(event.x, event.y, gain=1))

        self.canvas.bind("<Double-Button-1>", self.app.abrir_editor_por_clique)

        # --- RODAPÉ (PAGINAÇÃO) ---
        frame_rodape = ctk.CTkFrame(frame_direita, height=60, fg_color="#1E1E1E")
        frame_rodape.pack(fill="x", pady=(15, 0))
        frame_rodape.pack_propagate(False)

        self.btn_ant = ctk.CTkButton(frame_rodape, text="<<< Anterior", width=120, fg_color="#424242", hover_color="#616161", state="disabled", command=self.app.chapa_anterior)
        self.btn_ant.pack(side="left", padx=15, pady=15)

        self.lbl_paginacao = ctk.CTkLabel(frame_rodape, text="Chapa 0 / 0", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_paginacao.pack(side="left", expand=True)

        self.btn_prox = ctk.CTkButton(frame_rodape, text="Próxima >>>", width=120, fg_color="#424242", hover_color="#616161", state="disabled", command=self.app.chapa_proxima)
        self.btn_prox.pack(side="right", padx=15, pady=15)

        self.barra_aprov = ctk.CTkProgressBar(frame_rodape, width=150, progress_color="#00E676")
        self.barra_aprov.set(0)
        self.barra_aprov.pack(side="right", padx=(10, 15), pady=20)

        self.lbl_aprov = ctk.CTkLabel(frame_rodape, text="Aprov: 0%", font=ctk.CTkFont(weight="bold"))
        self.lbl_aprov.pack(side="right", padx=5)

    def _criar_titulo_secao(self, pai, texto):
        f = ctk.CTkFrame(pai, fg_color="transparent")
        f.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(f, text=texto, text_color="#5C5C5C", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")
        ctk.CTkFrame(f, height=1, fg_color="#333333").pack(side="left", fill="x", expand=True, padx=(10, 0))

    def abrir_modal_historico_clientes(self):
        """Abre uma janela secundária listando os projetos salvos no banco SQLite."""
        projetos = self.app.db.listar_projetos_salvos()
        if not projetos:
            tk.messagebox.showinfo("Histórico Vazio", "Nenhum projeto salvo encontrado no banco de dados.")
            return

        janela_hist = ctk.CTkToplevel(self.root)
        janela_hist.title("Banco de Dados - Projetos Salvos")
        janela_hist.geometry("500x400")
        janela_hist.grab_set()

        ctk.CTkLabel(janela_hist, text="📁 PROJETOS ARMAZENADOS", font=ctk.CTkFont(weight="bold", size=14)).pack(pady=15)

        frame_lista = ctk.CTkScrollableFrame(janela_hist, fg_color="#1E1E1E", width=450, height=280)
        frame_lista.pack(padx=20, pady=5)

        def carregar_e_fechar(p_id):
            dados = self.app.db.carregar_projeto_cliente(p_id)
            if dados:
                self.app.nome_cliente = dados["nome_cliente"]
                self.app.nome_ambiente = dados["nome_ambiente"]
                self.app.lotes_por_material = dados["lotes"]
                self.app.chapas_globais = dados["chapas"]
                self.app.projeto_id_atual = p_id

                janela_hist.destroy()
                self.construir_tela_projeto()
                
                # Atualiza os componentes visuais
                materiais = list(self.app.chapas_globais.keys())
                if materiais:
                    self.combo_materiais.configure(values=materiais)
                    self.combo_materiais.set(materiais[0])
                    self.app.mudar_material_preview()
                
                self.app.logger.info(f"Projeto de {self.app.nome_cliente} carregado do banco de dados com sucesso.")

            self.app.projeto_id_atual = p_id

        for p_id, cliente, ambiente, data in projetos:
            f_item = ctk.CTkFrame(frame_lista, fg_color="#2C2C2C")
            f_item.pack(fill="x", pady=5, padx=5)
            
            texto_info = f"Cliente: {cliente} | Amb: {ambiente}\nSalvo em: {data}"
            ctk.CTkLabel(f_item, text=texto_info, font=ctk.CTkFont(size=11), text_color="#E0E0E0", justify="left").pack(side="left", padx=10, pady=8)
            
            ctk.CTkButton(
                f_item, text="Carregar", width=80, fg_color="#388E3C", hover_color="#2E7D32",
                command=lambda pid=p_id: carregar_e_fechar(pid)
            ).pack(side="right", padx=10, pady=8)