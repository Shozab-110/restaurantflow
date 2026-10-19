# Testing and verification evidence

## Evidence from the implemented build

The original Windows/Python 3.12.2/PostgreSQL 17.11 build completed:

| Check | Result |
|---|---|
| Full PostgreSQL business suite | **29 tests passed**, 163.635 seconds |
| Additional final page/form regression | Passed after sorting/wording changes |
| Additional final authentication regression | Passed, including a second staff account on the same IP |
| POS interactions against actual rendered markup | **5 DOM tests passed** |
| Normal / production Django checks | Passed with zero issues |
| Migration consistency / applied schema | Passed; no model changes missing migrations |
| Owner login and primary HTTP routes | Passed: 17 endpoints, 8 local assets |
| Production Django/WhiteNoise request stack | Dashboard, orders, reports and hashed CSS/HTMX returned 200 |
| Frontend build / static collection / JS syntax | Passed |
| Demo idempotency and threaded transaction tests | Passed as part of the PostgreSQL suite |

Repository-preparation rerun on Windows: 29 PostgreSQL tests passed in 80.435 seconds, 5 POS DOM tests and 4 configuration-helper tests passed, as did the HTTP/static/configuration checks. The thread-cleanup regression then passed both concurrency tests with successful fresh test-database deletion.

## Verified Linux and Docker run

The [successful GitHub CI run](https://github.com/Shozab-110/restaurantflow/actions/runs/39275185992), dated 2026-10-19 on application commit `bad6305`, verified:

- **29 PostgreSQL tests** in 15.107 seconds, including successful fresh test-database cleanup.
- **4 configuration-helper tests** and **5 POS DOM tests**: 38 automated tests total.
- Locked dependency installation, asset build/static collection, migration consistency, 44 relative documentation links, normal Django checks and production settings checks.
- Full Linux Docker image build and stack initialization; PostgreSQL/Gunicorn healthy; real health and login HTTP endpoints; initial owner creation; in-container production checks; successful teardown.

The first hosted run exposed retained thread connections during test-database deletion even though its test assertions passed. Explicit per-thread connection closure fixed it; the successful run above includes that fix. See [findings](FINDINGS_AND_SOLUTIONS.md).

This verifies the application container stack on Linux. It does not verify a public Caddy certificate, target VPS configuration, responsive browser rendering, or a physical receipt printer.

## Run locally

Use an isolated development PostgreSQL server. Django creates `test_<POSTGRES_DB>` for the business suite; its test login needs CREATEDB. Keep that permission out of production runtime credentials.

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python -m unittest discover -s tests -v
python manage.py test operations.tests --noinput --verbosity 2
```

`--keepdb` can be added for repeated development runs. The PostgreSQL concurrency tests use real separate connections and threads; they are not equivalent to a SQLite test run.

## Business coverage

- Authentication, active/inactive accounts, login throttling, logout, CSRF and password changes.
- Role enforcement, order visibility/isolation, manager scope, staff resets and self-owner protection.
- Category/menu/staff creation and price updates through the custom frontend.
- Table assignment, occupied-table protection and competing operators.
- Dine-in, takeaway and delivery validation; historical names/prices/rates/currencies.
- Decimal rounding, discounts, complimentary bills and immutable closed orders.
- Kitchen transitions, duplicate dispatch, additional tickets and sent-item voids.
- Partial/multiple payments, overpayment rejection, token payload matching and duplicate concurrent requests.
- Cancellation reasons/permissions, manually confirmed refunds, retry prevention and table release.
- Sales/collections/refunds/outstanding reconciliation, currency filtering and CSV routes.
- Safe uploads, demo idempotency, and all primary page/form routes.

The four requested scenarios—dine-in, takeaway, owner administration, cancellation—are exercised. The dine-in HTTP client test changes roles through POS creation, kitchen preparation, serving, receipt and final payment.

## POS DOM tests

Against a **seeded development** database:

```bash
npm ci
npm run build
python scripts/render_pos_fixture.py
npm run test:pos
```

The fixture is actual Django-rendered POS HTML in ignored `.local/verified-pos.html`. Tests execute the real `static/js/pos.js` in JSDOM and verify checkout blocking, quantities/tax/service previews, notes/customizations, filters and dine-in/delivery requirements.

JSDOM does not render CSS or certify touch targets, responsive layout, real browser printing or visual accessibility. Those remain separate browser/device checks.

## Production settings check

Use a real random secret and the intended environment. PowerShell:

```powershell
$env:DJANGO_DEBUG = 'false'
$env:DJANGO_SECURE_SSL_REDIRECT = 'true'
python manage.py check --deploy --fail-level WARNING
Remove-Item Env:DJANGO_DEBUG
Remove-Item Env:DJANGO_SECURE_SSL_REDIRECT
```

Bash:

```bash
DJANGO_DEBUG=false DJANGO_SECURE_SSL_REDIRECT=true python manage.py check --deploy --fail-level WARNING
```

Passing the checklist does not verify DNS, a public certificate, a live proxy, production database grants, backup restoration, or an actual receipt printer.

## GitHub CI

`.github/workflows/ci.yml` uses pinned official action commits and a disposable PostgreSQL 17 service. It installs locked dependencies, generates throwaway secrets, builds assets, applies migrations, checks drift, runs configuration/business/DOM tests, checks production settings, then builds/starts the full Compose stack and verifies health/login/owner initialization. It uses read-only repository permissions and does not deploy a public website.

The CI database password is explicitly disposable test configuration. Production secrets, local `.env`, database files, uploads and pgAdmin credentials are excluded from the repository/build context. Container diagnostics and teardown run even when checks fail.

Review [findings and fixes](FINDINGS_AND_SOLUTIONS.md), [screenshots/device checks](SCREENSHOTS.md), and the [go-live guide](DEPLOYMENT.md) before claiming production readiness.
