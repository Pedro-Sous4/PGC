from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    print('playwright import ok')
    browser = p.chromium.launch(headless=True)
    print('launched chromium')
    browser.close()
    print('browser closed')
