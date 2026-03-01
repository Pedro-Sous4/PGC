import requests, re, time, os
BASE='http://192.168.1.105:8000'
FP='envio_rendimentos/scripts/tmp/test_lgm.xlsx'
s=requests.Session()
print('GET login...')
r=s.get(BASE+'/accounts/login/')
csrftoken=s.cookies.get('csrftoken')
print('csrf:', bool(csrftoken))
payload={'username':'testuser','password':'testpass','csrfmiddlewaretoken':csrftoken}
headers={'Referer':BASE+'/accounts/login/'}
r=s.post(BASE+'/accounts/login/',data=payload,headers=headers,allow_redirects=True)
print('login status', r.status_code)
print('file exists?', os.path.exists(FP))
with open(FP,'rb') as f:
    files={'arquivo':('test_lgm.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    r=s.post(BASE+'/lgm/', files=files)
    print('post status', r.status_code, 'len', len(r.content))
    text=r.text
    # find request_id in rendered HTML
    m=re.search(r'id="request_id"\s+name="request_id"\s+value="([0-9a-f-]+)"', text)
    print('match', bool(m))
    if m:
        rid=m.group(1)
        print('found request_id in HTML:', rid)
        time.sleep(1)
        rs=s.get(f'{BASE}/lgm/status/{rid}/', headers={'Accept':'application/json','X-Requested-With':'XMLHttpRequest'})
        print('status GET', rs.status_code, rs.text[:400])
    else:
        print('no request_id in HTML response')
    print('\n--- HTML preview ---\n', text[:800])