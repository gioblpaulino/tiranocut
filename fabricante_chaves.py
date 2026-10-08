# fabricante_chaves.py
import hashlib

def gerar_chave_para_cliente():
    print("========================================")
    print(" 🔑 GERADOR DE LICENÇAS - TIRANOGIO 🔑")
    print("========================================")
    
    # ATENÇÃO: Tem que ser EXATAMENTE a mesma frase do seguranca.py
    salt_secreto = "TiranoGio_SuperSecret_2026!@#"
    
    maquina_id = input("\nCole o [Código da Máquina] que o cliente te enviou: ").strip()
    
    if not maquina_id:
        print("Erro: O ID da máquina não pode estar vazio.")
        return
        
    # A mesma matemática do core/seguranca.py
    texto_base = f"{maquina_id}{salt_secreto}".encode('utf-8')
    hash_completo = hashlib.sha256(texto_base).hexdigest()
    chave_final = hash_completo[:20].upper()
    
    # Salva no arquivo
    with open("licenca.key", "w", encoding="utf-8") as f:
        f.write(chave_final)
        
    print("\n✅ SUCESSO!")
    print(f"Chave Gerada: {chave_final}")
    print("O arquivo 'licenca.key' foi criado na sua pasta.")
    print("Envie este arquivo para o cliente colocar junto ao executável (.exe).\n")

if __name__ == "__main__":
    gerar_chave_para_cliente()
    input("Pressione ENTER para sair...")