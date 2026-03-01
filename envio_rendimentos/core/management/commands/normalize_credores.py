from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Credor


def _normalized_name(name: str) -> str:
    if not name:
        return ""
    cleaned = str(name).strip()
    return cleaned.lower().capitalize()


class Command(BaseCommand):
    help = "Normaliza nomes de Credor no banco (primeira letra maiúscula, demais minúsculas)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Mostra alterações sem aplicar')
        parser.add_argument('--apply', action='store_true', help='Aplica as mudanças')

    def handle(self, *args, **options):
        dry = options['dry_run']
        apply_changes = options['apply']

        credores = list(Credor.objects.all())
        mapping = {}
        conflicts = {}

        for c in credores:
            new = _normalized_name(c.nome)
            mapping.setdefault(new, []).append(c)

        # Detectar conflitos: mesmo novo nome para múltiplos registros distintos
        for new, items in mapping.items():
            if len(items) > 1:
                conflicts[new] = items

        if conflicts:
            self.stdout.write(self.style.WARNING('Foram detectados possíveis conflitos ao normalizar nomes:'))
            for new, items in conflicts.items():
                ids = ', '.join(str(i.id) for i in items)
                nomes = ' | '.join(i.nome for i in items)
                self.stdout.write(f"  -> '{new}': IDs [{ids}] - nomes: {nomes}")
            self.stdout.write(self.style.ERROR('Resolva conflitos antes de aplicar. Use --dry-run para revisar.'))
            return

        # Mostrar plano
        self.stdout.write('Plano de normalização:')
        for new, items in mapping.items():
            for c in items:
                if c.nome != new:
                    self.stdout.write(f"  {c.id}: '{c.nome}' -> '{new}'")

        if dry or not apply_changes:
            self.stdout.write(self.style.SUCCESS('Dry-run concluído. Use --apply para efetivar as mudanças.'))
            return

        # Aplicar mudanças dentro de transação
        with transaction.atomic():
            for new, items in mapping.items():
                for c in items:
                    if c.nome != new:
                        c.nome = new
                        c.save()

        self.stdout.write(self.style.SUCCESS('Normalização aplicada com sucesso.'))
