import os

BASE_DIR = r"C:\PGC\envio_rendimentos\arquivos_gerados\PGC\34"

renomeadas = []

for nome in os.listdir(BASE_DIR):
    caminho = os.path.join(BASE_DIR, nome)

    # ignora arquivos (ex: MINIMO.xlsx)
    if not os.path.isdir(caminho):
        continue

    # se não for totalmente maiúsculo
    if nome != nome.upper():
        novo_nome = nome.upper()
        novo_caminho = os.path.join(BASE_DIR, novo_nome)

        # evita sobrescrever caso já exista
        if not os.path.exists(novo_caminho):
            os.rename(caminho, novo_caminho)
            renomeadas.append((nome, novo_nome))
        else:
            print(f"[ATENÇÃO] Já existe: {novo_nome}")

print("\n=== PASTAS RENOMEADAS ===")
for antigo, novo in renomeadas:
    print(f"{antigo}  →  {novo}")

print(f"\nTotal corrigidas: {len(renomeadas)}")
