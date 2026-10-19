"""Guarded Ubuntu cohosting installer. Run only for an authorized existing-server deployment.

Creates RestaurantFlow under /opt/restaurantflow. Does not edit nginx/ERPNext,
upgrade existing packages, reboot, or restart unrelated services.
"""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import time
import urllib.request

ROOT = Path('/opt/restaurantflow')
RESULT = Path('/root/restaurantflow-deployment-result.json')
PACKAGES = ['docker-ce', 'docker-ce-cli', 'containerd.io', 'docker-buildx-plugin', 'docker-compose-plugin']


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def output(args):
    return subprocess.check_output(args, text=True).strip()


def write_private(path, content):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
        handle.write(content)


def erp_health(address):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request('http://127.0.0.1/', headers={'Host': address})
    with opener.open(request, timeout=15) as response:
        body = response.read().decode('utf-8', errors='replace')
        if response.status != 200 or not re.search('frappe|erpnext', body, re.I):
            raise RuntimeError('ERPNext baseline health check failed; no deployment should proceed.')
        return response.status


def nginx_hashes():
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in Path('/etc/nginx').rglob('*') if path.is_file()}


def require_erp_unchanged(address, before):
    erp_health(address)
    if nginx_hashes() != before:
        raise RuntimeError('nginx configuration changed since baseline. Stop and investigate; do not overwrite ERP configuration.')


def installed(package):
    result = subprocess.run(['dpkg-query', '-W', '-f=${db:Status-Status}', package],
                            capture_output=True, text=True)
    return result.returncode == 0 and result.stdout == 'installed'


def install_docker():
    if shutil.which('docker'):
        run(['docker', 'info'], stdout=subprocess.DEVNULL)
        return
    conflicts = [name for name in ['docker.io', 'containerd', 'runc', 'podman-docker'] if installed(name)]
    if conflicts:
        raise RuntimeError('Existing container runtime packages require review; nothing will be uninstalled: ' + ', '.join(conflicts))
    release = Path('/etc/os-release').read_text()
    if 'ID=ubuntu' not in release or 'VERSION_CODENAME=noble' not in release:
        raise RuntimeError('This installer was prepared for audited Ubuntu 24.04 only.')
    architecture = output(['dpkg', '--print-architecture'])
    if architecture != 'amd64':
        raise RuntimeError('Revalidate the deployment for this CPU architecture first.')
    key = Path('/etc/apt/keyrings/restaurantflow-docker.asc')
    key.parent.mkdir(mode=0o755, exist_ok=True)
    source = Path('/etc/apt/sources.list.d/restaurantflow-docker.sources')
    content = ('Types: deb\nURIs: https://download.docker.com/linux/ubuntu\nSuites: noble\n'
               'Components: stable\nArchitectures: amd64\nSigned-By: ' + str(key) + '\n')
    if source.exists() and source.read_text() != content:
        raise RuntimeError('Existing Docker repository file differs; no overwrite allowed.')
    if not key.exists():
        with urllib.request.urlopen('https://download.docker.com/linux/ubuntu/gpg', timeout=30) as response:
            key.write_bytes(response.read())
        key.chmod(0o644)
    if not source.exists():
        source.write_text(content)
        source.chmod(0o644)
    environment = {**os.environ, 'DEBIAN_FRONTEND': 'noninteractive', 'NEEDRESTART_MODE': 'l'}
    run(['apt-get', 'update'], env=environment)
    simulation = output(['apt-get', '-s', '--no-remove', '--no-install-recommends', 'install', *PACKAGES])
    if re.search(r'^Remv\s|^Inst\s+\S+\s+\[', simulation, re.M):
        raise RuntimeError('Docker installation would remove/upgrade an existing package; aborting to protect ERPNext.')
    run(['apt-get', '-y', '--no-remove', '--no-install-recommends',
         '-o', 'Dpkg::Options::=--force-confold', 'install', *PACKAGES], env=environment)
    run(['docker', 'info'], stdout=subprocess.DEVNULL)


def compose(*args, **kwargs):
    return run(['docker', 'compose', '-p', 'restaurantflow', '-f', 'docker-compose.cohost.yml', *args],
               cwd=ROOT, **kwargs)


def initialize_configuration(address):
    if (ROOT / '.env').exists():
        raise RuntimeError('Existing RestaurantFlow environment found. Use a reviewed update, not first-install initialization.')
    runtime_password = secrets.token_urlsafe(40)
    migration_password = secrets.token_urlsafe(40)
    app = {
        'PUBLIC_IP': address, 'DJANGO_SECRET_KEY': secrets.token_urlsafe(60),
        'DJANGO_DEBUG': 'false', 'DJANGO_ALLOWED_HOSTS': address + ',localhost,127.0.0.1',
        'CSRF_TRUSTED_ORIGINS': 'https://' + address, 'DJANGO_TIME_ZONE': 'Asia/Karachi',
        'DJANGO_SECURE_SSL_REDIRECT': 'true', 'TRUST_PROXY_HEADERS': 'true',
        'DJANGO_SESSION_COOKIE_NAME': 'restaurantflow_session',
        'DJANGO_CSRF_COOKIE_NAME': 'restaurantflow_csrf',
        'POSTGRES_DB': 'restaurantflow', 'POSTGRES_USER': 'restaurantflow_app',
        'POSTGRES_PASSWORD': runtime_password, 'POSTGRES_HOST': 'db', 'POSTGRES_PORT': '5432',
    }
    database = {'POSTGRES_DB': 'restaurantflow', 'POSTGRES_USER': 'restaurantflow_migrator',
                'POSTGRES_PASSWORD': migration_password}
    migration = {**database, 'RESTAURANTFLOW_RUNTIME_DB_USER': 'restaurantflow_app',
                 'RESTAURANTFLOW_RUNTIME_DB_PASSWORD': runtime_password}
    for filename, values in [('.env', app), ('.env.database', database), ('.env.migration', migration)]:
        write_private(ROOT / filename, ''.join(f'{name}={value}\n' for name, value in values.items()))


def demo_accounts():
    password = secrets.token_urlsafe(24)
    environment = {**os.environ, 'RESTAURANTFLOW_DEMO_PASSWORD': password}
    compose('exec', '-T', '-e', 'DJANGO_DEBUG=true', '-e', 'RESTAURANTFLOW_DEMO_PASSWORD',
            'web', 'python', 'manage.py', 'seed_demo', '--confirm-demo', env=environment)
    accounts = {name: secrets.token_urlsafe(20) for name in ['owner', 'manager', 'cashier', 'waiter', 'kitchen']}
    # Passwords go over the process's stdin, never command arguments or logs.
    program = ('import json\nfrom django.contrib.auth import get_user_model\n'
               'accounts=' + repr(accounts) + '\n'
               'for name,password in accounts.items():\n'
               ' user=get_user_model().objects.get(username=name)\n'
               ' user.set_password(password)\n user.save(update_fields=["password"])\n'
               'print("Independent demo account passwords configured.")\n')
    compose('exec', '-T', 'web', 'python', 'manage.py', 'shell', '--no-imports', input=program)
    return accounts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-ip', required=True)
    parser.add_argument('--source-ref', required=True)
    args = parser.parse_args()
    address = str(ipaddress.IPv4Address(args.public_ip))
    if not re.fullmatch('[0-9a-f]{40}', args.source_ref):
        parser.error('Pin an exact reviewed Git commit.')
    if os.geteuid() != 0:
        raise RuntimeError('Run the authorized installer as root.')
    os.environ['LC_ALL'] = 'C'
    if ROOT.exists():
        raise RuntimeError('/opt/restaurantflow already exists; will not overwrite another deployment.')
    if shutil.disk_usage('/opt').free < 6 * 1024**3:
        raise RuntimeError('At least 6 GiB free disk space required.')
    available = int(re.search(r'MemAvailable:\s+(\d+)', Path('/proc/meminfo').read_text()).group(1))
    if available < 2 * 1024**2:
        raise RuntimeError('Insufficient spare memory; preserve ERPNext capacity.')
    erp_health(address)
    before = nginx_hashes()
    for protocol in [socket.SOCK_STREAM, socket.SOCK_DGRAM]:
        with socket.socket(socket.AF_INET, protocol) as probe:
            probe.bind(('0.0.0.0', 443))
    print('ERPNext baseline healthy; nginx configuration fingerprint captured; port 443 is free.', flush=True)
    install_docker()
    require_erp_unchanged(address, before)
    ROOT.mkdir(mode=0o700)
    run(['git', 'clone', 'https://github.com/Shozab-110/restaurantflow.git', str(ROOT)])
    run(['git', 'checkout', '--detach', args.source_ref], cwd=ROOT)
    initialize_configuration(address)
    compose('config', '--quiet')
    compose('build', '--pull', 'web')
    # Validate without attaching named volumes: the application image must seed
    # media/static ownership before the proxy first mounts those volumes.
    run(['docker', 'run', '--rm', '--entrypoint', 'caddy',
         '--env', 'PUBLIC_IP=' + address,
         '--volume', str(ROOT / 'deploy/Caddyfile.cohost') + ':/etc/caddy/Caddyfile:ro',
         'caddy:2.11.7-alpine', 'validate', '--config', '/etc/caddy/Caddyfile'])
    compose('up', '-d', '--wait', '--wait-timeout', '240')
    require_erp_unchanged(address, before)
    compose('exec', '-T', 'web', 'python', 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING')
    accounts = demo_accounts()
    # TLS verification is deliberately enabled. No insecure certificate bypass.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for attempt in range(60):
        try:
            with opener.open('https://' + address + '/health/', timeout=10) as response:
                if json.load(response) != {'status': 'ok', 'database': 'postgresql'}:
                    raise RuntimeError('Unexpected application health result.')
            break
        except OSError:
            if attempt == 59:
                raise
            time.sleep(5)
    require_erp_unchanged(address, before)
    result = {'state': 'deployed', 'url': 'https://' + address + '/', 'erp_status': 200,
              'nginx_configuration_unchanged': True, 'source_commit': args.source_ref,
              'demo_accounts': accounts, 'note': 'New isolated demo database; laptop data was not copied.'}
    write_private(RESULT, json.dumps(result, indent=2))
    print('RF_DEPLOYMENT_RESULT=' + json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
