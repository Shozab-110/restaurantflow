"""Protect existing services from shared-host port and credential collisions."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('docker'), 'Docker CLI required for Compose schema validation')
class CohostConfigurationTests(unittest.TestCase):
    def compose_services(self, filename):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            shutil.copyfile(ROOT / filename, folder / 'compose.yml')
            (folder / '.env').write_text('PUBLIC_IP=192.0.2.10\nPOSTGRES_USER=runtime_user\nPOSTGRES_PASSWORD=synthetic-runtime-only\n')
            (folder / '.env.database').write_text('POSTGRES_USER=migration_user\nPOSTGRES_PASSWORD=synthetic-migration-only\nPOSTGRES_DB=restaurantflow\n')
            (folder / '.env.migration').write_text('POSTGRES_USER=migration_user\nPOSTGRES_PASSWORD=synthetic-migration-only\nRESTAURANTFLOW_RUNTIME_DB_USER=runtime_user\nRESTAURANTFLOW_RUNTIME_DB_PASSWORD=synthetic-runtime-only\n')
            config = folder / 'docker-config'
            config.mkdir()
            result = subprocess.run(['docker', '--config', str(config), 'compose',
                '--env-file', str(folder / '.env'), '-f', str(folder / 'compose.yml'),
                'config', '--format', 'json'], capture_output=True, text=True, check=True)
            return json.loads(result.stdout)['services']

    def test_only_https_is_published_and_web_has_no_migration_credentials(self):
        services = self.compose_services('docker-compose.cohost.yml')
        self.assertEqual(services['web']['environment']['POSTGRES_USER'], 'runtime_user')
        self.assertNotIn('RESTAURANTFLOW_RUNTIME_DB_PASSWORD', services['web']['environment'])
        self.assertNotIn('synthetic-migration-only', json.dumps(services['web']))
        self.assertEqual(services['init']['environment']['POSTGRES_USER'], 'migration_user')
        for name in ['db', 'init', 'web']:
            self.assertFalse(services[name].get('ports'), name)
            self.assertIn('mem_limit', services[name])
        self.assertEqual({str(port['published']) for port in services['proxy']['ports']}, {'443'})
        caddy = (ROOT / 'deploy/Caddyfile.cohost').read_text()
        self.assertIn('auto_https disable_redirects', caddy)
        self.assertIn('disable_http_challenge', caddy)
        self.assertNotRegex(caddy, r':80(?:\s|$)')

    def test_shared_proxy_only_publishes_loopback_and_preserves_volume_names(self):
        services = self.compose_services('docker-compose.shared.yml')
        for name in ['db', 'init', 'web']:
            self.assertFalse(services[name].get('ports'), name)
        ports = services['proxy']['ports']
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0]['host_ip'], '127.0.0.1')
        self.assertEqual(str(ports[0]['published']), '18080')
        self.assertNotIn('synthetic-migration-only', json.dumps(services['web']))
        self.assertEqual(services['db']['volumes'][0]['source'], 'postgres')
        self.assertEqual(services['proxy']['volumes'][1]['source'], 'media')
        caddy = (ROOT / 'deploy/Caddyfile.shared').read_text()
        self.assertIn('header_up X-Forwarded-Proto https', caddy)
