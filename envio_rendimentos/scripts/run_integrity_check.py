import os
import sys

# Ensure project root is on path
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'envio_rendimentos.settings')
import django
django.setup()

from django.db.models import Count
from core.models import Credor
import csv

total = Credor.objects.count()
null_norm = Credor.objects.filter(nome_normalizado__isnull=True).count()
distinct = (
    Credor.objects.exclude(nome_normalizado__isnull=True)
    .values('nome_normalizado')
    .distinct()
    .count()
)

dups = (
    Credor.objects.values('nome_normalizado')
    .annotate(c=Count('id'))
    .filter(nome_normalizado__isnull=False, c__gt=1)
    .order_by('-c')
)

print(f"Total de registros em Credor: {total}")
print(f"Registros com nome_normalizado nulo: {null_norm}")
print(f"Total de nomes normalizados distintos (não-nulos): {distinct}")
print('\nPrincipais duplicações (nome_normalizado -> count):')
for d in dups[:50]:
    print(f"{d['nome_normalizado']} -> {d['c']}")

# Write CSV report
out_dir = os.path.join('core', 'management', 'reports')
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'integrity_duplicates.csv')
with open(out_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['nome_normalizado', 'count'])
    for d in dups:
        w.writerow([d['nome_normalizado'], d['c']])

print(f"\nRelatório CSV gerado: {out_path}")