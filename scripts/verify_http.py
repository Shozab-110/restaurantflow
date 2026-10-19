"""Read-only HTTP verification of the running local demo, including real session login."""
import http.cookiejar
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

base='http://127.0.0.1:8000'
jar=http.cookiejar.CookieJar()
client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
# Startup checks may run immediately after launching the development process.
for attempt in range(30):
    try:
        with client.open(base+'/health/', timeout=2) as probe:
            if probe.status == 200:
                break
    except OSError:
        if attempt == 29:
            raise
        time.sleep(0.5)
def get(path):
    with client.open(base+path,timeout=20) as response:
        body=response.read().decode('utf-8')
        assert response.status==200,(path,response.status)
        return response.geturl(),body
_,login=get('/login/')
token=re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"',login).group(1)
access=Path('.local/demo-access.txt').read_text(encoding='utf-8')
password=next(line.removeprefix('Password: ') for line in access.splitlines() if line.startswith('Password: '))
payload=urllib.parse.urlencode({'username':'owner','password':password,'csrfmiddlewaretoken':token}).encode()
request=urllib.request.Request(base+'/login/',data=payload,headers={'Referer':base+'/login/'})
with client.open(request,timeout=20) as response:
    assert response.geturl()==base+'/', 'Owner login did not reach the dashboard'
pages=['/','/pos/','/orders/','/kitchen/','/kitchen/board/','/tables/','/manage/menu/','/manage/categories/','/manage/customers/','/payments/','/reports/','/staff/','/settings/','/audit/','/profile/','/reports/?export=daily','/health/']
assets=set()
for path in pages:
    url,body=get(path)
    assert '/login/' not in url, f'Unexpected authentication redirect: {path}'
    assert 'Traceback' not in body and 'TemplateSyntaxError' not in body, path
    print('PASS',path)
    assets.update(re.findall(r'(?:src|href)="(/static/[^"?]+)',body))
    if path=='/pos/':Path('.local/verified-pos.html').write_text(body,encoding='utf-8')
for asset in sorted(assets):
    with client.open(base+asset,timeout=20) as response:
        assert response.status==200
        response.read()
    print('PASS asset',asset)
print(f'Verified owner session, {len(pages)} HTTP endpoints, and {len(assets)} local assets. No browser rendering claimed.')
