# Security and sensitive data

RestaurantFlow is a tested MVP with deployment-specific checks still required. See [verification results](docs/TESTING.md) and [deployment requirements](docs/DEPLOYMENT.md).

## Reporting a vulnerability

Do not publish exploit details, credentials, or customer/payment data in a public issue. Use this repository's **Security → Advisories → Report a vulnerability** option if enabled. If that option is unavailable, contact the repository owner through their [GitHub profile](https://github.com/Shozab-110) to arrange a private reporting channel before sharing details.

Include the affected commit, minimal reproduction using synthetic data, the role/permissions involved, impact, and a suggested fix if available. Remove secrets and personal data from logs and screenshots.

## Deployment boundaries

- Keep `.env`, database files/dumps, staff/customer data, and local viewer credentials out of Git.
- Production needs HTTPS, specific allowed hosts/origins, secure cookies, a strong random secret, and a trusted reverse proxy.
- Use a restricted production database runtime role; the simple Compose initialization user is a migration/bootstrap account.
- Keep PostgreSQL and development servers off the public internet.
- Use an isolated test database with CREATEDB privileges; do not grant that privilege to the production runtime role.
- Verify backups by restoring into an isolated environment.
- Local pgAdmin access is an optional developer tool. Do not expose it as a public business interface.

There is no promised security support period or production SLA. Update dependencies and review the application's operational limits before using it with live restaurant data.
