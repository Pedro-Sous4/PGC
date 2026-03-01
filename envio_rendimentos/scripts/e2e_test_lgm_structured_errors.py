from playwright.sync_api import sync_playwright
from pathlib import Path
import pandas as pd
import time

BASE = 'http://127.0.0.1:8000'
FP = Path(__file__).parent / 'tmp' / 'test_lgm_structured.xlsx'

# create a file that has the required sheets and a bad valor to generate per-credor errors
if not FP.exists():
    with pd.ExcelWriter(FP) as w:
        # base sheet must contain 'PGC' and 'base' and number
        df_base = pd.DataFrame({'Credor': ['CRED_1'], 'Valor': ['N/A'], 'Empresa': ['X']})
        df_base.to_excel(w, sheet_name='PGC 123 base', index=False)
        df_extrato = pd.DataFrame({'credor_canonico': ['CRED_1'], 'documento': [1], 'valor_original': [100]})
        df_extrato.to_excel(w, sheet_name='extrato', index=False)
        df_prod = pd.DataFrame({'credor_canonico': ['CRED_1'], 'prod': [1]})
        df_prod.to_excel(w, sheet_name='produtividade', index=False)
        df_min = pd.DataFrame({'A':[1]})
        df_min.to_excel(w, sheet_name='PGC 123', index=False)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # login
        page.goto(BASE + '/accounts/login/')
        page.fill('input[name=username]', 'testuser')
        page.fill('input[name=password]', 'testpass')
        page.click('button[type=submit]')
        page.wait_for_load_state('networkidle')

        # upload
        page.goto(BASE + '/lgm/')
        page.set_input_files('input[type=file]#arquivo', str(FP))
        post_res = page.evaluate("async () => { const form = document.getElementById('uploadForm'); const fd = new FormData(form); const r = await fetch(location.href, {method:'POST', body: fd, credentials:'same-origin', headers:{'X-Requested-With':'XMLHttpRequest','Accept':'application/json'}}); return r.json(); }")
        print('POST returned', post_res)
        rid = post_res.get('request_id')
        if not rid:
            print('FAIL: no request id')
            raise SystemExit(1)

        # wait for status completed or error
        for _ in range(60):
            s = page.evaluate("(rid)=>fetch('/lgm/status/'+rid+'/',{credentials:'same-origin', headers:{'Accept':'application/json','X-Requested-With':'XMLHttpRequest'}}).then(r=>r.json()).catch(e=>({__err__:String(e)}))", rid)
            if isinstance(s, dict) and s.get('__err__'):
                time.sleep(0.5); continue
            if s.get('status') in ('completed','error'):
                print('status reached', s.get('status'))
                break
            time.sleep(0.5)
        else:
            print('FAIL: status did not reach completion in time')
            raise SystemExit(1)

        errs = page.evaluate("(rid)=>fetch('/lgm/errors/'+rid+'/').then(r=>r.json()).catch(e=>({__err__:String(e)}))", rid)
        print('errors endpoint:', errs)
        if not isinstance(errs, dict) or not errs.get('errors'):
            print('FAIL: structured errors not present')
            raise SystemExit(1)

        # attempt reprocess for first structured error
        slug = errs['errors'][0].get('credor')
        if not slug:
            print('FAIL: no slug in structured error')
            raise SystemExit(1)

        # attempt reprocess for first structured error via server-side requests (more reliable)
        slug = errs['errors'][0].get('credor')
        if not slug:
            print('FAIL: no slug in structured error')
            raise SystemExit(1)

        import requests
        s = requests.Session()
        r = s.get(BASE + '/accounts/login/')
        csrftoken = s.cookies.get('csrftoken')
        login_res = s.post(BASE + '/accounts/login/', data={'username':'testuser','password':'testpass','csrfmiddlewaretoken':csrftoken}, headers={'Referer': BASE + '/accounts/login/'}, allow_redirects=True)
        if login_res.status_code not in (200,302):
            print('FAIL: could not login via requests', login_res.status_code)
            raise SystemExit(1)

        # start reprocess via requests
        resp = s.post(BASE + '/lgm/reprocess/', json={'request_id': rid, 'credores': [slug]}, headers={'X-Requested-With':'XMLHttpRequest','Accept':'application/json'})
        print('reprocess POST status', resp.status_code, 'ct', resp.headers.get('content-type'))
        try:
            reproc = resp.json()
        except Exception:
            print('reprocess returned non-json (preview):', resp.text[:800])
            raise SystemExit(1)

        print('reproc returned', reproc)
        if not isinstance(reproc, dict) or not reproc.get('job_id'):
            print('FAIL: reprocess did not start')
            raise SystemExit(1)

        job_id = reproc['job_id']
        # poll reprocess status via requests
        for _ in range(60):
            jr = s.get(f"{BASE}/lgm/reprocess/status/{job_id}/")
            if jr.status_code == 200:
                jrj = jr.json()
                if jrj.get('status') in ('completed','error'):
                    print('reproc status', jrj.get('status'))
                    break
            time.sleep(0.5)
        else:
            print('FAIL: reprocess job did not complete')
            raise SystemExit(1)

        print('structured errors E2E passed')
        browser.close()


if __name__ == '__main__':
    run()
