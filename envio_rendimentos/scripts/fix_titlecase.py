import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'envio_rendimentos.settings')
import django
django.setup()

from core.models import Credor, titlecase_name

# Update all credores with proper titlecase
count = 0
for credor in Credor.objects.all():
    old_name = credor.nome
    # Force titlecase
    credor.nome = titlecase_name(old_name)
    if credor.nome != old_name:
        count += 1
    credor.save()

print(f"Atualizados {count} credores com título case corrigido.")
