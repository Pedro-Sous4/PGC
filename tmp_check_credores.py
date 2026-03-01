import os, sys
sys.path.append(r'C:\PGC\envio_rendimentos\envio_rendimentos')
sys.path.append(r'C:\PGC\envio_rendimentos')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','settings')
import django
django.setup()
from core.models import Credor
print('Total credores:', Credor.objects.count())
for c in Credor.objects.filter(nome__icontains='ACME'):
    print('Found:', c.id, repr(c.nome), c.periodo)
