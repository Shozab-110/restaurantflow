# RestaurantFlow progress and verification

Updated: 21 October 2026 (Asia/Karachi).

## Current delivery status

**Running, tested shared-VPS demonstration.** Application commit `fbd54c6` (compact theme) is deployed behind trusted IP HTTPS on port 8443 using `docker-compose.shared.yml`. ERP HTTP/login and four local assets are restored; its original nginx files and existing backend/database services were preserved. Exact access details are in the private ignored handover, never in Git.

All 48 hosted automated tests passed for the compact theme (31 PostgreSQL, 12 configuration/planner, 5 DOM). Core public HTTPS acceptance before the theme update passed all four requested workflows, role logins/denials, administration, receipts/reports, duplicate dispatch/payments and table release. Persisted transaction states/totals, report reconciliation and restricted runtime database grants were verified. A 136,370-byte backup restored into a separate test database, financial/status rows matched, and a hash-verified private copy was recovered to the laptop. The earlier 14-minute routing observation passed, but a later external whole-config replacement removed the app routes; they were restored during this update. External proxy configuration ownership remains unresolved.

This is not certified production-ready: physical browser/tablet/printer checks, expected-load checks, future certificate renewal and scheduled off-host backup/retention operations remain. Future whole-config changes by the external proxy controller must preserve the additional listeners; see `docs/SHARED_PROXY.md`. No authenticated ERP transaction or host reboot test was performed. Local offline phone testing remains pending the firewall approval previously canceled by the user.

## Working local application

### Compact theme update — deployed and verified

- Shared design tokens, 208px sidebar, 54px header, 13px base text, 24px page headings, tighter cards/tables, shorter headings and responsive two-column forms.
- POS product art is 80px on desktop, with a sticky cart and denser customer/order fields. Coarse-pointer controls retain at least 44px height; kitchen actions retain at least 48px. Existing print rules are preserved exactly.
- Installed headless Chrome inspected actual authenticated Django-rendered local fixtures with local assets. Thirteen emulated page/viewport combinations passed: dashboard/POS/settings/orders at 1440px, kitchen at 1024px, POS at 768px, dashboard/settings/orders/tables/login/receipt at 390px, and login at 1366px.
- Assertions verified exact viewport widths, no document horizontal overflow, coarse-pointer targets, kitchen action sizes, phone form stacking and selecting two POS products. Actual dashboard/POS screenshots with synthetic data are in `docs/screenshots/`. Polling was disabled only in the fixtures. This does not certify physical devices, live browser sessions or printers.
- The same-data first desktop comparison reduced dashboard document height from 1,630px to 1,333px and stat cards from 165px to 131px. Final screenshots use a seven-day reporting range.
- Final local checks passed: asset build, static collection, Django system check, 5 POS DOM tests, 68 documentation links and Git whitespace check. Receipt print rules match the previous source exactly. Local servers on ports 8000 and 8001 were restarted with the new templates.
- [Compact theme CI](https://github.com/Shozab-110/restaurantflow/actions/runs/39622398886), application commit `fbd54c6`: all 48 tests passed (31 PostgreSQL in 16.858s, 12 configuration/planner, 5 POS DOM), plus asset compilation, migration/security checks and complete Docker startup/health/login checks.
- Live rollout passed: pinned source/image, 136,849-byte private pre-update PostgreSQL backup, static collection and replacement of only the RestaurantFlow web container. Production deployment check reported zero issues. Database/container proxy and native Caddy/MariaDB/supervisor/ERP bridge retained their start times/PIDs.
- Trusted public HTTPS checks passed 17 routes, 8 assets, all 5 role logins, 4 permission denials, compact page headings and hashed CSS `app.dc584ead5572.css`. No business records were created/edited by this theme verification.
- Separate VPS issue observed before rollout: an external whole-config proxy replacement removed both previously approved public app routes. The guard stopped before changing the app. The existing tested additive planner restored ERP HTTP and RestaurantFlow HTTPS using a private backup, Caddy validation and ETag protection; the managed 443 server was preserved exactly. ERP login and four assets returned HTTP 200. Proxy config remained unchanged during the subsequent theme rollout and final check at 15:15 UTC. Durable coordination with the external controller remains necessary; no competing overwrite loop was installed. See `docs/SHARED_PROXY.md`.

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
| Full PostgreSQL acceptance suite | **PASS: latest 31 tests in 99.310 seconds locally; 12.636 seconds in hosted CI** |
| Configuration / shared proxy preservation | **PASS: 12 tests** |
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
| Linux GitHub CI / complete Docker stack | PASS; image build, initialization, PostgreSQL/Gunicorn health, login, owner creation and container production check |
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

1. **Physical device/live browser/printer acceptance:** headless Chrome layout checks and real fixture screenshots now pass; connected interactive browser inventory is still empty. On the intended devices, complete `docs/OPERATIONS.md`, verify live kitchen polling, focus/keyboard behavior and physical receipt output. Headless emulation is not a physical device test.
2. **Local Windows Docker:** the original Docker Desktop engine remains unavailable / returns HTTP 500. Linux CI and actual VPS Docker/HTTPS checks now pass. Use native PostgreSQL locally, or repair/start the local Docker engine before selecting local full-Docker startup. On the shared VPS use only the reviewed `docker-compose.shared.yml`; do not start the base HTTPS profile over existing listeners.
3. **Production operational acceptance:** trusted HTTPS, restricted runtime credentials and a private off-host backup/isolated restore passed. Establish scheduled backup retention, monitor renewals, verify expected load and a real receipt printer, and coordinate future external proxy-controller changes. Demo/security checks do not certify all production operations.

## Explicit MVP limitations / deferred features

- Single restaurant per installation. No inventory, purchasing, multi-tenant billing, split checks, formal cash-drawer shifts, table transfers, independent offline device queues/synchronization, or delivery dispatch integration. Laptop-hosted offline LAN use is supported.
- Payment/refund entries are manual records, not gateway integrations. Money must actually be returned before confirming a refund.
- Closed orders are immutable; post-close accounting corrections require a controlled external process in this MVP.
- Order-wide exclusive tax/service on discounted subtotal; no item-specific tax regimes, inclusive pricing, or exchange-rate conversion. Currency uses two decimal places.
- Percentage offers convert to fixed discounts on application. Advanced promotions are deferred.
- Operating hours are informational rather than enforced.
- HTML printing / browser Save as PDF is supported; dedicated PDF generation, kitchen sound, and advanced analytics are deferred.
- PostgreSQL binaries, live records, demo database contents, and generated credentials remain local-only. Only sanitized application source, migrations, assets, and documentation are authorized for GitHub publication.

## Deployment status

**Usable, tested local MVP and shared-VPS demonstration; not certified production-ready.** Outstanding checks and exact next actions are stated above. See `README.md`, `docs/OPERATIONS.md`, `docs/DEPLOYMENT.md` and `docs/SHARED_PROXY.md`.

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
- First hosted [CI run](https://github.com/Shozab-110/restaurantflow/actions/runs/39274706348): all 29 test assertions passed in 16.056 seconds, but test-database teardown failed because worker threads retained healthy connections. Fixed the concurrency tests to close each thread's connections explicitly in `finally`.
- Enabled GitHub private vulnerability reporting. Generated disposable CI secrets are now masked in runner output.
- Local fix verification: both concurrency tests passed in 13.623 seconds with successful fresh test-database creation and deletion.
- Final hosted [CI run — PASS](https://github.com/Shozab-110/restaurantflow/actions/runs/39275185992) on application commit `bad6305`: 29 PostgreSQL tests in 15.107 seconds with successful teardown, 4 configuration tests, 5 POS DOM tests, asset build, migration drift, 44 documentation links and production checks all passed.
- Linux Docker verification passed: multi-stage image built; init completed migrations/roles/static collection; PostgreSQL and Gunicorn became healthy; `/health/` returned PostgreSQL `ok`; `/login/` returned success; initial owner creation and in-container deployment checks passed. CI containers shut down successfully.
- Public README/banner were fetched successfully without authentication. Remaining acceptance concerns are browser/tablet/screenshots, physical printer, and the actual production HTTPS/backup/privilege/load configuration described above.
- Final follow-up is documentation-only; validated relative links locally and retained the successful application CI evidence rather than rerunning unchanged application tests.

## Offline multi-device demonstration — 2026-10-19

- Added `Start Offline Demo.cmd` / `scripts/demo_server.py`: local address discovery, explicit allowed hosts/CSRF origins, no `.env` rewrite, portable database startup, readiness check, duplicate detection, and separate port 8001.
- Added `Enable LAN Access.cmd` / `scripts/enable_lan.ps1`: administrator-approved firewall rule restricted to the Python interpreter, TCP 8001, and local-subnet clients. PostgreSQL remains loopback-only.
- Added offline/device/VPS guidance and a plain Git editing/commit/push guide; clarified that frontend business records are PostgreSQL data and are not pushed to GitHub.
- Seven configuration/launcher tests passed; PowerShell firewall helper parsed successfully; launcher dry run discovered the laptop's private IPv4 addresses without contacting internet servers.
- Offline regression passed: the full dine-in HTTP-client flow and runtime-asset inspection completed with Python socket connections blocked (1 test, 13.279 seconds).
- Real LAN-address verification passed: owner session, 17 endpoints and 8 assets over the laptop Wi-Fi address on port 8001. Server listens on all IPv4 interfaces; PostgreSQL remains loopback-only.
- Windows UAC elevation was canceled by the user. No firewall exception was installed; do not retry elevation automatically. Exact next action: when ready, run `Enable LAN Access.cmd` and approve it, then connect a phone/tablet on the same network and test login/kitchen polling.
- Seven final setup/launcher tests and all 54 documentation links passed. Hosted CI pending; no physical phone/tablet connection or literal Wi-Fi-off device session is claimed.
- Full updated local PostgreSQL suite passed: 30 tests in 102.376 seconds, including the offline workflow/resource regression. Offline-change CI is queued on GitHub; no hosted result is claimed for that commit yet.

## Shared VPS deployment preparation — 2026-10-19

- Owner requested use of an existing Ubuntu VPS while preserving its ERPNext installation. A password-only, read-only SSH inspection completed; no persistent SSH key was added. Automatic approval review rejected persistent root-key installation; the safer password-only method was used instead.
- Audit: Ubuntu 24.04, approximately 8 GiB RAM with substantial free memory, approximately 85 GiB disk free; native ERPNext/nginx/MariaDB/Redis remain running. HTTP 80 and ERP backend 8000 are occupied; HTTPS 443 is free; Docker is not installed.
- Prepared a dedicated cohost Compose file that publishes only HTTPS 443; PostgreSQL/backend stay internal, resource limits preserve capacity, and separate migration/runtime credentials enforce a restricted web database account.
- Verified the official Caddy 2.11.7 release and current Let's Encrypt public-IP/short-lived certificate support. Prepared IP-based TLS-ALPN issuance without claiming HTTP 80, and configurable distinct application cookie names.
- Eight local configuration/model tests passed. A disposable PostgreSQL integration check verified migration/static initialization, runtime data writes/demo seeding, and absence of superuser/CREATEDB/CREATEROLE/schema CREATE privileges; its temporary database and role were removed.
- Guarded first-install script is prepared with ERP health/nginx fingerprint checks, no existing-package upgrades/removals, no ERP/nginx restart, exact source pinning, separate files/volumes, and trusted TLS verification.
- Pending: reviewed source publication, password-only installer execution, actual certificate/app logins, production checks and before/after ERPNext verification. No VPS deployment success is claimed yet.

## User-requested pause — 2026-10-19

- User asked to continue tomorrow; no new deployment work is to be started until resumed.
- The already authenticated password-only installer was in flight. Its latest inspected output showed Docker/containerd/Compose package installation and package triggers. No final deployment/HTTPS result is claimed.
- Safe resume checkpoint saved in ignored `.local/RESUME_VPS.md`. First inspect `.local/vps-deploy-status.json` and the sanitized deployment log; do not rerun a first-install over a partial deployment.
- ERPNext preservation remains mandatory. Verify current ERP and RestaurantFlow state before any further changes. Root passwords remain outside chat and files.
- Final pause snapshot: SSH ended with exit code 255; image build and Caddy configuration validation had completed, but no final deployment result was received. Remote container/HTTPS state remains unverified and must be inspected read-only on resume. No retry was initiated after the pause request.

## Resumed — 2026-10-21

- Owner explicitly resumed the task. Read the saved pause checkpoint and retained the mandatory ERPNext preservation constraint.
- Current source commit `4bc211c` has a [successful hosted CI run](https://github.com/Shozab-110/restaurantflow/actions/runs/39284932897): 30 PostgreSQL tests (10.098 seconds), 8 configuration/launcher/Compose tests, and 5 POS DOM tests, plus the Docker stack and production checks. Earlier queued status is superseded by this actual result.
- Public checks found HTTP 80 returning a Caddy HTTPS redirect and HTTPS failing its handshake. This differs from the original nginx HTTP baseline; cause is not yet established, and no server repair or configuration change has been attempted on resume.
- Opened an approved password-only read-only SSH inspection for ports, nginx fingerprints/routing, existing containers and redacted logs. Awaiting local password entry; root credentials remain outside chat/files and no persistent SSH key is installed.
- Authenticated read-only inspection completed: PostgreSQL and Gunicorn are healthy, initialization exited successfully, and the original RestaurantFlow proxy obtained a publicly trusted IP certificate on October 19. A root-only deployment result exists, so the disconnected local wrapper was not proof that the remote installer failed.
- Current routing differs from that completed installation: the RestaurantFlow Docker proxy exited cleanly on October 20, and a native Caddy process now owns both 80 and 443. ERPNext's Gunicorn/MariaDB/Redis remain running, but its public HTTP route redirects to failing HTTPS. Native proxy provenance/configuration must be inspected before any repair. No server mutation has been performed during resume.
- Further inspection found an active, API-managed domain route on the native Caddy and a stopped original nginx service. Owner explicitly authorized additive shared routing while keeping existing services running. Recovered the original demo credentials into an ignored account-restricted local file without changing passwords or exposing them in source/log output.
- Prepared `docker-compose.shared.yml`, a private HTTP proxy configuration, an additive Caddy planning helper and a separate ERP nginx bridge generator. All 12 local configuration/planner tests pass, including route/certificate-policy preservation, ambiguity rejection, private bindings and original ERP asset/site/WebSocket rule preservation. Actual shared-host application remains pending.
- Backed up active Caddy JSON and the RestaurantFlow database (131,464-byte custom-format archive); nginx/Caddy syntax validation passed. Published revision `813dca6`; its [hosted CI passed](https://github.com/Shozab-110/restaurantflow/actions/runs/39608884784): 30 PostgreSQL tests in 15.569 seconds, 12 configuration/planner tests, 5 POS DOM tests, full container stack and production checks.
- Created only the RestaurantFlow private proxy and a separate localhost ERP nginx bridge. Initial shared routes restored ERP HTTP and trusted RestaurantFlow HTTPS, preserving the cloud site's 200 response and original nginx file fingerprints. A transient proxy-start reset was diagnosed read-only and resumed from the confirmed checkpoint.
- Persistence check then found a controller GET on the managed 443 route list followed by a whole-config `/load` that removed our additions. No competing rewrite timer was installed. Revising the plan to keep the entire managed 443 server untouched and give RestaurantFlow a separate native HTTPS 8443 listener; persistence and live workflows still require verification.
- Revised native listener applied at 13:42:51 UTC with the managed 443 server unchanged. External trusted HTTPS on 8443 and ERP HTTP passed. All five staff role logins, secure cookies, 17 owner endpoints, 8 assets, CSV, server-side permission denials, owner menu/price/category/staff creation and staff deactivation passed through public HTTPS.
- Live POS testing exposed a real nullable-customer rendering defect after saving an order-level note. Reproduced it locally for dine-in, takeaway and delivery in a new regression (three failing subcases), then replaced the eager template fallback with guarded branches. Original saved transaction remains preserved; verification is continuing before any completion claim.
- Fixed application verification: all 31 local PostgreSQL workflow/concurrency tests passed in 99.310 seconds, all 12 configuration/planner tests passed, and all 61 documentation links passed. At 13:48 UTC the revised shared plan was unchanged after the controller's next route-list poll, with no follow-up `/load` observed. Application rollout and complete live order retest remain pending.
- Published/deployed exact application commit `13580e7`; [hosted CI passed](https://github.com/Shozab-110/restaurantflow/actions/runs/39611389128): 31 PostgreSQL tests in 12.636 seconds, 12 configuration/planner tests, 5 DOM tests and complete Docker/security checks. Rebuilt/initialized only RestaurantFlow, retained a rollback image and fresh data/environment backup, and passed on-server `check --deploy --fail-level WARNING` and migration drift checks.
- Complete live HTTPS retest passed workflows A–D, all roles/denials, owner CRUD/price/staff deactivation, 17 routes, 8 assets, CSV and receipts. Closed synthetic dine-in/takeaway orders retained exactly two collections each despite retries; kitchen dispatch stayed single; table released; manager cancellation preserved exactly one audit event. Failed test order was canceled with a reason and retained, and synthetic menu/category/staff were deactivated.
- At 13:56:59 UTC shared routing still matched the plan, original nginx files matched their fingerprints, DB/backend ports were unpublished and only the proxy's localhost port was exposed. Runtime flags confirmed no superuser/CREATEDB/CREATEROLE/replication/BYPASSRLS/schema CREATE privileges; report totals reconciled.
- Final PostgreSQL backup/restore rehearsal passed in a disposable `rf_restorecheck_...` database; selected order statuses/financial totals matched and only that temporary database was removed. A 136,370-byte archive was copied over SSH to the account-restricted ignored local backup folder, with SHA-256 verified. Existing ERP login/assets and RestaurantFlow trusted certificate/health passed external checks. No scheduled backup job, reboot, physical browser/device/printer or load test is claimed.
