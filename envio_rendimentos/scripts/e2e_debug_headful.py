from playwright.sync_api import sync_playwright
from pathlib import Path
import time
import sys

BASE = 'http://127.0.0.1:8000'
FP = Path(__file__).parent / 'tmp' / 'test_lgm.xlsx'
OUT = Path(__file__).parent / 'tmp' / 'debug_output'
OUT.mkdir(parents=True, exist_ok=True)

if not FP.exists():
    raise SystemExit('Test file not found: ' + str(FP))


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # log responses for /lgm/
        def on_response(r):
            try:
                if '/lgm/' in r.url or '/accounts/login' in r.url:
                    req = r.request
                    m = getattr(req, 'method', 'UNKNOWN')
                    print(f"[RESP] {r.status} {r.url} (req method={m})")
                    try:
                        if m == 'POST':
                            try:
                                print('[REQ POST DATA PREVIEW]', req.post_data or '<no post data>')
                            except Exception:
                                print('[REQ POST DATA PREVIEW] <unreadable>')
                        txt = r.text()
                        print('[RESP BODY PREVIEW]', txt[:800])
                    except Exception as e:
                        print('[RESP BODY READ ERROR]', e)
            except Exception as e:
                print('on_response err', e)

        page.on('response', on_response)
        page.on('console', lambda msg: print('[CONSOLE]', msg.text))

        # 1) Login
        print('NAV: login')
        page.goto(BASE + '/accounts/login/')
        page.fill('input[name=username]', 'testuser')
        page.fill('input[name=password]', 'testpass')
        page.click('button[type=submit]')

        # wait for navigation away from login or for a known element
        print('Waiting for login to complete (networkidle)')
        page.wait_for_load_state('networkidle', timeout=10000)
        print('Current URL after login:', page.url)

        # 2) Go to LGM page and upload via JS (AJAX)
        print('NAV: lgm')
        page.goto(BASE + '/lgm/')
        page.wait_for_load_state('networkidle')
        # sanity-check: container exists
        try:
            cont = page.evaluate("() => ({hasContainer: !!document.querySelector('.container'), containerPreview: document.querySelector('.container')?document.querySelector('.container').outerHTML.slice(0,200):null})")
            print('Container info:', cont)
            # quick DOM insertion sanity check
            try:
                ok = page.evaluate("() => { try { document.querySelector('.container').insertAdjacentHTML('afterbegin','<div id=\"testauth\">TEST</div>'); return !!document.querySelector('#testauth'); } catch(e) { return {error: e.toString()}; } }")
                print('DOM insertion test result:', ok)
                if type(ok) is dict and ok.get('error'):
                    print('DOM insertion error:', ok['error'])
                else:
                    # clean up
                    page.evaluate("() => { document.getElementById('testauth')?.remove(); }")
            except Exception as e:
                print('DOM insertion check failed:', e)
            # print showAuthBanner source to inspect closure behavior
            try:
                src = page.evaluate("() => (window.showAuthBanner ? window.showAuthBanner.toString() : null)")
                print('showAuthBanner source preview:', (src or '')[:600])
            except Exception as e:
                print('Could not read showAuthBanner source:', e)
        except Exception as e:
            print('Container check failed:', e)
        page.set_input_files('input[type=file]#arquivo', str(FP))
        # Use JS fetch to perform the AJAX upload (ensures headers and behavior match client-side)
        # Perform AJAX upload via fetch from the page context and then set request_id and reveal cards
        page.evaluate("async () => { const form = document.getElementById('uploadForm'); const fd = new FormData(form); const r = await fetch(location.href, {method:'POST', body: fd, credentials:'same-origin', headers:{'X-Requested-With':'XMLHttpRequest','Accept':'application/json'}}); try { const j = await r.json(); document.getElementById('request_id').value = j.request_id; document.getElementById('progress-card').classList.remove('d-none'); document.getElementById('logs-card').classList.remove('d-none'); console.log('POST returned request_id', j.request_id); const pc = document.getElementById('progress-card'); const pb = document.getElementById('progress-bar'); console.log('progress-card class:', pc.className); console.log('progress-card display:', window.getComputedStyle(pc).display); console.log('progress-bar display:', window.getComputedStyle(pb).display); return j; } catch(e) { return {error: 'non-json response'} } }")

        # wait for progress card (30s) — progress bar might be 0% initially so wait for the card itself
        try:
            print('Waiting for progress card...')
            page.wait_for_selector('#progress-card', timeout=30000)
            print('Progress card found')
        except Exception as e:
            print('Timeout waiting for progress card:', e)
            # dump page html and screenshot for inspection
            html = page.content()
            (OUT / 'page_content.html').write_text(html, encoding='utf-8')
            page.screenshot(path=str(OUT / 'screenshot.png'))
            print('Wrote', OUT / 'screenshot.png', 'and page_content.html')
            # also print logs element if exists
            try:
                logs = page.eval_on_selector('#logs', 'el=>el.textContent')
                print('Logs snippet:', (logs or '')[:800])
            except Exception:
                print('No #logs element')
            browser.close()
            sys.exit(2)

        # wait some seconds for logs to appear
        time.sleep(2)
        logs = page.eval_on_selector('#logs', 'el=>el.textContent')
        print('Logs snippet:', (logs or '')[:1000])

        # 3) Now simulate being logged out: clear cookies and try polling (should show friendly message)
        context.clear_cookies()
        rid = page.eval_on_selector('#request_id', 'el=>el.value')
        if rid:
            print('Polling as anonymous for', rid)
            # perform the same fetch the client does and ask it to render the banner if unauthenticated
            # check presence of poll helper and print its source
            try:
                hasPoll = page.evaluate("() => !!window._lgm_pollProgress")
                hasForce = page.evaluate("() => !!window.__lgm_force_poll")
                print('page has _lgm_pollProgress?:', hasPoll, 'has __lgm_force_poll?:', hasForce)
                if hasPoll:
                    try:
                        src = page.evaluate("() => window._lgm_pollProgress.toString().slice(0,400)")
                        print('poll function preview:', src)
                    except Exception:
                        pass
                # trigger the page's own poll function which contains the inline banner insertion logic
                if hasPoll:
                    page.evaluate('(rid)=>{ if (window._lgm_pollProgress) window._lgm_pollProgress(); }', rid)
                elif hasForce:
                    print('Calling __lgm_force_poll fallback')
                    page.evaluate('(rid)=>{ if (window.__lgm_force_poll) window.__lgm_force_poll(); }', rid)
                else:
                    print('No poll helper present to call')
            except Exception as e:
                print('Failed to call page poll function:', e)

            # short wait to allow banner rendering
            time.sleep(0.7)
            has = page.evaluate("() => !!document.querySelector('#auth-banner')")
            if has:
                ab_html = page.evaluate("() => document.querySelector('#auth-banner') ? document.querySelector('#auth-banner').outerHTML : null")
                print('Auth banner HTML preview:', (ab_html or '')[:400])
            else:
                print('No auth banner found')
        else:
            print('No request_id present in page')

        # keep browser open a little
        print('Done — keeping browser open for 5s so you can inspect.')
        # always save artifacts for inspection
        try:
            html = page.content()
            (OUT / 'page_content.html').write_text(html, encoding='utf-8')
        except Exception as e:
            print('Failed to write page_content:', e)
        try:
            page.screenshot(path=str(OUT / 'screenshot.png'))
            print('Wrote', OUT / 'screenshot.png')
        except Exception as e:
            print('Failed to take screenshot:', e)
        time.sleep(1)
        browser.close()


if __name__ == '__main__':
    run()
