"""Read-only HTTP verification of the running local demo, including real session login."""
import http.cookiejar
import argparse
import ipaddress
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url',default='http://127.0.0.1:8000')
base=parser.parse_args().base_url.rstrip('/')
target=urllib.parse.urlsplit(base)
try:
    address=ipaddress.ip_address(target.hostname) if target.hostname!='localhost' else ipaddress.ip_address('127.0.0.1')
    private_ranges=[ipaddress.ip_network(value) for value in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16']]
    assert target.scheme=='http' and not target.username and not target.password and not target.path and not target.query and not target.fragment
    assert address.is_loopback or any(address in network for network in private_ranges)
except (ValueError,AssertionError,TypeError):
    parser.error('Use a loopback or private LAN HTTP base URL; this verifier must not send local demo credentials to a public server.')
jar=http.cookiejar.CookieJar()
client=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
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
