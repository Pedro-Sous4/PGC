# Create normalized sheets (BASE, PRODUTIVIDADE, EXTRATO, EMISSAO, MINIMO) from a PGC workbook
import sys
import os

# ensure project path
sys.path.append(r'C:\PGC\envio_rendimentos\envio_rendimentos')
sys.path.append(r'C:\PGC\envio_rendimentos')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
import django
django.setup()

import pandas as pd
from core.utils import normalizar_e_salvar_planilha_base, salvar_minimos_como_excel
from core.utils_lgm import extrair_numero_pgc, localizar_abas, ler_minimo, encontrar_coluna

# Auto-detect the most recent PGC xlsx under arquivos_gerados/PGC
root = os.path.join('envio_rendimentos', 'arquivos_gerados', 'PGC')
pgc_files = [os.path.join(root, f) for f in os.listdir(root) if f.lower().endswith('.xlsx') and f.lower().startswith('pgc')]
if not pgc_files:
    print('Nenhum arquivo PGC encontrado em', root)
    raise SystemExit(1)
# pick the newest
pgc_files = sorted(pgc_files, key=lambda p: os.path.getmtime(p), reverse=True)
file_path = pgc_files[0]
print('Usando arquivo:', file_path)

# read sheet names to extract numero
xls = pd.ExcelFile(file_path)
numero_pgc = extrair_numero_pgc(xls.sheet_names)
print('Número PGC detectado:', numero_pgc)

# Normalize and save base/extrato/produtividade using existing util (try-fast; on fail, read sheets individually)
try:
    pasta_pgc = normalizar_e_salvar_planilha_base(file_path, numero_pgc)
    print('Planilhas base/extrato/produtividade normalizadas salvas em:', pasta_pgc)
except KeyboardInterrupt as e:
    print('normalizacao interrompida por KeyboardInterrupt; executando fallback por aba individual')
    # fallback: read minimal sheets and save
    xls = pd.ExcelFile(file_path)
    pasta_pgc = os.path.join('envio_rendimentos','arquivos_gerados','PGC', str(int(numero_pgc)))
    os.makedirs(pasta_pgc, exist_ok=True)
    # base
    for s in xls.sheet_names:
        if 'base' in s.lower() and f'pgc {numero_pgc}' in s.lower():
            df_base = pd.read_excel(file_path, sheet_name=s)
            from core.utils import normalizar_colunas_simples
            df_base = normalizar_colunas_simples(df_base)
            df_base.to_excel(os.path.join(pasta_pgc, f'BASE PGC {numero_pgc}.xlsx'), index=False)
            print('BASE salva (fallback):', s)
        elif 'extrato' in s.lower():
            df_ext = pd.read_excel(file_path, sheet_name=s)
            from core.utils import normalizar_colunas_simples
            df_ext = normalizar_colunas_simples(df_ext)
            df_ext.to_excel(os.path.join(pasta_pgc, 'EXTRATO.xlsx'), index=False)
            print('EXTRATO salva (fallback):', s)
        elif 'prod' in s.lower() or 'perodutiv' in s.lower():
            df_prod = pd.read_excel(file_path, sheet_name=s)
            from core.utils import normalizar_colunas_simples
            df_prod = normalizar_colunas_simples(df_prod)
            df_prod.to_excel(os.path.join(pasta_pgc, 'PRODUTIVIDADE.xlsx'), index=False)
            print('PRODUTIVIDADE salva (fallback):', s)
    # copy original PGC file into folder
    try:
        dst = os.path.join(pasta_pgc, f'PGC {numero_pgc}.xlsx')
        if not os.path.exists(dst):
            import shutil
            shutil.copy(file_path, dst)
            print('Arquivo PGC original copiado para', dst)
    except Exception as e2:
        print('Não foi possível copiar PGC original:', e2)
except Exception as e:
    print('normalizar_e_salvar_planilha_base falhou, fazendo fallback por aba individual:', e)
    # fallback: read minimal sheets and save
    xls = pd.ExcelFile(file_path)
    pasta_pgc = os.path.join('envio_rendimentos','arquivos_gerados','PGC', str(int(numero_pgc)))
    os.makedirs(pasta_pgc, exist_ok=True)
    # base
    for s in xls.sheet_names:
        if 'base' in s.lower() and f'pgc {numero_pgc}' in s.lower():
            df_base = pd.read_excel(file_path, sheet_name=s)
            from core.utils import normalizar_colunas_simples
            df_base = normalizar_colunas_simples(df_base)
            df_base.to_excel(os.path.join(pasta_pgc, f'BASE PGC {numero_pgc}.xlsx'), index=False)
            print('BASE salva (fallback):', s)
        elif 'extrato' in s.lower():
            df_ext = pd.read_excel(file_path, sheet_name=s)
            from core.utils import normalizar_colunas_simples
            df_ext = normalizar_colunas_simples(df_ext)
            df_ext.to_excel(os.path.join(pasta_pgc, 'EXTRATO.xlsx'), index=False)
            print('EXTRATO salva (fallback):', s)
        elif 'prod' in s.lower() or 'perodutiv' in s.lower():
            df_prod = pd.read_excel(file_path, sheet_name=s)
            from core.utils import normalizar_colunas_simples
            df_prod = normalizar_colunas_simples(df_prod)
            df_prod.to_excel(os.path.join(pasta_pgc, 'PRODUTIVIDADE.xlsx'), index=False)
            print('PRODUTIVIDADE salva (fallback):', s)
    # copy original PGC file into folder
    try:
        dst = os.path.join(pasta_pgc, f'PGC {numero_pgc}.xlsx')
        if not os.path.exists(dst):
            import shutil
            shutil.copy(file_path, dst)
            print('Arquivo PGC original copiado para', dst)
    except Exception as e2:
        print('Não foi possível copiar PGC original:', e2)

# Create EMISSAO.xlsx from base file if present
base_filename = os.path.join(pasta_pgc, f'BASE PGC {numero_pgc}.xlsx')
if os.path.exists(base_filename):
    df_base = pd.read_excel(base_filename)
    # candidate columns for emissao
    candidates = ['cnpj_para_emissao', 'cnpj para emissao', 'cnpj_para_emissao', 'cnpj', 'empresa', 'documento', 'cliente', 'valor', 'valor_original', 'dt_emissao', 'dt_vencimento', 'parcela', 'obs_baixa']
    cols = []
    for c in candidates:
        col = encontrar_coluna(df_base, [c])
        if col and col not in cols:
            cols.append(col)
    if not cols:
        # fallback: include most columns
        cols = list(df_base.columns)[:10]
    df_emissao = df_base[cols].copy()
    out_emissao = os.path.join(pasta_pgc, 'EMISSAO.xlsx')
    df_emissao.to_excel(out_emissao, index=False)
    print('EMISSAO gerada:', out_emissao)
else:
    print('BASE PGC não encontrada; pulando EMISSAO')

# Ensure PRODUTIVIDADE exists: try to find a sheet with 'prod' or 'perodutiv' in the original workbook
prod_path = os.path.join(pasta_pgc, 'PRODUTIVIDADE.xlsx')
if not os.path.exists(prod_path):
    prod_sheet = None
    for s in xls.sheet_names:
        if 'prod' in s.lower() or 'perodutiv' in s.lower():
            prod_sheet = s
            break
    if prod_sheet:
        print('Encontrada aba de produtividade:', prod_sheet)
        df_prod = pd.read_excel(file_path, sheet_name=prod_sheet)
        # use simple normalization
        from core.utils import normalizar_colunas_simples
        df_prod = normalizar_colunas_simples(df_prod)
        df_prod.to_excel(prod_path, index=False)
        print('PRODUTIVIDADE gerada:', prod_path)
    else:
        print('Nenhuma aba de produtividade encontrada; pulando PRODUTIVIDADE')

# Read minimo sheet and save as MINIMO.xlsx if exists
abas = localizar_abas(xls.sheet_names, numero_pgc)
if 'minimo' in abas:
    df_minimo = ler_minimo(file_path, abas['minimo'])
    if not df_minimo.empty:
        caminho_minimo = salvar_minimos_como_excel(df_minimo, str(numero_pgc))
        print('MINIMO gerada:', caminho_minimo)
    else:
        print('Aba minimo encontrada mas sem dados relevantes.')
else:
    print('Aba MINIMO não encontrada nas abas da planilha.')

print('\nResumo dos arquivos no PGC:')
for root_dir, dirs, files in os.walk(pasta_pgc):
    for fn in files:
        print(' -', os.path.join(root_dir, fn))

print('\nPronto. Agora podemos trabalhar sobre essas planilhas para gerar os arquivos por credor.')