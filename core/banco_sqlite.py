# TiranoGio_App/core/banco_sqlite.py

import sqlite3
import os
import json

class BancoDadosSQLite:
    def __init__(self, nome_banco="tiranogio_data.db"):
        self.nome_banco = nome_banco
        self._criar_tabelas()
        self._verificar_e_atualizar_schema()
        self._garantir_configuracao_padrao()

        # --- PONTE DE MEMÓRIA UNIFICADA PARA A INTERFACE ---
        self.config_cnc = {"maquina": {}, "ferramentas": []}
        self.pos_processadores = {}
        
        # 1. Tenta sugar os dados legados antes de ler o banco
        self.importar_tudo_do_legado()
        
        # 2. Carrega do banco por cima para manter a persistência atualizada
        self.carregar_config_cnc()
        self.carregar_pos_processadores_unificado()

    def conectar(self):
        return sqlite3.connect(self.nome_banco)

    def _criar_tabelas(self):
        with self.conectar() as conn:
            cursor = conn.cursor()
            
            # Tabela 1: Configurações da Máquina
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config_maquina (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    chapa_largura REAL,
                    chapa_altura REAL,
                    refilo REAL,
                    gap_fresa REAL,
                    sobrecorte_mm REAL,
                    angulo_rampa_graus REAL,
                    z_seguranca_add REAL,
                    usar_tabs INTEGER,
                    tab_largura REAL,
                    tab_espessura REAL
                )
            ''')
            
            # Tabela 2: Biblioteca de Ferramentas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ferramentas (
                    id_ferramenta TEXT PRIMARY KEY,
                    cone TEXT,
                    tipo TEXT,
                    min_d REAL,
                    max_d REAL,
                    z_desce TEXT,
                    rpm INTEGER,
                    mergulho INTEGER,
                    corte INTEGER,
                    metros_rodados REAL DEFAULT 0.0
                )
            ''')

            # Tabela 3: Projetos e Planos de Corte dos Clientes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projetos_clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_cliente TEXT NOT NULL,
                    nome_ambiente TEXT,
                    data_salvamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    lotes_json TEXT,
                    chapas_json TEXT
                )
            ''')
            
            # Tabela 4: Cofre de Retalhos Disponíveis
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS retalhos_disponiveis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material TEXT NOT NULL,
                    largura REAL NOT NULL,
                    altura REAL NOT NULL,
                    espessura REAL NOT NULL,
                    possui_veio INTEGER DEFAULT 0,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Tabela 5: Parâmetros de Filtro de Sobras Úteis
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config_retalhos (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    area_min_x REAL DEFAULT 300.0,
                    area_min_y REAL DEFAULT 300.0
                )
            ''')

            # Garante o registro de configuração padrão se estiver vazio
            cursor.execute("SELECT COUNT(*) FROM config_retalhos")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO config_retalhos (id, area_min_x, area_min_y) VALUES (1, 300.0, 300.0)")
            conn.commit()


    def _verificar_e_atualizar_schema(self):
        """Varre a estrutura para garantir que usuários com bancos antigos ganhem a coluna do hodômetro"""
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(ferramentas)")
            colunas = [col[1] for col in cursor.fetchall()]
            if "metros_rodados" not in colunas:
                try:
                    cursor.execute("ALTER TABLE ferramentas ADD COLUMN metros_rodados REAL DEFAULT 0.0")
                    conn.commit()
                except Exception as e:
                    print(f"Erro ao atualizar schema da tabela ferramentas: {e}")

    def _garantir_configuracao_padrao(self):
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM config_maquina")
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO config_maquina (
                        id, chapa_largura, chapa_altura, refilo, gap_fresa,
                        sobrecorte_mm, angulo_rampa_graus, z_seguranca_add, usar_tabs, tab_largura, tab_espessura
                    ) VALUES (1, 2750.0, 1830.0, 20.0, 6.0, 0.5, 15.0, 15.0, 1, 5.0, 2.0)
                ''')
            conn.commit()

    def listar_projetos_salvos(self):
        """Retorna a listagem indexada de projetos para a interface gráfica"""
        try:
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, nome_cliente, nome_ambiente, data_salvamento FROM projetos_clientes ORDER BY data_salvamento DESC")
                return cursor.fetchall()
        except Exception as e:
            print(f"Erro ao listar projetos: {e}")
            return []

    def carregar_projeto_cliente(self, projeto_id):
        """Busca os pacotes JSON de geometrias e lotes estruturados pelo ID"""
        try:
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT nome_cliente, nome_ambiente, lotes_json, chapas_json FROM projetos_clientes WHERE id = ?", (projeto_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "nome_cliente": row[0],
                        "nome_ambiente": row[1],
                        "lotes": json.loads(row[2]) if row[2] else {},
                        "chapas": json.loads(row[3]) if row[3] else {}
                    }
        except Exception as e:
            print(f"Erro ao carregar projeto individual: {e}")
        return None

    def salvar_projeto_cliente(self, nome_cliente, nome_ambiente, lotes_dict, chapas_dict):
        """Cria um novo registro para o plano de corte do cliente no banco blindado"""
        try:
            # Transforma os objetos em estruturas JSON limpas de string para o SQLite
            lotes_json = json.dumps(lotes_dict, default=lambda o: o.__dict__ if hasattr(o, '__dict__') else str(o), ensure_ascii=False)
            chapas_json = json.dumps(chapas_dict, ensure_ascii=False)
            
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO projetos_clientes (nome_cliente, nome_ambiente, lotes_json, chapas_json)
                    VALUES (?, ?, ?, ?)
                ''', (str(nome_cliente).strip().upper(), str(nome_ambiente).strip(), lotes_json, chapas_json))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Erro ao inserir novo projeto do cliente: {e}")
            raise e

    def atualizar_projeto_cliente(self, projeto_id, nome_cliente, nome_ambiente, lotes_dict, chapas_dict):
        """Atualiza um plano de corte existente mantendo o ID intacto"""
        try:
            lotes_json = json.dumps(lotes_dict, default=lambda o: o.__dict__ if hasattr(o, '__dict__') else str(o), ensure_ascii=False)
            chapas_json = json.dumps(chapas_dict, ensure_ascii=False)
            
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE projetos_clientes 
                    SET nome_cliente = ?, nome_ambiente = ?, lotes_json = ?, chapas_json = ?, data_salvamento = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (str(nome_cliente).strip().upper(), str(nome_ambiente).strip(), lotes_json, chapas_json, int(projeto_id)))
                conn.commit()
        except Exception as e:
            print(f"Erro ao atualizar projeto do cliente: {e}")
            raise e

    def importar_tudo_do_legado(self):
        caminho_json_cnc = "config_cnc.json"
        if os.path.exists(caminho_json_cnc):
            try:
                with open(caminho_json_cnc, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                with self.conectar() as conn:
                    cursor = conn.cursor()
                    if "maquina" in dados:
                        m = dados["maquina"]
                        cursor.execute('''
                            UPDATE config_maquina SET 
                            sobrecorte_mm = ?, angulo_rampa_graus = ?, z_seguranca_add = ?, 
                            usar_tabs = ?, tab_largura = ?, tab_espessura = ? WHERE id = 1
                        ''', (m.get("sobrecorte_mm", 0.5), m.get("angulo_rampa_graus", 15.0), m.get("z_seguranca_add", 15.0), int(m.get("usar_tabs", 1)), m.get("tab_largura", 5.0), m.get("tab_espessura", 2.0)))
                    
                    if "ferramentas" in dados:
                        for f_old in dados["ferramentas"]:
                            cursor.execute('''
                                INSERT OR IGNORE INTO ferramentas (id_ferramenta, cone, tipo, min_d, max_d, z_desce, rpm, mergulho, corte, metros_rodados)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0)
                            ''', (f_old.get("id", "Desconhecida"), f_old.get("cone", "T1"), f_old.get("tipo", "corte"), f_old.get("min_d", 0.0), f_old.get("max_d", 0.0), str(f_old.get("z_desce", "passante")), f_old.get("rpm", 18000), f_old.get("mergulho", 3000), f_old.get("corte", 8000)))
                
                dest_cnc = f"{caminho_json_cnc}.old"
                if os.path.exists(dest_cnc): os.remove(dest_cnc)
                os.rename(caminho_json_cnc, dest_cnc)
            except Exception as e:
                print(f"Erro ao migrar JSON antigo: {e}")

        caminho_hodo = "config_ferramentas.json"
        if os.path.exists(caminho_hodo):
            try:
                with open(caminho_hodo, "r", encoding="utf-8") as f:
                    dados_hodo = json.load(f)
                with self.conectar() as conn:
                    cursor = conn.cursor()
                    for chave, info in dados_hodo.items():
                        id_convertido = "Fresa de Corte 6mm (UP/DOWN)" if "6mm" in chave else info.get("nome")
                        cursor.execute('''
                            UPDATE ferramentas SET metros_rodados = ? WHERE id_ferramenta = ? OR cone = ?
                        ''', (float(info.get("metros_rodados", 0.0)), id_convertido, chave))
                
                dest_hodo = f"{caminho_hodo}.old"
                if os.path.exists(dest_hodo): os.remove(dest_hodo)
                os.rename(caminho_hodo, dest_hodo)
            except Exception as e:
                print(f"Erro ao migrar dados de desgaste do Hodômetro: {e}")

    def carregar_pos_processadores_unificado(self):
        self.pos_processadores = {
            "GRBL Padrão (MDF)": {
                "header": "G90 G21\nM3 S{rpm}\nG0 Z{z_safe}",
                "tool_change": "M5\nT{tool} M6\nM3 S{rpm}",
                "footer": "M5\nG0 Z{z_safe}\nM30"
            },
            "Mach3 Genérico (Router)": {
                "header": "(--- TIRANOGIO V12 ---\nG90 G21\nG17 G40 G49 G80\nG0 Z{z_safe}",
                "tool_change": "M6 {tool}\nM3 S{rpm}\nG4 P2",
                "footer": "G0 Z{z_safe}\nG0 X0 Y0\nM5\nM30"
            }
        }

        pasta_pp = "pos_processadores"
        if os.path.exists(pasta_pp):
            for arquivo in os.listdir(pasta_pp):
                if arquivo.endswith(".json"):
                    caminho_completo = os.path.join(pasta_pp, arquivo)
                    try:
                        with open(caminho_completo, "r", encoding="utf-8") as f:
                            dados_custom = json.load(f)
                            for nome_pp, script in dados_custom.items():
                                self.pos_processadores[nome_pp] = script
                    except Exception as e:
                        print(f"Erro ao ler pós-processador customizado {arquivo}: {e}")

    def carregar_config_cnc(self):
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM config_maquina WHERE id = 1")
            row = cursor.fetchone()
            if row:
                self.config_cnc["maquina"] = {
                    "chapa_largura": row[1], "chapa_altura": row[2], "refilo": row[3],
                    "gap_fresa": row[4], "sobrecorte_mm": row[5], "angulo_rampa_graus": row[6],
                    "z_seguranca_add": row[7], "usar_tabs": bool(row[8]),
                    "tab_largura": row[9], "tab_espessura": row[10]
                }
            
            self.config_cnc["ferramentas"] = []
            cursor.execute("SELECT id_ferramenta, cone, tipo, min_d, max_d, z_desce, rpm, mergulho, corte FROM ferramentas")
            for r in cursor.fetchall():
                self.config_cnc["ferramentas"].append({
                    "id": r[0], "cone": r[1], "tipo": r[2], "min_d": r[3], "max_d": r[4],
                    "z_desce": r[5], "rpm": r[6], "mergulho": r[7], "corte": r[8]
                })

    def salvar_config_cnc(self):
        with self.conectar() as conn:
            cursor = conn.cursor()
            m = self.config_cnc.get("maquina", {})
            cursor.execute('''
                UPDATE config_maquina SET 
                sobrecorte_mm = ?, angulo_rampa_graus = ?, z_seguranca_add = ?, usar_tabs = ?, tab_largura = ?, tab_espessura = ?
                WHERE id = 1
            ''', (m.get("sobrecorte_mm", 0.5), m.get("angulo_rampa_graus", 15.0), m.get("z_seguranca_add", 15.0), int(m.get("usar_tabs", 1)), m.get("tab_largura", 5.0), m.get("tab_espessura", 2.0)))
            
            for f in self.config_cnc.get("ferramentas", []):
                cursor.execute('''
                    INSERT INTO ferramentas (id_ferramenta, cone, tipo, min_d, max_d, z_desce, rpm, mergulho, corte, metros_rodados)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0)
                    ON CONFLICT(id_ferramenta) DO UPDATE SET
                    cone=excluded.cone, tipo=excluded.tipo, min_d=excluded.min_d, max_d=excluded.max_d,
                    z_desce=excluded.z_desce, rpm=excluded.rpm, mergulho=excluded.mergulho, corte=excluded.corte
                ''', (f.get("id"), f.get("cone"), f.get("tipo"), f.get("min_d", 0.0), f.get("max_d", 0.0), str(f.get("z_desce", "passante")), f.get("rpm", 18000), f.get("mergulho", 3000), f.get("corte", 8000)))
            conn.commit()

    def buscar_ferramenta(self, tipo_desejado, diametro_alvo=None):
        melhor_ferramenta = None
        for f in self.config_cnc.get("ferramentas", []):
            if f.get("tipo") == tipo_desejado:
                if diametro_alvo:
                    min_d = float(f.get("min_d", 0))
                    max_d = float(f.get("max_d", 0))
                    if min_d <= diametro_alvo <= max_d:
                        melhor_ferramenta = f
                        break
                else:
                    melhor_ferramenta = f
                    break
        return melhor_ferramenta
    
    def obter_limites_retalho(self):
        """Retorna o comprimento e largura mínimos para considerar uma sobra útil"""
        try:
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT area_min_x, area_min_y FROM config_retalhos WHERE id = 1")
                row = cursor.fetchone()
                return (row[0], row[1]) if row else (300.0, 300.0)
        except Exception as e:
            print(f"Erro ao ler limites de retalho: {e}")
            return (300.0, 300.0)

    def atualizar_limites_retalho(self, min_x, min_y):
        """Atualiza os filtros de área mínima configurados pelo operador"""
        try:
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE config_retalhos SET area_min_x = ?, area_min_y = ? WHERE id = 1", (float(min_x), float(min_y)))
                conn.commit()
        except Exception as e:
            print(f"Erro ao atualizar limites de retalho: {e}")

    def salvar_retalho_avulso(self, material, largura, altura, espessura, possui_veio):
        """Insere um retalho qualificado (manual ou via nesting) no cofre blindado"""
        try:
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO retalhos_disponiveis (material, largura, altura, espessura, possui_veio)
                    VALUES (?, ?, ?, ?, ?)
                ''', (str(material).strip().upper(), float(largura), float(altura), float(espessura), int(possui_veio)))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Erro ao salvar retalho: {e}")
            return None

    def listar_retalhos_por_material(self, material):
        """Busca retalhos utilizáveis compatíveis com o MDF do projeto ativo"""
        try:
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, largura, altura, espessura, possui_veio 
                    FROM retalhos_disponiveis 
                    WHERE material = ? 
                    ORDER BY largura DESC, altura DESC
                ''', (str(material).strip().upper(),))
                return cursor.fetchall()
        except Exception as e:
            print(f"Erro ao listar retalhos: {e}")
            return []

    def consumir_retalho_banco(self, retalho_id):
        """Remove o retalho do banco assim que ele for alocado em um plano de corte"""
        try:
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM retalhos_disponiveis WHERE id = ?", (int(retalho_id),))
                conn.commit()
        except Exception as e:
            print(f"Erro ao consumir retalho: {e}")