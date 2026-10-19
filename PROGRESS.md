# RestaurantFlow progress and verification

Updated: 19 October 2026 (Asia/Karachi).

## Working local application

- URL: **http://127.0.0.1:8000/**
- PostgreSQL 17.11: **127.0.0.1:5433**, password authentication, persistent data under ignored `.local/pgdata/`.
- Python 3.12.2 / Django 5.2.18. No SQLite fallback was used.
- Demonstration accounts: `owner`, `manager`, `cashier`, `waiter`, `kitchen`.
- Generated local-only password: ignored **`.local/demo-access.txt`**. No production credentials are committed.
- Restart on Windows: `./scripts/start.ps1`, or start PostgreSQL with `.venv/Scripts/python.exe scripts/local_postgres.py start` and Django with `.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000 --noreload`.
- Development server PID/logs: `.local/server.pid`, `.local/server.log`, `.local/server-error.log`.
- Local database viewer: **http://127.0.0.1:5050/** (bundled pgAdmin desktop mode, loopback only). Registered connection: `RestaurantFlow - Read only`; it uses the `restaurantflow_viewer` PostgreSQL role with SELECT access to business/staff tables and no write privileges. Viewer configuration/credentials remain ignored under `.local/pgadmin/`. pgAdmin metadata is separate from the application's PostgreSQL data.

## Completed functionality

- Normalized PostgreSQL schema, migrations, protected historical foreign keys, indexes, money constraints, and unique active table sessions.
- Secure login/logout, hashed passwords, CSRF/session protection, per-account/IP login throttling, profiles/password changes, staff resets, activation, Groups/Permissions, and protected business views/services.
- Owner/Manager/Cashier/Waiter/Kitchen roles, role-based sidebar, manager scope restrictions, and protection against last-owner/self lockout.
- All 13 custom navigation areas: dashboard, POS, orders, kitchen, tables/areas, menu, categories, customers, payments, reports, staff/roles, settings, audit.
- Frontend menu/category CRUD with deactivation, prices, availability, descriptions, ordering, dietary flags, safe/re-encoded image uploads, and preparation targets.
- Visual floor/table layout, capacities, waiter assignments, reservations/cleaning, synchronized occupation/release, and concurrent-session prevention.
- Real dine-in/takeaway/delivery orders, menu search/categories, touch cart controls, item/order notes, delivery validation, exact totals, and historical price/tax/currency snapshots.
- Kitchen batches for added items, retry prevention, preparing/ready controls, elapsed/overdue indicators, instructions, and five-second HTMX polling.
- Separate order/fulfillment/payment states, draft editing, reasoned kitchen-item voiding, serving/handoff rules, and complete order history.
- Partial/multiple manually confirmed payments, references, overpayment prevention, idempotency keys, transaction locks, discounts, configurable tax/service, accurate balances, and print-friendly bills/receipts.
- Authorized open-order cancellation with reason, explicit confirmation of externally performed refunds, one refund per collection, preserved history, and correct table release.
- Database dashboard metrics, Chart.js trend, top items, recent orders, net cash/digital collections, and own payment activity.
- Date/currency reports and CSV: daily, menu item, category, final collecting cashier, payment method, cancellations, discounts, outstanding balances, kitchen turnaround.
- Restaurant identity/logo, currency/timezone, receipt text, charge defaults, operating-hours text, and safe order-prefix settings. Currency changes require settling open orders.
- Safe `create_owner`, idempotent `bootstrap_roles`, and separated `seed_demo --confirm-demo` commands.
- Demo: three areas, 12 tables, five categories, 25 menu items, customers, five roles, paid/open/partial/cancelled orders and kitchen/payment records.
- Local Tailwind, HTMX, Alpine.js, Chart.js and vendor licenses; responsive templates, empty states, validation/notifications, confirmations, sorting/search/filtering, print CSS.
- Lockfiles, Dockerfile/Compose, migration/static initialization, Gunicorn/WhiteNoise, optional Caddy HTTPS, health probe, README, deployment/backup/restore and operations documentation.

## Executed checks

| Check | Actual result |
|---|---|
| PostgreSQL initialization/connection | PASS; official 17.11 runtime, loopback only |
| `manage.py migrate` | PASS; all Django/Axes/operations migrations applied |
| `makemigrations --check --dry-run` | PASS; no changes detected |
| `showmigrations operations` | PASS; `0001_initial` applied |
| `manage.py check` | PASS; zero issues |
| Production `check --deploy --fail-level WARNING` | PASS; zero issues, DEBUG=false |
| Full PostgreSQL acceptance suite | **PASS: 29 tests in 163.635 seconds** |
| Final primary-page/form regression | PASS; 1 focused test after sorting/wording changes |
| Final throttling regression | PASS; 1 focused test verifies another staff account can still log in from the same IP |
| POS DOM interaction tests | **PASS: 5 tests**, actual rendered HTML |
| Real HTTP owner login/session | PASS |
| Real HTTP primary routes | PASS: 17 endpoints, including kitchen partial and CSV |
| Local HTTP assets | PASS: 8 assets, no CDN dependency |
| Production Django request stack | PASS: dashboard/orders/reports over secure test requests |
| Production WhiteNoise hashed CSS/HTMX | PASS: HTTP 200 through production-configured middleware |
| Tailwind/vendor build, JavaScript syntax | PASS |
| `collectstatic --noinput` | PASS; hashed/compressed assets generated |
| npm installation audit | PASS; zero vulnerabilities reported |
| Template compilation | PASS: all 22 templates |
| `docker compose config --quiet` | PASS |
| Git ignore inspection | PASS: environment, credentials, runtime/database data, venv, caches and editor settings excluded |
| Generated-secret source scan | PASS: 85 source files checked; no generated Django/database/demo credentials present |

Source and migration files are committed to a local Git repository. The owner has authorized publication to the public `Shozab-110/restaurantflow` repository; repository preparation and upload verification are recorded below.

Tests cover all four requested workflows, authentication/deactivation/CSRF/throttling, permissions/isolation, frontend administration, table conflicts, Decimal totals, snapshots, kitchen transitions, additional tickets, partial/retried/concurrent payments, refunds/cancellation, upload validation, reporting reconciliation, currencies, password changes, demo idempotency, and primary forms/pages.

POS DOM tests cover cart quantities, exact integer tax/service previews, instructions, category/search filters, and delivery/table requirements. They do not certify visual browser rendering.

## Resolved setup issues

- Dependencies were installed after initial network restrictions were approved.
- Docker was initially unavailable; official portable PostgreSQL was installed within this workspace without changing Windows services.
- Windows reserves port 55432, so PostgreSQL uses verified available port 5433.
- The local PostgreSQL helper avoids a Windows inherited-pipe wait after server detachment.
- Tailwind source is outside served static files; broken optional source-map references were removed from vendor distributions, with licenses retained.
- Initial reporting aggregate shadowing and requestless login-test failures were fixed before the passing runs.
- HTTP verification includes a readiness retry for immediate post-launch checks.

## Blocked verification and exact next actions

1. **Browser layout/tablet interaction/screenshots/physical receipt printing:** browser inventory is empty; both IAB and Chrome return `Browser is not available`. Connect a supported browser, open the local URL, run the session in `docs/OPERATIONS.md`, inspect desktop/tablet layouts, and capture actual screenshots for README. No screenshots were fabricated.
2. **Docker image/container/Caddy HTTPS runtime:** Docker Desktop was started, but its Linux engine remains unavailable / returns HTTP 500 for its information API. On a host with a working engine, run `docker compose config --quiet`, `docker compose --profile https up -d --build`, then the health/HTTPS checks in `docs/DEPLOYMENT.md`. Compose configuration passes; a successful container deployment is not claimed. Account sign-in is normally optional and is not needed for the current local app.
3. **Production operational acceptance:** configure target DNS/TLS, restricted runtime database credentials, external backups, restore rehearsal, expected-load checks, and a real receipt printer. Local security checks do not certify a production deployment.

## Explicit MVP limitations / deferred features

- Single restaurant per installation. No inventory, purchasing, multi-tenant billing, split checks, formal cash-drawer shifts, table transfers, offline mode, or delivery dispatch integration.
- Payment/refund entries are manual records, not gateway integrations. Money must actually be returned before confirming a refund.
- Closed orders are immutable; post-close accounting corrections require a controlled external process in this MVP.
- Order-wide exclusive tax/service on discounted subtotal; no item-specific tax regimes, inclusive pricing, or exchange-rate conversion. Currency uses two decimal places.
- Percentage offers convert to fixed discounts on application. Advanced promotions are deferred.
- Operating hours are informational rather than enforced.
- HTML printing / browser Save as PDF is supported; dedicated PDF generation, kitchen sound, and advanced analytics are deferred.
- PostgreSQL binaries, live records, demo database contents, and generated credentials remain local-only. Only sanitized application source, migrations, assets, and documentation are authorized for GitHub publication.

## Deployment status

**Usable, tested local MVP; not certified production-ready.** Outstanding checks and exact next actions are stated above. See `README.md`, `docs/OPERATIONS.md`, and `docs/DEPLOYMENT.md`.

## Public repository preparation — 2026-10-19

- Target: public `Shozab-110/restaurantflow`, explicitly authorized by the owner. Existing Git credentials authenticate as the correct account; the target name was available at the initial check.
- Added a branded README, linked setup/architecture/database/testing/troubleshooting guides, findings and solutions, contribution/security/change records, issue forms, and a PR template.
- Added a safe local environment generator that never overwrites an existing `.env`; PostgreSQL credentials containing literal interpolation characters are handled without expansion.
- Added a loopback-only Docker database development override, so a host Python process can reach PostgreSQL without exposing the production database.
- Added pinned GitHub Actions automation for PostgreSQL tests, frontend checks, deployment settings, and an actual Linux Docker smoke test.
- Final repository-preparation rerun: all 29 PostgreSQL tests passed in 80.435 seconds; all 5 POS DOM tests and all 4 configuration-helper tests passed.
- Frontend rebuild/static collection, normal and production Django checks, migration drift, both Compose configurations, and all 44 relative documentation links passed.
- Authenticated HTTP rerun passed: owner session, all 17 endpoints, and all 8 local assets.
- Full-history audit passed before upload: all 4 commits / 108 historical blobs checked against generated local credentials and token/private-key patterns; excluded runtime/data paths absent.
- Published source to the authorized [public repository](https://github.com/Shozab-110/restaurantflow); verified remote `main` matches commit `fba95a8`.
- First hosted [CI run](https://github.com/Shozab-110/restaurantflow/actions/runs/39274706348): all 29 test assertions passed in 16.056 seconds, but test-database teardown failed because worker threads retained healthy connections. Fixed the concurrency tests to close each thread's connections explicitly in `finally`; rerun pending.
- Enabled GitHub private vulnerability reporting. Generated disposable CI secrets are now masked in runner output.
