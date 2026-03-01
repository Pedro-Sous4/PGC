import os, sys
# Ensure the 'envio_rendimentos' package root is on sys.path so we can import 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.minimo_display import format_empresa_para_exibicao


def test_strip_prefix_number():
    assert format_empresa_para_exibicao('24 - LGM PARTICIPACOES LTDA | FILIAL PEDRAS ALTAS') == 'LGM PARTICIPACOES LTDA | FILIAL PEDRAS ALTAS'
    assert format_empresa_para_exibicao('2 - Empresa X') == 'Empresa X'
    assert format_empresa_para_exibicao('EMPRESA SEM NUMERO') == 'EMPRESA SEM NUMERO'
    assert format_empresa_para_exibicao(None) is None
    assert format_empresa_para_exibicao('') == ''
