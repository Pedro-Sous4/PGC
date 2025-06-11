from django.core.management.base import BaseCommand
from django.conf import settings
import os
import pandas as pd
from core.utils import normalizar_colunas_simples

class Command(BaseCommand):
    help = 'Gera o arquivo EXTRATO.xlsx a partir da aba EXTRATO CREDOR da planilha original (TEMPORARIOS)'

    def add_arguments(self, parser):
        parser.add_argument('numero_pgc', type=int, help='Número do PGC (ex: 26)')

    def handle(self, *args, **kwargs):
        numero_pgc = kwargs['numero_pgc']
        nome_arquivo = f"PGC_{numero_pgc}_ORIGINAL.xlsx"
        caminho = os.path.join(settings.MEDIA_ROOT, 'TEMPORARIOS', nome_arquivo)

        if not os.path.exists(caminho):
            self.stderr.write(self.style.ERROR(f"Arquivo não encontrado: {caminho}"))
            return

        try:
            planilhas = pd.ExcelFile(caminho)
            abas = planilhas.sheet_names

            # Encontrar aba que contenha "extrato" e "credor" (ou variantes)
            aba_encontrada = next(
                (nome for nome in abas if "extrato" in nome.lower() and "credor" in nome.lower()),
                None
            )
            if not aba_encontrada:
                aba_encontrada = next(
                    (nome for nome in abas if "exrato" in nome.lower() and "credor" in nome.lower()),
                    None
                )

            if not aba_encontrada:
                self.stderr.write(self.style.ERROR(f"Aba de extrato credor não encontrada nas abas: {abas}"))
                return

            df = pd.read_excel(planilhas, sheet_name=aba_encontrada)
            df_normalizado = normalizar_colunas_simples(df)

            pasta_saida = os.path.join(settings.MEDIA_ROOT, 'PGC', str(numero_pgc))
            os.makedirs(pasta_saida, exist_ok=True)
            caminho_saida = os.path.join(pasta_saida, "EXTRATO.xlsx")
            df_normalizado.to_excel(caminho_saida, index=False)

            self.stdout.write(self.style.SUCCESS(f"EXTRATO.xlsx gerado com sucesso em: {caminho_saida}"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Erro ao processar planilha: {e}"))
