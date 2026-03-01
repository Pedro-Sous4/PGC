import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'envio_rendimentos.settings')

import django
django.setup()

from core.models import Credor, Grupo

# Limpa dados de teste
Grupo.objects.filter(nome='Teste Grupo').delete()
Credor.objects.filter(nome__icontains='Teste Credor').delete()

g = Grupo.objects.create(nome='Teste Grupo')
cred, created = Credor.get_or_create_by_nome('Teste Credor', defaults={'email':'old@example.com', 'grupo':g})
print('First create:', cred.nome, created)
# Attempt again with different formatting
cred2, created2 = Credor.get_or_create_by_nome('teste credor', defaults={'email':'new@example.com', 'grupo':g})
print('Second call:', cred2.nome, created2, 'email now:', cred2.email)
print('Total credores with name like:', Credor.objects.filter(nome__icontains='Teste Credor').count())
