import tkinter as tk
import customtkinter as ctk
import math

class EditorPoligonos(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configurações da Janela Principal
        self.title("TiranoGio - Prancheta Vetorial 2D")
        self.geometry("1000x700")
        self.configure(fg_color="#121212")

        # Configurações do Desenho (Tudo em Milímetros)
        self.pontos_mm = [] # Armazena os vértices exatos da peça
        self.grid_mm = 50.0 # Passo da malha magnética
        self.escala = 0.5   # 1mm = 0.5px na tela
        self.offset_x = 50  # Margem do canvas
        self.offset_y = 50
        
        # Variáveis de Controle do Mouse
        self.mouse_x_mm = 0
        self.mouse_y_mm = 0
        
        self.setup_ui()

    def setup_ui(self):
        # ==========================================
        # PAINEL LATERAL (FERRAMENTAS)
        # ==========================================
        
        # Painel Lateral
        self.frame_tools = ctk.CTkFrame(self, width=250, fg_color="#1E1E1E", corner_radius=0)
        self.frame_tools.pack(side="left", fill="y")
        self.frame_tools.pack_propagate(False)

        ctk.CTkLabel(self.frame_tools, text="📐 FORMAS RÁPIDAS", font=ctk.CTkFont(weight="bold")).pack(pady=(20, 10))
        
        ctk.CTkButton(self.frame_tools, text="🟩 Retângulo (1000x500)", fg_color="#388E3C", hover_color="#2E7D32", command=lambda: self.carregar_forma("retangulo")).pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(self.frame_tools, text="📐 Corte em 'L' (Cozinha)", fg_color="#388E3C", hover_color="#2E7D32", command=lambda: self.carregar_forma("corte_l")).pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(self.frame_tools, text="🔺 Triângulo Retângulo", fg_color="#388E3C", hover_color="#2E7D32", command=lambda: self.carregar_forma("triangulo")).pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(self.frame_tools, text="🖱️ DESENHO LIVRE", font=ctk.CTkFont(weight="bold")).pack(pady=(30, 10))
        ctk.CTkLabel(self.frame_tools, text="• Clique Esquerdo: Adiciona Ponto\n• Clique Direito: Fecha Polígono\n• Esc: Cancela Desenho", text_color="#9E9E9E", justify="left").pack(padx=20)

        self.btn_limpar = ctk.CTkButton(self.frame_tools, text="🗑️ Limpar Prancheta", fg_color="#D32F2F", hover_color="#B71C1C", command=self.limpar_prancheta)
        self.btn_limpar.pack(side="bottom", fill="x", padx=20, pady=20)
        
        self.btn_salvar = ctk.CTkButton(self.frame_tools, text="💾 Exportar Geometria", fg_color="#00796B", hover_color="#004D40", height=40, font=ctk.CTkFont(weight="bold"), command=self.exportar_geometria)
        self.btn_salvar.pack(side="bottom", fill="x", padx=20, pady=0)

        # ==========================================
        # CANVAS (ÁREA DE DESENHO)
        # ==========================================
        self.frame_canvas = ctk.CTkFrame(self, fg_color="#2B2B2B")
        self.frame_canvas.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(self.frame_canvas, bg="#2B2B2B", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Eventos do Mouse e Teclado
        self.canvas.bind("<Motion>", self.ao_mover_mouse)
        self.canvas.bind("<Button-1>", self.ao_clicar_esquerdo)
        self.canvas.bind("<Button-3>", self.ao_clicar_direito)
        self.bind("<Escape>", lambda e: self.limpar_prancheta())
        self.canvas.bind("<Configure>", lambda e: self.desenhar_tudo())

        # HUD de Coordenadas
        self.lbl_coords = ctk.CTkLabel(self.frame_canvas, text="X: 0 mm | Y: 0 mm", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00E676", bg_color="#2B2B2B")
        self.lbl_coords.place(relx=0.02, rely=0.02)

    # ==========================================
    # LÓGICA MATEMÁTICA E COORDENADAS
    # ==========================================
    def mm_para_px(self, x_mm, y_mm):
        """Converte milímetros reais para pixels da tela, invertendo o Y"""
        ch = self.canvas.winfo_height()
        x_px = self.offset_x + (x_mm * self.escala)
        y_px = ch - self.offset_y - (y_mm * self.escala)
        return x_px, y_px

    def px_para_mm(self, x_px, y_px):
        """Converte o clique do mouse em milímetros reais da peça"""
        ch = self.canvas.winfo_height()
        x_mm = (x_px - self.offset_x) / self.escala
        y_mm = (ch - self.offset_y - y_px) / self.escala
        return x_mm, y_mm

    def aplicar_snap(self, valor):
        """Puxa a coordenada para o ponto mais próximo do Grid"""
        return round(valor / self.grid_mm) * self.grid_mm

    # ==========================================
    # INTERAÇÃO DO USUÁRIO
    # ==========================================
    def ao_mover_mouse(self, event):
        raw_x_mm, raw_y_mm = self.px_para_mm(event.x, event.y)
        self.mouse_x_mm = self.aplicar_snap(raw_x_mm)
        self.mouse_y_mm = self.aplicar_snap(raw_y_mm)
        
        # Trava para não desenhar coordenadas negativas
        self.mouse_x_mm = max(0.0, self.mouse_x_mm)
        self.mouse_y_mm = max(0.0, self.mouse_y_mm)

        self.lbl_coords.configure(text=f"X: {self.mouse_x_mm:.0f} mm | Y: {self.mouse_y_mm:.0f} mm")
        self.desenhar_tudo()

    def ao_clicar_esquerdo(self, event):
        # Adiciona um novo vértice à peça
        self.pontos_mm.append({"x": self.mouse_x_mm, "y": self.mouse_y_mm, "tem_fita": False})
        self.desenhar_tudo()

    def ao_clicar_direito(self, event):
        # Fecha o polígono conectando o último ponto ao primeiro
        if len(self.pontos_mm) > 2:
            print("Polígono Fechado!")
            self.pontos_mm.append(self.pontos_mm[0].copy())
            self.desenhar_tudo()

    # ==========================================
    # RENDERIZAÇÃO GRÁFICA
    # ==========================================
    def desenhar_tudo(self):
        self.canvas.delete("all")
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 50: return

        # 1. Desenhar a Malha Magnética (Grid)
        step_px = self.grid_mm * self.escala
        
        # Linhas Verticais
        for i in range(int(cw // step_px)):
            x = self.offset_x + (i * step_px)
            self.canvas.create_line(x, 0, x, ch, fill="#1F1F1F")
            
        # Linhas Horizontais
        for i in range(int(ch // step_px)):
            y = ch - self.offset_y - (i * step_px)
            self.canvas.create_line(0, y, cw, y, fill="#1F1F1F")

        # Desenha os eixos X e Y principais (Ponto 0,0)
        zero_x, zero_y = self.mm_para_px(0, 0)
        self.canvas.create_line(zero_x, 0, zero_x, ch, fill="#4CAF50", width=2) # Eixo Y
        self.canvas.create_line(0, zero_y, cw, zero_y, fill="#F44336", width=2) # Eixo X

        # 2. Desenhar a Peça Atual
        if len(self.pontos_mm) > 0:
            coords_px = []
            for pt in self.pontos_mm:
                px, py = self.mm_para_px(pt['x'], pt['y'])
                coords_px.extend([px, py])
                # Desenha a "bolinha" do vértice
                self.canvas.create_oval(px-4, py-4, px+4, py+4, fill="#FFEB3B", outline="")

            # Desenha as linhas já confirmadas
            if len(self.pontos_mm) > 1:
                self.canvas.create_line(coords_px, fill="#E6C280", width=3)
            
            # 3. Linha Elástica (Preview do próximo ponto)
            # Só desenha a linha elástica se o polígono não estiver fechado
            poligono_fechado = len(self.pontos_mm) > 2 and self.pontos_mm[0] == self.pontos_mm[-1]
            
            if not poligono_fechado:
                ultimo_pt = self.pontos_mm[-1]
                upx, upy = self.mm_para_px(ultimo_pt['x'], ultimo_pt['y'])
                mpx, mpy = self.mm_para_px(self.mouse_x_mm, self.mouse_y_mm)
                self.canvas.create_line(upx, upy, mpx, mpy, fill="#00B0FF", dash=(4, 4), width=2)
                self.canvas.create_oval(mpx-4, mpy-4, mpx+4, mpy+4, fill="#00B0FF", outline="")

    # ==========================================
    # FUNÇÕES DE APOIO
    # ==========================================
    def limpar_prancheta(self):
        self.pontos_mm.clear()
        self.desenhar_tudo()

    def carregar_forma(self, tipo):
        self.limpar_prancheta()
        if tipo == "retangulo":
            self.pontos_mm = [
                {"x": 0, "y": 0, "tem_fita": False},
                {"x": 1000, "y": 0, "tem_fita": False},
                {"x": 1000, "y": 500, "tem_fita": False},
                {"x": 0, "y": 500, "tem_fita": False},
                {"x": 0, "y": 0, "tem_fita": False} # Fecha
            ]
        elif tipo == "corte_l":
            self.pontos_mm = [
                {"x": 0, "y": 0, "tem_fita": False},
                {"x": 1000, "y": 0, "tem_fita": False},
                {"x": 1000, "y": 600, "tem_fita": False},
                {"x": 400, "y": 600, "tem_fita": False},
                {"x": 400, "y": 1000, "tem_fita": False},
                {"x": 0, "y": 1000, "tem_fita": False},
                {"x": 0, "y": 0, "tem_fita": False} # Fecha
            ]
        elif tipo == "triangulo":
            self.pontos_mm = [
                {"x": 0, "y": 0, "tem_fita": False},
                {"x": 800, "y": 0, "tem_fita": False},
                {"x": 0, "y": 800, "tem_fita": False},
                {"x": 0, "y": 0, "tem_fita": False} # Fecha
            ]
        self.desenhar_tudo()

    def exportar_geometria(self):
        if len(self.pontos_mm) < 3:
            tk.messagebox.showwarning("Incompleto", "Desenhe pelo menos 3 pontos e feche o polígono!")
            return
            
        print("\n=== DNA VETORIAL GERADO PARA O BANCO DE DADOS ===")
        import pprint
        pprint.pprint(self.pontos_mm)
        tk.messagebox.showinfo("Exportado", "Dicionário de coordenadas impresso no console!")

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = EditorPoligonos()
    app.mainloop()