"""LAN configuration must be explicit and must not depend on internet discovery."""
import importlib.util
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'demo_server', Path(__file__).resolve().parents[1] / 'scripts/demo_server.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class DemoLauncherTests(unittest.TestCase):
    def test_child_configuration_is_limited_to_explicit_local_hosts(self):
        original = {'DJANGO_DEBUG': 'true', 'POSTGRES_HOST': '127.0.0.1',
                    'DJANGO_ALLOWED_HOSTS': 'localhost', 'TRUST_PROXY_HEADERS': 'true'}
        result = demo.demo_environment(original, ['192.168.18.13', '192.168.18.13'], 8001)
        self.assertEqual(result['DJANGO_ALLOWED_HOSTS'], '127.0.0.1,localhost,192.168.18.13')
        self.assertIn('http://192.168.18.13:8001', result['CSRF_TRUSTED_ORIGINS'])
        self.assertEqual(result['POSTGRES_HOST'], '127.0.0.1')
        self.assertEqual(result['TRUST_PROXY_HEADERS'], 'false')
        self.assertEqual(original['DJANGO_ALLOWED_HOSTS'], 'localhost')

    def test_public_addresses_production_and_invalid_ports_are_rejected(self):
        for address in ['8.8.8.8', '0.0.0.0', '127.0.0.1', '169.254.1.1', '::1', '*', 'example.com']:
            with self.subTest(address=address), self.assertRaises(ValueError):
                demo.demo_environment({'DJANGO_DEBUG': 'true'}, [address], 8001)
        for current, addresses, port in [({}, ['192.168.1.2'], 8001),
                ({'DJANGO_DEBUG': 'false'}, ['192.168.1.2'], 8001),
                ({'DJANGO_DEBUG': 'true', 'POSTGRES_HOST': 'remote.example.com'}, ['192.168.1.2'], 8001),
                ({'DJANGO_DEBUG': 'true'}, [], 8001),
                ({'DJANGO_DEBUG': 'true'}, ['192.168.1.2'], 80),
                ({'DJANGO_DEBUG': 'true'}, ['192.168.1.2'], 65536)]:
            with self.subTest(port=port), self.assertRaises(ValueError):
                demo.demo_environment(current, addresses, port)

    def test_discovery_resolves_only_computer_name_and_filters_non_lan_addresses(self):
        candidates = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (value, 0)) for value in
                      ['192.168.1.2', '10.0.0.2', '192.168.1.2', '127.0.0.1', '169.254.1.1', '8.8.8.8']]
        with patch.object(demo.socket, 'gethostname', return_value='local-laptop'), \
                patch.object(demo.socket, 'getaddrinfo', return_value=candidates) as resolver:
            self.assertEqual(demo.local_addresses(), ['10.0.0.2', '192.168.1.2'])
            resolver.assert_called_once_with('local-laptop', None, socket.AF_INET)


if __name__ == '__main__':
    unittest.main()
