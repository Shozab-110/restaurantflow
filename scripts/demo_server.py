"""Run a preinstalled RestaurantFlow demo on a local network without internet."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_NETWORKS = tuple(ipaddress.ip_network(value) for value in
                         ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'])


def private_ipv4(value):
    address = ipaddress.ip_address(value)
    if address.version != 4 or not any(address in network for network in PRIVATE_NETWORKS):
        raise ValueError('Use the laptop private Wi-Fi/hotspot IPv4 address.')
    return str(address)


def local_addresses():
    """Resolve this computer's own name, never probe a public internet host."""
    try:
        candidates = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except socket.gaierror:
        return []
    found = set()
    for candidate in candidates:
        try:
            found.add(private_ipv4(candidate[4][0]))
        except ValueError:
            continue
    return sorted(found)


def demo_environment(current, addresses, port):
    if not 1024 <= port <= 65535:
        raise ValueError('Choose a port between 1024 and 65535.')
    if current.get('DJANGO_DEBUG', 'false').lower() != 'true':
        raise ValueError('LAN demo requires a development/demo .env with DJANGO_DEBUG=true; use HTTPS deployment for production.')
    database_host = current.get('POSTGRES_HOST', '127.0.0.1')
    if database_host not in ['127.0.0.1', 'localhost', '::1']:
        try:
            private_ipv4(database_host)
        except ValueError:
            raise ValueError('Offline demo requires PostgreSQL on this computer or its private LAN; keep VPS database configuration separate.') from None
    addresses = list(dict.fromkeys(private_ipv4(value) for value in addresses))
    if not addresses:
        raise ValueError('No private IPv4 address found. Connect to local Wi-Fi/hotspot, or supply --host-ip.')
    hosts = ['127.0.0.1', 'localhost', *addresses]
    return {**current, 'DJANGO_ALLOWED_HOSTS': ','.join(hosts),
            'CSRF_TRUSTED_ORIGINS': ','.join(f'http://{host}:{port}' for host in hosts),
            'DJANGO_SECURE_SSL_REDIRECT': 'false', 'TRUST_PROXY_HEADERS': 'false',
            'PYTHONUNBUFFERED': '1'}


def healthy(port):
    # Bypass system HTTP proxies: the demo never needs an internet proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f'http://127.0.0.1:{port}/health/', timeout=2) as response:
            content = json.load(response)
            return response.status == 200 and content == {'status': 'ok', 'database': 'postgresql'}
    except (OSError, ValueError, urllib.error.URLError):
        return False


def show_urls(addresses, port):
    print('\nRestaurantFlow OFFLINE LAN DEMO', flush=True)
    print(f'Laptop: http://127.0.0.1:{port}/', flush=True)
    print('On phones/tablets connected to the SAME Wi-Fi/hotspot, try the Wi-Fi address:', flush=True)
    for address in addresses:
        print(f'  http://{address}:{port}/', flush=True)
    print('Use separate cashier / waiter / kitchen accounts. Internet is not required.', flush=True)
    print('Keep the laptop awake and this server window open. Ctrl+C stops this demo.', flush=True)
    print('If devices cannot connect, run Enable LAN Access.cmd once (Windows admin approval).', flush=True)
    print('Use demo accounts on a trusted local network; this HTTP demo is not public hosting.\n', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8001)
    parser.add_argument('--host-ip', action='append', help='Laptop private IPv4; repeat if needed.')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--check', action='store_true', help='Validate local configuration without starting services.')
    args = parser.parse_args()
    from dotenv import load_dotenv
    if not (ROOT / '.env').is_file():
        parser.exit(1, 'Missing .env. Complete docs/GETTING_STARTED.md once while online.\n')
    load_dotenv(ROOT / '.env', interpolate=False)
    addresses = args.host_ip or local_addresses()
    try:
        environment = demo_environment(dict(os.environ), addresses, args.port)
    except ValueError as exc:
        parser.exit(1, str(exc) + '\n')
    addresses = environment['DJANGO_ALLOWED_HOSTS'].split(',')[2:]
    if args.check:
        show_urls(addresses, args.port)
        print('Configuration valid. No services started or settings changed.')
        return
    if healthy(args.port):
        show_urls(addresses, args.port)
        print('A RestaurantFlow server is already healthy on this port; no duplicate started.')
        if not args.no_browser:
            webbrowser.open(f'http://127.0.0.1:{args.port}/')
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(('0.0.0.0', args.port))
        except OSError:
            parser.exit(1, f'Port {args.port} is busy. Stop the old demo window or choose --port.\n')
    runtimes = [ROOT / '.local/pg-runtime/pgsql/bin/pg_ctl.exe', ROOT / '.local/pgsql/bin/pg_ctl.exe']
    if os.name == 'nt' and any(path.is_file() for path in runtimes):
        if not (ROOT / '.local/pgdata/PG_VERSION').is_file():
            parser.exit(1, 'Portable database data is missing. Restore/setup the demo database; the launcher will not create an empty replacement.\n')
        subprocess.run([sys.executable, str(ROOT / 'scripts/local_postgres.py'), 'start'],
                       cwd=ROOT, env=environment, check=True)
    process = subprocess.Popen([sys.executable, 'manage.py', 'runserver',
                                f'0.0.0.0:{args.port}', '--noreload'], cwd=ROOT, env=environment)
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError('Demo server exited. Read the error above.')
            if healthy(args.port):
                show_urls(addresses, args.port)
                if not args.no_browser:
                    webbrowser.open(f'http://127.0.0.1:{args.port}/')
                break
            time.sleep(0.5)
        else:
            raise RuntimeError('Demo startup timed out. Check PostgreSQL and the server output.')
        process.wait()
    except KeyboardInterrupt:
        print('\nStopping demo server; PostgreSQL records remain saved.')
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc))
