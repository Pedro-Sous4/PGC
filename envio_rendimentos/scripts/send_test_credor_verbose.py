import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'envio_rendimentos.settings')
import django
django.setup()

from django.conf import settings
from django.core.mail import EmailMessage
from core.models import Credor

NAME = 'Thiago da Silva Correa'
credor = Credor.objects.filter(nome__iexact=NAME).first()
if not credor:
    print('Credor not found:', NAME)
    sys.exit(1)

print('Found', credor.nome, credor.email)
numero_pgc = str(credor.historicos.order_by('-data_envio').first().numero_pgc).zfill(3) if credor.historicos.exists() else '015'
base_pgc = os.path.join(settings.MEDIA_ROOT, 'PGC', numero_pgc)
print('PGC base:', base_pgc)

from core.utils import encontrar_pasta_case_insensitive
pasta_credor = encontrar_pasta_case_insensitive(base_pgc, credor.nome)
print('Pasta encontrada:', pasta_credor)

if not pasta_credor:
    print('Pasta credor não encontrada, abortando send.')
    raise SystemExit(1)

arquivos = [os.path.join(pasta_credor, f) for f in os.listdir(pasta_credor) if f.endswith('.xlsx')]
print('Attachments:', arquivos)

assunto = f'Teste de envio para {credor.nome} (verbose)'
corpo = 'Teste (verbose)'
email = EmailMessage(assunto, corpo, settings.DEFAULT_FROM_EMAIL, [credor.email])
email.encoding = 'utf-8'
for arq in arquivos:
    email.attach_file(arq)

try:
    print('Attempting send...')
    res = email.send(fail_silently=False)
    print('send() returned:', res)
except Exception as e:
    import traceback
    print('Exception during send:')
    traceback.print_exc()
    print('Exception type:', type(e))

print('Done')
