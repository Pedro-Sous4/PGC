import os
import pandas as pd
import tempfile

from django.test import override_settings

from core.utils_lgm import gerar_minimo


def make_sample_workbook(path, pgc_num='123'):
    cols = list(range(43))
    rows = []
    for r in range(12):
        row = ['' for _ in cols]
        if r >= 7:
            row[35] = f'Credor Teste {r}'
            row[41] = 'LGM FILIAL'
            row[40] = 100 + r
        rows.append(row)
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(path, engine='openpyxl') as w:
        df.to_excel(w, sheet_name=f'PGC {pgc_num}', header=False, index=False)


def test_gerar_minimo_creates_file(tmp_path):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    arquivo = tmp_path / 'sample.xlsx'
    make_sample_workbook(str(arquivo), pgc_num='321')
    base_output = tmp_path / 'PGC' / '321'
    base_output.mkdir(parents=True, exist_ok=True)

    # Create EMPRESAS file used for CNPJ lookup
    from core.utils_lgm import EMPRESAS_PATH
    emp_df = pd.DataFrame({'nome_curto': ['LGM FILIAL'], 'cnpj': ['12.345.678/0001-90']})
    emp_dir = os.path.dirname(EMPRESAS_PATH)
    os.makedirs(emp_dir, exist_ok=True)
    emp_df.to_excel(EMPRESAS_PATH, index=False)

    gerar_minimo(str(arquivo), 'PGC 321', '321', str(base_output), request_id='pytest')

    out = base_output / 'MINIMO.xlsx'
    assert out.exists(), 'MINIMO.xlsx should be created'

    df_out = pd.read_excel(out)
    assert 'CREDOR' in df_out.columns
    assert 'MINIMO/FIXO GARANTIDO PARA EMISSAO NF' in df_out.columns
    assert 'EMPRESA EMISSÃO NF' in df_out.columns
    assert 'CNPJ' in df_out.columns
    # should contain only rows with minima (we created 5)
    assert len(df_out) == 5
