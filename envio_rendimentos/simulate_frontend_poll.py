import time
import requests
import sys

BASE = "http://localhost:8000"
# Use latest known request_id (you can change to a new one after upload)
REQUEST_ID = "0a1ea73a-c569-497c-b31d-c68e998d269e"

seen = 0

print(f"Simulando polling para /laghetto-sports/status/{REQUEST_ID}/\n")
for _ in range(10):
    try:
        r = requests.get(f"{BASE}/laghetto-sports/status/{REQUEST_ID}/", timeout=5)
        r.raise_for_status()
        j = r.json()
    except Exception as e:
        print(f"[Poll] Erro: {e}")
        time.sleep(1.5)
        continue

    print(f"[Poll] status={j.get('status')} percent={j.get('percent')} processed={j.get('processed')}/{j.get('total_credores')}")

    logs = j.get('logs') or []
    if isinstance(logs, list) and len(logs) > seen:
        for log in logs[seen:]:
            t = log.get('time') or ''
            msg = log.get('msg') or str(log)
            tp = log.get('type') or 'info'
            print(f"[Log][{tp}][{t}] {msg}")
        seen = len(logs)
    else:
        print(f"[Poll] Nenhum log novo (total={len(logs)})")

    if j.get('status') in ('completed', 'error'):
        print("[Poll] Processamento finalizado — saindo")
        break

    time.sleep(1.5)

print('\nSimulação completa')
