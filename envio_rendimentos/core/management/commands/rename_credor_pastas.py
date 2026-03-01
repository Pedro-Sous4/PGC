import os
from django.core.management.base import BaseCommand
from django.conf import settings
from core.scripts.renomear_pastas_credor import normalizar_nome_pasta, renomear_pastas_pgc, renomear_pastas_pgc as _dummy


class Command(BaseCommand):
    help = "Renomeia pastas de credores em MEDIA_ROOT/PGC para o padrão de capitalização."

    def add_arguments(self, parser):
        parser.add_argument('--pgc', type=int, help='Número do PGC para processar (padrão: todos)')
        parser.add_argument('--dry-run', action='store_true', help='Mostra mudanças sem aplicar')
        parser.add_argument('--apply', action='store_true', help='Aplica as mudanças')

    def handle(self, *args, **options):
        pgc = options.get('pgc')
        dry = options.get('dry_run')
        apply_changes = options.get('apply')

        base = os.path.join(settings.MEDIA_ROOT, 'PGC')
        if not os.path.isdir(base):
            self.stdout.write(self.style.ERROR(f'Pasta {base} não encontrada.'))
            return

        targets = []
        if pgc:
            base_pgc = os.path.join(base, str(pgc))
            if not os.path.isdir(base_pgc):
                self.stdout.write(self.style.ERROR(f'PGC {pgc} não encontrado em {base_pgc}'))
                return
            targets.append(base_pgc)
        else:
            for entry in os.listdir(base):
                path = os.path.join(base, entry)
                if os.path.isdir(path):
                    targets.append(path)

        planned = []
        for base_pgc in targets:
            for pasta_atual in os.listdir(base_pgc):
                caminho_atual = os.path.join(base_pgc, pasta_atual)
                if not os.path.isdir(caminho_atual):
                    continue
                if pasta_atual.upper() in ['MINIMO', 'TEMP', 'TMP']:
                    continue
                nome_normalizado = normalizar_nome_pasta(pasta_atual)
                if pasta_atual != nome_normalizado:
                    planned.append((caminho_atual, os.path.join(base_pgc, nome_normalizado)))

        if not planned:
            self.stdout.write(self.style.SUCCESS('Nenhuma pasta precisa ser renomeada.'))
            return

        self.stdout.write('Alterações planejadas:')
        for old, new in planned:
            self.stdout.write(f"  '{old}' -> '{new}'")

        if dry or not apply_changes:
            self.stdout.write(self.style.SUCCESS('Dry-run concluído. Use --apply para efetivar as mudanças.'))
            return

        # Aplicar renomeações
        for old, new in planned:
            if os.path.exists(new):
                self.stdout.write(self.style.WARNING(f"Destino já existe, pulando: {new}"))
                continue
            try:
                os.rename(old, new)
                self.stdout.write(self.style.SUCCESS(f"Renomeado: {old} -> {new}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao renomear {old}: {e}"))

        self.stdout.write(self.style.SUCCESS('Renomeação concluída.'))
