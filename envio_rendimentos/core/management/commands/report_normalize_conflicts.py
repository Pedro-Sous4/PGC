import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Credor


class Command(BaseCommand):
    help = "Gera um CSV com conflitos de normalização de nomes de Credor."

    def add_arguments(self, parser):
        parser.add_argument('--out', help='Caminho do arquivo de saída (CSV).', default=None)

    def handle(self, *args, **options):
        out = options.get('out')
        if not out:
            out_dir = os.path.join(settings.BASE_DIR, 'core', 'management', 'reports')
            os.makedirs(out_dir, exist_ok=True)
            out = os.path.join(out_dir, 'normalize_conflicts.csv')

        mapping = {}
        for c in Credor.objects.all():
            new = (str(c.nome).strip().lower().capitalize()) if c.nome else ''
            mapping.setdefault(new, []).append((c.id, c.nome))

        conflicts = {k: v for k, v in mapping.items() if len(v) > 1}

        if not conflicts:
            self.stdout.write(self.style.SUCCESS('Nenhum conflito detectado.'))
            return

        with open(out, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['normalized_name', 'id', 'current_name'])
            for new, items in conflicts.items():
                for id_, name in items:
                    writer.writerow([new, id_, name])

        self.stdout.write(self.style.SUCCESS(f'CSV gerado em: {out}'))
