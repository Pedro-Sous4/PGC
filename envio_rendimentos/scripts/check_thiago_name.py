import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','envio_rendimentos.settings')
import django
django.setup()
from core.models import Credor
c=Credor.objects.filter(nome__icontains='Thiago da Silva Correa').first()
print('repr nome:',repr(c.nome))
print('upper repr:',repr(c.nome.upper()))
