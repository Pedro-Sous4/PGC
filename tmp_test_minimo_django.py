import os, sys
# Configure Django env similar to tests
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'envio_rendimentos.settings')
import django
try:
    django.setup()
except Exception as e:
    print('Django setup warning:', e)

from envio_rendimentos.core.utils import gerar_minimos_por_coluna_ap
import pandas as pd
# create fake pgc
path='tmp_pgc_test.xlsx'
cols=[f'col_{i}' for i in range(50)]
rows=[]
for r in range(12):
    row=['' for _ in cols]
    if r>=7:
        row[29]=f'Credor Teste {r}'
        row[35]=100+r
        row[36]='EMPRESA X' if r%2==0 else 'EMPRESA Y'
        row[37]='XX/XX'
        row[41]='EMPRESA X' if r%2==0 else 'EMPRESA Y'
    rows.append(row)
df=pd.DataFrame(rows, columns=cols)
with pd.ExcelWriter(path, engine='openpyxl') as w:
    df.to_excel(w, sheet_name='PGC 99', header=False, index=False)
# create empresas lookup
emp_path=r'C:\PGC\envio_rendimentos\arquivos_gerados\EMPRESAS_NOMECURTO_CNPJ.xlsx'
os.makedirs(os.path.dirname(emp_path), exist_ok=True)
emp_df=pd.DataFrame({'nome_curto':['EMPRESA X','EMPRESA Y'], 'cnpj':['11.111.111/0001-11','22.222.222/0001-22']})
emp_df.to_excel(emp_path, index=False)
# run
out=gerar_minimos_por_coluna_ap(path, '99', pasta_saida='.')
print('generated:', out)
if out and os.path.exists(out):
    import pandas as pd
    df_out=pd.read_excel(out)
    print(df_out.head())
