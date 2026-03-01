from django.test import TestCase, Client
from django.contrib.auth.models import User
from core.models import Credor, Grupo
import io

class UploadEmailsTests(TestCase):
    def test_upload_handles_existing_with_different_format(self):
        # cria usuário e grupo
        user = User.objects.create_user(username='testuser', password='pw')
        grupo = Grupo.objects.create(nome='Grupo 1')

        # cria credor com formatação diferente
        credor = Credor.objects.create(nome='Joao da Silva', email='old@example.com', grupo=grupo)

        client = Client()
        logged = client.login(username='testuser', password='pw')
        self.assertTrue(logged)

        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_bytes = b'nome,email,grupo\nJOAO DA SILVA,new@example.com,Grupo 1\n'
        uploaded = SimpleUploadedFile('test.csv', csv_bytes, content_type='text/csv')
        response = client.post('/upload-emails/', {'file': uploaded}, follow=True)

        # o redirect deve ocorrer para a mesma página (200 após follow)
        self.assertEqual(response.status_code, 200)

        # garante que não foram criados duplicados e que o email foi atualizado
        credores = Credor.objects.filter(nome__icontains='Joao da Silva')
        self.assertEqual(credores.count(), 1)
        credor.refresh_from_db()
        self.assertEqual(credor.email, 'new@example.com')
