from core.models import EmailLog, HistoricoPGC
from django.db import connection

print('EmailLog model imported OK')

cursor = connection.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='core_emaillog'")
table_exists = bool(cursor.fetchall())
print('core_emaillog table exists:', table_exists)

# tenta criar um EmailLog de teste
try:
    h = HistoricoPGC.objects.first()
    if h:
        c = h.credor
        log, created = EmailLog.objects.get_or_create(historico=h, credor=c, defaults={'numero_pgc': h.numero_pgc or 0})
        print('EmailLog created/found:', log.id, 'Status:', log.status)
except Exception as e:
    print('ERROR:', e)
