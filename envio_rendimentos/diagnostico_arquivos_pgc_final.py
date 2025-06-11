
import os
import pandas as pd
from django.conf import settings

def diagnosticar_arquivos_pgc(numero_pgc):
    base_path = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc))
    base_file = os.path.join(base_path, 'BASE PGC %s.xlsx' % numero_pgc)

    if not os.path.exists(base_file):
        print(f"[ERRO] BASE PGC {numero_pgc}.xlsx não encontrado.")
        return

    df = pd.read_excel(base_file)
    nomes_credor = df['credor'].unique()

    relatorio = []

    for nome in nomes_credor:
        nome_pasta = None
        for pasta in os.listdir(base_path):
            if pasta.endswith(nome):
                nome_pasta = pasta
                break

        if not nome_pasta:
            relatorio.append((nome, "❌ Pasta do credor não encontrada"))
            continue

        pasta_credor = os.path.join(base_path, nome_pasta)
        arquivos = os.listdir(pasta_credor)
        esperados = [
            f"{nome} - PGC {numero_pgc}.xlsx",
            f"{nome} - PGC {numero_pgc} EMISSÃO.xlsx",
            f"{nome} - EXTRATO.xlsx",
            f"{nome} - PRODUTIVIDADE"
        ]

        faltando = [arq for arq in esperados if not any(arq in f for f in arquivos)]
        if faltando:
            relatorio.append((nome, f"⚠️ Faltando: {', '.join(faltando)}"))
        else:
            relatorio.append((nome, "✅ OK"))

    print("\n=== Diagnóstico dos Arquivos Gerados ===")
    for nome, status in relatorio:
        print(f"- {nome}: {status}")
