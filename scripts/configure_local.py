"""Create a development .env without overwriting existing configuration."""
import argparse
import getpass
import os
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parent.parent


def create_environment(output, *, host='127.0.0.1', port=5433,
                       database='restaurantflow', user='restaurantflow',
                       database_password=None):
    """Create the file exclusively; existing credentials are never replaced."""
    if not 1 <= int(port) <= 65535:
        raise ValueError('Database port must be between 1 and 65535.')
    connection = {'POSTGRES_HOST': host, 'POSTGRES_DB': database,
                  'POSTGRES_USER': user,
                  'POSTGRES_PASSWORD': database_password or secrets.token_urlsafe(32)}
    for value in connection.values():
        if not value or any(c in value for c in '\r\n\x00'):
            raise ValueError('Connection values must be nonempty single-line values.')
    lines = [
        '# Generated for local development. Keep this file out of Git.',
        'DJANGO_SECRET_KEY=' + secrets.token_urlsafe(60),
        'DJANGO_DEBUG=true',
        'DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1',
        'CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000',
        'DJANGO_TIME_ZONE=Asia/Karachi',
        'DJANGO_SECURE_SSL_REDIRECT=false',
        'TRUST_PROXY_HEADERS=false',
    ]
    # Serialize existing native PostgreSQL credentials for python-dotenv without
    # interpolation. Generated credentials are URL-safe for Compose as well.
    for name, value in connection.items():
        escaped = value.replace('\\', '\\\\').replace("'", "\\'")
        lines.append(f"{name}='{escaped}'")
    lines.extend([f'POSTGRES_PORT={int(port)}', 'APP_PORT=8000'])
    path = Path(output)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(lines) + '\n')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.env')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5433)
    parser.add_argument('--database', default='restaurantflow')
    parser.add_argument('--user', default='restaurantflow')
    parser.add_argument('--existing-database', action='store_true',
                        help='Prompt for an existing PostgreSQL password without echoing it.')
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(1, f'{args.output} already exists; no changes made.\n')
    password = os.getenv('POSTGRES_PASSWORD')
    if args.existing_database and not password:
        password = getpass.getpass('Existing PostgreSQL password (hidden): ')
        if not password:
            parser.exit(1, 'An existing database password is required.\n')
    try:
        path = create_environment(args.output, host=args.host, port=args.port,
                                  database=args.database, user=args.user,
                                  database_password=password)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Configuration was not created: {exc}\n')
    print(f'Created {path}. No secrets printed; existing files are never overwritten.')
    print(f'Development database: {args.database} on {args.host}:{args.port}.')
    print('Next: follow docs/GETTING_STARTED.md for Docker or native Python startup.')


if __name__ == '__main__':
    main()
