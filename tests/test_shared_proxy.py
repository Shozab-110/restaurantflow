"""Guard shared-service preservation and private ERP bridge generation."""
from copy import deepcopy
import unittest

from deploy.shared_proxy import merge_routes, nginx_bridge


class SharedProxyTests(unittest.TestCase):
    def setUp(self):
        self.existing = {'admin': {'listen': '127.0.0.1:2019'}, 'apps': {
            'http': {'servers': {'shared': {'listen': [':443'], 'routes': [
                {'@id': 'existing-app', 'match': [{'host': ['other.example.com']}],
                 'handle': [{'handler': 'reverse_proxy', 'upstreams': [{'dial': '192.0.2.20:2424'}]}]}]}}},
            'tls': {'automation': {'policies': [{'issuers': [{'module': 'acme', 'email': 'ops@example.com'}]}]}}}}

    def test_preserves_existing_hosts_and_certificate_policy_and_is_idempotent(self):
        before = deepcopy(self.existing)
        merged = merge_routes(self.existing, '192.0.2.10')
        self.assertEqual(self.existing, before)
        self.assertEqual(merged['apps']['http']['servers']['shared']['routes'][0],
                         before['apps']['http']['servers']['shared']['routes'][0])
        self.assertEqual(merged['apps']['tls']['automation']['policies'][1:],
                         before['apps']['tls']['automation']['policies'])
        self.assertEqual(merge_routes(merged, '192.0.2.10'), merged)
        self.assertEqual(merged['admin'], before['admin'])

    def test_refuses_ambiguous_or_existing_ip_routing(self):
        for change in [[], [{'host': ['192.0.2.10']}], [{'host': ['*.example.com']}]]:
            with self.subTest(change=change):
                config = deepcopy(self.existing)
                config['apps']['http']['servers']['shared']['routes'][0]['match'] = change
                with self.assertRaises(ValueError):
                    merge_routes(config, '192.0.2.10')

    def test_bridge_preserves_site_assets_headers_and_websocket_rules(self):
        original = 'upstream backend { server 127.0.0.1:8000; }\nserver {\n listen 80;\n listen [::]:80;\n root /srv/erp/sites;\n location /assets { try_files $uri =404; }\n location /socket.io { proxy_pass http://backend; }\n proxy_set_header X-Frappe-Site-Name erp.example;\n}\n'
        result = nginx_bridge(original)
        self.assertIn('listen 127.0.0.1:18081;', result)
        self.assertIn('listen [::1]:18081;', result)
        for line in original.splitlines():
            if 'listen ' not in line:
                self.assertIn(line, result)
        self.assertNotIn('listen 80;', result)
        with self.assertRaises(ValueError):
            nginx_bridge(original.replace('listen 80;', 'listen 443 ssl;'))
