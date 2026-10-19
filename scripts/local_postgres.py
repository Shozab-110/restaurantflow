"""Workspace-scoped PostgreSQL helper for Windows development; no system service changes."""
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

root = Path(__file__).resolve().parent.parent
load_dotenv(root / '.env', interpolate=False)
local = root / '.local'
runtime = local / 'pg-runtime' / 'pgsql'
bin_dir = (runtime if runtime.exists() else local / 'pgsql') / 'bin'
data = local / 'pgdata'
port = os.getenv('POSTGRES_PORT', '5433')
env = {**os.environ, 'PGPASSWORD': os.environ['POSTGRES_PASSWORD']}
def run(exe, *args, check=True):
    # pg_ctl's detached server may retain inherited pipe handles on Windows.
    # A file handle lets us wait on the helper without waiting on server pipe EOF.
    with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as output:
        result = subprocess.run([str(bin_dir / (exe + '.exe')), *map(str,args)], env=env, stdout=output, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        output.seek(0)
        print(output.read(), end='', flush=True)
    if check:
        result.check_returncode()
    return result
if not (bin_dir / 'initdb.exe').exists():
    sys.exit('Download official PostgreSQL Windows binaries and extract pgsql into .local first. See README.')
action = sys.argv[1] if len(sys.argv)>1 else 'start'
if action == 'stop':
    run('pg_ctl','-D',data,'-m','fast','stop')
    sys.exit()
if not (data / 'PG_VERSION').exists():
    password_file=local/'init-password.tmp'
    password_file.write_text(os.environ['POSTGRES_PASSWORD'], encoding='utf-8')
    try:
        run('initdb','-D',data,'-U',os.environ['POSTGRES_USER'],'-E','UTF8','--locale=C','-A','scram-sha-256','--pwfile',password_file)
    finally:
        password_file.unlink(missing_ok=True)
status=subprocess.run([str(bin_dir/'pg_ctl.exe'),'-D',str(data),'status'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
if status.returncode:
    run('pg_ctl','-D',data,'-l',local/'postgres.log','-o',f'-p {port} -h 127.0.0.1','-w','start')
name=os.getenv('POSTGRES_DB','restaurantflow')
result=subprocess.run([str(bin_dir/'psql.exe'),'-h','127.0.0.1','-p',port,'-U',os.environ['POSTGRES_USER'],'-d','postgres','-tAc','SELECT datname FROM pg_database'],env=env,capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
if name not in result.stdout.split():
    run('createdb','-h','127.0.0.1','-p',port,'-U',os.environ['POSTGRES_USER'],name)
print(f'PostgreSQL is running at 127.0.0.1:{port}; database {name}.')
