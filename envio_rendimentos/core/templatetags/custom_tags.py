from django import template
from django.conf import settings
import os
import glob

register = template.Library()

@register.filter
def listar_pdfs(relative_path):
    import os
    import glob
    from django.conf import settings

    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    print("DEBUG > Caminho completo analisado:", full_path)
    if not os.path.isdir(full_path):
        print("DEBUG > A pasta NÃO existe.")
        return []

    # Captura tanto .pdf quanto .PDF
    arquivos_pdf = glob.glob(os.path.join(full_path, "*.pdf"))
    arquivos_PDF = glob.glob(os.path.join(full_path, "*.PDF"))

    arquivos = arquivos_pdf + arquivos_PDF

    return [os.path.relpath(a, settings.MEDIA_ROOT).replace("\\", "/") for a in arquivos]


@register.filter
def filename(path):
    return os.path.basename(path)

@register.filter
def listar_arquivos(relative_dir):
    full_path = os.path.join(settings.MEDIA_ROOT, relative_dir)
    print("DEBUG > Caminho completo analisado:", full_path)
    if not os.path.isdir(full_path):
        print("DEBUG > A pasta NÃO existe.")
        return []
    arquivos = glob.glob(os.path.join(full_path, '*.*'))
    print("DEBUG > Arquivos encontrados:", arquivos)
    return [os.path.relpath(a, settings.MEDIA_ROOT).replace('\\', '/') for a in arquivos]

@register.filter
def underscore(value):
    return value.replace(" ", "_")
