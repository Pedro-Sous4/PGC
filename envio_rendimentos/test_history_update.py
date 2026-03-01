from django.test import Client
from django.contrib.auth import get_user_model
from core.models import Credor, Rendimento, HistoricoPGC

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
print('USER', u.username, 'CREDOR', cred.id, cred.nome)

c.force_login(u)

periodo = '03/2026'
# 1) adicionar 2000
resp = c.post(f'/credor/{cred.id}/rendimentos/adicionar/', {'periodo': periodo, 'valor': 'R$ 2.000,00'})
print('ADD 2000 status', resp.status_code)
print('Historicos:', list(HistoricoPGC.objects.filter(credor=cred, periodo=periodo).values_list('id','numero_pgc','valor_total')))

# 2) adicionar 500
resp = c.post(f'/credor/{cred.id}/rendimentos/adicionar/', {'periodo': periodo, 'valor': 'R$ 500,00'})
print('ADD 500 status', resp.status_code)
print('Historicos after add:', list(HistoricoPGC.objects.filter(credor=cred, periodo=periodo).values_list('id','numero_pgc','valor_total')))

# 3) editar primeiro rendimento para 1000
r = Rendimento.objects.filter(Credor=cred, periodo=periodo).order_by('id').first()
print('Editing rendimento id', r.id, 'old valor', r.valor)
resp = c.post(f'/rendimentos/{r.id}/editar/', {'periodo': periodo, 'valor': 'R$ 1.000,00'})
print('EDIT status', resp.status_code)
print('Historicos after edit:', list(HistoricoPGC.objects.filter(credor=cred, periodo=periodo).values_list('id','numero_pgc','valor_total')))

# 4) delete one rendimento
r2 = Rendimento.objects.filter(Credor=cred, periodo=periodo).order_by('id').first()
print('Deleting rendimento id', r2.id)
resp = c.get(f'/rendimentos/{r2.id}/excluir/')
print('DELETE status', resp.status_code)
print('Historicos after delete:', list(HistoricoPGC.objects.filter(credor=cred, periodo=periodo).values_list('id','numero_pgc','valor_total')))
