# This script is meant to be executed via `python manage.py shell < local_run_lgm_django.py`
# It runs inside Django shell so settings are already configured.
import time
import os
import json
import threading

from core.utils_progress import init_progress, get_progress, log_progress
from core.utils_lgm import processar_pgc_lgm

FILE = r'envio_rendimentos\arquivos_gerados\tmp_lgm\LGM_dffa33ca-dae7-4629-81a8-7e8fe72fc15e_test_lgm.xlsx'
if not os.path.exists(FILE):
    print('Arquivo de teste não encontrado:', FILE)
    raise SystemExit(1)

print('Inicializando progresso e disparando processador (Django shell)...')
request_id = init_progress()
log_progress(request_id, '✅ Teste (Django shell): iniciando processamento (thread)')

th = threading.Thread(target=processar_pgc_lgm, args=(request_id, FILE), daemon=True)
th.start()

start = time.time()
max_wait = 600
seen_logs = 0

print('Polling local progress store... (request_id=', request_id, ')')
while True:
    p = get_progress(request_id)
    if not p:
        print('Progresso não encontrado (store limpou?)')
        break
    status = p.get('status')
    percent = p.get('percent')
    processed = p.get('processed')
    total = p.get('total')
    current = p.get('current_credor')

    logs = p.get('logs', [])
    if len(logs) > seen_logs:
        for l in logs[seen_logs:]:
            print(f"[{l.get('time')}] {l.get('msg')}")
        seen_logs = len(logs)

    print(f"STATUS={status} percent={percent} processed={processed}/{total} current={current}")

    if status in ('completed', 'error'):
        print('Finalizado com status:', status)
        break

    if time.time() - start > max_wait:
        print('Timeout atingido')
        break

    time.sleep(2)

proc_dir = os.path.join('envio_rendimentos', 'arquivos_gerados', 'processing', request_id)
print('Processing dir exists:', os.path.exists(proc_dir))
if os.path.exists(proc_dir):
    for root, dirs, files in os.walk(proc_dir):
        for name in files:
            print(' -', os.path.join(root, name))

print('\nStatus final:')
print(json.dumps(get_progress(request_id), indent=2, ensure_ascii=False))
print('\nFim do script')
