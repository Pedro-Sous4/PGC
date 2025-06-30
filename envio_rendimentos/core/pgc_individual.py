import os
import sys

# === Ajuste de caminho do projeto para importar Django ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))         # .../core
PROJETO_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))   # .../envio_rendimentos
sys.path.append(PROJETO_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "envio_rendimentos.settings")

import django
django.setup()

import pandas as pd
from core.models import Credor
from core.utils import (
    normalizar_nome,
    obter_minimo_garantido_para_credor,
    gerar_arquivos_credor
)
from django.conf import settings


def processar_credor_individual(numero_pgc, nome_credor):
    print(f"\n🔄 Processando PGC {numero_pgc} para o credor: {nome_credor}")

    pasta_pgc = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc))
    caminho_base = os.path.join(pasta_pgc, f'BASE PGC {numero_pgc}.xlsx')
    caminho_extrato = os.path.join(pasta_pgc, 'EXTRATO.xlsx')
    caminho_prod = os.path.join(pasta_pgc, 'PRODUTIVIDADE.xlsx')
    caminho_minimo = os.path.join(pasta_pgc, 'mínimo.xlsx')

    if not os.path.exists(caminho_base):
        print("❌ Arquivo BASE não encontrado.")
        return

    base_df = pd.read_excel(caminho_base)
    extrato_df = pd.read_excel(caminho_extrato) if os.path.exists(caminho_extrato) else None
    prod_df = pd.read_excel(caminho_prod) if os.path.exists(caminho_prod) else None
    minimo_df = pd.read_excel(caminho_minimo) if os.path.exists(caminho_minimo) else None

    base_df['credor'] = base_df['credor'].astype(str)
    nome_norm = normalizar_nome(nome_credor)
    df_credor = base_df[base_df['credor'].apply(normalizar_nome) == nome_norm]

    if df_credor.empty and (
        minimo_df is None or minimo_df[minimo_df['credor'].apply(normalizar_nome) == nome_norm].empty
    ):
        print("❌ Credor não encontrado na BASE nem no mínimo.xlsx.")
        return

    # Busca ou cria objeto Credor
    credor_obj, _ = Credor.objects.get_or_create(
        nome=nome_credor.strip(), defaults={'email': '', 'periodo': ''}
    )

    # Gera os arquivos normalmente
    gerar_arquivos_credor(
        credor=credor_obj,
        numero_pgc=numero_pgc,
        base_df=base_df,
        extrato_df=extrato_df,
        prod_df=prod_df,
        minimo_df=minimo_df
    )

    print(f"✅ Arquivos gerados com sucesso para {credor_obj.nome}!")
    print(f"📂 Pasta: {os.path.join(pasta_pgc, credor_obj.nome_pasta())}")


# === Execução via terminal ===
if __name__ == "__main__":
    try:
        numero_pgc = input("Número do PGC: ").strip()
        nome_credor = input("Nome do credor: ").strip()
        processar_credor_individual(numero_pgc, nome_credor)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
