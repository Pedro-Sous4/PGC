from django.conf import settings
from core.models import Credor
from django.core.mail import EmailMessage
from django.utils import timezone as dj_timezone
import traceback

NAME = 'Thiago da Silva Correa'

print('DEFAULT_FROM_EMAIL:', getattr(settings, 'DEFAULT_FROM_EMAIL', None))
print('EMAIL_BACKEND:', getattr(settings, 'EMAIL_BACKEND', None))
print('EMAIL_HOST:', getattr(settings, 'EMAIL_HOST', None))

credor = Credor.objects.filter(nome__iexact=NAME).first()
if not credor:
    # try normalized match
    try:
        from core.utils import normalizar_nome_completo
        cname = normalizar_nome_completo(NAME)
        credor = Credor.objects.filter(nome__icontains=NAME).first() or Credor.objects.filter(nome__icontains=cname).first()
    except Exception:
        credor = Credor.objects.filter(nome__icontains=NAME).first()

if not credor:
    print('Credor not found:', NAME)
else:
    print('Found Credor id=', credor.id, 'nome=', credor.nome, 'email=', credor.email)
    assunto = f'Teste de envio para {credor.nome}'
    corpo = 'Este é um envio de teste gerado pelo script de debug.'
    # force UTF-8 encoding to avoid mojibake in recipients that mis-detect charset
    email = EmailMessage(assunto, corpo, settings.DEFAULT_FROM_EMAIL, [credor.email])
    try:
        email.encoding = 'utf-8'
        # also ensure explicit header for clients that rely on it
        if not isinstance(email.extra_headers, dict):
            email.extra_headers = {}
        email.extra_headers['Content-Type'] = 'text/plain; charset="utf-8"'
    except Exception:
        pass
    try:
        print('Attempting to send...')
        result = email.send(fail_silently=False)
        print('send() returned:', result)
        credor.enviado = True
        credor.data_envio = dj_timezone.now()
        credor.save(update_fields=['enviado', 'data_envio'])
        print('Credor marcado como enviado (enviado=True).')
    except Exception as e:
        print('Exception during send:')
        traceback.print_exc()
        try:
            credor.enviado = False
            credor.save(update_fields=['enviado'])
        except Exception:
            pass

print('Script finished.')
