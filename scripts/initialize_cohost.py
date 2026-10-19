"""Initialize schema with migration credentials, then grant a restricted runtime role."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
subprocess.run([sys.executable, str(ROOT / 'scripts/initialize.py')], cwd=ROOT, check=True)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurantflow.settings')
import django
django.setup()
from django.db import connection
from psycopg import sql

runtime = os.environ['RESTAURANTFLOW_RUNTIME_DB_USER']
password = os.environ['RESTAURANTFLOW_RUNTIME_DB_PASSWORD']
if runtime == connection.settings_dict['USER']:
    raise SystemExit('Runtime and migration database users must be different.')
with connection.cursor() as cursor:
    cursor.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', [runtime])
    if not cursor.fetchone():
        cursor.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(runtime)))
    cursor.execute(sql.SQL('ALTER ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(
        sql.Identifier(runtime), sql.Literal(password)))
    cursor.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(
        sql.Identifier(connection.settings_dict['NAME']), sql.Identifier(runtime)))
    cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(runtime)))
    cursor.execute(sql.SQL('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}').format(sql.Identifier(runtime)))
    cursor.execute(sql.SQL('GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {}').format(sql.Identifier(runtime)))
    cursor.execute(sql.SQL('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}').format(sql.Identifier(runtime)))
    cursor.execute(sql.SQL('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {}').format(sql.Identifier(runtime)))
print('Restricted runtime database role provisioned; migration credentials are not supplied to web.')
