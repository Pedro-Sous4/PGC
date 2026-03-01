import requests
r = requests.get('http://127.0.0.1:8000/lgm/', allow_redirects=True)
print('GET ->', r.status_code, r.url)
print('history:', [(h.status_code, h.headers.get('Location')) for h in r.history])
print('content len', len(r.text))
print(r.text[:600])
