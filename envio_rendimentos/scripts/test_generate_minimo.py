"""Script rápido para testar geração de minimo.xlsx para LGM
Gera um arquivo de amostra em processing/<tmp> e chama gerar_minimo
"""
import os
import pandas as pd
from core.utils_lgm import gerar_minimo

TMP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tmp')
os.makedirs(TMP, exist_ok=True)

pgc_num = '999'
file_path = os.path.join(TMP, f'pgc_sample_{pgc_num}.xlsx')

# Construir uma planilha com colunas A..AQ (0..42)
cols = list(range(43))
# criar 12 linhas, com primeiras 7 sendo cabeçalho/descrições
rows = []
for r in range(12):
    row = ['' for _ in cols]
    # colocar valores a partir da linha 8 (idx 7)
    if r >= 7:
        row[35] = f'Credor Teste {r}'   # AJ
        row[41] = 'LGM FILIAL'          # AP - empresa abreviada (short name)
        row[40] = 100 + r               # AO - minimo
    rows.append(row)

# escrever para a aba 'PGC 999' (nome esperado)
df = pd.DataFrame(rows)
with pd.ExcelWriter(file_path, engine='openpyxl') as w:
    df.to_excel(w, sheet_name=f'PGC {pgc_num}', header=False, index=False)

print('Sample workbook written:', file_path)

# Write EMPRESAS file used to lookup CNPJ (nome_curto -> cnpj)
from core.utils_lgm import EMPRESAS_PATH
emp_df = pd.DataFrame({'nome_curto': ['LGM FILIAL'], 'cnpj': ['12.345.678/0001-90']})
emp_dir = os.path.dirname(EMPRESAS_PATH)
os.makedirs(emp_dir, exist_ok=True)
emp_df.to_excel(EMPRESAS_PATH, index=False)

# destino: should be arquivos_gerados/PGC/999/minimo.xlsx
base_output = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'arquivos_gerados', 'PGC', pgc_num)
os.makedirs(base_output, exist_ok=True)

# Call gerar_minimo
gerar_minimo(file_path, f'PGC {pgc_num}', pgc_num, base_output, request_id='test')

out = os.path.join(base_output, 'minimo.xlsx')
print('Output exists?', os.path.exists(out))
if os.path.exists(out):
    df_out = pd.read_excel(out)
    print('Generated minimo.xlsx contents:')
    print(df_out)
else:
    print('No minimo.xlsx generated')
