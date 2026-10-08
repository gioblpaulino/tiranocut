# TiranoGio_App/core/motor_usinagem.py

class CalculadoraUsinagem:
    """
    Motor matemático responsável por calcular os Feeds & Speeds ideais
    com base na Carga por Dente (Chip Load) e nas especificações da ferramenta.
    """
    def __init__(self):
        # Futuramente, isso virá do seu banco de dados (JSON ou SQLite)
        # Já deixei engatilhado com exemplos reais para MDF
        self.catalogo_ferramentas = {
            "T1_Corte_4mm_1C": {
                "fabricante": "Fresas Curitiba",
                "tipo": "Reta 1 Corte",
                "diametro_mm": 4.0,
                "cortes_z": 1,
                "chip_load_mdf": 0.15,  # mm arrancados por dente a cada giro
                "rpm_maxima": 24000
            },
            "T2_Corte_6mm_2C": {
                "fabricante": "Código G",
                "tipo": "Compressão 2 Cortes",
                "diametro_mm": 6.0,
                "cortes_z": 2,
                "chip_load_mdf": 0.22, 
                "rpm_maxima": 18000
            },
            "T3_Broca_Passante_5mm": {
                "fabricante": "Generica",
                "tipo": "Broca de Furação",
                "diametro_mm": 5.0,
                "cortes_z": 1,
                "chip_load_mdf": 0.10, 
                "rpm_maxima": 12000
            }
        }

    def calcular_parametros(self, id_ferramenta, rpm_alvo, fator_mergulho=0.4):
        """
        Calcula o Feed Rate (Avanço) e o Plunge Rate (Mergulho) exatos.
        - fator_mergulho: A descida em Z geralmente é de 40% a 50% do avanço de corte.
        """
        ferramenta = self.catalogo_ferramentas.get(id_ferramenta)
        
        if not ferramenta:
            return {"erro": "Ferramenta não cadastrada no sistema."}

        # Trava de segurança: não deixa o RPM passar do limite da fresa
        rpm_usado = min(rpm_alvo, ferramenta["rpm_maxima"])
        
        z_cortes = ferramenta["cortes_z"]
        chip_load = ferramenta["chip_load_mdf"]

        # FÓRMULA MESTRA: Avanço (mm/min) = RPM * Número de Cortes * Chip Load
        feed_rate_calculado = rpm_usado * z_cortes * chip_load
        
        # O mergulho da broca no MDF precisa ser mais suave para escoar o pó
        plunge_rate_calculado = feed_rate_calculado * fator_mergulho

        return {
            "id_ferramenta": id_ferramenta,
            "rpm_final": int(rpm_usado),
            "feed_rate_F": int(feed_rate_calculado),
            "plunge_rate_F": int(plunge_rate_calculado),
            "carga_por_dente": chip_load
        }

# ==========================================
# EXEMPLO DE USO NO SEU CÓDIGO FUTURO
# ==========================================
if __name__ == "__main__":
    motor = CalculadoraUsinagem()
    
    # Simulação: O operador configurou o Spindle para 18.000 RPM
    rpm_maquina = 18000
    
    print("--- CÁLCULO DE USINAGEM TIRANOGIO ---")
    
    # Calculando para a fresa de 1 Corte
    resultado_fresa1 = motor.calcular_parametros("T1_Corte_4mm_1C", rpm_maquina)
    print(f"\nFresa 1 Corte (4mm):")
    print(f"-> G-Code Sugerido: G1 X... Y... F{resultado_fresa1['feed_rate_F']}")
    print(f"-> Descida em Z: G1 Z... F{resultado_fresa1['plunge_rate_F']}")
    
    # Calculando para a fresa de 2 Cortes (Mesmo RPM)
    resultado_fresa2 = motor.calcular_parametros("T2_Corte_6mm_2C", rpm_maquina)
    print(f"\nFresa 2 Cortes (6mm):")
    print(f"-> G-Code Sugerido: G1 X... Y... F{resultado_fresa2['feed_rate_F']}")
    print(f"-> Descida em Z: G1 Z... F{resultado_fresa2['plunge_rate_F']}")