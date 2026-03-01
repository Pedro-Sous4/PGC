import requests
r = requests.get('http://127.0.0.1:8000/lgm/')
print('status', r.status_code, 'len', len(r.text))
print('has showAuthBanner?', 'showAuthBanner' in r.text)
print('snippet index:', r.text.find('showAuthBanner'))
print(r.text[r.text.find('showAuthBanner')-200:r.text.find('showAuthBanner')+200])