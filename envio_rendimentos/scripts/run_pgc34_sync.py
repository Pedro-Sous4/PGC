# Synchronous runner for processing a real PGC file (PGC 34)
import sys
import os
import json

sys.path.append(r'C:\PGC\envio_rendimentos\envio_rendimentos')
sys.path.append(r'C:\PGC\envio_rendimentos')
import os as _os
_os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
import django
django.setup()

from core.utils_progress import init_progress, get_progress, log_progress
from core.utils_lgm import processar_pgc_lgm

FILE = r'envio_rendimentos\arquivos_gerados\PGC\PGC 34.xlsx'
if not os.path.exists(FILE):
    print('Arquivo não encontrado:', FILE)
    raise SystemExit(1)

request_id = init_progress()
log_progress(request_id, '✅ Iniciando processamento PGC 34')

try:
    processar_pgc_lgm(request_id, FILE)
except Exception as e:
    print('Exceção não capturada em processar_pgc_lgm:', e)
    import traceback
    traceback.print_exc()

print('Final do processamento; status:')
print(json.dumps(get_progress(request_id), indent=2, ensure_ascii=False))

proc_dir = os.path.join('envio_rendimentos', 'arquivos_gerados', 'processing', request_id)
print('Processing dir:', proc_dir)
print('Processing dir exists:', os.path.exists(proc_dir))
if os.path.exists(proc_dir):
    for root, dirs, files in os.walk(proc_dir):
        for name in files:
            print(' -', os.path.join(root, name))

# List generated files under arquivos_gerados/PGC/PGC 34 output
base_out = r'envio_rendimentos\arquivos_gerados\PGC\34'
print('\nListing candidate output directories under arquivos_gerados/PGC:')
pgc_root = r'envio_rendimentos\arquivos_gerados\PGC'
for root, dirs, files in os.walk(pgc_root):
    level = root.replace(pgc_root, '')
    if 'PGC 34' in root or root.endswith('34') or 'PGC\34' in root:
        print(root)
        for name in files:
            print('  *', name)
