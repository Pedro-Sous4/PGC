# Run the processor synchronously to observe exceptions and logs directly
import sys
import time
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

FILE = r'envio_rendimentos\arquivos_gerados\tmp_lgm\LGM_dffa33ca-dae7-4629-81a8-7e8fe72fc15e_test_lgm.xlsx'
if not os.path.exists(FILE):
    print('Arquivo de teste não encontrado:', FILE)
    raise SystemExit(1)

request_id = init_progress()
log_progress(request_id, '✅ Teste SYNC: iniciando processamento')

try:
    processar_pgc_lgm(request_id, FILE)
except Exception as e:
    print('Exceção não capturada em processar_pgc_lgm:', e)
    import traceback
    traceback.print_exc()

print('Final do run sync; status:')
print(json.dumps(get_progress(request_id), indent=2, ensure_ascii=False))

proc_dir = os.path.join('envio_rendimentos', 'arquivos_gerados', 'processing', request_id)
print('Processing dir exists:', os.path.exists(proc_dir))
if os.path.exists(proc_dir):
    for root, dirs, files in os.walk(proc_dir):
        for name in files:
            print(' -', os.path.join(root, name))
