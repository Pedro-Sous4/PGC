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

@register.filter
def aggregate_total(queryset):
    if not queryset:
        return 0
    total = sum(item.valor_total for item in queryset if hasattr(item, 'valor_total'))
    return total

@register.filter
def aggregate_average(queryset):
    if not queryset:
        return 0
    items = [item.valor_total for item in queryset if hasattr(item, 'valor_total')]
    return sum(items) / len(items) if items else 0
@register.filter
def aggregate_total_field(queryset, field_name='valor'):
    """Agrega soma de um queryset por um nome de campo (ex: 'valor' ou 'valor_total')."""
    if not queryset:
        return 0
    total = 0
    for item in queryset:
        try:
            total += float(getattr(item, field_name, 0) or 0)
        except Exception:
            continue
    return total


@register.filter
def aggregate_average_field(queryset, field_name='valor'):
    """Calcula média de um queryset por um nome de campo."""
    if not queryset:
        return 0
    values = []
    for item in queryset:
        try:
            v = float(getattr(item, field_name, 0) or 0)
            values.append(v)
        except Exception:
            continue
    return sum(values) / len(values) if values else 0
@register.filter
def format_currency_br(value):
    """Formata valor em moeda brasileira: R$ xxx,xx"""
    try:
        if value is None:
            return "R$ 0,00"
        # Converte para float
        valor_float = float(value)
        # Formata com 2 casas decimais usando vírgula e ponto
        return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"