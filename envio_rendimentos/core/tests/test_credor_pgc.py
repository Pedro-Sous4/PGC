from django.test import TestCase
from core.models import Credor

class CredorPGCTest(TestCase):
    def test_protected_fields_not_overwritten_by_pgc(self):
        credor = Credor.objects.create(nome='Empresa Teste', email='orig@example.com', periodo='2020-01')

        result = credor.update_from_pgc({
            'nome': 'Outra Empresa',
            'email': 'new@example.com',
            'periodo': '2021-02'
        })

        # Nome e email não devem ser sobrescritos
        credor.refresh_from_db()
        self.assertEqual(credor.nome, 'Empresa Teste')
        self.assertEqual(credor.email, 'orig@example.com')
        # Periodo pode ser atualizado
        self.assertEqual(credor.periodo, '2021-02')
        # Resultado indica campos bloqueados
        self.assertIn('nome', result['blocked'])
        self.assertIn('email', result['blocked'])
        self.assertIn('periodo', result['updated'])

    def test_get_or_create_allows_protected_on_create(self):
        # Quando criado, defaults com campos protegidos devem ser aplicados
        credor, created = Credor.get_or_create_by_nome('Nova Empresa', defaults={'email': 'created@example.com', 'periodo': '2022-01'})
        self.assertTrue(created)
        self.assertEqual(credor.email, 'created@example.com')
        self.assertEqual(credor.periodo, '2022-01')

    def test_get_or_create_does_not_overwrite_protected_on_existing(self):
        credor = Credor.objects.create(nome='Empresa Existente', email='orig@ex.com')
        found, created = Credor.get_or_create_by_nome('Empresa Existente', defaults={'email': 'att@ex.com', 'periodo': '2030-01'})
        self.assertFalse(created)
        # email nao deve ter sido sobrescrito
        self.assertEqual(found.email, 'orig@ex.com')
        # periodo deve ter sido atualizado, pois nao e protegido
        self.assertEqual(found.periodo, '2030-01')

    def test_non_protected_fields_update(self):
        credor = Credor.objects.create(nome='Empresa Outra', periodo='2019-12')
        result = credor.update_from_pgc({'periodo': '2020-12'})
        credor.refresh_from_db()
        self.assertEqual(credor.periodo, '2020-12')
        self.assertIn('periodo', result['updated'])
        self.assertEqual(result['blocked'], [])

    def test_upload_emails_does_not_overwrite_protected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.urls import reverse
        from core.models import Grupo

        grupo = Grupo.objects.create(nome='Grupo A')
        credor = Credor.objects.create(nome='Empresa CSV', email='orig@csv.com')

        csv_content = 'nome,email,grupo\n"Empresa CSV",new@csv.com,Grupo A\n'
        f = SimpleUploadedFile('emails.csv', csv_content.encode('utf-8'), content_type='text/csv')

        client = self.client
        url = reverse('upload_emails')
        resp = client.post(url, {'file': f})
        self.assertEqual(resp.status_code, 302)  # redirect on success

        credor.refresh_from_db()
        self.assertEqual(credor.email, 'orig@csv.com')
