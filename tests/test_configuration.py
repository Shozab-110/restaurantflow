"""Safety checks for the setup helper; these do not require a database."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from dotenv import dotenv_values

spec = importlib.util.spec_from_file_location(
    'configure_local', Path(__file__).resolve().parents[1] / 'scripts/configure_local.py')
configuration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configuration)


class ConfigurationTests(unittest.TestCase):
    def test_existing_configuration_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('original configuration', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                configuration.create_environment(path)
            self.assertEqual(path.read_text(encoding='utf-8'), 'original configuration')

    def test_generated_secrets_are_unique_and_development_settings_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ['first.env', 'second.env']]
            for path in paths:
                configuration.create_environment(path)
            first, second = [dotenv_values(path) for path in paths]
            self.assertNotEqual(first['DJANGO_SECRET_KEY'], second['DJANGO_SECRET_KEY'])
            self.assertNotEqual(first['POSTGRES_PASSWORD'], second['POSTGRES_PASSWORD'])
            self.assertGreaterEqual(len(first['DJANGO_SECRET_KEY']), 50)
            self.assertEqual(first['DJANGO_DEBUG'], 'true')
            self.assertEqual(first['DJANGO_SECURE_SSL_REDIRECT'], 'false')
            self.assertEqual(first['POSTGRES_PORT'], '5433')

    def test_existing_password_round_trips_without_interpolation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            password = "spaces # dollars $ literal ${NO_SUCH_VALUE} ' quote \\ slash"
            configuration.create_environment(path, database_password=password, port=5432)
            self.assertEqual(dotenv_values(path, interpolate=False)['POSTGRES_PASSWORD'], password)

    def test_invalid_values_do_not_create_partial_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            for options in [{'port': 70000}, {'user': 'name\nINJECTED=true'}]:
                with self.assertRaises(ValueError):
                    configuration.create_environment(path, **options)
                self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
