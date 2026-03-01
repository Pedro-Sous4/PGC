from playwright.sync_api import sync_playwright
BASE='http://192.168.1.105:8000'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        r = page.goto(BASE, timeout=10000)
        print('goto succeeded, url:', page.url)
        print('response status:', r.status)
    except Exception as e:
        print('goto failed:', repr(e))
    finally:
        browser.close()
