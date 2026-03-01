import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'envio_rendimentos.settings')
import django
django.setup()

from core.models import Credor

# Show first 20 credores with their names
credores = Credor.objects.all()[:20]
print("Exemplos de nomes atualizados (Title Case com preposições em minúsculas):\n")
print(f"{'ID':<6} | {'Nome':<50}")
print("-" * 60)
for c in credores:
    print(f"{c.id:<6} | {c.nome}")
