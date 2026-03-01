import pandas as pd
import os
import time
import threading
import requests

BASE = 'http://127.0.0.1:8000'
OUT = os.path.join(os.path.dirname(__file__), 'tmp')
os.makedirs(OUT, exist_ok=True)
FP = os.path.join(OUT, 'test_lgm.xlsx')

# ===== create workbook =====
# BASE sheet
base = pd.DataFrame([
    {'Credor': 'ACME', 'Empresa': 'Empresa A', 'Documento': '123', 'Cliente': 'Cliente X', 'Parcela': 1, 'DT_Emissao': '2026-01-01', 'Valor': 100.0},
    {'Credor': 'ACME', 'Empresa': 'Empresa A', 'Documento': '124', 'Cliente': 'Cliente Y', 'Parcela': 2, 'DT_Emissao': '2026-01-02', 'Valor': 200.0},
])
# EXTRATO & PRODUTIVIDADE
extrato = pd.DataFrame([
    {'Credor': 'ACME', 'Documento': '123'},
])
prod = pd.DataFrame([
    {'Credor': 'ACME', 'Prod': 10},
])
# MINIMO sheet: many cols, headerless; fill rows until index 10 and cols >= 43
min_rows = 20
min_cols = 50
import numpy as np
min_df = pd.DataFrame(np.nan, index=range(min_rows), columns=range(min_cols))
# set some rows starting at index 7
for i in range(7, 10):
    min_df.iat[i, 35] = 'ACME'
    min_df.iat[i, 40] = 100
    min_df.iat[i, 41] = 'Empresa A'
    min_df.iat[i, 42] = '00.000.000/0000-00'

with pd.ExcelWriter(FP, engine='openpyxl') as w:
    base.to_excel(w, sheet_name='BASE PGC 123', index=False)
    extrato.to_excel(w, sheet_name='EXTRATO', index=False)
    prod.to_excel(w, sheet_name='PRODUTIVIDADE', index=False)
    min_df.to_excel(w, sheet_name='PGC123', index=False, header=False)

print('Arquivo de teste criado:', FP)

# ===== helper to post file =====

def login_session(username='testuser', password='testpass'):
    s = requests.Session()
    # GET login page to get csrf cookie
    r = s.get(BASE + '/accounts/login/')
    csrftoken = s.cookies.get('csrftoken')
    if not csrftoken:
        print('Não encontrou csrftoken ao acessar login')
    payload = {
        'username': username,
        'password': password,
        'csrfmiddlewaretoken': csrftoken,
    }
    headers = {'Referer': BASE + '/accounts/login/'}
    r2 = s.post(BASE + '/accounts/login/', data=payload, headers=headers)
    print('login ->', r2.status_code, r2.url)
    return s


def post_file(session=None):
    s = session or requests
    with open(FP, 'rb') as f:
        files = {'arquivo': ('test_lgm.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        r = s.post(f'{BASE}/lgm/', files=files, allow_redirects=True)
        print('POST ->', r.status_code, 'URL:', r.url)
        if r.history:
            print('Redirect history:')
            for h in r.history:
                print(' ', h.status_code, h.headers.get('Location'))
        print('Response headers:', dict(r.headers))
        try:
            j = r.json()
        except Exception:
            print('Resposta não-JSON:', r.status_code, r.text[:400])
            return None
        print('Upload response:', j)
        return j.get('request_id')

# ===== run two uploads concurrently =====
# login duas sessões distintas para simular concorrência
s1 = login_session()
s2 = login_session()

ids = []

def do_post_and_store(session):
    rid = post_file(session=session)
    ids.append(rid)

threads = [threading.Thread(target=do_post_and_store, args=(s,)) for s in (s1, s2)]
for t in threads:
    t.start()
    time.sleep(0.1)
for t in threads:
    t.join()

print('Request IDs:', ids)

# ===== poll statuses =====

def poll(rid):
    if not rid:
        print('No request_id to poll')
        return
    url = f'{BASE}/lgm/status/{rid}/'
    while True:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 404:
                print(f'[{rid}] status not found yet')
            else:
                d = r.json()
                print(f'[{rid}]', d.get('status'), d.get('percent'), 'logs:', len(d.get('logs', [])))
                if d.get('status') in ('completed', 'error'):
                    print(f'[{rid}] final:', d.get('status'))
                    # print last logs
                    for l in d.get('logs', [])[-10:]:
                        print('   ', l)
                    break
        except Exception as e:
            print('Poll error:', e)
        time.sleep(1.5)

poll_threads = [threading.Thread(target=poll, args=(rid,)) for rid in ids]
for t in poll_threads:
    t.start()
for t in poll_threads:
    t.join()

print('Teste concluído')
