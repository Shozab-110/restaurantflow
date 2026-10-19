# RestaurantFlow

A persistent, multi-user restaurant POS, order management, and kitchen display application built with Django and PostgreSQL. RestaurantFlow connects the dining room, kitchen, and cashier through a shared workflow, with a custom business frontend rather than a dependency on Django Admin.

## What it does

- Secure staff login, rate limiting, password changes, owner/manager password resets, role assignment, and account activation.
- Custom dashboard with actual paid-and-fulfilled sales, net cash/digital collections, order value, table occupancy, recent orders, top items, and a Chart.js trend.
- Touch-friendly POS with category/search filters, draft quantity/notes editing, dine-in, takeaway, and delivery details.
- Kitchen tickets with instructions, elapsed times, overdue indicators, validated transitions, additional submissions, and five-second HTMX polling.
- Separate order, fulfillment, kitchen, and payment states. Tables remain occupied until fulfillment and full settlement, then become available.
- Decimal billing, historical price/tax/currency snapshots, permission-controlled discounts, partial/multiple payments, idempotency keys, and row locking.
- Manually confirmed cash, card, bank, and other digital payments. **No live payment gateway is connected.**
- Safe cancellation and kitchen-item voiding, recorded reasons, confirmed full refunds for eligible open orders, and audit history.
- Frontend menu/category CRUD, validated image uploads, table/area management, customers, discount offers, staff, restaurant settings, and a payment ledger.
- Date-filtered daily/item/category/cashier/payment/discount/cancellation/outstanding/kitchen reports and CSV exports; print-friendly HTML bills/receipts.

## Stack and structure

Python 3.12, Django 5.2 LTS, PostgreSQL 17, Django templates, compiled Tailwind CSS, locally bundled HTMX/Alpine.js/Chart.js, Django Axes, WhiteNoise, Gunicorn, Docker Compose, and optional Caddy HTTPS reverse proxy. Dependencies are pinned in `requirements.lock` and `package-lock.json`; compiled frontend assets are checked in so local Python startup does not need Node.

```text
restaurantflow/       Environment-based Django configuration
operations/           Models, permissions, forms, views, reporting
  services.py         Transactional ordering, kitchen, payment, refund rules
  migrations/         PostgreSQL schema migrations
  management/commands/ Safe initialization and separate demo seeding
  tests/              Business, frontend, security, and concurrency tests
templates/            Shared design system and custom business pages
static/               Compiled CSS, local libraries, application JS
scripts/              Asset build, initialization, health and Windows startup
deploy/               HTTPS reverse proxy configuration
docs/                 Operations and deployment guides
PROGRESS.md           Actual verification results and remaining limitations
```

## Screenshots

Browser verification results and screenshots, when available, are recorded in `PROGRESS.md`. The application includes dashboard, POS, kitchen, floor layout, management, and print receipt views. No mock screenshots are presented as proof of functionality.

## Roles

| Role | Business access |
|---|---|
| Owner | All business operations, settings, staff/roles, reports, audit |
| Manager | Operations, menu/tables/customers, discounts/cancellations, reports, audit; manages operational staff |
| Cashier | POS, all orders, service/handoff, payments, customers, dashboard and own payment activity |
| Waiter | Assigned/unassigned available tables, own/assigned dine-in orders, kitchen submission, serving, bill requests |
| Kitchen Staff | Kitchen board and preparing/ready transitions |

Business owners are normal Django users with group permissions, not technical superusers. Business staff cannot access the technical admin. Inactive users cannot authenticate. Views and transactional services both enforce permissions.

## Local installation with PostgreSQL

Use Python 3.12+ and PostgreSQL 14+ (17 is recommended). **There is no SQLite fallback.**

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
cp .env.example .env
```

Set `DJANGO_SECRET_KEY` to a randomly generated value (e.g. `python -c "import secrets; print(secrets.token_urlsafe(60))"`). For loopback development set `DJANGO_DEBUG=true`, `DJANGO_SECURE_SSL_REDIRECT=false`, `TRUST_PROXY_HEADERS=false`, `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`, and the PostgreSQL connection fields. Do not reuse local secrets for production.

Create the database/user using your PostgreSQL installation, or start just the database with Docker:

```bash
docker compose up -d db
# For a host Python process, use your installed PostgreSQL or publish a loopback-only
# database port with a local Compose override. The default Compose database is internal.
python manage.py migrate
python manage.py bootstrap_roles
python manage.py create_owner --username owner --email owner@example.com
python manage.py collectstatic --noinput
python manage.py runserver 127.0.0.1:8000
```

`create_owner` prompts for the password without echoing it, or reads `RESTAURANTFLOW_OWNER_PASSWORD` temporarily from the environment. It refuses to overwrite existing users or create a second initial owner; subsequent accounts are managed in **Staff & Roles**. Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

For this Windows workspace, the official portable PostgreSQL runtime is installed under ignored `.local/pg-runtime/pgsql/` (the helper also supports `.local/pgsql/`). With the runtime installed and `.env` configured, `python scripts/local_postgres.py start` initializes a password-authenticated cluster bound only to `127.0.0.1` and creates the application database. `scripts/start.ps1` starts it and Django; `python scripts/local_postgres.py stop` stops it. Its workspace port is 5433. This helper does not install or change Windows services. Binaries come from the [official PostgreSQL Windows download](https://www.postgresql.org/download/windows/) / [EDB vendor archive](https://www.enterprisedb.com/download-postgresql-binaries), and are not included in Git.

## Demonstration setup

Use a **separate non-production database** with `DJANGO_DEBUG=true`:

```bash
python manage.py migrate
# Set RESTAURANTFLOW_DEMO_PASSWORD in your shell to a strong temporary password.
python manage.py seed_demo --confirm-demo
```

This idempotent command adds The Olive Table, 3 areas, 12 tables, 5 categories, 25 items, sample customers, realistic paid/open/cancelled orders, kitchen tickets, payments, and `owner`, `manager`, `cashier`, `waiter`, `kitchen` accounts. It does not reset existing passwords or overwrite operational records. New demo accounts use the password you supplied; keep it out of Git and unset it afterward. **Never seed or retain demo accounts on a live restaurant database.**

If this workspace was initialized during implementation, locally generated demo access details are in the ignored `.local/demo-access.txt` file. These are disposable local credentials, not production credentials.

## Daily workflows

1. **Dine-in:** waiter selects a table → creates items → sends kitchen ticket → kitchen starts and marks ready → waiter marks served → cashier prints bill and records full/partial collections → order closes when fully settled → table releases.
2. **Takeaway/delivery:** cashier creates order → kitchen prepares and marks ready → cashier collects the full bill → confirms handoff. Delivery requires name, phone, and address.
3. **Added items:** open an existing unfulfilled order → Add items → save → Send new items to kitchen. Existing tickets remain intact.
4. **Cancellation:** manager/owner opens an eligible open order → gives a reason → if money was collected, returns it manually via original methods and confirms this → cancellation/refunds recorded atomically. Retrying does not create duplicate refunds.

See [operations and accounting rules](docs/OPERATIONS.md) for detailed behavior.

## Testing and asset development

Executed build verification: **29 PostgreSQL tests and 5 POS DOM interaction tests passed**, with additional focused authentication/page regressions. Normal and production security checks, migration consistency, real HTTP owner login/17 endpoints/8 assets, and production WhiteNoise assets passed. Browser screenshot/layout and Docker/HTTPS runtime verification remain environment-blocked; exact details and next actions are in [PROGRESS.md](PROGRESS.md).

The test database uses PostgreSQL. The test user needs `CREATEDB` on a **development/test server**, not on a production application role.

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test operations.tests --verbosity 2
# Run with production environment flags and a real random secret:
DJANGO_DEBUG=false python manage.py check --deploy --fail-level WARNING
```

On PowerShell set `$env:DJANGO_DEBUG='false'` for the deploy check, then remove it to restore `.env` development settings. Workflow, authentication, role enforcement, menu administration, immutable prices, table conflicts, kitchen transitions, Decimal/partial/idempotent payments, cancellation/refunds, reporting reconciliation, uploads, password changes, frontend routes, and PostgreSQL concurrency are tested. Consult `PROGRESS.md` for actual executed results; the existence of tests alone is not a passed test run.

To change CSS or library versions:

```bash
npm ci
npm run build
python manage.py collectstatic --noinput
```

To verify POS interactions without a browser against a seeded development database:

```bash
python scripts/render_pos_fixture.py
npm run test:pos
```

These five DOM tests exercise the actual rendered POS markup: checkout requirements, quantity changes, special instructions, search/categories, and integer-based tax/service previews. They do not replace responsive browser layout or receipt-printer verification.

## Database overview

Restaurant settings are a singleton; Django users/groups supply authentication and permissions. Areas own tables, categories own menu items, and customers are optional order references. Orders snapshot customer details, currency, tax/service rates, item names/categories/prices. Order items are individually linked to kitchen ticket lines; each new submission contains only unsent lines. Payments are an append-only business ledger with unique retry tokens and one-to-one original-payment refund links. Audit entries record staff actions and reasons. Historical foreign keys use protection rather than cascade deletion.

Unique partial constraints prevent more than one open order per table; monetary and table/type constraints complement service validation. Critical services use transactions and PostgreSQL `SELECT FOR UPDATE`. Every menu change affects future additions only. Category and item deactivation preserves order history.

## Deployment

See [Ubuntu / Docker deployment](docs/DEPLOYMENT.md) for HTTPS, secrets, migration sequencing, media/static files, health checks, backups, and restore commands. Production uses PostgreSQL and Gunicorn behind an HTTPS reverse proxy. **Do not expose Django runserver or a database port to the internet.**

```bash
docker compose config --quiet
docker compose up -d --build
docker compose exec web python manage.py create_owner --username owner
# With DNS configured and RESTAURANT_DOMAIN set:
docker compose --profile https up -d
```

No GitHub remote is configured and nothing is published automatically.

## Known scope limits

- Single restaurant per installation. No multi-tenant billing, inventory, purchasing, shift opening/closing cash reconciliation, split checks, table transfers, offline mode, or delivery dispatch integration.
- Payment methods are manually recorded; refunds must actually be performed outside the application before confirmation. No gateway or fiscal/tax authority integration.
- Closed orders are immutable in this MVP. Post-close corrections require a controlled, documented accounting adjustment outside this application; do not edit historical database rows.
- Percentage offers are converted to fixed order discounts when applied. Tax and service are computed on the discounted item subtotal using half-up currency rounding; no tax-inclusive pricing or multi-rate item tax rules.
- HTML receipts support browser printing / Save as PDF; a dedicated PDF generator and kitchen sound notifications are deferred.
- Live display uses polling, not WebSockets. A kitchen operator shares one restaurant queue.
- Production readiness requires deployment-specific HTTPS, backups, restore practice, upload serving, load checks, and business acceptance. Passing local checks alone does not certify a deployed environment.

Future improvements include inventory, formal shifts/cash drawers, split checks, controlled post-close adjustments, granular item fulfillment, and stronger deployment observability.
