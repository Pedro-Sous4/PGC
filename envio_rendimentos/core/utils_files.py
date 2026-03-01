# core/utils_files.py
"""
Funções EXCLUSIVAS para salvar arquivos temporários.
Cada fluxo tem sua própria função para evitar conflitos.
"""

import os
import uuid
from django.conf import settings


def salvar_planilha_temporaria_lgm(uploaded_file):
    """
    Salva a planilha enviada no fluxo LGM.

    Retorna:
        caminho absoluto do arquivo salvo
    """
    pasta = os.path.join(settings.MEDIA_ROOT, "tmp_lgm")
    os.makedirs(pasta, exist_ok=True)

    nome_arquivo = f"LGM_{uuid.uuid4()}_{uploaded_file.name}"
    caminho = os.path.join(pasta, nome_arquivo)

    with open(caminho, "wb+") as destino:
        for chunk in uploaded_file.chunks():
            destino.write(chunk)

    return caminho
