"""Render the real local POS template for JavaScript DOM tests. Requires a seeded dev DB."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','restaurantflow.settings')
import django
django.setup()
from django.conf import settings
from django.test import Client, override_settings
from django.contrib.auth import get_user_model
if not settings.DEBUG:
    raise SystemExit('POS fixtures may only be rendered from a development database.')
user=get_user_model().objects.get(username='owner',is_active=True)
with override_settings(ALLOWED_HOSTS=['testserver']):
    client=Client();client.force_login(user)
    response=client.get('/pos/')
    assert response.status_code==200
    local=Path('.local');local.mkdir(exist_ok=True)
    (local/'verified-pos.html').write_bytes(response.content)
print('Real POS HTML rendered for local DOM interaction tests.')
