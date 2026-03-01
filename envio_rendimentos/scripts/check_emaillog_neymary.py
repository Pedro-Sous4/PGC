import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'envio_rendimentos.settings')
import django
django.setup()

from core.models import Credor, EmailLog

name = 'NEIMARY STEFANY AVILA PINTO'
cred = Credor.objects.filter(nome__iexact=name).first()
if not cred:
    print('Credor not found for name:', name)
else:
    logs = EmailLog.objects.filter(credor=cred).order_by('-last_attempt_at')[:10]
    if not logs:
        print('No EmailLog entries found for credor', cred.nome)
    else:
        for l in logs:
            print('Log:', l.id, 'status=', l.status, 'attempts=', l.attempts, 'last_attempt_at=', l.last_attempt_at, 'sent_at=', l.sent_at)
            if l.error_message:
                print('  error_message:', l.error_message)
