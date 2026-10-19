# Contributing

Start with [Getting started](docs/GETTING_STARTED.md), then read [Architecture](docs/ARCHITECTURE.md) and [Operations and accounting](docs/OPERATIONS.md).

## Development workflow

1. Create a branch from `main` for one concrete problem.
2. Use a separate development PostgreSQL database and synthetic data. Keep `.env`, uploads, local binaries, credentials, logs, and dumps outside Git.
3. Put transactional order/payment rules in `operations/services.py`; views should validate forms and call services.
4. Enforce permissions on the server. Preserve historical prices, payment records, kitchen submissions, cancellation reasons, and audit history.
5. Include migrations when models change. Do not edit an already deployed migration to avoid creating a new one.
6. Run the relevant checks below and describe the actual results in the pull request.

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test operations.tests --noinput
python -m unittest discover -s tests -v
npm ci
npm run build
```

For POS interaction changes, seed an isolated demonstration database, run `python scripts/render_pos_fixture.py`, then `npm run test:pos`. For production-setting changes, run the deploy check documented in [Testing](docs/TESTING.md). Do not run production security checks using placeholder secrets.

## Review expectations

- Explain the user-visible problem and resulting behavior.
- Validate money calculations, invalid transitions, duplicate requests, permissions, and races when those behaviors change.
- Keep money in Decimal; JS previews use integer minor units. The server remains authoritative.
- Use deactivation or explicit void/refund records to preserve history.
- Build CSS and bundled libraries when asset inputs change; include the resulting `static/` changes.
- Record new environment variables in `.env.example` and document migration/deployment consequences.
- Use genuine screenshots for layout work and state any verification that could not run.

Use the issue templates for reproducible bugs and feature proposals. Report vulnerabilities through the process in [SECURITY.md](SECURITY.md). A project-wide license has not yet been selected; preserve bundled third-party license notices.
