import os
import sys
# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','envio_rendimentos.settings')
import django
django.setup()
from core.utils_progress import init_progress, log_progress
import requests

rid = init_progress()
log_progress(rid, '✅ Log de teste 1')
log_progress(rid, '⚠️ Log de teste 2 (warning)')
log_progress(rid, '❌ Log de teste 3 (error)')

print('Request id:', rid)

r = requests.get(f'http://127.0.0.1:8000/lgm/status/{rid}/')
print('GET status:', r.status_code)
try:
    print('JSON:', r.json())
except Exception as e:
    print('Erro ao parsear JSON:', e)

# raw store from utils
from core.utils_progress import get_errors, get_progress
print('Store logs:', get_progress(rid).get('logs'))
print('Errors persisted path exists?', os.path.exists(os.path.join('arquivos_gerados','processing',rid,'errors.json')))
