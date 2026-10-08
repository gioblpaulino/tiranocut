# TiranoGio_App/core/modelos.py

class PecaPlanejado:
    """
    Classe base que representa uma peça a ser cortada na CNC.
    Guarda as dimensões, furos, rasgos e contornos extraídos do CSV ou DXF.
    """
    def __init__(self, id_peca, descricao, material, espessura, quantidade, tem_veio=False):
        self.id_peca = id_peca
        self.descricao = descricao
        self.material = material
        self.tem_veio = tem_veio
        
        # Tratamento de espessura para evitar erros se vier com vírgula do CSV
        try: 
            self.espessura = float(str(espessura).replace(',', '.'))
        except ValueError: 
            self.espessura = 15.0
            
        # Tratamento da quantidade
        try: 
            self.quantidade = int(quantidade)
        except ValueError: 
            self.quantidade = 1
        
        # Listas para guardar a geometria e usinagens da peça
        self.vertices_x = []
        self.vertices_y = []
        self.pontos_perimetro = [] 
        self.furos = []
        self.rasgos = []
        
        # Dimensões base vindas do CSV (usadas quando não há DXF associado)
        self.dim_x_csv = 0.0
        self.dim_y_csv = 0.0
        
    @property
    def largura(self):
        """Calcula a largura baseada nos vértices do DXF ou retorna a do CSV."""
        if not self.vertices_x: 
            return self.dim_x_csv
        return max(self.vertices_x) - min(self.vertices_x)
        
    @property
    def altura(self):
        """Calcula a altura baseada nos vértices do DXF ou retorna a do CSV."""
        if not self.vertices_y: 
            return self.dim_y_csv
        return max(self.vertices_y) - min(self.vertices_y)
