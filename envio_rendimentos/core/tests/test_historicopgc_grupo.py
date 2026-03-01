from django.test import TestCase
from core.models import Credor, Grupo, HistoricoPGC
from core.services.pgc_processor.process_pgcs import process_credor
import pandas as pd
from datetime import datetime

class HistoricoGrupoTestCase(TestCase):
    def test_process_credor_sets_grupo_on_credor_and_historico(self):
        grupo, _ = Grupo.objects.get_or_create(nome='LGM')

        # Create a Credor
        credor, _ = Credor.get_or_create_by_nome('ACME LTDA', defaults={'periodo': '01/2026'})

        # Prepare a minimal base_df that matches the normalized name
        base_df = pd.DataFrame({
            'credor_normalizado': ['acme ltda'],
            'valor_original': [100.0]
        })

        # Call process_credor with pgc_prefix to simulate LGM
        process_credor(
            credor=credor,
            numero_pgc=123,
            base_df=base_df,
            pgc_prefix='LGM',
            pasta_credores='.',
            nome_original='ACME LTDA'
        )

        credor.refresh_from_db()
        self.assertIsNotNone(credor.grupo)
        self.assertEqual(credor.grupo.nome, 'LGM')

        historicos = HistoricoPGC.objects.filter(credor=credor, numero_pgc=123)
        self.assertTrue(historicos.exists())
        hist = historicos.first()
        self.assertIsNotNone(hist.grupo)
        self.assertEqual(hist.grupo.nome, 'LGM')
