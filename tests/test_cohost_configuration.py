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
    def test_only_https_is_published_and_web_has_no_migration_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            shutil.copyfile(ROOT / 'docker-compose.cohost.yml', folder / 'compose.yml')
            (folder / '.env').write_text('PUBLIC_IP=192.0.2.10\nPOSTGRES_USER=runtime_user\nPOSTGRES_PASSWORD=synthetic-runtime-only\n')
            (folder / '.env.database').write_text('POSTGRES_USER=migration_user\nPOSTGRES_PASSWORD=synthetic-migration-only\nPOSTGRES_DB=restaurantflow\n')
            (folder / '.env.migration').write_text('POSTGRES_USER=migration_user\nPOSTGRES_PASSWORD=synthetic-migration-only\nRESTAURANTFLOW_RUNTIME_DB_USER=runtime_user\nRESTAURANTFLOW_RUNTIME_DB_PASSWORD=synthetic-runtime-only\n')
            config = folder / 'docker-config'
            config.mkdir()
            result = subprocess.run(['docker', '--config', str(config), 'compose',
                '--env-file', str(folder / '.env'), '-f', str(folder / 'compose.yml'),
                'config', '--format', 'json'], capture_output=True, text=True, check=True)
            services = json.loads(result.stdout)['services']
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
