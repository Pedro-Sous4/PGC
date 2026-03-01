from django.test import Client
from core.models import Credor, Rendimento
from django.contrib.auth import get_user_model

c = Client()
User = get_user_model()
user = User.objects.filter(is_active=True).first()
if not user:
    print('NO_USER')
else:
    credor = Credor.objects.first()
    if not credor:
        print('NO_CREDOR')
    else:
        print('CREDOR', credor.id, credor.nome)
        c.force_login(user)
        resp = c.post(f'/credor/{credor.id}/rendimentos/adicionar/', {'periodo': '01/2026', 'valor': 'R$ 1.234,56'})
        print('STATUS', resp.status_code)
        try:
            loc = resp['Location']
        except Exception:
            loc = None
        print('LOCATION', loc)
        r = Rendimento.objects.filter(Credor=credor).order_by('-id').first()
        if r:
            print('SAVED', r.id, r.periodo, str(r.valor))
        else:
            print('NOT_SAVED')
