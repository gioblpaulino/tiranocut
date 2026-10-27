# TiranoGio_App/core/importadores.py

import csv
import json
import os
import re
import uuid
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Importamos a planta baixa da peça
from core.modelos import PecaPlanejado

class GerenciadorImportacao:
    """
    Gaveta responsável exclusivamente por ler arquivos externos (CSV, DXF e JSON),
    transformá-los em objetos 'PecaPlanejado' e entregar para o Maestro.
    """
    def __init__(self, app_core):
        self.app = app_core

    # ==========================================================
    # MOTOR NLP: INTERPRETADOR DE OBSERVAÇÕES PROMOB
    # ==========================================================
    @staticmethod
    def interpretar_observacao(texto_obs, esp_base_mdf=15.0):
        texto = str(texto_obs or "").strip().upper()
        
        try: e_base = float(str(esp_base_mdf).replace(',', '.'))
        except: e_base = 15.0

        if not texto or texto in ["NONE", "0", ""]:
            return {"critico": False, "tipo": "NORMAL", "lados": "", "esp_alvo": int(e_base)}

        critico = False
        tipo = "NORMAL"
        lados = "Lados não informados"
        esp_alvo = 0

        # 1. Farejador do Tipo de Estrutura
        if any(w in texto for w in ["SANDUICHE", "SANDUÍCHE", "SANDU"]):
            tipo = "SANDUICHE"; critico = True
        elif any(w in texto for w in ["DUPLAD", "DUPLAR", "MACIC", "MACIÇ"]):
            tipo = "DUPLADA"; critico = True
        elif any(w in texto for w in ["ENGROSS", "ENGR"]):
            tipo = "ENGROSSADA"; critico = True
        elif any(w in texto for w in ["ATENÇÃO", "IMPORTANTE", "QUARENTENA", "MOLDURA"]):
            tipo = "ESPECIAL"; critico = True

        # 2. MOTOR POLIGLOTA DE ESPESSURA
        mA = re.search(r'(\d{2,3})\s*MM', texto)
        mB = re.search(r'(?:ESPESSURA|ESP|E)\s*=?\s*(\d{2,3})\b', texto)
        mC = re.search(r'#\s*(\d{2,3})\b', texto)

        if mA: esp_alvo = int(mA.group(1))
        elif mB: esp_alvo = int(mB.group(1))
        elif mC: esp_alvo = int(mC.group(1))

        # 3. Matemática Autoconsciente
        if not esp_alvo:
            if critico: esp_alvo = int(e_base * 2)
            else: esp_alvo = int(e_base)

        # 4. Captura a quantidade de Lados
        match_lados = re.search(r'(\d)\s*LADO', texto)
        if match_lados:
            qtd = match_lados.group(1)
            lados = f"{qtd} Lado{'s' if int(qtd) > 1 else ''}"
        else:
            faces = []
            if any(w in texto for w in ["TOPO", "SUP", "CIMA"]): faces.append("Topo")
            if any(w in texto for w in ["BASE", "INF", "BAIXO"]): faces.append("Base")
            if any(w in texto for w in ["DIR", "DIREIT"]): faces.append("Dir")
            if any(w in texto for w in ["ESQ", "ESQUERD"]): faces.append("Esq")
            if faces: lados = " + ".join(faces)

        return {"critico": critico, "tipo": tipo, "lados": lados, "esp_alvo": esp_alvo}

    # =========================================================================
    # 🧬 GENÉTICA MATRIARCAL (Separa a Rainha das Operárias)
    # =========================================================================
    @staticmethod
    def aplicar_genetica_matriarcal(lote_pecas):
        grupos = {}
        for p in lote_pecas:
            desc = getattr(p, 'descricao', getattr(p, 'nome', ''))
            # Limpa parênteses de medidas do tipo "(1500x700)" para achar o DNA real
            chave = re.sub(r'\s*\(\s*\d+(?:[.,]\d+)?\s*[xX*]\s*\d+(?:[.,]\d+)?\s*\)', '', desc)
            chave = chave.strip().upper()
            
            if chave not in grupos: grupos[chave] = []
            grupos[chave].append(p)

        for chave, cla in grupos.items():
            if len(cla) <= 1:
                for p in cla: p.is_mae = True; p.is_filho_engrosso = False
                continue

            # Se o clã não tem nenhuma peça crítica, são apenas peças idênticas comuns
            tem_alerta = any(getattr(p, 'is_critica', False) for p in cla) or any(w in chave for w in ['ENG', 'DUP', 'SAND', 'MACI'])
            if not tem_alerta:
                for p in cla: p.is_mae = True; p.is_filho_engrosso = False
                continue

            # Ordena por Tamanho Físico (Área)
            cla_ordenado = sorted(
                cla, 
                key=lambda p: float(getattr(p, 'dim_x_csv', getattr(p, 'largura', 0))) * float(getattr(p, 'dim_y_csv', getattr(p, 'altura', 0))), 
                reverse=True
            )

            # 👑 1. Coroação da Rainha (A maior de todas)
            mae = cla_ordenado[0]
            mae.is_mae = True
            mae.is_filho_engrosso = False
            mae.is_critica = True
            if hasattr(mae, 'dados_extras'):
                mae.dados_extras['is_critica'] = True
                mae.dados_extras['is_mae'] = True
                mae.dados_extras['is_filho_engrosso'] = False

            # 👷‍♂️ 2. O Rebaixamento das Operárias (Sarrafos)
            for filho in cla_ordenado[1:]:
                filho.is_mae = False
                filho.is_filho_engrosso = True
                
                # O TIRO DE MISERICÓRDIA: Tiramos o rádio-alerta visual dele!
                filho.is_critica = False 

                if hasattr(filho, 'dados_extras'):
                    filho.dados_extras['is_critica'] = False
                    filho.dados_extras['is_mae'] = False
                    filho.dados_extras['is_filho_engrosso'] = True

                # Injeta o "ENG_" mantendo a tag de módulo intacta
                desc_atual = getattr(filho, 'descricao', '')
                if "] " in desc_atual:
                    mod, resto = desc_atual.split("] ", 1)
                    if not resto.startswith("ENG_"):
                        filho.descricao = f"{mod}] ENG_{resto}"
                else:
                    if not desc_atual.startswith("ENG_"):
                        filho.descricao = f"ENG_{desc_atual}"

                if hasattr(filho, 'nome'): filho.nome = filho.descricao

    # ==========================================================
    # IMPORTAÇÃO DE CSV (PROMOB)
    # ==========================================================
    def ler_csv(self):
        caminho_arquivo = filedialog.askopenfilename(title="Selecione o CSV", filetypes=[("Arquivos CSV", "*.csv")])
        if not caminho_arquivo: return
        
        self.app.lotes_por_material.clear()
        pecas_temporarias = {}
        self.app.nome_cliente = "Não Informado"
        self.app.nome_ambiente = "Não Informado"
        
        try:
            self.app.pasta_projeto = os.path.dirname(caminho_arquivo)
            
            with open(caminho_arquivo, 'r', encoding='utf-8-sig') as f:
                primeira_linha = f.readline()
                delimitador = '\t' if '\t' in primeira_linha else ';'
            
            with open(caminho_arquivo, mode='r', encoding='utf-8-sig') as arquivo:
                leitor = csv.DictReader(arquivo, delimiter=delimitador)
                leitor.fieldnames = [col.strip() if col else col for col in leitor.fieldnames]
                
                for linha in leitor:
                    if self.app.nome_cliente == "Não Informado":
                        c_nome = str(linha.get('CLIENTE - DADOS DO CLIENTE', '')).strip()
                        if c_nome: self.app.nome_cliente = c_nome
                    if self.app.nome_ambiente == "Não Informado":
                        a_nome = str(linha.get('AMBIENTE', '')).strip()
                        if a_nome: self.app.nome_ambiente = a_nome

                    tem_materia_prima = linha.get('COLUMN_ITEM_HAS_RAW_MATERIAL') or linha.get('ITEM TEM MATÉRIA PRIMA', '1')
                    if str(tem_materia_prima).strip() in ['0', 'False', 'false', 'NÃO', 'NAO', '']: continue
                    
                    material = linha.get('NOME DO MATERIAL') or linha.get('DESCRIÇÃO DO MATERIAL', '')
                    if not material or str(material).strip() == '': continue

                    id_peca = linha.get('COLUMN_ITEM_CODE') or linha.get('PEÇA ID', '')
                    id_peca = str(id_peca).strip()
                    if not id_peca or id_peca == '0' or id_peca == 'None': continue 
                    
                    if id_peca not in pecas_temporarias:
                        espessura = linha.get('ESPESSURA DO MATERIAL') or linha.get('COLUMN_ITEM_DEPTH', '15')
                        descricao = str(linha.get('PEÇA DESCRIÇÃO') or linha.get('REFERÊNCIA', 'Peça')).strip()
                        str_veio = str(linha.get('VEIO') or linha.get('COLUMN_WOOD_GRAIN_DIRECTION', '0')).strip()
                        tem_veio = str_veio not in ['0', 'None', 'Nenhum', '']
                        
                        modulo_oficial = "Avulso"
                        nome_limpo = descricao
                        
                        if '!' in nome_limpo:
                            partes = nome_limpo.split('!', 1)
                            modulo_oficial = partes[0].strip()
                            nome_sujo = partes[1]
                            nome_limpo = nome_sujo.replace('-__', '').replace('__', '').replace('_', ' ').strip().title()
                            nome_limpo = f"[{modulo_oficial}] {nome_limpo}"
                        
                        nova_peca = PecaPlanejado(id_peca=id_peca, descricao=nome_limpo, material=str(material).strip(), espessura=str(espessura).strip(), quantidade=linha.get('QUANTIDADE ITEM', '1'), tem_veio=tem_veio)
                        
                        id_promob = str(linha.get('ID MÓDULO') or linha.get('COLUMN_MODULE_ID') or '').strip()
                        nova_peca.id_modulo_pai = modulo_oficial if modulo_oficial != "Avulso" else (id_promob if id_promob else "Avulso")
                        
                        foto = linha.get('CAMINHO DA ETIQUETA') or linha.get('COLUMN_EXPLODED_MODULE_IMAGE') or ''
                        nova_peca.imagem_explodida = str(foto).strip()

                        obs_bruta = str(linha.get('OBSERVAÇÕES-PROMOB') or linha.get('OBSERVAÇÕES') or '').strip()
                        pos_bruta = str(linha.get('PEÇA POSIÇÃO') or linha.get('POSIÇÃO') or '').strip()
                        top_bruta = str(linha.get('TOPOLOGIA') or '').strip()

                        info_obs = self.interpretar_observacao(obs_bruta)

                        nova_peca.observacao_promob = obs_bruta
                        nova_peca.posicao_promob = pos_bruta
                        nova_peca.topologia_promob = top_bruta

                        nova_peca.is_critica = info_obs["critico"]
                        nova_peca.tipo_engrosso = info_obs["tipo"]
                        nova_peca.lados_engrosso = info_obs["lados"]
                        nova_peca.esp_alvo_engrosso = info_obs["esp_alvo"]

                        str_operacoes = linha.get('OPERAÇÕES', '{}').strip()
                        if str_operacoes:
                            try:
                                json_ops = json.loads(str_operacoes)
                                furos = json_ops.get("Holes", [])
                                nova_peca.furos = furos
                                nova_peca.rasgos = json_ops.get("Grooves", [])
                                nova_peca.furos_brutos_json = furos
                            except Exception as e_json: 
                                self.app.logger.erro(f"CSV -> Erro ao ler operações JSON da peça {id_peca}. O campo pode estar corrompido.")

                        if not hasattr(nova_peca, 'dados_extras'): nova_peca.dados_extras = {}
                        nova_peca.dados_extras.update({
                            "furos_brutos_json": getattr(nova_peca, 'furos_brutos_json', []),
                            "observacao_promob": obs_bruta,
                            "posicao_promob": pos_bruta,
                            "topologia_promob": top_bruta,
                            "is_critica": info_obs["critico"],
                            "tipo_engrosso": info_obs["tipo"],
                            "lados_engrosso": info_obs["lados"],
                            "esp_alvo_engrosso": info_obs["esp_alvo"]
                        })
                            
                        if nova_peca.espessura == 6.0 or nova_peca.espessura == 6:
                            nova_peca.rasgos = []
                            
                        try:
                            nova_peca.dim_x_csv = float(str(linha.get('ALTURA (X)', '0')).replace(',', '.'))
                            nova_peca.dim_y_csv = float(str(linha.get('PROF (Y)', '0')).replace(',', '.'))
                        except Exception as e_dim: 
                            self.app.logger.aviso(f"CSV -> Peça {id_peca} sem medidas explícitas em X e Y ou formato inválido.")
                        
                        pecas_temporarias[id_peca] = nova_peca
                        
                    try:
                        str_x = str(linha.get('COLUMN_POINT_X_ITEM', '0')).replace(',', '.')
                        str_y = str(linha.get('COLUMN_POINT_Y_ITEM', '0')).replace(',', '.')
                        fita = str(linha.get('COLUMN_BORDER_FINISHING', '')).strip()
                        tem_fita = bool(fita and fita != '0' and fita.lower() != 'none')
                        if str_x and str_y:
                            px, py = float(str_x), float(str_y)
                            pecas_temporarias[id_peca].vertices_x.append(px)
                            pecas_temporarias[id_peca].vertices_y.append(py)
                            pecas_temporarias[id_peca].pontos_perimetro.append({'x': px, 'y': py, 'tem_fita': tem_fita})
                    except: pass
            
            total_pecas = 0
            for peca in pecas_temporarias.values():
                if peca.largura <= 0 or peca.altura <= 0: continue
                chave_lote = f"{peca.material} ({peca.espessura}mm)"
                if chave_lote not in self.app.lotes_por_material: 
                    self.app.lotes_por_material[chave_lote] = []
                for _ in range(peca.quantidade):
                    self.app.lotes_por_material[chave_lote].append(peca)
                    total_pecas += 1
            
            # =================================================================
            # 💉 INJEÇÃO DA GENÉTICA MATRIARCAL NOS LOTES
            # =================================================================
            for lista_pecas in self.app.lotes_por_material.values():
                self.aplicar_genetica_matriarcal(lista_pecas)

            self.app.cofre_pecas_originais = pecas_temporarias.copy()
            
            if total_pecas > 0:
                lista_materiais = list(self.app.lotes_por_material.keys())
                self.app.ui.combo_materiais.configure(values=lista_materiais)
                self.app.ui.combo_materiais.set(lista_materiais[0])
                self.app.ui.lbl_status.configure(text=f"CSV Carregado! Cliente: {self.app.nome_cliente}", text_color="#00E676")
            else: 
                messagebox.showwarning("Aviso", "Nenhuma peça encontrada.")
        except Exception as e: 
            messagebox.showerror("Erro", f"Erro:\n{e}")

    # ==========================================================
    # IMPORTAÇÃO DE DXF
    # ==========================================================
    def abrir_importador_dxf(self):
        try: 
            import ezdxf
            from ezdxf import path 
        except ImportError:
            messagebox.showerror("Falta Biblioteca", "A biblioteca EZDXF não foi encontrada!\nAbra o Terminal/CMD e digite:\npip install ezdxf"); return
            
        caminhos = filedialog.askopenfilenames(title="Selecione as Peças DXF", filetypes=[("Arquivo DXF", "*.dxf")])
        if not caminhos: return

        camadas_encontradas = set()
        try:
            for caminho in caminhos:
                doc = ezdxf.readfile(caminho)
                msp = doc.modelspace()
                for e in msp:
                    camadas_encontradas.add(e.dxf.layer)
                    if e.dxftype() == 'INSERT':
                        try:
                            for ent in e.virtual_entities(): camadas_encontradas.add(ent.dxf.layer)
                        except Exception as inner_e:
                            self.app.logger.aviso(f"Falha ao ler bloco interno DXF em {caminho}: {inner_e}")
        except Exception as e: 
            self.app.logger.erro(f"Erro crítico na pré-leitura do DXF: {caminho}")
            print(f"Erro na pré-leitura: {e}")

        janela_dxf = tk.Toplevel(self.app.root)
        janela_dxf.title("Configurar Lote DXF Inteligente")
        janela_dxf.geometry("480x550"); janela_dxf.grab_set()
        
        tk.Label(janela_dxf, text=f"{len(caminhos)} DXF(s) Selecionado(s)", font=("Arial", 12, "bold")).pack(pady=(15, 5))
        
        frame_inputs = tk.Frame(janela_dxf)
        frame_inputs.pack(fill="x", padx=20)
        
        tk.Label(frame_inputs, text="Material Base:").grid(row=0, column=0, pady=5, sticky="w")
        materiais_existentes = list(set([m.split(' (')[0] for m in self.app.lotes_por_material.keys()])) or ["MDF Branco TX", "MDF Madeirado"]
        v_mat = tk.StringVar(value=materiais_existentes[0])
        ttk.Combobox(frame_inputs, textvariable=v_mat, values=materiais_existentes, width=18).grid(row=0, column=1, pady=5, padx=5)
        
        tk.Label(frame_inputs, text="Espessura (mm):").grid(row=1, column=0, pady=5, sticky="w")
        v_esp = tk.StringVar(value="15")
        tk.Entry(frame_inputs, textvariable=v_esp, width=10, justify="center").grid(row=1, column=1, pady=5, padx=5, sticky="w")
        
        tk.Label(frame_inputs, text="Cópias por arquivo:").grid(row=2, column=0, pady=5, sticky="w")
        v_qtd = tk.IntVar(value=1)
        tk.Entry(frame_inputs, textvariable=v_qtd, width=10, justify="center").grid(row=2, column=1, pady=5, padx=5, sticky="w")

        tk.Label(frame_inputs, text="Nome Base da Peça:").grid(row=3, column=0, pady=5, sticky="w")
        v_nome_base = tk.StringVar(value="Peça Avulsa DXF")
        tk.Entry(frame_inputs, textvariable=v_nome_base, width=18).grid(row=3, column=1, pady=5, padx=5, sticky="w")

        tk.Label(frame_inputs, text="Cliente (Opcional):").grid(row=4, column=0, pady=5, sticky="w")
        v_cliente = tk.StringVar(value=self.app.nome_cliente if self.app.nome_cliente != "Não Informado" else "")
        tk.Entry(frame_inputs, textvariable=v_cliente, width=18).grid(row=4, column=1, pady=5, padx=5, sticky="w")

        tk.Label(frame_inputs, text="Ambiente (Opcional):").grid(row=5, column=0, pady=5, sticky="w")
        v_ambiente = tk.StringVar(value=self.app.nome_ambiente if self.app.nome_ambiente != "Não Informado" else "")
        tk.Entry(frame_inputs, textvariable=v_ambiente, width=18).grid(row=5, column=1, pady=5, padx=5, sticky="w")

        v_giro = tk.BooleanVar(value=False)
        tk.Checkbutton(frame_inputs, text="Permitir giro da peça no Nesting?", variable=v_giro).grid(row=6, column=0, columnspan=2, pady=10, sticky="w")

        tk.Label(janela_dxf, text="Mapeamento de Camadas (Layers):", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        
        frame_camadas = tk.Frame(janela_dxf, relief="groove", bd=2, padx=10, pady=5)
        frame_camadas.pack(fill="both", expand=True, padx=20)
        
        opcoes_acao = ["Corte Contorno", "Furação", "Rasgo", "Ignorar"]
        mapeamento_vars = {}
        
        for i, cam in enumerate(sorted(list(camadas_encontradas))):
            tk.Label(frame_camadas, text=f"Layer '{cam}':", font=("Arial", 9)).grid(row=i, column=0, sticky="w", pady=2)
            c_upper = cam.upper()
            default_val = "Ignorar"
            
            if "CHAPA" in c_upper or "SOBRA" in c_upper: default_val = "Ignorar"
            elif "PECA" in c_upper or "PEÇA" in c_upper: default_val = "Corte Contorno"
            elif "FURO" in c_upper: default_val = "Furação"
            elif "RASGO" in c_upper: default_val = "Rasgo"
            else:
                c_low = cam.lower()
                if any(palavra in c_low for palavra in ["corte", "contorno", "0", "board", "exterior"]): 
                    default_val = "Corte Contorno"
            
            var_acao = tk.StringVar(value=default_val)
            mapeamento_vars[cam] = var_acao
            ttk.Combobox(frame_camadas, textvariable=var_acao, values=opcoes_acao, state="readonly", width=16).grid(row=i, column=1, padx=10, pady=2)

        def ler_e_adicionar_dxf():
            tem_corte_mapeado = any(v.get() == "Corte Contorno" for v in mapeamento_vars.values())
            if not tem_corte_mapeado:
                if not messagebox.askyesno("Aviso", "Nenhuma camada definida como 'Corte Contorno'!\nSem isso, as peças não terão tamanho e ficarão invisíveis. Continuar?"): return

            mat = v_mat.get().strip(); esp = float(v_esp.get().replace(',','.')); qtd = v_qtd.get()
            chave_lote = f"{mat} ({esp}mm)"
            
            if chave_lote not in self.app.lotes_por_material:
                self.app.lotes_por_material[chave_lote] = []
                lista_materiais = list(self.app.lotes_por_material.keys())
                self.app.ui.combo_materiais.configure(values=lista_materiais)
                self.app.ui.combo_materiais.set(chave_lote)
            
            import ezdxf
            from ezdxf import path 
            erros_encontrados = []
            
            for caminho in caminhos:
                nome_arquivo = os.path.basename(caminho).replace(".dxf", "")
                try:
                    doc = ezdxf.readfile(caminho)
                    msp = doc.modelspace()
                    
                    todas_entidades = []
                    for e in msp:
                        if e.dxftype() == 'INSERT':
                            try:
                                for ent in e.virtual_entities(): todas_entidades.append(ent)
                            except: pass
                        else: todas_entidades.append(e)
                    
                    entidades_corte = []
                    outras_entidades = []
                    
                    for e in todas_entidades:
                        acao_escolhida = mapeamento_vars.get(e.dxf.layer, tk.StringVar(value="Ignorar")).get()
                        if acao_escolhida == "Corte Contorno": entidades_corte.append(e)
                        elif acao_escolhida != "Ignorar": outras_entidades.append((e, acao_escolhida))
                    
                    contornos_validos = []
                    for e in entidades_corte:
                        caminho_visual = path.make_path(e)
                        pontos = list(caminho_visual.flattening(distance=0.1))
                        
                        if pontos:
                            pts = [(p.x, p.y) for p in pontos]
                            if pts[0] != pts[-1]: pts.append(pts[0])
                            if len(pts) >= 4: contornos_validos.append(pts)

                    def calcular_area(pts):
                        area = 0.0
                        for i in range(len(pts)-1):
                            area += (pts[i][0]*pts[i+1][1] - pts[i+1][0]*pts[i][1])
                        return abs(area) / 2.0
                    
                    contornos_validos.sort(key=calcular_area, reverse=True)

                    pecas_dxf = []
                    for pts in contornos_validos:
                        min_x, max_x = min(p[0] for p in pts), max(p[0] for p in pts)
                        min_y, max_y = min(p[1] for p in pts), max(p[1] for p in pts)

                        eh_buraco = False
                        for peca in pecas_dxf:
                            p_min_x, p_max_x, p_min_y, p_max_y = peca['bbox']
                            if p_min_x - 2 <= min_x and max_x <= p_max_x + 2 and p_min_y - 2 <= min_y and max_y <= p_max_y + 2:
                                peca['buracos'].append(pts)
                                eh_buraco = True
                                break

                        if not eh_buraco:
                            pecas_dxf.append({'externo': pts, 'buracos': [], 'bbox': (min_x, max_x, min_y, max_y)})

                    for idx, peca_dxf in enumerate(pecas_dxf):
                        pts_externo = peca_dxf['externo']
                        pts_internos_lista = peca_dxf['buracos']
                        min_x, max_x, min_y, max_y = peca_dxf['bbox']

                        w_calc = max_x - min_x
                        h_calc = max_y - min_y

                        if w_calc < 15 or h_calc < 15: continue
                        
                        if v_cliente.get().strip(): self.app.nome_cliente = v_cliente.get().strip()
                        if v_ambiente.get().strip(): self.app.nome_ambiente = v_ambiente.get().strip()
                        
                        nome_base = v_nome_base.get().strip()
                        nome_peca = nome_base if len(pecas_dxf) == 1 else f"{nome_base}_P{idx+1}"
                        
                        uid_seguro = str(uuid.uuid4())[:6]
                        id_oficial = f"DXF-{idx}-{uid_seguro}"
                        
                        nova_peca = PecaPlanejado(id_peca=id_oficial, descricao=nome_peca, material=mat, espessura=esp, quantidade=1)
                        nova_peca.tem_veio = not v_giro.get() 
                        nova_peca.dim_x_csv = w_calc
                        nova_peca.dim_y_csv = h_calc
                        
                        nova_peca.vetor_externo = [{'x': p[0]-min_x, 'y': p[1]-min_y} for p in pts_externo]
                        nova_peca.vetores_internos = [[{'x': p[0]-min_x, 'y': p[1]-min_y} for p in buraco] for buraco in pts_internos_lista]

                        nova_peca.vertices_x = [0, w_calc]
                        nova_peca.vertices_y = [0, h_calc]
                        nova_peca.pontos_perimetro = [{'x': p['x'], 'y': p['y'], 'tem_fita': False} for p in nova_peca.vetor_externo]
                        
                        def ta_dentro(x, y): return (min_x - 2) <= x <= (max_x + 2) and (min_y - 2) <= y <= (max_y + 2)

                        for e, acao in outras_entidades:
                            if acao == "Furação":
                                layer_name = e.dxf.layer
                                match_diam = re.search(r'(\d+(?:[.,]\d+)?)', layer_name)
                                diam_oficial = float(match_diam.group(1).replace(',', '.')) if match_diam else 5.0
                                
                                if e.dxftype() == 'CIRCLE':
                                    cx, cy = e.dxf.center.x, e.dxf.center.y
                                    if ta_dentro(cx, cy):
                                        nova_peca.furos.append({'X': cx - min_x, 'Y': cy - min_y, 'Diameter': e.dxf.radius * 2})
                                elif e.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                                    e_pts = [(p[0], p[1]) for p in e.get_points('xy')] if e.dxftype() == 'LWPOLYLINE' else [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
                                    if e_pts:
                                        xs, ys = [p[0] for p in e_pts], [p[1] for p in e_pts]
                                        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
                                        if ta_dentro(cx, cy):
                                            diam_geo = max(xs) - min(xs)
                                            nova_peca.furos.append({'X': cx - min_x, 'Y': cy - min_y, 'Diameter': diam_oficial if diam_geo < 1.0 else diam_geo})
                                            
                            elif acao == "Rasgo":
                                if e.dxftype() == 'LINE':
                                    x1, y1 = e.dxf.start.x, e.dxf.start.y
                                    x2, y2 = e.dxf.end.x, e.dxf.end.y
                                    if ta_dentro((x1+x2)/2, (y1+y2)/2):
                                        if abs(x2 - x1) > abs(y2 - y1): nova_peca.rasgos.append({'X': min(x1, x2) - min_x, 'Y': ((y1+y2)/2) - min_y, 'Length': abs(x2-x1), 'Width': 6.0, 'Dir': 'H'})
                                        else: nova_peca.rasgos.append({'X': ((x1+x2)/2) - min_x, 'Y': min(y1, y2) - min_y, 'Length': abs(y2-y1), 'Width': 6.0, 'Dir': 'V'})
                                elif e.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                                    e_pts = [(p[0], p[1]) for p in e.get_points('xy')] if e.dxftype() == 'LWPOLYLINE' else [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
                                    if e_pts:
                                        xs, ys = [p[0] for p in e_pts], [p[1] for p in e_pts]
                                        if ta_dentro((min(xs)+max(xs))/2, (min(ys)+max(ys))/2):
                                            rx_min, ry_min = min(xs) - min_x, min(ys) - min_y
                                            rw, rh = max(xs) - min(xs), max(ys) - min(ys)
                                            if rw > rh: nova_peca.rasgos.append({'X': rx_min, 'Y': ry_min, 'Length': rw, 'Width': max(rh, 3.0), 'Dir': 'H'})
                                            else: nova_peca.rasgos.append({'X': rx_min, 'Y': ry_min, 'Length': rh, 'Width': max(rw, 3.0), 'Dir': 'V'})
                        
                        if esp == 6.0 or esp == 6: nova_peca.rasgos = []
                        for _ in range(qtd): self.app.lotes_por_material[chave_lote].append(nova_peca)
                        
                except Exception as ex: 
                    erros_encontrados.append(f"{nome_arquivo}: {str(ex)}")
            
            janela_dxf.destroy()
            
            if erros_encontrados:
                messagebox.showerror("Atenção: Erros no DXF", "Alguns arquivos tiveram falhas:\n\n" + "\n".join(erros_encontrados))
            else:
                messagebox.showinfo("Sucesso!", f"{len(caminhos)} DXFs integrados.")
                
            for lista_pecas in self.app.lotes_por_material.values():
                self.aplicar_genetica_matriarcal(lista_pecas)
                
            self.app.ui.lbl_status.configure(text="Processando novas peças...", fg="blue")
            self.app.root.update()
            self.app.processar_nesting()

        tk.Button(janela_dxf, text="Injetar DXFs no Nesting", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=ler_e_adicionar_dxf).pack(pady=(15, 10))

    # ==========================================================
    # IMPORTAÇÃO DE JSON (CORTECLOUD / TERCEIROS)
    # ==========================================================
    def ler_json(self):
        caminho_arquivo = filedialog.askopenfilename(title="Selecione o arquivo JSON", filetypes=[("Arquivos JSON", "*.json")])
        if not caminho_arquivo: return
        
        self.app.lotes_por_material.clear()
        self.app.nome_cliente = "Cliente JSON"
        self.app.nome_ambiente = "Importação CorteCloud"
        
        try:
            self.app.pasta_projeto = os.path.dirname(caminho_arquivo)
            
            with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
                dados = json.load(arquivo)
                
            partes = dados.get("parts", [])
            total_pecas = 0
            
            for idx, p_data in enumerate(partes):
                qte = int(p_data.get("quantity", 1))
                w = float(p_data.get("c", 0))
                h = float(p_data.get("l", 0))
                if w <= 0 or h <= 0: continue
                
                descricao_bruta = str(p_data.get("function", f"Peca_JSON_{idx}")).strip()
                id_promob = str(p_data.get("complement", "Avulso")).strip()
                mat_bruto = str(p_data.get("material", "MDF Desconhecido")).strip()
                if '(' in mat_bruto: mat_bruto = mat_bruto.split('(')[0].strip()
                
                machining = p_data.get("machining", {})
                espessura = float(machining.get("z", 15.0))
                
                modulo_oficial = "Avulso"
                nome_limpo = descricao_bruta
                
                if '!' in nome_limpo:
                    partes_nome = nome_limpo.split('!', 1)
                    modulo_oficial = partes_nome[0].strip()
                    nome_sujo = partes_nome[1]
                    nome_limpo = nome_sujo.replace('-__', '').replace('__', '').replace('_', ' ').strip().title()
                    nome_limpo = f"[{modulo_oficial}] {nome_limpo}"
                
                id_peca = f"JSON-{idx}-{str(uuid.uuid4())[:4]}"
                nova_peca = PecaPlanejado(id_peca=id_peca, descricao=nome_limpo, material=mat_bruto, espessura=espessura, quantidade=1, tem_veio=False)
                nova_peca.id_modulo_pai = modulo_oficial if modulo_oficial != "Avulso" else (id_promob if id_promob else "Avulso")
                nova_peca.dim_x_csv = w
                nova_peca.dim_y_csv = h
                
                tem_c1, tem_l1 = p_data.get("c1") is not None, p_data.get("l1") is not None
                tem_c2, tem_l2 = p_data.get("c2") is not None, p_data.get("l2") is not None
                
                nova_peca.vertices_x = [0, w, w, 0]
                nova_peca.vertices_y = [0, 0, h, h]
                nova_peca.pontos_perimetro = [{'x': 0, 'y': 0, 'tem_fita': tem_c1}, {'x': w, 'y': 0, 'tem_fita': tem_l1}, {'x': w, 'y': h, 'tem_fita': tem_c2}, {'x': 0, 'y': h, 'tem_fita': tem_l2}]
                
                drills = machining.get("verticalDrills", [])
                furos_formatados = []
                for d in drills: furos_formatados.append({'X': float(d.get('x', 0)), 'Y': float(d.get('y', 0)), 'Diameter': float(d.get('diameter', 5)), 'Depth': float(d.get('depth', espessura))})
                
                nova_peca.furos = furos_formatados
                nova_peca.rasgos = []
                nova_peca.furos_brutos_json = furos_formatados
                
                if not hasattr(nova_peca, 'dados_extras'): nova_peca.dados_extras = {}
                nova_peca.dados_extras.update({"furos_brutos_json": furos_formatados, "is_critica": False, "tipo_engrosso": "NORMAL", "lados_engrosso": "", "esp_alvo_engrosso": espessura})
                
                chave_lote = f"{mat_bruto} ({espessura}mm)"
                if chave_lote not in self.app.lotes_por_material: self.app.lotes_por_material[chave_lote] = []
                for _ in range(qte):
                    self.app.lotes_por_material[chave_lote].append(nova_peca)
                    total_pecas += 1

            for lista_pecas in self.app.lotes_por_material.values():
                self.aplicar_genetica_matriarcal(lista_pecas)
                    
            if total_pecas > 0:
                lista_materiais = list(self.app.lotes_por_material.keys())
                self.app.ui.combo_materiais.configure(values=lista_materiais)
                self.app.ui.combo_materiais.set(lista_materiais[0])
                self.app.ui.lbl_status.configure(text=f"JSON Carregado ({total_pecas} peças)!", text_color="#00E676")
                self.app.processar_nesting()
            else: messagebox.showwarning("Aviso", "Nenhuma peça válida encontrada no JSON.")
        except Exception as e: messagebox.showerror("Erro no JSON", f"Falha ao processar:\n{e}")

    def carregar_modulo_tiranogio_json(self, dados_modulo):
        """
        Converte o payload nativo do TiranoGio 3D para o modelo oficial PecaPlanejado,
        respeitando estritamente a mesma tipagem e estrutura do importador CSV e DXF.
        """
        import json
        from core.modelos import PecaPlanejado

        if isinstance(dados_modulo, str):
            try: dados_modulo = json.loads(dados_modulo)
            except: return False

        pecas_raw = dados_modulo.get("lista_de_pecas", [])
        if not pecas_raw and isinstance(dados_modulo, dict):
            pecas_raw = dados_modulo.get("pecas") or dados_modulo.get("parts") or []

        if not pecas_raw: return False

        self.app.nome_cliente = str(dados_modulo.get("nome_projeto", "BALCAO_3D")).upper()
        self.app.nome_ambiente = str(dados_modulo.get("familia", "MODULO_INFERIOR")).upper()

        parametros = dados_modulo.get("parametros", {})
        mat_caixaria = str(parametros.get("material_caixaria", "MDF_BRANCO_15MM")).upper()
        mat_frentes = str(parametros.get("material_frentes", "MDF_FREIJO_15MM")).upper()

        self.app.lotes_por_material.clear()

        for p_data in pecas_raw:
            if not isinstance(p_data, dict): continue

            categoria = str(p_data.get("categoria_industrial", "")).lower()
            id_peca = str(p_data.get("id_peca", "PEC"))
            nome_peca = str(p_data.get("nome_comercial", "Peça"))

            mat_base = mat_frentes if any(term in categoria for term in ["frente", "porta", "gaveta"]) else mat_caixaria

            dim = p_data.get("dimensoes", {})
            dx, dy, dz = float(dim.get("x", 0)), float(dim.get("y", 0)), float(dim.get("z", 0))
            
            # =================================================================
            # 1. FIX DA ROTAÇÃO: PRESERVAR O EIXO X e Y ORIGINAIS DA PEÇA
            # =================================================================
            # Preserva a orientação original do SketchUp para que as coordenadas
            # dos furos batam exatamente com o mapa da peça.
            if dx > 0 and dy > 0 and dz > 0:
                esp = min(dx, dy, dz)
                if esp == dz: dim_x, dim_y = dx, dy
                elif esp == dx: dim_x, dim_y = dy, dz
                else: dim_x, dim_y = dx, dz
            else:
                dims_ord = sorted([dx, dy, dz])
                esp = dims_ord[0] if dims_ord[0] > 0 else 15.0
                dim_x = dims_ord[1] 
                dim_y = dims_ord[2] 

            if dim_x <= 0 or dim_y <= 0: continue
            mat_peca = f"{mat_base} ({esp}mm)"

            if mat_peca not in self.app.lotes_por_material:
                self.app.lotes_por_material[mat_peca] = []

            peca_obj = PecaPlanejado(
                id_peca=id_peca,
                descricao=f"[{self.app.nome_ambiente}] {nome_peca}",
                material=mat_peca, espessura=esp, quantidade=1, tem_veio=False
            )

            # Injeta as dimensões que casam perfeitamente com os furos
            peca_obj.dim_x_csv = dim_x
            peca_obj.dim_y_csv = dim_y
            
            # =================================================================
            # 2. TRADUTOR DE USINAGENS (A ALFÂNDEGA BILINGUE)
            # =================================================================
            usinagens = p_data.get("usinagens", {})
            
            furos_padrao = []
            for f in usinagens.get("furos", []):
                furos_padrao.append({
                    "X": float(f.get("X", f.get("x", 0))),
                    "Y": float(f.get("Y", f.get("y", 0))),
                    "Diameter": float(f.get("Diameter", f.get("diametro", 5))),
                    "Depth": "passante"
                })
                
            rasgos_padrao = []
            for r in usinagens.get("rasgos", []):
                d_raw = str(r.get("Dir", r.get("direcao", "V"))).upper()
                r_dir = d_raw[0] if d_raw else "V"

                # 1. Busca as chaves de tamanho
                rw = float(r.get("Width", r.get("largura", r.get("espessura", 6))))
                rl = float(r.get("Length", r.get("comprimento", dim_x if r_dir == 'H' else dim_y)))
                
                # 2. Caça-Palavras: Tenta achar a cota exata (X/Y) ou jargões de marcenaria
                rx = float(r.get("X", r.get("x", 0)))
                ry = float(r.get("Y", r.get("y", 0)))
                afastamento = float(r.get("afastamento", r.get("offset", r.get("recuo", r.get("distancia", 0)))))

                # Se o JSON mandou apenas o afastamento, nós convertemos para a coordenada correta
                if rx == 0 and ry == 0 and afastamento > 0:
                    if r_dir == 'V':
                        rx = afastamento
                    else:
                        ry = afastamento

                # 3. FIX DO LADO CONTRÁRIO (Espelhamento de Origem)
                # Subtrai o recuo e a espessura da dimensão total da peça para jogar o rasgo pro lado oposto
                if r_dir == 'V' and rx > 0:
                    rx = dim_x - rx - rw
                elif r_dir == 'H' and ry > 0:
                    ry = dim_y - ry - rw

                rasgos_padrao.append({
                    "X": rx,
                    "Y": ry,
                    "Width": rw,
                    "Length": rl,
                    "Dir": r_dir
                })
                
            peca_obj.furos = furos_padrao
            peca_obj.rasgos = rasgos_padrao
            
            # Ajusta o perímetro para respeitar as dimensões preservadas
            perimetro = [
                {"x": 0.0, "y": 0.0, "tem_fita": False},
                {"x": dim_x, "y": 0.0, "tem_fita": False},
                {"x": dim_x, "y": dim_y, "tem_fita": False},
                {"x": 0.0, "y": dim_y, "tem_fita": False}
            ]
            peca_obj.pontos_perimetro = perimetro
            peca_obj.vertices_x = [p['x'] for p in perimetro]
            peca_obj.vertices_y = [p['y'] for p in perimetro]

            peca_obj.dados_extras = {
                "furos_brutos_json": peca_obj.furos,
                "is_critica": False, "tipo_engrosso": "NORMAL",
                "lados_engrosso": "", "esp_alvo_engrosso": esp
            }
            peca_obj.is_critica = False
            peca_obj.tipo_engrosso = "NORMAL"

            self.app.lotes_por_material[mat_peca].append(peca_obj)

        for lista_pecas in self.app.lotes_por_material.values():
            if hasattr(self, 'aplicar_genetica_matriarcal'):
                self.aplicar_genetica_matriarcal(lista_pecas)

        for mat in self.app.lotes_por_material.keys():
            if mat not in self.app.chapas_globais or not self.app.chapas_globais[mat]:
                esp_chapa = float(mat.split('(')[-1].replace('mm)', '')) if '(' in mat else 15.0
                self.app.chapas_globais[mat] = [[{
                    "tipo": "metadados", "limite_x_corte": 0, "limite_y_corte": 0,
                    "espessura_chapa": esp_chapa, "possui_veio": False
                }]]

        return len(self.app.lotes_por_material) > 0