import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'envio_rendimentos.settings')
import django
django.setup()

from core.models import Credor, EmailLog

cred = Credor.objects.filter(nome__iexact='Thiago da Silva Correa').first()
if not cred:
    print('Credor not found')
else:
    logs = EmailLog.objects.filter(credor=cred).order_by('-last_attempt_at')[:5]
    if not logs:
        print('No EmailLog entries found for credor')
    else:
        for l in logs:
            print('Log:', l.id, l.status, l.attempts, l.last_attempt_at, l.error_message)
