import os
import re
import unicodedata
import logging
from django.conf import settings

logger = logging.getLogger("renomear_pastas")
logger.setLevel(logging.INFO)

# Import titlecase function from models
import sys
import django
from pathlib import Path

# Setup Django to access models
if not django.apps.apps.ready:
    django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
    if not django_settings:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'envio_rendimentos.settings')
    django.setup()

from core.models import titlecase_name


def normalizar_nome_pasta(nome):
    """
    Normaliza o nome para padrão único de pasta usando title-case com preposições em minúsculas.
    Remove acentos e aplica a mesma lógica de titlecase_name.
    """
    if not nome:
        return ""

    nome = str(nome)

    # Remove prefixos numéricos
    nome = re.sub(r'^\d+\s*-\s*', '', nome)

    # Remove sufixos entre parênteses
    nome = re.sub(r'\s*\([^)]*\)', '', nome)

    # Remove acentos
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))

    # Remove espaços duplicados
    nome = re.sub(r'\s+', ' ', nome).strip()

    # Apply titlecase logic (preserva preposições em minúsculas)
    return titlecase_name(nome)



def renomear_pastas_pgc(numero_pgc):
    """
    Renomeia todas as pastas de credores dentro de um PGC.
    """
    base_pgc = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc))

    if not os.path.isdir(base_pgc):
        print(f"❌ Pasta PGC não encontrada: {base_pgc}")
        return

    print(f"🔍 Processando PGC {numero_pgc}")
    print(f"📂 Base: {base_pgc}\n")

    for pasta_atual in os.listdir(base_pgc):
        caminho_atual = os.path.join(base_pgc, pasta_atual)

        # Ignora arquivos
        if not os.path.isdir(caminho_atual):
            continue

        # Ignora pasta MINIMO ou outras técnicas
        if pasta_atual.upper() in ['MINIMO', 'TEMP', 'TMP']:
            continue

        nome_normalizado = normalizar_nome_pasta(pasta_atual)

        if pasta_atual == nome_normalizado:
            print(f"✔️ OK: {pasta_atual}")
            continue

        caminho_novo = os.path.join(base_pgc, nome_normalizado)

        # Evita sobrescrever
        if os.path.exists(caminho_novo):
            print(
                f"⚠️ CONFLITO: '{pasta_atual}' → '{nome_normalizado}' "
                f"(destino já existe)"
            )
            continue

        try:
            os.rename(caminho_atual, caminho_novo)
            print(f"🔁 RENOMEADO: '{pasta_atual}' → '{nome_normalizado}'")
        except Exception as e:
            print(f"❌ ERRO ao renomear '{pasta_atual}': {e}")


def renomear_todos_pgcs():
    """
    Percorre todos os PGCs existentes.
    """
    raiz_pgc = os.path.join(settings.MEDIA_ROOT, 'PGC')

    if not os.path.isdir(raiz_pgc):
        print("❌ Pasta raiz PGC não encontrada.")
        return

    for pgc in os.listdir(raiz_pgc):
        caminho = os.path.join(raiz_pgc, pgc)
        if os.path.isdir(caminho):
            renomear_pastas_pgc(pgc)
