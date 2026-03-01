import requests

url = 'http://127.0.0.1:8000/.well-known/appspecific/com.chrome.devtools.json'
try:
    r = requests.get(url, timeout=5)
    print('GET', url, '->', r.status_code)
    print('Content-Length:', len(r.content))
    print('Headers:', dict(r.headers))
except Exception as e:
    print('Erro ao consultar:', e)
