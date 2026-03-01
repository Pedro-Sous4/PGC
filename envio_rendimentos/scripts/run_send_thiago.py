import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'envio_rendimentos.settings')
import django
django.setup()

from django.conf import settings
from core.models import Credor
from core.utils import enviar_email_com_arquivos

print('DEFAULT_FROM_EMAIL:', getattr(settings, 'DEFAULT_FROM_EMAIL', None))
print('EMAIL_BACKEND:', getattr(settings, 'EMAIL_BACKEND', None))
print('EMAIL_HOST:', getattr(settings, 'EMAIL_HOST', None))

NAME = 'Thiago da Silva Correa'
credor = Credor.objects.filter(nome__iexact=NAME).first()
if not credor:
    print('Credor not found:', NAME)
else:
    print('Found Credor id=', credor.id, 'nome=', credor.nome, 'email=', credor.email)
    ok = enviar_email_com_arquivos(credor)
    print('Email send result:', ok)
