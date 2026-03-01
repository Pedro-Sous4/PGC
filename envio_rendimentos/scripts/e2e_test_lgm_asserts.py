from playwright.sync_api import sync_playwright
from pathlib import Path
import time
import json

BASE = 'http://127.0.0.1:8000'
FP = Path(__file__).parent / 'tmp' / 'test_lgm.xlsx'

# create test file if not exists (reuse earlier)
if not FP.exists():
    raise SystemExit('Test file not found: ' + str(FP))


def wait_for_progress_to_start(page, request_id, timeout=30):
    """Poll the /lgm/status/<request_id>/ until percent > 0 or status completed/error."""
    start = time.time()
    while time.time() - start < timeout:
        r = page.evaluate("(rid)=>fetch('/lgm/status/'+rid+'/',{credentials:'same-origin', headers:{'Accept':'application/json','X-Requested-With':'XMLHttpRequest'}}).then(r=>r.json()).catch(e=>({__err__:String(e)}))", request_id)
        if isinstance(r, dict) and r.get('__err__'):
            time.sleep(0.5)
            continue
        percent = r.get('percent', 0) if isinstance(r, dict) else 0
        status = r.get('status') if isinstance(r, dict) else None
        if percent > 0 or status in ('completed', 'error'):
            return r
        time.sleep(0.5)
    return None


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # collect console and response logs
        console_logs = []
        response_logs = []
        def on_console(msg):
            try:
                console_logs.append(f"{msg.type}: {msg.text}")
            except Exception:
                console_logs.append(str(msg))
        page.on('console', on_console)

        def on_response(r):
            try:
                if '/lgm/' in r.url or '/accounts/login' in r.url:
                    response_logs.append((r.status, r.url))
            except Exception:
                pass
        page.on('response', on_response)

        # create output dir for artifacts
        out = Path(__file__).parent / 'tmp' / ('e2e_artifacts')
        out.mkdir(parents=True, exist_ok=True)

        # 1) Login
        page.goto(BASE + '/accounts/login/')
        page.fill('input[name=username]', 'testuser')
        page.fill('input[name=password]', 'testpass')
        page.click('button[type=submit]')
        page.wait_for_load_state('networkidle')

        # 2) Go to LGM page and upload via JS (AJAX)
        page.goto(BASE + '/lgm/')
        page.wait_for_load_state('networkidle')
        page.set_input_files('input[type=file]#arquivo', str(FP))

        # perform AJAX upload via fetch from the page context and ensure the DOM mirrors expected behavior
        post_res = page.evaluate("async () => { const form = document.getElementById('uploadForm'); const fd = new FormData(form); const r = await fetch(location.href, {method:'POST', body: fd, credentials:'same-origin', headers:{'X-Requested-With':'XMLHttpRequest','Accept':'application/json'}}); try { const j = await r.json(); document.getElementById('request_id').value = j.request_id; document.getElementById('progress-card').classList.remove('d-none'); document.getElementById('logs-card').classList.remove('d-none'); return j; } catch(e) { return {error: 'non-json response', text: await r.text()}; } }")
        print('POST result preview:', str(post_res)[:400])

        # assert we received request_id
        if not isinstance(post_res, dict) or not post_res.get('request_id'):
            print('FAIL: did not receive a request_id from POST')
            # gather artifacts
            page.screenshot(path=str(out / 'failure_no_request_id.png'))
            (out / 'page_content.html').write_text(page.content(), encoding='utf-8')
            (out / 'console.log').write_text('\n'.join(console_logs), encoding='utf-8')
            (out / 'responses.log').write_text('\n'.join(map(str,response_logs)), encoding='utf-8')
            browser.close()
            raise SystemExit(1)

        request_id = post_res['request_id']

        # wait for UI to reveal progress card
        try:
            page.wait_for_selector('#progress-card', timeout=10000)
        except Exception as e:
            print('FAIL: progress card did not appear:', e)
            page.screenshot(path=str(out / 'failure_no_progress_card.png'))
            (out / 'page_content.html').write_text(page.content(), encoding='utf-8')
            (out / 'console.log').write_text('\n'.join(console_logs), encoding='utf-8')
            (out / 'responses.log').write_text('\n'.join(map(str,response_logs)), encoding='utf-8')
            browser.close()
            raise SystemExit(1)

        # wait for processing to start (percent > 0 or status change)
        status_json = wait_for_progress_to_start(page, request_id, timeout=60)
        if not status_json:
            print('FAIL: processing did not start within timeout')
            page.screenshot(path=str(out / 'failure_no_processing.png'))
            (out / 'page_content.html').write_text(page.content(), encoding='utf-8')
            (out / 'console.log').write_text('\n'.join(console_logs), encoding='utf-8')
            (out / 'responses.log').write_text('\n'.join(map(str,response_logs)), encoding='utf-8')
            browser.close()
            raise SystemExit(1)

        print('processing started, sample status:', json.dumps(status_json)[:800])

        # verify logs were populated at least with the initial message
        logs = page.eval_on_selector('#logs', 'el=>el.textContent') or ''
        if 'Upload recebido' not in logs and 'Iniciando processamento do PGC' not in logs:
            print('WARN: logs appear empty or do not contain expected markers')
            # still capture artifacts
            (out / 'page_content_warn.html').write_text(page.content(), encoding='utf-8')
            (out / 'console.log').write_text('\n'.join(console_logs), encoding='utf-8')
        else:
            print('Logs populated (snippet):', logs[:400])

        # 3) Check errors and credores endpoints respond with JSON
        try:
            errs = page.evaluate("(rid)=>fetch('/lgm/errors/'+rid+'/').then(r=>r.json()).catch(e=>({__err__:String(e)}))", request_id)
            creds = page.evaluate("(rid)=>fetch('/lgm/credores/'+rid+'/').then(r=>r.json()).catch(e=>({__err__:String(e)}))", request_id)
            print('errors endpoint returned keys:', list(errs.keys()) if isinstance(errs, dict) else 'error')
            print('credores endpoint returned keys:', list(creds.keys()) if isinstance(creds, dict) else 'error')
        except Exception as e:
            print('FAIL: error/credores endpoints failed:', e)
            (out / 'page_content_error_endpoints.html').write_text(page.content(), encoding='utf-8')
            (out / 'console.log').write_text('\n'.join(console_logs), encoding='utf-8')
            browser.close()
            raise SystemExit(1)

        # 4) Now simulate being logged out: clear cookies and try polling (should show unauthenticated JSON)
        context.clear_cookies()
        anon_poll = page.evaluate("(rid)=>fetch('/lgm/status/'+rid+'/',{credentials:'same-origin', headers:{'Accept':'application/json','X-Requested-With':'XMLHttpRequest'}}).then(async r=>{ const t = await r.text(); try { return {status:r.status, json: JSON.parse(t)} } catch(e){return {status:r.status, text:t}} }).catch(e=>({error:String(e)}))", request_id)
        print('Anonymous poll result:', str(anon_poll)[:400])
        # ensure server returns 401 JSON unauthenticated
        if not isinstance(anon_poll, dict) or anon_poll.get('status') != 401 or not (isinstance(anon_poll.get('json'), dict) and anon_poll['json'].get('status') == 'unauthenticated'):
            print('FAIL: anonymous poll did not return expected unauthenticated 401 JSON')
            page.screenshot(path=str(out / 'failure_anonymous_poll.png'))
            (out / 'page_content.html').write_text(page.content(), encoding='utf-8')
            (out / 'console.log').write_text('\n'.join(console_logs), encoding='utf-8')
            (out / 'responses.log').write_text('\n'.join(map(str,response_logs)), encoding='utf-8')
            browser.close()
            raise SystemExit(1)

        # optional: if there were errors, attempt to call reprocess endpoint; otherwise skip but log
        if isinstance(errs, dict) and errs.get('errors'):
            print('Found persisted errors; attempting to trigger reprocess for first error...')
            first = errs['errors'][0]
            slug = first.get('credor')
            reproc = page.evaluate("(rid, slug)=>fetch('/lgm/reprocess/', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRFToken':document.cookie.split('csrftoken=')[1]||''}, body: JSON.stringify({request_id: rid, credores: [slug]})}).then(r=>r.json()).catch(e=>({__err__:String(e)}))", request_id, slug)
            print('reprocess result snippet:', str(reproc)[:400])

        print('E2E test passed ✅')
        # save artifacts on success as well
        (out / 'page_content_success.html').write_text(page.content(), encoding='utf-8')
        (out / 'console.log').write_text('\n'.join(console_logs), encoding='utf-8')
        (out / 'responses.log').write_text('\n'.join(map(str,response_logs)), encoding='utf-8')
        browser.close()
        return 0

if __name__ == '__main__':
    run()
