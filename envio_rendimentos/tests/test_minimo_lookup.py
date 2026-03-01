import os
import pandas as pd
from django.test import override_settings
from django.conf import settings
from core.utils import obter_minimo_garantido_para_credor


def make_minimo_file(path, rows):
    df = pd.DataFrame(rows)
    df.to_excel(path, index=False)


@override_settings(MEDIA_ROOT=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tmp_media'))
def test_obter_minimo_from_minimo_xlsx(tmp_path):
    media = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tmp_media')
    pgc_dir = os.path.join(media, 'PGC', '15')
    os.makedirs(pgc_dir, exist_ok=True)

    # Create 'minimo.xlsx' with uppercase columns and varying names
    rows = [
        {
            'CREDOR': '  123 - João Silva (CAPTADOR)  ',
            'MINIMO/FIXO GARANTIDO PARA EMISSAO NF': 150.5,
            'EMPRESA EMISSÃO NF': 'LGM FILIAL',
            'CNPJ': '12.345.678/0001-90'
        }
    ]
    caminho = os.path.join(pgc_dir, 'minimo.xlsx')
    make_minimo_file(caminho, rows)

    result = obter_minimo_garantido_para_credor('123 - JoAo silva (captador)', '15')
    assert result is not None
    assert float(result['valor']) == 150.5
    assert str(result['empresa']).strip() == 'LGM FILIAL'
    assert str(result['cnpj']).strip() == '12.345.678/0001-90'


@override_settings(MEDIA_ROOT=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tmp_media'))
def test_obter_minimo_from_MINIMO_XLSX(tmp_path):
    media = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tmp_media')
    pgc_dir = os.path.join(media, 'PGC', '99')
    os.makedirs(pgc_dir, exist_ok=True)

    rows = [
        {
            'credor': 'Fulano de Tal',
            'minimo': 200,
            'empresa_emissao': 'LGM FILIAL',
            'cnpj': '98.765.432/0001-10'
        }
    ]
    caminho = os.path.join(pgc_dir, 'MINIMO.xlsx')
    make_minimo_file(caminho, rows)

    res = obter_minimo_garantido_para_credor('FULANO DE TAL', '99')
    assert res is not None
    assert float(res['valor']) == 200
    assert res['cnpj'] == '98.765.432/0001-10'