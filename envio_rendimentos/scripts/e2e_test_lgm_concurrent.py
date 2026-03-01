import requests
import threading
import time
from pathlib import Path

BASE = 'http://192.168.1.105:8000'
FP = Path(__file__).parent / 'tmp' / 'test_lgm.xlsx'

SESSIONS = []
NUM = 5

# ensure file exists
if not FP.exists():
    raise SystemExit('Need test file at ' + str(FP))

results = []
lock = threading.Lock()


def worker(i):
    s = requests.Session()
    # login
    r = s.get(BASE + '/accounts/login/')
    csrftoken = s.cookies.get('csrftoken')
    payload = {'username':'testuser','password':'testpass','csrfmiddlewaretoken':csrftoken}
    headers = {'Referer': BASE + '/accounts/login/'}
    s.post(BASE + '/accounts/login/', data=payload, headers=headers)

    with open(FP,'rb') as f:
        files = {'arquivo': ('test_lgm.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        r = s.post(BASE + '/lgm/', files=files, headers={'X-Requested-With':'XMLHttpRequest','Accept':'application/json'})
        try:
            j = r.json()
        except Exception as e:
            with lock:
                results.append((i, 'post_failed', r.status_code, r.text[:200]))
            return
        rid = j.get('request_id')
        with lock:
            results.append((i, 'started', rid))

        # poll status until completed
        for _ in range(60):
            rp = s.get(f'{BASE}/lgm/status/{rid}/', headers={'Accept':'application/json','X-Requested-With':'XMLHttpRequest'})
            try:
                js = rp.json()
            except Exception:
                time.sleep(0.5); continue
            if js.get('status') in ('completed','error'):
                with lock:
                    results.append((i, 'done', js.get('status')))
                return
            time.sleep(0.5)
        with lock:
            results.append((i, 'timeout'))


threads=[]
for i in range(NUM):
    t = threading.Thread(target=worker, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print('Concurrent results:')
for r in results:
    print(r)

# Basic assert: all started and done
started = [r for r in results if r[1]=='started']
done = [r for r in results if r[1]=='done']
if len(started) != NUM or len(done) != NUM:
    print('FAIL: Not all uploads completed successfully')
    raise SystemExit(1)

print('Concurrency test passed')
