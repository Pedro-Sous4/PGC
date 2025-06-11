
import os
import pandas as pd
from django.conf import settings

def diagnosticar_arquivos_pgc(numero_pgc):
    base_path = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc))
    base_file = os.path.join(base_path, f'BASE PGC {numero_pgc}.xlsx')

    if not os.path.exists(base_file):
        print(f"[ERRO] BASE PGC {numero_pgc}.xlsx não encontrado.")
        return

    df = pd.read_excel(base_file)
    nomes_credor = df['credor'].unique()

    relatorio = []

    colunas_esperadas = {
        'PGC': ['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original'],
        'EMISSAO': ['EMPRESA', 'CREDOR', 'CNPJ PARA EMISSÃO', 'VALOR'],
        'EXTRATO': ['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento', 'obs_baixa'],
        'PRODUTIVIDADE': ['empresa', 'credor', 'documento', 'cliente', 'parcela', 'dt_emissao', 'valor_original', 'dt_vencimento']
    }

    for nome in nomes_credor:
        pasta_credor = None
        for p in os.listdir(base_path):
            if nome in p:
                pasta_credor = os.path.join(base_path, p)
                break

        if not pasta_credor or not os.path.isdir(pasta_credor):
            relatorio.append((nome, "❌ Pasta não encontrada"))
            continue

        arquivos = os.listdir(pasta_credor)
        status = []

        for tipo, colunas in colunas_esperadas.items():
            tipo_busca = tipo if tipo != 'EMISSAO' else 'PGC'
            arqs = [a for a in arquivos if tipo_busca in a.upper()]
            if not arqs:
                status.append(f"❌ {tipo}")
                continue

            try:
                df_arq = pd.read_excel(os.path.join(pasta_credor, arqs[0]))
                faltando = [c for c in colunas if c not in df_arq.columns]
                if faltando:
                    status.append(f"⚠️ {tipo} faltando colunas: {', '.join(faltando)}")
                else:
                    status.append(f"✅ {tipo}")
            except Exception as e:
                status.append(f"❌ {tipo} erro: {str(e)}")

        relatorio.append((nome, status))

    print("\n=== Diagnóstico Detalhado dos Arquivos por Credor ===")
    for nome, sts in relatorio:
        print(f"\n{nome}:")
        for linha in sts if isinstance(sts, list) else [sts]:
            print(f"  - {linha}")
