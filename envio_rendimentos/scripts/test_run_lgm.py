import requests
import time
import os
import json

BASE = 'http://127.0.0.1:8000'
# Small test file present in repo
FILE = r'envio_rendimentos\arquivos_gerados\tmp_lgm\LGM_dffa33ca-dae7-4629-81a8-7e8fe72fc15e_test_lgm.xlsx'

if not os.path.exists(FILE):
    print('Arquivo de teste não encontrado:', FILE)
    raise SystemExit(1)

print('Fazendo upload do arquivo:', FILE)
with open(FILE, 'rb') as f:
    files = {'arquivo': (os.path.basename(FILE), f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    try:
        r = requests.post(BASE + '/lgm/', files=files, timeout=30)
    except Exception as e:
        print('Erro ao enviar POST /lgm/:', e)
        raise

print('Resposta do POST:', r.status_code, r.text[:500])
if r.status_code != 200:
    print('Upload falhou')
    raise SystemExit(1)

j = r.json()
request_id = j.get('request_id')
print('Request ID:', request_id)

if not request_id:
    print('Nenhum request_id retornado, abortando')
    raise SystemExit(1)

# Polling loop
start = time.time()
max_wait = 600  # seconds
errors_seen = None
credores_seen = None

print('Iniciando polling por status...')
while True:
    try:
        r = requests.get(BASE + f'/lgm/status/{request_id}/', timeout=10)
    except Exception as e:
        print('Erro ao consultar status:', e)
        time.sleep(2)
        continue

    if r.status_code == 404:
        print('[status] 404 - progresso ainda não inicializado')
        time.sleep(1)
        continue

    try:
        data = r.json()
    except Exception as e:
        print('Não foi possível parsear JSON do status:', e, r.text[:200])
        time.sleep(1)
        continue

    now = int(time.time() - start)
    logs = data.get('logs', [])
    last_log = logs[-1]['msg'] if logs else ''
    print(f'[{now:3}s] status={data.get("status")} percent={data.get("percent")} processed={data.get("processed")} total={data.get("total")} current_credor={data.get("current_credor")} last_log="{last_log[:80]}"')

    # fetch errors and credores to show changes
    try:
        er = requests.get(BASE + f'/lgm/errors/{request_id}/', timeout=5).json()
        cr = requests.get(BASE + f'/lgm/credores/{request_id}/', timeout=5).json()
    except Exception as e:
        print('Erro ao buscar errors/credores:', e)
        er = {'errors': []}
        cr = {'credores': {}}

    if er != errors_seen:
        print('  [errors] count=', len(er.get('errors', [])))
        errors_seen = er
    if cr != credores_seen:
        print('  [credores] count=', len(cr.get('credores', {}).keys()))
        credores_seen = cr

    if data.get('status') in ('completed', 'error'):
        print('Processamento finalizado com status:', data.get('status'))
        break

    if time.time() - start > max_wait:
        print('Timeout de espera atingido')
        break

    time.sleep(2)

print('Polling finalizado. Verificando arquivos em disk...')
proc_dir = os.path.join('envio_rendimentos', 'arquivos_gerados', 'processing', request_id)
print('Processing dir exists:', os.path.exists(proc_dir))
if os.path.exists(proc_dir):
    for root, dirs, files in os.walk(proc_dir):
        for name in files:
            print(' -', os.path.join(root, name))

print('\nResumo final do status:')
try:
    print(json.dumps(requests.get(BASE + f'/lgm/status/{request_id}/').json(), indent=2, ensure_ascii=False)[:2000])
except Exception as e:
    print('Erro ao obter status final:', e)

print('\nErros:')
try:
    print(json.dumps(requests.get(BASE + f'/lgm/errors/{request_id}/').json(), indent=2, ensure_ascii=False)[:2000])
except Exception as e:
    print('Erro ao obter errors:', e)

print('\nCredores:')
try:
    print(json.dumps(requests.get(BASE + f'/lgm/credores/{request_id}/').json(), indent=2, ensure_ascii=False)[:2000])
except Exception as e:
    print('Erro ao obter credores:', e)

print('\nFim do script')
