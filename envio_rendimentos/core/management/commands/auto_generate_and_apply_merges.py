import json
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from core.models import Credor


class Command(BaseCommand):
    help = "Gera mapping automático para merges e aplica-os (prefere registro já capitalizado)."

    def add_arguments(self, parser):
        parser.add_argument('--mapping-out', help='Arquivo JSON de saída com o mapping gerado', default='core/management/merge_map_generated.json')
        parser.add_argument('--dry-run', action='store_true', help='Gera mapping e faz somente dry-run dos merges')

    def handle(self, *args, **options):
        out_file = options.get('mapping_out')
        # Resolve path relative to project base dir if necessário
        if not os.path.isabs(out_file):
            out_file = os.path.join(settings.BASE_DIR, out_file)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        dry = options.get('dry_run')

        # Agrupa por nome normalizado (primeira maiúscula, resto minúsculas)
        groups = {}
        for c in Credor.objects.all():
            normalized = (str(c.nome).strip().lower().capitalize()) if c.nome else ''
            groups.setdefault(normalized, []).append(c)

        mapping = {}
        for normalized, items in groups.items():
            if len(items) <= 1:
                continue
            # Preferir item já no formato normalized
            target = None
            for c in items:
                if c.nome == normalized:
                    target = c
                    break
            if not target:
                # fallback: escolher o menor id
                target = min(items, key=lambda x: x.id)

            sources = [c.id for c in items if c.id != target.id]
            if sources:
                mapping[str(target.id)] = sources

        if not mapping:
            self.stdout.write(self.style.SUCCESS('Nenhum conflito encontrado. Nada a fazer.'))
            return

        # Salvar mapping
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f'Mapping gerado em: {out_file}'))

        # Executar dry-run do merge
        self.stdout.write('Executando dry-run do merge...')
        call_command('merge_credores', '--mapping', out_file, '--dry-run')

        if dry:
            self.stdout.write(self.style.SUCCESS('Dry-run solicitado; não aplicando merges.'))
            return

        # Aplicar merges
        self.stdout.write('Aplicando merges...')
        call_command('merge_credores', '--mapping', out_file, '--apply')
        self.stdout.write(self.style.SUCCESS('Merges aplicados com sucesso.'))
