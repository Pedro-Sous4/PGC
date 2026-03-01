from core.models import HistoricoPGC, EmailLog
from django.utils import timezone

created = 0
for h in HistoricoPGC.objects.all():
    try:
        if not EmailLog.objects.filter(historico=h).exists():
            EmailLog.objects.create(historico=h, credor=h.credor, numero_pgc=h.numero_pgc, status='pending')
            created += 1
    except Exception as e:
        print('ERROR', e)

print('EmailLogs created:', created)
