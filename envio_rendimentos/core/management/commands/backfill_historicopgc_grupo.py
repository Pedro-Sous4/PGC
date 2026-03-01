from django.core.management.base import BaseCommand
from core.models import HistoricoPGC
import csv
import os
from django.conf import settings

REPORT_DIR = os.path.join(settings.BASE_DIR, 'tmp') if hasattr(settings, 'BASE_DIR') else os.path.join(settings.MEDIA_ROOT, 'tmp')

class Command(BaseCommand):
    help = 'Dry-run or apply backfill of HistoricoPGC.grupo from credor.grupo when missing.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Apply the changes (destructive).')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of records to process (0 = all).')

    def handle(self, *args, **options):
        apply_changes = options['apply']
        limit = options['limit']

        os.makedirs(REPORT_DIR, exist_ok=True)
        report_path = os.path.join(REPORT_DIR, 'backfill_historicopgc_grupo_report.csv')

        queryset = HistoricoPGC.objects.filter(grupo__isnull=True)
        total = queryset.count()
        self.stdout.write(self.style.NOTICE(f'Found {total} HistoricoPGC with null grupo.'))

        if limit > 0:
            queryset = queryset[:limit]

        processed = 0
        with open(report_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['id', 'credor_id', 'credor_nome', 'credor_grupo', 'action'])
            writer.writeheader()

            for h in queryset:
                inferred = None
                if h.credor and h.credor.grupo:
                    inferred = h.credor.grupo
                action = 'none'
                if inferred:
                    action = 'set-to-credor.grupo'
                    writer.writerow({'id': h.id, 'credor_id': h.credor_id, 'credor_nome': str(h.credor), 'credor_grupo': str(inferred), 'action': action})
                    if apply_changes:
                        h.grupo = inferred
                        h.save(update_fields=['grupo'])
                else:
                    writer.writerow({'id': h.id, 'credor_id': h.credor_id, 'credor_nome': str(h.credor), 'credor_grupo': '', 'action': action})
                processed += 1

        self.stdout.write(self.style.SUCCESS(f'Report written to {report_path}'))
        self.stdout.write(self.style.SUCCESS(f'Processed {processed} records (apply={apply_changes}).'))

        if not apply_changes:
            self.stdout.write(self.style.WARNING('Dry-run complete. To apply changes re-run with --apply.'))
