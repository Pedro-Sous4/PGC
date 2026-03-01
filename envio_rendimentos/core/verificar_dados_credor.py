
import os
import pandas as pd
import time
from core.models import Credor
from core.utils import gerar_arquivos_credor, normalizar_nome
from django.conf import settings

def verificar_dados_credor(nome_credor, numero_pgc):
    print(f"Analisando credor: {nome_credor}\n")

    # Tempo de execução
    try:
        credor = Credor.objects.get(nome__icontains=nome_credor)
        start = time.time()
        gerar_arquivos_credor(credor, numero_pgc)
        end = time.time()
        print(f"Tempo para gerar arquivos: {end - start:.2f} segundos")
    except Exception as e:
        print(f"Erro ao gerar arquivos: {e}")
        return

    # Verifica mínimo (arquivo padrão no root do PGC)
    caminho_minimo = os.path.join(settings.MEDIA_ROOT, "PGC", str(numero_pgc), "MINIMO.xlsx")
    try:
        df_min = pd.read_excel(caminho_minimo)
        print("\n🔍 Mínimo encontrado:")
        for _, row in df_min.iterrows():
            if normalizar_nome(row['credor']) == normalizar_nome(nome_credor):
                print(row[['credor', 'minimo', 'empresa', 'cnpj']])
    except Exception as e:
        print(f"Erro ao ler mínimo.xlsx: {e}")

    # Empresa do extrato
    try:
        # Pastas de credores usam o NOME PARA EXIBIÇÃO em MAIÚSCULAS
        nome_pasta = str(credor.nome).strip().upper()
        caminho_ext = os.path.join(settings.MEDIA_ROOT, "PGC", str(numero_pgc), nome_pasta, f"{nome_pasta} - EXTRATO.xlsx")
        df_ext = pd.read_excel(caminho_ext)
        empresas = df_ext['empresa'].dropna().unique()
        print(f"\n🏢 Empresas encontradas no extrato: {empresas}")
    except Exception as e:
        print(f"Erro ao ler EXTRATO.xlsx: {e}")
        return

    # CNPJ na planilha EMPRESAS
    try:
        empresa_alvo = empresas[0]  # analisa a primeira para exemplo
        df_emp = pd.read_excel(r"C:\PGC\envio_rendimentos\arquivos_gerados\EMPRESAS_NOMECURTO_CNPJ.xlsx")
        df_emp['normalizado'] = df_emp['nome_curto'].astype(str).apply(normalizar_nome)
        empresa_limpa = normalizar_nome(empresa_alvo)
        resultado = df_emp[df_emp['normalizado'] == empresa_limpa]
        print("\n🔗 Empresa mapeada na planilha de CNPJ:")
        print(resultado[['nome_curto', 'cnpj']])
    except Exception as e:
        print(f"Erro ao verificar CNPJ da empresa: {e}")
