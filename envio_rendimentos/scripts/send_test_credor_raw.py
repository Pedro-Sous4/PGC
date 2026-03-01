import smtplib
import base64
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from django.conf import settings
from core.models import Credor

NAME = 'Thiago da Silva Correa'

credor = Credor.objects.filter(nome__iexact=NAME).first()
if not credor:
    print('Credor not found:', NAME)
    raise SystemExit(1)

to_addr = credor.email
from_addr = settings.DEFAULT_FROM_EMAIL
subject = f'Teste RAW UTF-8 para {credor.nome}'
plain = 'Este é um envio de teste gerado pelo script de debug.'
html = '<html><body><p>Este é um <b>envio de teste</b> gerado pelo script de debug.</p></body></html>'

# Build multipart message
msg = MIMEMultipart('alternative')
msg['From'] = formataddr((str(Header('Laghetto PGC', 'utf-8')), from_addr))
msg['To'] = to_addr
msg['Subject'] = Header(subject, 'utf-8')

# Plain part
part1 = MIMEText(plain.encode('utf-8'), 'plain', 'utf-8')
# Force base64 transfer encoding
from email import encoders
encoders.encode_base64(part1)
part1.replace_header('Content-Transfer-Encoding', 'base64')

# HTML part
part2 = MIMEText(html.encode('utf-8'), 'html', 'utf-8')
encoders.encode_base64(part2)
part2.replace_header('Content-Transfer-Encoding', 'base64')

msg.attach(part1)
msg.attach(part2)

# Print raw message for inspection
raw = msg.as_bytes()
print('--- RAW MESSAGE START ---')
print(raw.decode('utf-8', errors='replace'))
print('--- RAW MESSAGE END ---')

# Send via SMTP
try:
    server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=30)
    server.ehlo()
    if settings.EMAIL_USE_TLS:
        server.starttls()
        server.ehlo()
    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    server.sendmail(from_addr, [to_addr], raw)
    server.quit()
    print('SMTP send OK')
except Exception as e:
    print('SMTP send failed:')
    traceback.print_exc()
    raise
