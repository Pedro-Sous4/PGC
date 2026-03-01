from playwright.sync_api import sync_playwright
from pathlib import Path
import time

BASE = 'http://127.0.0.1:8000'
FP = Path(__file__).parent / 'tmp' / 'test_lgm.xlsx'

# create test file if not exists (reuse earlier)
if not FP.exists():
    raise SystemExit('Test file not found: ' + str(FP))


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1) Login
        page.goto(BASE + '/accounts/login/')
        page.fill('input[name=username]', 'testuser')
        page.fill('input[name=password]', 'testpass')
        page.click('button[type=submit]')
        time.sleep(0.4)

        # 2) Go to LGM page and upload via JS (AJAX)
        page.goto(BASE + '/lgm/')
        page.set_input_files('input[type=file]#arquivo', str(FP))
        # Perform AJAX upload via fetch and set request_id in DOM so the page behaves like the submit handler
        page.evaluate("async () => { const form = document.getElementById('uploadForm'); const fd = new FormData(form); const r = await fetch(location.href, {method:'POST', body: fd, credentials:'same-origin', headers:{'X-Requested-With':'XMLHttpRequest','Accept':'application/json'}}); const j = await r.json(); document.getElementById('request_id').value = j.request_id; document.getElementById('progress-card').classList.remove('d-none'); document.getElementById('logs-card').classList.remove('d-none'); }")

        # wait for progress card to be visible (progress-bar may have 0% width initially)
        page.wait_for_selector('#progress-card', timeout=5000)
        # wait some seconds for logs to appear (progress starts)
        time.sleep(2)
        logs = page.eval_on_selector('#logs', 'el=>el.textContent')
        print('Logs snippet:', logs[:500])

        # 3) Now simulate being logged out: clear cookies and try polling (should show friendly message)
        context.clear_cookies()
        # perform manual fetch in page to poll current request id
        rid = page.eval_on_selector('#request_id', 'el=>el.value')
        if rid:
            print('Polling as anonymous for', rid)
            res = page.evaluate("(rid)=>fetch('/lgm/status/'+rid+'/',{credentials:'same-origin', headers:{'Accept':'application/json','X-Requested-With':'XMLHttpRequest'}}).then(r=>r.text()).catch(e=>e.toString())", rid)
            print('Poll result (preview):', res[:500])
        else:
            print('No request_id present in page')

        browser.close()

if __name__ == '__main__':
    run()
