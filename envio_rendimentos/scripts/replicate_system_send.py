from django.conf import settings
from core.models import Credor, HistoricoPGC, EmailLog
from core.utils import carregar_mensagens, obter_minimo_garantido_para_credor
from django.core.mail import EmailMessage
from django.utils import timezone as dj_timezone
import os, traceback

NAME = 'Thiago da Silva Correa'
PGC_NUMBER = 15

credor = Credor.objects.filter(nome__iexact=NAME).first()
if not credor:
    print('Credor not found:', NAME)
    raise SystemExit(1)

historico = credor.historicos.filter(numero_pgc=PGC_NUMBER).order_by('-id').first()
if not historico:
    print('Historico not found for PGC', PGC_NUMBER)
    raise SystemExit(1)

mensagens = carregar_mensagens()
mensagem_padrao = mensagens.get('mensagem', 'Relatórios PGC {historico}')
info_minimo_padrao = mensagens.get('info_minimo', '')
mensagem_personalizada = mensagem_padrao
info_minimo_template = info_minimo_padrao

# build info_minimo
info_minimo_dict = obter_minimo_garantido_para_credor(credor.nome, str(PGC_NUMBER))
if info_minimo_dict:
    valor = float(info_minimo_dict.get('valor', 0) or 0)
    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    # Mostrar empresa sem prefixo numérico no texto (sem alterar o valor original)
    from core.utils import format_empresa_para_exibicao

    info_minimo_texto = info_minimo_template.format(
        valor_formatado=valor_formatado,
        empresa=format_empresa_para_exibicao(info_minimo_dict.get('empresa', '')),
        cnpj=info_minimo_dict.get('cnpj', ''),
    )
else:
    info_minimo_texto = ''

corpo_email = mensagem_personalizada.format(
    credor=credor,
    historico=historico,
    info_minimo=info_minimo_texto,
)

# attachments
pgc_str = str(int(PGC_NUMBER))
pasta_credor = os.path.join(settings.MEDIA_ROOT, 'PGC', pgc_str, credor.nome_pasta())
anexos = []
if not os.path.isdir(pasta_credor):
    print('Pasta do credor não existe:', pasta_credor)
else:
    anexos = [os.path.join(pasta_credor, f) for f in os.listdir(pasta_credor) if f.lower().endswith('.xlsx')]
    print('Anexos encontrados:', anexos)

# ensure EmailLog exists
log, created = EmailLog.objects.get_or_create(historico=historico, credor=credor, defaults={
    'numero_pgc': PGC_NUMBER,
    'status': 'sending',
    'attempts': 1,
    'last_attempt_at': dj_timezone.now(),
})
if not created:
    log.status = 'sending'
    log.attempts = (log.attempts or 0) + 1
    log.last_attempt_at = dj_timezone.now()
    log.save()

print('Sending to', credor.email)
email = EmailMessage(f'Relatórios financeiros PGC {historico.numero_pgc}', corpo_email, settings.DEFAULT_FROM_EMAIL, [credor.email])
for arq in anexos or []:
    try:
        email.attach_file(arq)
    except Exception as e:
        print('Failed to attach', arq, e)

try:
    email.send(fail_silently=False)
    credor.enviado = True
    credor.data_envio = dj_timezone.now()
    credor.save(update_fields=['enviado', 'data_envio'])
    log.status = 'sent'
    log.sent_at = dj_timezone.now()
    log.error_message = None
    log.save()
    print('Sent OK')
except Exception as e:
    print('Send failed:')
    traceback.print_exc()
    try:
        credor.enviado = False
        credor.save(update_fields=['enviado'])
    except Exception:
        pass
    try:
        log.status = 'failed'
        log.error_message = str(e)
        log.save()
    except Exception:
        pass
    raise

print('Done')
