import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from email import encoders
from django.conf import settings
from core.models import Credor

NAME = 'Thiago da Silva Correa'
credor = Credor.objects.filter(nome__iexact=NAME).first()
if not credor:
    print('Credor not found:', NAME)
    raise SystemExit(1)

to_addr = credor.email
from_addr = settings.DEFAULT_FROM_EMAIL
subject = f'Teste QP UTF-8 para {credor.nome}'
plain = 'Este é um envio de teste gerado pelo script de debug.'
html = '<html><body><p>Este é um <b>envio de teste</b> gerado pelo script de debug.</p></body></html>'

msg = MIMEMultipart('alternative')
msg['From'] = formataddr((str(Header('Laghetto PGC', 'utf-8')), from_addr))
msg['To'] = to_addr
msg['Subject'] = Header(subject, 'utf-8')

# Create parts as unicode (no pre-encoding)
part1 = MIMEText(plain, 'plain', 'utf-8')
part2 = MIMEText(html, 'html', 'utf-8')

# Force quoted-printable transfer encoding
encoders.encode_quopri(part1)
encoders.encode_quopri(part2)
part1.replace_header('Content-Transfer-Encoding', 'quoted-printable')
part2.replace_header('Content-Transfer-Encoding', 'quoted-printable')

msg.attach(part1)
msg.attach(part2)

raw = msg.as_bytes()
print('--- RAW QP MESSAGE START ---')
print(raw.decode('utf-8', errors='replace'))
print('--- RAW QP MESSAGE END ---')

try:
    server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=30)
    server.ehlo()
    if settings.EMAIL_USE_TLS:
        server.starttls()
        server.ehlo()
    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    server.sendmail(from_addr, [to_addr], raw)
    server.quit()
    print('SMTP QP send OK')
except Exception:
    print('SMTP QP send failed:')
    traceback.print_exc()
    raise
