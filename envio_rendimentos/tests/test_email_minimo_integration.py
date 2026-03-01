from django.test import TestCase, override_settings
from django.core import mail
from django.conf import settings
import os
import pandas as pd
from core.models import Credor, HistoricoPGC
from core.utils import enviar_email_com_arquivos


@override_settings(
    MEDIA_ROOT=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tmp_media'),
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
)
class EmailMinimoIntegrationTest(TestCase):
    def setUp(self):
        # create media PGC folder and minimo
        media = settings.MEDIA_ROOT
        pgc_dir = os.path.join(media, 'PGC', '15')
        os.makedirs(pgc_dir, exist_ok=True)

        rows = [
            {
                'CREDOR': '123 - João Silva (CAPTADOR)',
                'MINIMO/FIXO GARANTIDO PARA EMISSAO NF': 250.75,
                # empresa comes from MINIMO.xlsx in the format "{numero} - {NOME EMPRESA}" used for lookup
                'EMPRESA EMISSÃO NF': '24 - LGM FILIAL',
                'CNPJ': '11.222.333/0001-44'
            }
        ]
        caminho = os.path.join(pgc_dir, 'minimo.xlsx')
        pd.DataFrame(rows).to_excel(caminho, index=False)

        # Create a Credor and HistoricoPGC
        self.credor = Credor.objects.create(nome='123 - João Silva (CAPTADOR)', email='joao@example.com')
        self.historico = HistoricoPGC.objects.create(credor=self.credor, numero_pgc=15, periodo='02/2026', valor_total=0)

        # Create folder for credor with one dummy xlsx to satisfy attachments logic
        base_pgc = os.path.join(media, 'PGC', str(self.historico.numero_pgc).zfill(3))
        # The system uses folder named with display name uppercased; create a matching folder name
        pasta = os.path.join(os.path.dirname(pgc_dir), str(int(15)), '123 - JOÃO SILVA (CAPTADOR)')
        # But to be safe, create folder directly under PGC/15 with name equal to normalized one
        pasta = os.path.join(os.path.dirname(pgc_dir), '15', '123 - JOÃO SILVA (CAPTADOR)')
        os.makedirs(pasta, exist_ok=True)
        dummy_xlsx = os.path.join(pasta, 'dummy.xlsx')
        pd.DataFrame({'a': [1]}).to_excel(dummy_xlsx, index=False)

    def test_email_contains_info_minimo(self):
        # ensure outbox empty
        mail.outbox = []
        result = enviar_email_com_arquivos(self.credor)
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        # Check that the expected phrase is in the body
        self.assertIn('Mínimo garantido', message.body)
        self.assertIn('11.222.333/0001-44', message.body)
        self.assertIn('LGM FILIAL', message.body)
        # Certifica que o prefixo numérico (ex.: "24 - ") não aparece na exibição do e-mail
        self.assertNotIn('24 -', message.body)
