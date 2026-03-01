from django.test import Client
from django.contrib.auth import get_user_model
from core.models import Credor, HistoricoPGC

c = Client()
User = get_user_model()
u = User.objects.filter(is_active=True).first()
if not u:
    print('NO_USER')
    raise SystemExit
cred = Credor.objects.first()
if not cred:
    print('NO_CREDOR')
    raise SystemExit

c.force_login(u)
resp = c.post(f'/credor/{cred.id}/rendimentos/adicionar/', {'periodo':'05/2026','valor':'R$ 10,00','numero_pgc':'123'})
print('POST', resp.status_code)
print(list(HistoricoPGC.objects.filter(credor=cred, periodo='05/2026').values_list('id','numero_pgc','valor_total')))
