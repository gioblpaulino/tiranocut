# TiranoGio_App/main.py

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import uuid
import copy

# Logs
from core.logger import GerenciadorLogs

# Gavetas do Core
from core.seguranca import GerenciadorLicenca
from core.banco_sqlite import BancoDadosSQLite
from core.importadores import GerenciadorImportacao
from core.hodometro import HodometroFerramentas

# Gavetas da Interface
from ui.interface import InterfacePrincipal
from ui.motor_grafico import MotorGrafico
from ui.menus_config import MenusConfiguracao

# Gavetas de Processamento
from processamento.motor_nesting import MotorNesting
from processamento.gerador_pdf import GeradorPDF
from processamento.gerador_gcode import GeradorGCode
from processamento.exportador_cortecloud import ExportadorCorteCloud
from processamento.gerador_etiquetas import GeradorEtiquetas


class TiranoGioApp:
    def __init__(self, root):

        # Inicializa a aplicação principal e configura a janela do sistema
        self.root = root

        # ==========================================
        # 1. CONFIGURAÇÃO DA JANELA PRINCIPAL (UI/UX)
        # ==========================================

        self.root.title("TiranoGio - Inicializando...")
        self.root.geometry("1300x800")

        # Ligar o sistema de rastreamento de logs
        self.logger = GerenciadorLogs()
        self.logger.info("Iniciando sistema... Verificando credenciais de acesso.")

        # Executa a validação de segurança com a janela ativa
        self.validar_acesso_sistema()

    def validar_acesso_sistema(self):

        # ==========================================
        # 2. VERIFICAÇÃO DE LICENÇA
        # ==========================================

        # Cria uma instância do gerenciador de licença e verifica se o software está autorizado a rodar na máquina atual
        self.seguranca = GerenciadorLicenca()
        # Verifica se o software está autorizado a rodar na máquina atual
        autorizado, maquina_id = self.seguranca.verificar_licenca()

        # Se a licença não for válida, exibe uma mensagem de erro e encerra o programa
        if not autorizado:
            # Registra o erro no log com o ID da máquina
            self.logger.erro(
                f"Licença negada! ID da máquina interceptado: {maquina_id}"
            )

            # Exibe uma mensagem de erro para o usuário informando que o software não está licenciado e fornece o código da máquina
            messagebox.showerror(
                "⚠️ ACESSO NEGADO",
                "SOFTWARE NÃO LICENCIADO!\n\n"
                f"Código da sua Máquina: {maquina_id}\n\n"
                "O arquivo 'licenca.key' não foi encontrado ou não pertence a este PC.\n"
                "Um arquivo de texto com o seu código foi gerado na pasta do programa.",
            )

            # Gera um arquivo de texto com o código da máquina para que o usuário possa enviar ao suporte e obter a licença correta
            with open("CODIGO_DA_MAQUINA.txt", "w", encoding="utf-8") as f:
                f.write(
                    f"Envie este código para o suporte para gerar sua licença:\n\n{maquina_id}"
                )

            # Encerra a aplicação
            self.root.destroy()
            return

        # ==========================================
        # 3. LIBERAÇÃO DOS MÓDULOS
        # ==========================================

        # Se a licença for válida, registra a informação no log e atualiza o título da janela para indicar que o software está licenciado
        self.logger.info("Licença validada com sucesso!")
        self.root.title("TiranoGio - Licenciado")

        # Inicializa as variáveis globais do sistema e os módulos principais
        self.carregar_variaveis_globais()
        self.inicializar_modulos_sistema()

    def carregar_variaveis_globais(self):

        self.logger.info("Iniciando carregamento das variáveis globais...")

        self.chapa_largura = 2750.0
        self.chapa_altura = 1830.0
        self.refilo = 20.0
        self.area_util_x = self.chapa_largura - (self.refilo * 2)
        self.area_util_y = self.chapa_altura - (self.refilo * 2)

        # Configurações de fresa e folga
        self.diam_fresa = 6.0
        self.folga_pecas = 4.0
        self.gap_nesting = 10.0  # Soma do diâmetro + folga
        self.gap_fresa = 10.0  # 🚀 Adicione esta linha (diam_fresa + folga_pecas)
        self.raio_fresa = 3.0
        if not hasattr(self, 'gap_fresa'): self.gap_fresa = 6.0
        if not hasattr(self, 'area_util_x'): self.area_util_x = 2750.0
        if not hasattr(self, 'area_util_y'): self.area_util_y = 1830.0
        if not hasattr(self, 'refilo'): self.refilo = 10.0
        # Variáveis de estado do projeto
        self.nome_cliente = "Não Informado"
        self.nome_ambiente = "Não Informado"
        self.pasta_projeto = ""
        self.lotes_por_material = {}
        self.chapas_globais = {}
        self.chapas_editaveis = []
        self.indice_chapa_atual = 0
        self.cores_por_tamanho = {}
        self.historico_undo = []
        self.historico_redo = []
        self.modo_raiox = False
        self.peca_destaque = None
        self.estoque_global_pecas = {}

        # Variável para armazenar o ID do projeto atual, útil para salvar e carregar projetos específicos
        self.projeto_id_atual = None

    def iniciar_novo_projeto(self):
        """Inicia um projeto do zero parametrizando o Estoque de Chapas e os Veios do MDF."""
        self.projeto_id_atual = None

        from customtkinter import (
            CTkInputDialog,
            CTkToplevel,
            CTkLabel,
            CTkEntry,
            CTkFrame,
            CTkButton,
            CTkSwitch,
        )

        dialog = CTkInputDialog(
            text="Digite o nome do Cliente ou Ambiente:", title="Novo Projeto do Zero"
        )
        nome = dialog.get_input()
        if not nome:
            return

        self.nome_cliente = str(nome).strip().upper()
        self.limpar_cache_projeto()

        # Janela de Setup de Matéria-Prima Inicial
        janela_mat = CTkToplevel(self.root)
        janela_mat.title("Abastecer Estoque de Chapas Inicial")
        janela_mat.geometry("400x480")
        janela_mat.grab_set()
        janela_mat.attributes("-topmost", True)

        CTkLabel(
            janela_mat,
            text="📋 CONFIGURAR MDF INICIAL",
            font=("Arial", 14, "bold"),
            text_color="#FF9800",
        ).pack(pady=15)

        form = CTkFrame(janela_mat, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20)

        v_material = tk.StringVar(value="MDF_BRANCO_15MM")
        v_largura = tk.StringVar(value="2750")
        v_altura = tk.StringVar(value="1830")
        v_espessura = tk.StringVar(value="15")
        v_qtd_chapas = tk.StringVar(value="2")
        v_tem_veio = tk.BooleanVar(value=False)

        def criar_campo(txt, var):
            CTkLabel(form, text=txt, font=("Arial", 11, "bold")).pack(
                anchor="w", pady=(5, 2)
            )
            CTkEntry(form, textvariable=var, height=30).pack(fill="x")

        criar_campo("Descrição/Cor do Material:", v_material)
        criar_campo("Comprimento da Chapa X (mm):", v_largura)
        criar_campo("Largura da Chapa Y (mm):", v_altura)
        criar_campo("Espessura do MDF (mm):", v_espessura)
        criar_campo("Quantidade de Chapas Disponíveis:", v_qtd_chapas)

        CTkSwitch(
            form,
            text="Material Possui Veio Amadeirado Ativo",
            variable=v_tem_veio,
            progress_color="#00E676",
        ).pack(anchor="w", pady=15)

        def confirmar_estoque():
            try:
                mat = v_material.get().strip().upper()
                w_chapa = float(v_largura.get())
                h_chapa = float(v_altura.get())
                esp = float(v_espessura.get())
                qtd = int(v_qtd_chapas.get())
            except ValueError:
                messagebox.showerror(
                    "Erro", "Insira valores numéricos válidos para as dimensões."
                )
                return

            self.chapa_largura = w_chapa
            self.chapa_altura = h_chapa
            self.area_util_x = w_chapa - (self.refilo * 2)
            self.area_util_y = h_chapa - (self.refilo * 2)

            # Inicializa a estrutura de dados com metadados para o material definido
            self.chapas_globais[mat] = []
            for _ in range(qtd):
                self.chapas_globais[mat].append(
                    [
                        {
                            "tipo": "metadados",
                            "limite_x_corte": 0,
                            "limite_y_corte": 0,
                            "espessura_chapa": esp,
                            "possui_veio": v_tem_veio.get(),
                        }
                    ]
                )

            self.logger.info(
                f"Projeto criado para {self.nome_cliente}. Estoque inicial: {qtd} chapa(s) de {mat}."
            )
            janela_mat.destroy()

            # Constrói o Workspace limpo pronto para receber inserções manuais
            self.ui.construir_tela_projeto()
            self.ui.combo_materiais.configure(values=list(self.chapas_globais.keys()))
            self.ui.combo_materiais.set(mat)
            self.mudar_material_preview()

        CTkButton(
            janela_mat,
            text="ABRIR AMBIENTE DE PROJETO",
            fg_color="#388E3C",
            hover_color="#2E7D32",
            height=38,
            font=("Arial", 12, "bold"),
            command=confirmar_estoque,
        ).pack(fill="x", padx=20, pady=15)

    def iniciar_via_importacao(self, tipo):

        # Solicita ao usuário o nome do cliente para o projeto importado e limpa quaisquer dados anteriores antes de importar os dados do arquivo selecionado
        from customtkinter import CTkInputDialog

        dialog = CTkInputDialog(
            text="Digite o nome do Cliente para este arquivo:", title="Importar Projeto"
        )
        nome = dialog.get_input()

        # Se o usuário não fornecer um nome, a função retorna sem fazer nada
        if not nome:
            return

        # Se o usuário fornecer um nome, o sistema registra o nome do cliente, limpa quaisquer dados anteriores e constrói a tela do projeto antes de importar os dados do arquivo selecionado
        self.nome_cliente = str(nome).strip().upper()
        self.limpar_cache_projeto()

        # Constrói a tela do projeto e atualiza o canvas do motor gráfico antes de importar os dados do arquivo selecionado
        self.ui.construir_tela_projeto()
        self.graficos.canvas = self.ui.canvas
        self.root.update()

        # Importa os dados do arquivo selecionado
        if tipo == "csv":
            self.importador.ler_csv()
        elif tipo == "json":
            self.importador.ler_json()
        elif tipo == "dxf":
            self.importador.abrir_importador_dxf()

        # Verifica se a importação trouxe dados
        if self.lotes_por_material:
            self.logger.info(
                f"Dados importados com sucesso. Processando Nesting inicial para {self.nome_cliente}."
            )
            self.processar_nesting()
        else:
            self.nome_cliente = "Não Informado"
            self.ui.construir_tela_inicial()

    def limpar_cache_projeto(self):
        """Limpa a memória para garantir que não haja peças fantasmas de outros clientes."""
        self.lotes_por_material.clear()
        self.chapas_globais.clear()
        self.chapas_editaveis = []
        self.historico_undo.clear()
        self.historico_redo.clear()
        self.estoque_global_pecas.clear()
        self.peca_destaque = None
        self.indice_chapa_atual = 0

    def voltar_para_home(self):
        tem_dados = any(self.chapas_globais.values()) or any(
            self.lotes_por_material.values()
        )

        if tem_dados:
            resposta = messagebox.askyesno(
                "Sair do Projeto",
                "Tem certeza que deseja voltar à tela inicial?\n\nOs dados não salvos deste cliente serão perdidos da memória.",
            )
            if not resposta:
                return

        self.nome_cliente = "Não Informado"
        self.ui.construir_tela_inicial()

    def inicializar_modulos_sistema(self):

        self.ui = InterfacePrincipal(self.root, self)
        self.db = BancoDadosSQLite()
        self.graficos = MotorGrafico(self)
        self.menus = MenusConfiguracao(self)
        self.hodometro = HodometroFerramentas(self)
        self.importador = GerenciadorImportacao(self)
        self.nesting = MotorNesting(self)
        self.exportador_pdf = GeradorPDF(self)
        self.exportador_gcode = GeradorGCode(self)
        self.exportador_cortecloud = ExportadorCorteCloud(self)
        self.gerador_etiquetas = GeradorEtiquetas(self)

        def safe_bind(event, acao):
            if isinstance(event.widget, (tk.Entry, ctk.CTkEntry, tk.Text, tk.Spinbox)):
                return
            acao()

            # Evita que a ação seja disparada se o foco estiver em um campo de entrada de texto

        self.root.bind(
            "<space>",
            lambda e: safe_bind(
                e, lambda: self.graficos.girar_peca_manual(None, hotkey=True)
            ),
        )
        self.root.bind(
            "<r>",
            lambda e: safe_bind(
                e, lambda: self.graficos.girar_peca_manual(None, hotkey=True)
            ),
        )
        self.root.bind(
            "<R>",
            lambda e: safe_bind(
                e, lambda: self.graficos.girar_peca_manual(None, hotkey=True)
            ),
        )
        self.root.bind(
            "<Delete>",
            lambda e: safe_bind(e, lambda: self.graficos.deletar_peca_selecionada()),
        )
        self.root.bind(
            "<Control-z>", lambda e: safe_bind(e, lambda: self.desfazer_acao())
        )
        self.root.bind(
            "<Control-y>", lambda e: safe_bind(e, lambda: self.refazer_acao())
        )

    # ==========================================
    # ROTAS DOS BOTÕES
    # ==========================================
    def ler_csv(self):
        self.importador.ler_csv()

    def ler_json(self):
        self.importador.ler_json()

    def abrir_importador_dxf(self):
        self.importador.abrir_importador_dxf()

    def processar_nesting(self):
        try:
            self.diam_fresa = float(self.ui.var_diam_fresa.get())
            self.folga_pecas = float(self.ui.var_folga_pecas.get())
            self.gap_nesting = self.diam_fresa + self.folga_pecas
            self.gap_fresa = self.gap_nesting
            self.raio_fresa = self.diam_fresa / 2.0
        except (AttributeError, ValueError):
            self.gap_fresa = 10.0
            self.gap_nesting = 10.0

        tem_layout = any(self.chapas_globais.values()) or any(
            self.estoque_global_pecas.values()
        )
        if tem_layout:
            resp = messagebox.askyesnocancel(
                "⚠️ Re-Nesting Detectado",
                "Você já possui peças na chapa ou no estoque.\n\n"
                "SIM: Juntar tudo e re-otimizar o layout.\n"
                "NÃO: Apagar tudo e começar do zero.\n"
                "CANCELAR: Abortar operação.",
            )
            if resp is None:
                return
            if resp == False:
                self.chapas_globais.clear()
                self.estoque_global_pecas.clear()

        # --- CONSOLIDAÇÃO DO LOTE ATIVO EM MEMÓRIA ---
        novo_lote = {}
        for mat, chapas in self.chapas_globais.items():
            if mat not in novo_lote:
                novo_lote[mat] = []
            for chapa in chapas:
                for p in chapa:
                    if p.get("tipo") != "metadados":
                        novo_lote[mat].append(p)

        for mat, pecas in self.estoque_global_pecas.items():
            if mat not in novo_lote:
                novo_lote[mat] = []
            novo_lote[mat].extend(pecas)

        self.lotes_por_material = novo_lote

        self.chapas_globais.clear()
        self.estoque_global_pecas.clear()

        # 🚀 ALOCAÇÃO PRIORITÁRIA DE RETALHOS APÓS CONSOLIDAÇÃO DO LOTE
        if (
            hasattr(self.ui, "var_usar_retalhos_banco")
            and self.ui.var_usar_retalhos_banco.get()
        ):
            for material in list(self.lotes_por_material.keys()):
                retalhos_banco = self.db.listar_retalhos_por_material(material)

                if retalhos_banco:
                    self.logger.info(
                        f"Encontrados {len(retalhos_banco)} retalhos de {material} no cofre. Injetando no plano..."
                    )

                    if material not in self.chapas_globais:
                        self.chapas_globais[material] = []

                    # Aloca os retalhos encontrados como as primeiras chapas (Bins) do Nesting
                    for r_id, r_w, r_h, r_esp, r_veio in retalhos_banco:
                        self.chapas_globais[material].insert(
                            0,
                            [
                                {
                                    "tipo": "metadados",
                                    "limite_x_corte": 0,
                                    "limite_y_corte": 0,
                                    "espessura_chapa": r_esp,
                                    "possui_veio": bool(r_veio),
                                    "id_retalho_banco": r_id,
                                    "largura_original_retalho": r_w,
                                    "altura_original_retalho": r_h,
                                }
                            ],
                        )

        self.logger.info(f"Iniciando Nesting. Gap: {self.gap_fresa}mm")
        self.nesting.processar()

    def mudar_material_preview(self, event=None):
        # Atualiza a chapa editável com base no material selecionado no combobox e redesenha a visualização
        mat = self.ui.combo_materiais.get()
        # Se o material selecionado estiver presente nas chapas globais, atualiza a chapa editável e redesenha a visualização
        if mat in self.chapas_globais:
            self.chapas_editaveis = self.chapas_globais[mat]
            self.indice_chapa_atual = 0
            # Atualiza a visualização da chapa apenas se houver chapas editáveis; caso contrário, limpa o canvas
            if len(self.chapas_editaveis) > 0:
                self.atualizar_paginacao()
                self.graficos.desenhar_chapa()

            # Se não houver chapas editáveis, limpa o canvas para evitar exibir dados antigos
            else:
                self.ui.canvas.delete("all")

        self.atualizar_lista_estoque()

    def abrir_gerenciador_ferramentas(self):
        self.menus.abrir_gerenciador_ferramentas()

    def abrir_setup_maquina(self):
        self.menus.abrir_setup_maquina()

    def gerar_pdf(self):
        self.exportador_pdf.gerar_pdf()

    def exportar_etiquetas(self):
        self.gerador_etiquetas.gerar_pdf_pimaco()

    def abrir_configuracao_gcode(self):
        # 1. Abre a interface operacional de configuração de GCode
        self.exportador_gcode.abrir_configuracao_gcode()

        # 2. Executa o cálculo preciso de percurso com base no layout final das chapas
        metros = self.calcular_perimetro_real_corte()

        # 3. Incrementa a quilometragem na ferramenta de corte principal dentro do SQLite
        with self.db.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE ferramentas SET metros_rodados = metros_rodados + ? 
                WHERE tipo = 'corte'
            """,
                (metros,),
            )
            conn.commit()

        print(
            f"Hodômetro unificado registrou {metros:.2f} metros lineares neste plano de corte."
        )

    def calcular_perimetro_real_corte(self):
        """Varre as chapas ativas calculando o perímetro real de cada peça alocada"""
        metros_totais = 0.0

        # Fluxo prioritário: Chapas globais estruturadas em memória pelo SQLite ou Nesting
        if self.chapas_globais:
            for material, lista_chapas in self.chapas_globais.items():
                for chapa in lista_chapas:
                    for peca in chapa:
                        if (
                            peca.get("tipo") == "metadados"
                            or peca.get("y", 0) >= self.area_util_y
                        ):
                            continue
                        dados = peca.get("rid", {})
                        w = float(dados.get("w_real", 0))
                        h = float(dados.get("h_real", 0))
                        metros_totais += ((w + h) * 2) / 1000.0

        # Fluxo secundário (fallback): Se o lote foi apenas importado e ainda não agrupado
        elif self.lotes_por_material:
            for material, lista_pecas in self.lotes_por_material.items():
                for peca in lista_pecas:
                    w = getattr(peca, "dim_x_csv", getattr(peca, "largura", 0))
                    h = getattr(peca, "dim_y_csv", getattr(peca, "altura", 0))
                    metros_totais += ((w + h) * 2) / 1000.0

        return metros_totais

    def exportar_cortecloud(self):
        self.exportador_cortecloud.exportar_projeto_json()

    def salvar_estado_historico(self):
        # Salva o estado atual da chapa editável no histórico de desfazer/refazer
        if len(self.historico_undo) > 15:
            self.historico_undo.pop(0)
        self.historico_undo.append(copy.deepcopy(self.chapas_editaveis))
        self.historico_redo.clear()

    def desfazer_acao(self):
        # Se houver ações para desfazer, restaura o estado anterior da chapa e redesenha a visualização
        if self.historico_undo:
            self.historico_redo.append(copy.deepcopy(self.chapas_editaveis))
            self.chapas_editaveis = self.historico_undo.pop()
            self.graficos.desenhar_chapa()

    def refazer_acao(self):
        # Se houver ações para refazer, restaura o estado anterior da chapa e redesenha a visualização
        if self.historico_redo:
            self.historico_undo.append(copy.deepcopy(self.chapas_editaveis))
            self.chapas_editaveis = self.historico_redo.pop()
            self.graficos.desenhar_chapa()

    # ==========================================
    # PAGINAÇÃO E MOUSE
    # ==========================================
    def atualizar_paginacao(self):
        # Atualiza o rótulo de paginação e os botões de navegação com base na chapa atual
        total, atual = len(self.chapas_editaveis), self.indice_chapa_atual + 1
        self.ui.lbl_paginacao.configure(
            text=f"Chapa {atual} / {total} | Visualizando: {self.ui.combo_materiais.get()}"
        )
        self.ui.btn_ant.configure(state="normal" if atual > 1 else "disabled")
        self.ui.btn_prox.configure(state="normal" if atual < total else "disabled")

    def chapa_anterior(self):
        # Volta para a chapa anterior, se houver, e atualiza a visualização
        if self.indice_chapa_atual > 0:
            self.indice_chapa_atual -= 1
            self.atualizar_paginacao()
            self.graficos.desenhar_chapa()

    def chapa_proxima(self):
        # Avança para a próxima chapa, se houver, e atualiza a visualização
        if self.indice_chapa_atual < len(self.chapas_editaveis) - 1:
            self.indice_chapa_atual += 1
            self.atualizar_paginacao()
            self.graficos.desenhar_chapa()

    def iniciar_arrasto(self, event):
        self.graficos.iniciar_arrasto(event)

    def arrastar_peca(self, event):
        self.graficos.arrastar_peca(event)

    def soltar_peca(self, event):
        self.graficos.soltar_peca(event)

    def girar_peca_manual(self, event):
        self.graficos.girar_peca_manual(event)

    def zoom_mouse(self, event):
        self.graficos.zoom_mouse(event)

    def alternar_raiox(self):
        # Alterna o modo de visualização Raio-X e redesenha a chapa
        self.modo_raiox = not self.modo_raiox
        self.graficos.desenhar_chapa()

    def destacar_peca_lista(self, event):
        # Destaca a peça selecionada na lista lateral e atualiza o desenho da chapa
        selecao = self.ui.lista_pecas.curselection()
        # Se não houver seleção, limpa o destaque e redesenha a chapa
        if selecao:
            texto = self.ui.lista_pecas.get(selecao[0])
            id_vis_clicado = texto.split(" | ")[0].strip()

            self.peca_destaque = None
            # Se houver chapas editáveis, procura a peça correspondente ao ID visual clicado
            if self.chapas_editaveis:
                # Procura a peça correspondente ao ID visual clicado e atualiza o destaque
                for p in self.chapas_editaveis[self.indice_chapa_atual]:
                    # Se a peça não for do tipo "metadados" e o ID visual corresponder ao clicado, define como destaque
                    if (
                        p.get("tipo") != "metadados"
                        and p["rid"].get("id_visual", "") == id_vis_clicado
                    ):
                        self.peca_destaque = p["uid"]
                        break
                self.graficos.desenhar_chapa()

    def calcular_aproveitamento(self):

        # Calcula o aproveitamento da chapa atual e atualiza a lista lateral de peças
        if not hasattr(self, "ui") or not hasattr(self.ui, "lista_pecas"):
            return

        # Se não houver chapas editáveis, zera o aproveitamento e limpa a lista
        if not self.chapas_editaveis:
            self.ui.lbl_aprov.configure(text="Aproveitamento: 0%", text_color="#9E9E9E")
            self.ui.barra_aprov.set(0.0)
            self.ui.lista_pecas.delete(0, tk.END)
            return

        area_chapa = self.area_util_x * self.area_util_y
        area_ocupada = 0
        self.ui.lista_pecas.delete(0, tk.END)

        # Itera sobre cada peça na chapa atual para calcular a área ocupada e atualizar a lista lateral
        for peca in self.chapas_editaveis[self.indice_chapa_atual]:

            # Se a peça não for do tipo "metadados", processa suas informações para exibição na lista lateral
            if peca.get("tipo") != "metadados":
                dados = peca["rid"]
                nome = dados.get("nome", "Peça")
                nome_limpo = nome.split("] ")[-1] if "] " in nome else nome
                id_vis = dados.get("id_visual", peca["uid"][:4])

                peca_intacta = self.graficos.farejar_peca_no_cofre(dados, peca)

                # Se a peça intacta for encontrada, utiliza seus atributos; caso contrário, utiliza os valores padrão do dicionário de dados
                if peca_intacta:
                    is_critica = getattr(peca_intacta, "is_critica", False)
                    esp_alvo = getattr(peca_intacta, "esp_alvo_engrosso", 30)
                else:
                    is_critica = dados.get("is_critica", False)
                    esp_alvo = dados.get("esp_alvo_engrosso", 30)

                # Monta o texto da lista lateral com base na criticidade da peça
                if is_critica:
                    texto_lista = f"{id_vis} | 🚨 [{esp_alvo}mm] {nome_limpo[:15]}"
                else:
                    texto_lista = f"{id_vis} | {nome_limpo[:15]}"

                self.ui.lista_pecas.insert(tk.END, texto_lista)

                # Calcula a área ocupada apenas se a peça estiver dentro da área útil da chapa
                if peca["y"] < self.area_util_y:
                    area_ocupada += peca["width"] * peca["height"]

        # Atualiza a barra de aproveitamento e o rótulo com a porcentagem calculada
        pct = (area_ocupada / area_chapa) * 100 if area_chapa > 0 else 0
        self.ui.barra_aprov.set(pct / 100.0)
        self.ui.lbl_aprov.configure(
            text=f"Aproveitamento: {pct:.1f}%",
            text_color=(
                "#00E676" if pct > 75 else ("#FF9800" if pct > 50 else "#F44336")
            ),
        )

    # ==========================================
    # GESTÃO DA ÁREA DE TRANSFERÊNCIA (MINI-CAD)
    # ==========================================
    def atualizar_lista_estoque(self):
        self.ui.lista_estoque.delete(0, tk.END)
        mat = self.ui.combo_materiais.get()
        pecas_no_estoque = self.estoque_global_pecas.get(mat, [])
        for peca in pecas_no_estoque:
            dados = peca["rid"]
            nome = dados.get("nome", "Peça Limpa")
            w, h = dados.get("w_real", 0), dados.get("h_real", 0)
            id_vis = dados.get("id_visual", peca["uid"][:4])

            self.ui.lista_estoque.insert(tk.END, f"{id_vis} | {w:.0f} x {h:.0f}")
            self.ui.lista_estoque.insert(tk.END, f"↳ {nome[:20]}")
            self.ui.lista_estoque.insert(tk.END, "-" * 25)

    def selecionar_bloco_estoque(self, event):
        selecao = self.ui.lista_estoque.curselection()
        if not selecao:
            return
        idx_clicado = selecao[0]
        idx_base = (idx_clicado // 3) * 3

        if idx_clicado != idx_base:
            self.ui.lista_estoque.selection_clear(0, tk.END)
            self.ui.lista_estoque.selection_set(idx_base)
            self.ui.lista_estoque.activate(idx_base)

    def resgatar_peca_estoque(self, event):
        selecao = self.ui.lista_estoque.curselection()
        if not selecao:
            return

        idx_clicado = selecao[0]
        idx_peca = idx_clicado // 3

        mat = self.ui.combo_materiais.get()
        if (
            mat in self.estoque_global_pecas
            and len(self.estoque_global_pecas[mat]) > idx_peca
        ):
            peca_resgatada = self.estoque_global_pecas[mat].pop(idx_peca)

            h_real = float(peca_resgatada["rid"].get("h_real", 50))
            if peca_resgatada.get("is_rotated"):
                h_real = float(peca_resgatada["rid"].get("w_real", 50))

            peca_resgatada["x"] = 50.0
            peca_resgatada["y"] = self.area_util_y - h_real - 50.0

            self.chapas_editaveis[self.indice_chapa_atual].append(peca_resgatada)
            self.salvar_estado_historico()

            self.atualizar_lista_estoque()
            self.graficos.desenhar_chapa()
            self.graficos.canvas.focus_set()

    def abrir_criador_pecas(self):
        mat_atual = self.ui.combo_materiais.get()
        if not mat_atual:
            messagebox.showwarning(
                "Atenção",
                "Selecione um Material da Chapa primeiro para saber onde injetar a peça!",
            )
            return

        janela_add = ctk.CTkToplevel(self.root)
        janela_add.title("Forjar Peça Avulsa")
        janela_add.geometry("350x450")
        janela_add.grab_set()
        janela_add.attributes("-topmost", True)

        ctk.CTkLabel(
            janela_add,
            text="🛠️ NOVA PEÇA AVULSA",
            font=ctk.CTkFont(weight="bold", size=16),
            text_color="#00E676",
        ).pack(pady=15)

        form = ctk.CTkFrame(janela_add, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20)

        ctk.CTkLabel(
            form,
            text=f"Destino: {mat_atual}",
            text_color="#9E9E9E",
            font=ctk.CTkFont(size=11, slant="italic"),
        ).pack(anchor="w", pady=(0, 15))

        v_nome = tk.StringVar(value="Recorte Manual")
        v_w = tk.StringVar(value="500")
        v_h = tk.StringVar(value="300")
        v_qtd = tk.StringVar(value="1")
        v_girar = tk.BooleanVar(value=True)

        def criar_campo(texto, var):
            ctk.CTkLabel(
                form, text=texto, text_color="#E0E0E0", font=ctk.CTkFont(weight="bold")
            ).pack(anchor="w")
            ctk.CTkEntry(form, textvariable=var, height=32).pack(fill="x", pady=(0, 12))

        criar_campo("Identificação / Nome:", v_nome)

        f_dim = ctk.CTkFrame(form, fg_color="transparent")
        f_dim.pack(fill="x", pady=(0, 10))

        f_w = ctk.CTkFrame(f_dim, fg_color="transparent")
        f_w.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkLabel(
            f_w,
            text="Comprimento X:",
            text_color="#E0E0E0",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w")
        ctk.CTkEntry(f_w, textvariable=v_w, height=32).pack(fill="x")

        f_h = ctk.CTkFrame(f_dim, fg_color="transparent")
        f_h.pack(side="right", fill="x", expand=True, padx=(5, 0))
        ctk.CTkLabel(
            f_h,
            text="Largura Y:",
            text_color="#E0E0E0",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w")
        ctk.CTkEntry(f_h, textvariable=v_h, height=32).pack(fill="x")

        criar_campo("Quantidade a Gerar:", v_qtd)
        ctk.CTkSwitch(
            form,
            text="Permitir Rotação Livre (Sem Veio)",
            variable=v_girar,
            progress_color="#00E676",
        ).pack(anchor="w", pady=5)

        def forjar():
            try:
                w, h, qtd = float(v_w.get()), float(v_h.get()), int(v_qtd.get())
            except ValueError:
                messagebox.showerror(
                    "⚠️ Erro de Entrada", "Por favor, insira valores numéricos válidos."
                )
                return

            if mat_atual not in self.estoque_global_pecas:
                self.estoque_global_pecas[mat_atual] = []

            # 🚀 SOLUÇÃO INTELIGENTE: Puxa a espessura varrendo o nome do material ativo (Ex: "MDF_BRANCO_6MM" -> 6.0)
            espessura_extraida = 15.0
            import re

            match = re.search(r"(\d+)\s*MM", mat_atual)
            if match:
                espessura_extraida = float(match.group(1))
            else:
                # Fallback secundário: tenta ler dos metadados da chapa limpa
                if mat_atual in self.chapas_globais and self.chapas_globais[mat_atual]:
                    for p in self.chapas_globais[mat_atual][0]:
                        if p.get("tipo") == "metadados":
                            espessura_extraida = float(p.get("espessura_chapa", 15.0))
                            break

            for _ in range(qtd):
                self.estoque_global_pecas[mat_atual].append(
                    {
                        "uid": f"uid_AVU_{uuid.uuid4().hex[:6]}",
                        "x": -1000,
                        "y": -1000,
                        "width": w,
                        "height": h,
                        "is_rotated": False,
                        "tipo": "peca",
                        "rid": {
                            "nome": v_nome.get(),
                            "w_real": w,
                            "h_real": h,
                            "espessura": espessura_extraida,  # Gravação perfeita e dinâmica sem travar!
                            "id_visual": "AVULSA",
                            "tem_veio": not v_girar.get(),
                            "pontos_perimetro": [
                                {"x": 0, "y": 0, "tem_fita": False},
                                {"x": w, "y": 0, "tem_fita": False},
                                {"x": w, "y": h, "tem_fita": False},
                                {"x": 0, "y": h, "tem_fita": False},
                            ],
                            "furos": [],
                            "rasgos": [],
                        },
                    }
                )

            self.atualizar_lista_estoque()
            janela_add.destroy()

        ctk.CTkButton(
            janela_add,
            text="INJETAR NO ESTOQUE",
            fg_color="#00796B",
            hover_color="#004D40",
            font=ctk.CTkFont(weight="bold"),
            height=35,
            command=forjar,
        ).pack(fill="x", padx=20, pady=10)

    def abrir_editor_por_clique(self, event):
        if not self.chapas_editaveis:
            return
        item = self.ui.canvas.find_withtag("current")
        if item:
            uid_alvo = next(
                (t for t in self.ui.canvas.gettags(item[0]) if t.startswith("uid_")),
                None,
            )
            if uid_alvo:
                self.abrir_editor_operacoes(uid_alvo)

    def abrir_editor_operacoes(self, uid_alvo=None):
        if not self.chapas_editaveis:
            return

        uid_alvo = uid_alvo or self.peca_destaque
        if not uid_alvo:
            messagebox.showwarning(
                "Atenção",
                "Selecione uma peça na lista lateral ou dê duplo clique nela!",
            )
            return

        # Invoca o novo ambiente CAD/CAM avançado isolado
        from ui.editor_cad_avancado import EditorCADAvancado

        EditorCADAvancado(self, uid_alvo)

    def persistir_projeto_atual(self):
        """Salva ou atualiza o plano de corte do cliente no banco de dados SQLite."""
        if not self.lotes_por_material:
            self.logger.aviso("Nenhum dado de lote ativo em memória para salvar.")
            return

        try:
            # Garante que estamos chamando a instância correta do banco unificado
            if not hasattr(self.db, "salvar_projeto_cliente"):
                self.logger.erro(
                    "Instância de banco de dados corrompida ou legada detectada."
                )
                messagebox.showerror(
                    "Erro de Persistência",
                    "O gerenciador de banco de dados ativo não suporta salvamento de projetos.",
                )
                return

            if getattr(self, "projeto_id_atual", None):
                # Atualiza o projeto existente mantendo o histórico
                self.db.atualizar_projeto_cliente(
                    projeto_id=self.projeto_id_atual,
                    nome_cliente=self.nome_cliente,
                    nome_ambiente=self.nome_ambiente,
                    lotes_dict=self.lotes_por_material,
                    chapas_dict=self.chapas_globais,
                )
                self.logger.info(
                    f"Projeto ID {self.projeto_id_atual} atualizado com sucesso no banco."
                )
            else:
                # Cria um novo registro blindado no banco
                novo_id = self.db.salvar_projeto_cliente(
                    nome_cliente=self.nome_cliente,
                    nome_ambiente=self.nome_ambiente,
                    lotes_dict=self.lotes_por_material,
                    chapas_dict=self.chapas_globais,
                )
                self.projeto_id_atual = novo_id
                self.logger.info(f"Novo projeto gerado e salvo com o ID: {novo_id}.")

        except Exception as e:
            self.logger.erro(f"Falha gravíssima ao salvar/atualizar projeto: {e}")
            messagebox.showerror(
                "Erro Crítico", f"Não foi possível persistir os dados no SQLite:\n{e}"
            )

    def abrir_injetor_chapas_dinamico(self):
        """Abre uma janela operacional para adicionar novos tipos de MDF/chapas ao projeto ativo."""
        if not hasattr(self, "ui") or not self.ui.combo_materiais:
            return

        from customtkinter import (
            CTkToplevel,
            CTkLabel,
            CTkEntry,
            CTkFrame,
            CTkButton,
            CTkSwitch,
            CTkComboBox,
        )

        janela_inj = CTkToplevel(self.root)
        janela_inj.title("Injetar Matéria-Prima no Projeto")
        janela_inj.geometry("400x480")
        janela_inj.grab_set()
        janela_inj.attributes("-topmost", True)

        CTkLabel(
            janela_inj,
            text="➕ INJETAR NOVAS CHAPAS",
            font=("Arial", 14, "bold"),
            text_color="#00E676",
        ).pack(pady=15)

        form = CTkFrame(janela_inj, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20)

        # Campos paramétricos com valores industriais sugeridos
        v_material = tk.StringVar(value="MDF_LOURO_FREIJO")
        v_largura = tk.StringVar(value="2750")
        v_altura = tk.StringVar(value="1830")
        v_espessura = tk.StringVar(value="15")
        v_qtd_chapas = tk.StringVar(value="1")
        v_tem_veio = tk.BooleanVar(value=True)

        CTkLabel(
            form, text="Descrição/Cor do Material:", font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(5, 2))
        CTkEntry(form, textvariable=v_material, height=30).pack(fill="x")

        f_dim = CTkFrame(form, fg_color="transparent")
        f_dim.pack(fill="x", pady=5)

        f_w = CTkFrame(f_dim, fg_color="transparent")
        f_w.pack(side="left", fill="x", expand=True, padx=(0, 5))
        CTkLabel(f_w, text="Comprimento X:", font=("Arial", 11, "bold")).pack(
            anchor="w"
        )
        CTkEntry(f_w, textvariable=v_largura, height=30).pack(fill="x")

        f_h = CTkFrame(f_dim, fg_color="transparent")
        f_h.pack(side="right", fill="x", expand=True, padx=(5, 0))
        CTkLabel(f_h, text="Largura Y:", font=("Arial", 11, "bold")).pack(anchor="w")
        CTkEntry(f_h, textvariable=v_altura, height=30).pack(fill="x")

        # Seleção de espessuras fixas padrão de mercado (3mm, 6mm, 15mm, 18mm, 25mm)
        CTkLabel(form, text="Espessura Nominal (mm):", font=("Arial", 11, "bold")).pack(
            anchor="w", pady=(5, 2)
        )
        combo_esp = CTkComboBox(
            form,
            variable=v_espessura,
            values=["3", "6", "15", "18", "25"],
            height=30,
            state="readonly",
        )
        combo_esp.pack(fill="x")

        CTkLabel(
            form, text="Quantidade de Chapas no Lote:", font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(5, 2))
        CTkEntry(form, textvariable=v_qtd_chapas, height=30).pack(fill="x")

        CTkSwitch(
            form,
            text="Material Possui Veio Amadeirado Ativo",
            variable=v_tem_veio,
            progress_color="#00E676",
        ).pack(anchor="w", pady=15)

        def executar_injecao():
            try:
                # Padroniza a string do material incluindo a espessura para evitar misturar lotes no Nesting
                mat_nome = f"{v_material.get().strip().upper()}_{v_espessura.get()}MM"
                w_chapa = float(v_largura.get())
                h_chapa = float(v_altura.get())
                esp = float(v_espessura.get())
                qtd = int(v_qtd_chapas.get())
            except ValueError:
                messagebox.showerror("Erro", "Insira valores válidos para o estoque.")
                return

            # Garante que as dimensões do palco de visualização sigam o padrão do material ativo
            self.chapa_largura = w_chapa
            self.chapa_altura = h_chapa
            self.area_util_x = w_chapa - (self.refilo * 2)
            self.area_util_y = h_chapa - (self.refilo * 2)

            # Se o material não existir nas chapas globais, inicializa o lote
            if mat_nome not in self.chapas_globais:
                self.chapas_globais[mat_nome] = []

            # Aloca as chapas contendo seus metadados de orientação estrutural
            for _ in range(qtd):
                self.chapas_globais[mat_nome].append(
                    [
                        {
                            "tipo": "metadados",
                            "limite_x_corte": 0,
                            "limite_y_corte": 0,
                            "espessura_chapa": esp,
                            "possui_veio": v_tem_veio.get(),
                        }
                    ]
                )

            self.logger.info(
                f"Estoque injetado: +{qtd} chapa(s) do material {mat_nome} inseridas."
            )
            janela_inj.destroy()

            # Atualiza o combobox de visualização em tempo real na barra de ferramentas
            lista_materiais_atualizada = list(self.chapas_globais.keys())
            self.ui.combo_materiais.configure(values=lista_materiais_atualizada)
            self.ui.combo_materiais.set(mat_nome)
            self.mudar_material_preview()

        CTkButton(
            janela_inj,
            text="INJETAR MATERIAL NO PROJETO",
            fg_color="#00796B",
            hover_color="#004D40",
            height=38,
            font=("Arial", 12, "bold"),
            command=executar_injecao,
        ).pack(fill="x", padx=20, pady=15)

    def abrir_gerenciador_retalhos_manual(self):
        """Abre a janela de cadastro de sobras externas e parametrização de área mínima útil."""
        from customtkinter import (
            CTkToplevel,
            CTkLabel,
            CTkEntry,
            CTkFrame,
            CTkButton,
            CTkSwitch,
            CTkTabview,
        )

        janela_ret = CTkToplevel(self.root)
        janela_ret.title("Depósito de Retalhos e Otimização de Sobras")
        janela_ret.geometry("420x520")
        janela_ret.grab_set()
        janela_ret.attributes("-topmost", True)

        tabs_r = CTkTabview(janela_ret)
        tabs_r.pack(fill="both", expand=True, padx=10, pady=5)
        tab_cadastro = tabs_r.add("📥 Cadastrar Sobra")
        tab_config = tabs_r.add("⚙️ Configurar Filtro")

        # =========================================================
        # ABA 1: CADASTRO MANUAL DE SOBRAS EXTERNAS
        # =========================================================
        f_cad = CTkFrame(tab_cadastro, fg_color="transparent")
        f_cad.pack(fill="both", expand=True, padx=15, pady=10)

        mat_sugerido = (
            self.ui.combo_materiais.get()
            if hasattr(self, "ui") and self.ui.combo_materiais
            else "MDF_BRANCO_15MM"
        )

        v_mat_r = tk.StringVar(value=mat_sugerido)
        v_w_r = tk.StringVar(value="600")
        v_h_r = tk.StringVar(value="400")
        v_esp_r = tk.StringVar(value="15")
        v_veio_r = tk.BooleanVar(value=False)

        def campo_r(pai, txt, var):
            CTkLabel(pai, text=txt, font=("Arial", 11, "bold")).pack(
                anchor="w", pady=(3, 1)
            )
            CTkEntry(pai, textvariable=var, height=30).pack(fill="x")

        campo_r(f_cad, "Material / Padrão do Retalho:", v_mat_r)

        f_dim_r = CTkFrame(f_cad, fg_color="transparent")
        f_dim_r.pack(fill="x", pady=5)
        f_w_sub = CTkFrame(f_dim_r, fg_color="transparent")
        f_w_sub.pack(side="left", fill="x", expand=True, padx=(0, 5))
        campo_r(f_w_sub, "Comprimento X (mm):", v_w_r)

        f_h_sub = CTkFrame(f_dim_r, fg_color="transparent")
        f_h_sub.pack(side="right", fill="x", expand=True, padx=(5, 0))
        campo_r(f_h_sub, "Largura Y (mm):", v_h_r)

        campo_r(f_cad, "Espessura Nominal (mm):", v_esp_r)
        CTkSwitch(
            f_cad,
            text="Sobra possui sentido de veio ativo",
            variable=v_veio_r,
            progress_color="#00E676",
        ).pack(anchor="w", pady=15)

        def executar_salvamento_manual():
            try:
                m_nome = v_mat_r.get().strip().upper()
                w_val = float(v_w_r.get())
                h_val = float(v_h_r.get())
                e_val = float(v_esp_r.get())
            except ValueError:
                messagebox.showerror(
                    "Erro de Entrada",
                    "Insira valores numéricos válidos para as dimensões.",
                )
                return

            rid_id = self.db.salvar_retalho_avulso(
                m_nome, w_val, h_val, e_val, v_veio_r.get()
            )
            if rid_id:
                self.logger.info(
                    f"Retalho manual ID {rid_id} inserido no cofre: {w_val}x{h_val}mm ({m_nome})."
                )
                messagebox.showinfo(
                    "Sucesso",
                    f"Sobra cadastrada com sucesso no depósito!\nID Registro: {rid_id}",
                )
                janela_ret.destroy()

        CTkButton(
            f_cad,
            text="DEPOSITAR SOBRA NO COFRE",
            fg_color="#388E3C",
            hover_color="#2E7D32",
            height=35,
            font=("Arial", 11, "bold"),
            command=executar_salvamento_manual,
        ).pack(fill="x", pady=10)

        # =========================================================
        # ABA 2: CONFIGURAÇÃO DE ÁREA ÚTIL MÍNIMA FILTRADA
        # =========================================================
        f_conf = CTkFrame(tab_config, fg_color="transparent")
        f_conf.pack(fill="both", expand=True, padx=15, pady=10)

        # Correção direta do typo: removida a verificação do método inexistente 'obter_limits_retalho'
        limite_atual_x, limite_atual_y = self.db.obter_limites_retalho()

        v_lim_x = tk.StringVar(value=str(limite_atual_x))
        v_lim_y = tk.StringVar(value=str(limite_atual_y))

        CTkLabel(
            f_conf,
            text="⚙️ PARÂMETROS DE REAPROVEITAMENTO",
            font=("Arial", 12, "bold"),
            text_color="#FF9800",
        ).pack(anchor="w", pady=(0, 10))
        CTkLabel(
            f_conf,
            text="Defina o tamanho mínimo para que as sobras geradas pelo Nesting entrem automaticamente no banco de dados. Áreas menores que isso serão descartadas como serragem.",
            font=("Arial", 10),
            text_color="#9E9E9E",
            justify="left",
            wraplength=340,
        ).pack(anchor="w", pady=(0, 15))

        campo_r(f_conf, "Comprimento Mínimo X (mm):", v_lim_x)
        campo_r(f_conf, "Largura Mínima Y (mm):", v_lim_y)

        def salvar_parametros_filtro():
            try:
                lx = float(v_lim_x.get())
                ly = float(v_lim_y.get())
            except ValueError:
                messagebox.showerror("Erro", "Insira valores numéricos válidos.")
                return

            self.db.atualizar_limites_retalho(lx, ly)
            self.logger.info(
                f"Filtro de retalhos atualizado pelo operador para: {lx}x{ly}mm."
            )
            messagebox.showinfo(
                "Filtro Atualizado",
                "Os novos limites de área útil foram gravados e serão aplicados no próximo Nesting!",
            )
            janela_ret.destroy()

        CTkButton(
            f_conf,
            text="SALVAR DIRETRIZES DE FILTRO",
            fg_color="#00796B",
            hover_color="#004D40",
            height=35,
            font=("Arial", 11, "bold"),
            command=salvar_parametros_filtro,
        ).pack(fill="x", pady=25)

    def puxar_modulo_servidor(self):
        """Requisita o módulo ativo no Flask, abastece a fábrica e prepara o canvas"""
        import urllib.request
        import json
        from tkinter import messagebox

        url = "http://localhost:5000/api/modulo/001"
        try:
            req = urllib.request.urlopen(url, timeout=3)
            if req.status == 200:
                payload = json.loads(req.read().decode('utf-8'))

                # Sincroniza dimensões padrão da chapa de MDF
                self.chapa_largura = 2750.0
                self.chapa_altura = 1830.0
                self.refilo = 20.0
                self.area_util_x = self.chapa_largura - (self.refilo * 2)
                self.area_util_y = self.chapa_altura - (self.refilo * 2)
                self.gap_fresa = 10.0

                # Constrói a tela limpa de projeto
                self.limpar_cache_projeto()
                self.ui.construir_tela_projeto()

                # Processa a conversão de peças e estoque
                sucesso = self.importador.carregar_modulo_tiranogio_json(payload)
                if sucesso:
                    materiais = list(self.lotes_por_material.keys())
                    self.ui.combo_materiais.configure(values=materiais)
                    if materiais:
                        self.ui.combo_materiais.set(materiais[0])
                        self.mudar_material_preview()

                    total_pecas = sum(len(v) for v in self.lotes_por_material.values())
                    messagebox.showinfo(
                        "Integração Concluída",
                        f"Módulo do TiranoGio 3D Carregado!\n\n"
                        f"Total de Peças: {total_pecas}\n"
                        f"Materiais: {', '.join(materiais)}\n\n"
                        f"Clique em 'PROCESSAR NESTING' para otimizar as chapas."
                    )
            else:
                messagebox.showerror("Erro de Servidor", f"O servidor respondeu com status: {req.status}")
        except Exception as e:
            messagebox.showerror(
                "Falha de Conexão",
                f"Certifique-se de que o servidor Flask (app.py) está ativo na porta 5000.\n\nDetalhes: {e}"
            )

    def atualizar_lista_pecas_ui(self):
        """Popula a lista da interface gráfica com base no material selecionado no combobox"""
        if hasattr(self.ui, 'lista_pecas') and self.ui.lista_pecas:
            self.ui.lista_pecas.delete(0, 'end')
            mat_sel = self.ui.combo_materiais.get() if hasattr(self.ui, 'combo_materiais') else None
            if mat_sel and mat_sel in self.lotes_por_material:
                for p in self.lotes_por_material[mat_sel]:
                    self.ui.lista_pecas.insert('end', f"{p.nome} ({int(p.largura)}x{int(p.altura)}mm)")
                    
if __name__ == "__main__":
    try:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        janela = ctk.CTk()
        app = TiranoGioApp(janela)
        janela.mainloop()

    except Exception as e:
        import traceback

        with open("CRASH_FATAL.txt", "w", encoding="utf-8") as f:
            f.write("=== O SISTEMA CAPOTOU NA INICIALIZAÇÃO ===\n\n")
            f.write(traceback.format_exc())

        print("🚨 CRASH FATAL! O ERRO FOI GRAVADO NO ARQUIVO 'CRASH_FATAL.txt' 🚨")
        print("\nDetalhes do Erro:")
        print(traceback.format_exc())
        input("\nPressione ENTER para fechar a tela...")
