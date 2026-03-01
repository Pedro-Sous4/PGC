import json
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Credor


class Command(BaseCommand):
    help = "Aplica merges de credores a partir de um arquivo JSON de mapeamento."

    def add_arguments(self, parser):
        parser.add_argument('--mapping', help='Arquivo JSON com o mapeamento.', default='core/management/merge_map.json')
        parser.add_argument('--dry-run', action='store_true', help='Mostra alterações sem aplicar')
        parser.add_argument('--apply', action='store_true', help='Aplica as mudanças')

    def handle(self, *args, **options):
        mapping_file = options.get('mapping')
        dry = options.get('dry_run')
        apply_changes = options.get('apply')

        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao ler mapping: {e}'))
            return

        # mapping should be {"target_id": [source_id1, source_id2, ...], ...}
        planned = []
        for target_str, sources in mapping.items():
            try:
                target_id = int(target_str)
            except ValueError:
                self.stdout.write(self.style.ERROR(f'Target inválido: {target_str} (deve ser id numérico)'))
                return

            try:
                target = Credor.objects.get(id=target_id)
            except Credor.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Target id não encontrado: {target_id}'))
                return

            for src in sources:
                if src == target_id:
                    continue
                try:
                    src_obj = Credor.objects.get(id=src)
                except Credor.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Source id não encontrado: {src}'))
                    continue
                planned.append((target, src_obj))

        if not planned:
            self.stdout.write(self.style.SUCCESS('Nenhuma ação planejada.'))
            return

        self.stdout.write('Plano de merge:')
        for t, s in planned:
            self.stdout.write(f"  {s.id} ('{s.nome}') -> {t.id} ('{t.nome}')")

        if dry or not apply_changes:
            self.stdout.write(self.style.SUCCESS('Dry-run concluído. Use --apply para efetivar as mudanças.'))
            return

        # Aplicar merges
        with transaction.atomic():
            for t, s in planned:
                # Reatribuir relacionados automaticamente usando introspecção
                for rel in s._meta.related_objects:
                    accessor = rel.get_accessor_name()
                    rel_qs = getattr(s, accessor).all()
                    if rel_qs.exists():
                        field_name = rel.field.name
                        rel_qs.update(**{field_name: t})

                # Remover o registro fonte
                s.delete()

        self.stdout.write(self.style.SUCCESS('Merges aplicados com sucesso.'))
