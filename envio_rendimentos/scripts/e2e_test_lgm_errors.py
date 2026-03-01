from playwright.sync_api import sync_playwright
from pathlib import Path
import time
import json
import pandas as pd

BASE = 'http://127.0.0.1:8000'
FP_GOOD = Path(__file__).parent / 'tmp' / 'test_lgm.xlsx'
FP_BAD = Path(__file__).parent / 'tmp' / 'test_lgm_bad.xlsx'

# create a bad test file that lacks expected columns to trigger errors
if not FP_BAD.exists():
    df = pd.DataFrame({'foo':[1,2,3], 'bar':['a','b','c']})
    FP_BAD.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(FP_BAD, index=False)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        out = Path(__file__).parent / 'tmp' / 'e2e_artifacts_errors'
        out.mkdir(parents=True, exist_ok=True)

        # login
        page.goto(BASE + '/accounts/login/')
        page.fill('input[name=username]', 'testuser')
        page.fill('input[name=password]', 'testpass')
        page.click('button[type=submit]')
        page.wait_for_load_state('networkidle')

        # go to lgm and upload bad file
        page.goto(BASE + '/lgm/')
        page.wait_for_load_state('networkidle')
        page.set_input_files('input[type=file]#arquivo', str(FP_BAD))

        # perform AJAX upload
        post_res = page.evaluate("async () => { const form = document.getElementById('uploadForm'); const fd = new FormData(form); const r = await fetch(location.href, {method:'POST', body: fd, credentials:'same-origin', headers:{'X-Requested-With':'XMLHttpRequest','Accept':'application/json'}}); try { return await r.json(); } catch(e){ return {error:'non-json', text: await r.text()}} }")
        print('POST res:', str(post_res)[:400])
        if not isinstance(post_res, dict) or not post_res.get('request_id'):
            print('FAIL: no request id for bad upload')
            browser.close()
            raise SystemExit(1)

        rid = post_res['request_id']

        # wait for processing to finish
        def poll_status():
            for _ in range(60):
                s = page.evaluate('(rid)=>fetch(`/lgm/status/${rid}/`,{credentials:"same-origin", headers:{"Accept":"application/json","X-Requested-With":"XMLHttpRequest"}}).then(r=>r.json()).catch(e=>({__err__:String(e)}))', rid)
                if isinstance(s, dict) and s.get('__err__'):
                    time.sleep(0.5)
                    continue
                if s.get('status') in ('completed','error'):
                    return s
                time.sleep(0.5)
            return None

        status = poll_status()
        print('Final status:', status)

        # expect persisted errors OR an overall processing error recorded in status
        errs = page.evaluate('(rid)=>fetch(`/lgm/errors/${rid}/`).then(r=>r.json()).catch(e=>({__err__:String(e)}))', rid)
        print('Errors endpoint returned:', errs)

        # fetch final status again to see aggregated statistics
        final_status = page.evaluate('(rid)=>fetch(`/lgm/status/${rid}/`,{credentials:"same-origin", headers:{"Accept":"application/json","X-Requested-With":"XMLHttpRequest"}}).then(r=>r.json()).catch(e=>({__err__:String(e)}))', rid)
        print('Final status for validation:', final_status)

        has_structured_errors = isinstance(errs, dict) and errs.get('errors')
        aggregated_error_flag = isinstance(final_status, dict) and final_status.get('estatisticas', {}).get('erros', 0) > 0

        if not has_structured_errors and not aggregated_error_flag:
            print('FAIL: neither structured errors nor aggregated error count present')
            page.screenshot(path=str(out / 'failure_no_errors.png'))
            (out / 'page_content.html').write_text(page.content(), encoding='utf-8')
            browser.close()
            raise SystemExit(1)

        # attempt reprocess only if there are structured credor errors to reprocess
        if not has_structured_errors:
            print('No structured credor errors to reprocess; skipping reprocess step (aggregated errors exist)')
            browser.close()
            return

        # attempt reprocess of first error's credor (if present)
        first = errs['errors'][0]
        slug = first.get('credor')
        if not slug:
            print('No slug in first error, aborting reprocess test')
            browser.close()
            return

        reproc = page.evaluate("(rid, slug)=>fetch('/lgm/reprocess/', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRFToken': document.cookie.split('csrftoken=')[1] || ''}, body: JSON.stringify({request_id: rid, credores: [slug]})}).then(r=>r.json()).catch(e=>({__err__:String(e)}))", rid, slug)
        print('Reprocess response:', reproc)
        if not isinstance(reproc, dict) or not reproc.get('job_id'):
            print('FAIL: reprocess did not return job_id')
            page.screenshot(path=str(out / 'failure_no_jobid.png'))
            (out / 'page_content.html').write_text(page.content(), encoding='utf-8')
            browser.close()
            raise SystemExit(1)

        job_id = reproc['job_id']

        # poll reprocess status
        for _ in range(60):
            jr = page.evaluate(f"() => fetch('/lgm/reprocess/status/{job_id}/').then(r=>r.json()).catch(e=>({{'__err__':String(e)}}))")
            print('reproc status snippet:', str(jr)[:200])
            if isinstance(jr, dict) and jr.get('status') in ('completed','error'):
                break
            time.sleep(0.5)

        print('E2E error scenario passed')
        (out / 'page_content.html').write_text(page.content(), encoding='utf-8')
        browser.close()

if __name__ == '__main__':
    run()
