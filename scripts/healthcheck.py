import http.client
import os
host=os.getenv('DJANGO_ALLOWED_HOSTS','localhost').split(',')[0]
conn=http.client.HTTPConnection('127.0.0.1',8000,timeout=4)
conn.request('GET','/health/',headers={'Host':host,'X-Forwarded-Proto':'https'})
response=conn.getresponse()
if response.status!=200:
    raise SystemExit(1)
