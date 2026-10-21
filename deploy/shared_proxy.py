"""Prepare an additive shared-Caddy plan. Never loads it or restarts services."""
import argparse
from copy import deepcopy
import ipaddress
import json
import os
from pathlib import Path
import re


def merge_routes(current, public_ip):
    """Preserve unrelated hosts/policies; reject layouts requiring manual review."""
    address = str(ipaddress.IPv4Address(public_ip))
    planned = deepcopy(current)
    servers = planned['apps']['http']['servers']
    candidates = [server for server in servers.values() if server.get('listen') == [':443']]
    if len(candidates) != 1:
        raise ValueError('Expected one shared :443 server; inspect this proxy manually.')
    desired = {'@id': 'restaurantflow-web', 'match': [{'host': [address]}],
               'handle': [{'handler': 'reverse_proxy', 'upstreams': [{'dial': '127.0.0.1:18080'}]}],
               'terminal': True}
    # A controller can compare its exact :443 route list and replace the whole
    # config when another app appends a route there. Keep that entire server intact.
    https = {'listen': [':8443'], 'routes': [desired],
             'tls_connection_policies': [{'default_sni': address}]}
    existing = servers.get('restaurantflow_https')
    if existing and existing != https:
        raise ValueError('Existing RestaurantFlow HTTPS server differs; refusing to replace it.')
    if any(any(listener.endswith(':8443') for listener in server.get('listen', []))
           for name, server in servers.items() if name != 'restaurantflow_https'):
        raise ValueError('Port 8443 is already configured; inspect its owner.')
    servers['restaurantflow_https'] = https
    erp_server = {'listen': [':80'], 'automatic_https': {'disable': True}, 'routes': [
        {'@id': 'restaurantflow-erp', 'match': [{'host': [address]}],
         'handle': [{'handler': 'reverse_proxy', 'upstreams': [{'dial': '127.0.0.1:18081'}]}],
         'terminal': True}]}
    existing = servers.get('restaurantflow_erp_http')
    if existing and existing != erp_server:
        raise ValueError('Existing ERP bridge server differs; refusing to replace it.')
    if any(':80' in server.get('listen', []) for name, server in servers.items()
           if name != 'restaurantflow_erp_http'):
        raise ValueError('An explicit HTTP listener already exists; merge it manually.')
    servers['restaurantflow_erp_http'] = erp_server
    automation = planned['apps'].setdefault('tls', {}).setdefault('automation', {})
    policies = automation.setdefault('policies', [])
    ip_policy = {'subjects': [address], 'issuers': [{'module': 'acme',
        'ca': 'https://acme-v02.api.letsencrypt.org/directory', 'profile': 'shortlived',
        'challenges': {'http': {'disabled': True}}}]}
    matches = [policy for policy in policies if address in policy.get('subjects', [])]
    if matches and matches != [ip_policy]:
        raise ValueError('An existing certificate policy already handles this IP.')
    if not matches:
        policies.insert(0, ip_policy)
    return planned


def nginx_bridge(site_config):
    """Use a private copy of a single audited HTTP-only ERP site, preserving assets/socket.io."""
    listeners = re.findall(r'^\s*listen\s+([^;]+);', site_config, flags=re.M)
    if not listeners or any(value.strip() not in ['80', '[::]:80'] for value in listeners):
        raise ValueError('ERP site must contain only simple port-80 listeners; inspect it manually.')
    if re.search(r'^\s*include\s', site_config, flags=re.M):
        raise ValueError('ERP site includes require manual inspection.')
    private_site = re.sub(r'(^\s*listen\s+)80;', r'\g<1>127.0.0.1:18081;', site_config, flags=re.M)
    private_site = re.sub(r'(^\s*listen\s+)\[::\]:80;', r'\g<1>[::1]:18081;', private_site, flags=re.M)
    return ('user www-data;\nworker_processes 1;\npid /run/restaurantflow-erp-bridge.pid;\n'
            'error_log /var/log/nginx/restaurantflow-bridge-error.log;\n'
            'events { worker_connections 512; }\nhttp {\n'
            'include /etc/nginx/mime.types;\ndefault_type application/octet-stream;\n'
            'access_log /var/log/nginx/restaurantflow-bridge-access.log;\n'
            'set_real_ip_from 127.0.0.1;\nreal_ip_header X-Forwarded-For;\nreal_ip_recursive on;\n'
            + private_site + '\n}\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current-json', type=Path, required=True)
    parser.add_argument('--public-ip', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Exclusive creation prevents accidentally replacing an existing plan/backup.
    plan = merge_routes(json.loads(args.current_json.read_text()), args.public_ip)
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as destination:
        destination.write(json.dumps(plan, indent=2) + '\n')
    print('Prepared shared proxy plan. No running service was changed.')
