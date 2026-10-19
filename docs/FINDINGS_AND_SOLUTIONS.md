# Findings, root causes, and solutions

This log distinguishes application defects, setup problems, and verification that still needs a target environment. It records implemented fixes and evidence rather than treating unexecuted configuration as a passed deployment.

## Resolved findings

| Finding / symptom | Cause | Implemented solution | Evidence / relevant files |
|---|---|---|---|
| Empty initial workspace | No project or database schema existed | Created the Django project, normalized models, migrations, role services, custom frontend and operational commands | Applied `operations/migrations/0001_initial.py`; workflow suite |
| Python packages could not download | Initial execution environment restricted outbound network access | Installed approved dependencies, then pinned Python/npm versions and bundled frontend libraries locally | `requirements.lock`, `package-lock.json`, asset build |
| Docker could not provide PostgreSQL initially | Docker Desktop service/engine was not available | Used official portable PostgreSQL 17.11 under ignored `.local`; retained PostgreSQL for all testing | PostgreSQL connection, migrations and concurrency tests passed; `scripts/local_postgres.py` |
| PostgreSQL could not bind port 55432 | Windows reserved a range containing that port | Read the excluded-port ranges, verified a free port, and configured loopback port 5433 | Database started at `127.0.0.1:5433`; no Windows network policy was changed |
| Windows startup helper waited after PostgreSQL was ready | Detached server retained inherited pipe handles | Redirected helper output through a temporary file and waited for the helper process instead of server pipe EOF | `scripts/local_postgres.py`; subsequent initialization/startup passed |
| Static collection reported a missing `src/tailwindcss` file | WhiteNoise encountered raw Tailwind source imports | Moved source CSS to `assets/input.css`, built compiled CSS into `static/css`, and removed optional unavailable vendor source-map references | `npm run build`, `collectstatic`, hashed production asset requests passed |
| Reporting raised a nested-aggregate error | A `quantity` aggregate alias shadowed the item quantity used by a revenue expression | Used a distinct `quantity_sold` aggregate alias and explicit reporting result mapping | `operations/reporting.py`; reconciliation and page tests |
| Login unit test failed before authentication | The login limiter requires a real request object; the original test called requestless authentication | Exercised the actual login form and verified successful login, deactivation, CSRF and lockouts | Authentication regression passed |
| One bad login series could affect another staff account on the same IP | IP-only lockout was too broad for a shared restaurant connection | Keyed throttling by the username/IP pair and tested a second staff login after the attempted account locked | `AXES_LOCKOUT_PARAMETERS`; focused final authentication test |
| Retried payments / competing table requests could corrupt operations | Multiple operators can submit concurrently | Added transaction/row locks, request-key constraints, payload validation, and a conditional active-table constraint | PostgreSQL threaded concurrency tests with separate operators |
| Fully discounted bills could never close | Settlement originally assumed a positive bill requiring a payment record | Allowed zero-total orders to close after fulfillment without inventing a collection | Complimentary-order regression test |
| Historical bills could change with menu/settings updates | Current product/settings values cannot safely represent past prices | Stored item and order snapshots and computed bills from those snapshots | Historical price/rate/currency tests |
| Reports could add amounts from different currencies | Settings can change after historical orders exist | Filtered monetary reports by currency and blocked currency changes while orders remain open | Currency isolation/change tests |
| First HTTP probe sometimes ran before startup completed | Process launch returned before the development server listened | Added a bounded readiness retry before the session/endpoint smoke checks | `scripts/verify_http.py`; final 17 endpoints / 8 assets passed |
| Database tables were not visible in a browser at port 5433 | PostgreSQL is a database protocol, not an HTTP UI | Documented the difference and configured an optional loopback pgAdmin connection with a distinct SELECT-only role in the original checkout | pgAdmin HTTP 200; SELECT succeeded, UPDATE privilege denied; `docs/DATABASE.md` |
| Bundled Windows pgAdmin could not find libpq | Its Python runtime needed the PostgreSQL DLL search directory | Added the installed PostgreSQL runtime directory to its local launcher DLL/PATH settings | Ignored `.local/pgadmin/run_tool.py`; server import and viewer startup passed |
| Fresh-clone instructions started a Docker DB unreachable from host Django | The base Compose stack deliberately has no published DB port | Added an explicit loopback-only development override and separate full-Docker/native setup paths | `docker-compose.dev.yml`, `docs/GETTING_STARTED.md` |
| Copying an example environment could leave placeholder secrets or replace working credentials | Manual setup was ambiguous and unsafe to repeat | Added exclusive-file environment generation, hidden existing-password input, generated secrets, literal dotenv loading and no-overwrite tests | `scripts/configure_local.py`, configuration safety tests |
| Repository evidence and operational notes were scattered | Build notes alone were insufficient for a new contributor | Added focused architecture, database, testing, troubleshooting, operations, deployment and contribution guides plus CI/templates | Documentation link check and repository review |
| First Linux CI run passed all 29 tests but could not drop its test database | Thread workers used `close_old_connections()`, which retains healthy persistent connections until their lifetime expires | Explicitly close each worker thread's connections in its `finally` block; retain the normal application connection lifetime | Both local concurrency tests passed with fresh teardown; [full hosted rerun passed](https://github.com/Shozab-110/restaurantflow/actions/runs/39275185992) |
| Original host could not verify the Docker image | Windows Docker engine was unavailable | Added a Linux GitHub Actions image/stack smoke test using disposable databases/secrets | [Verified CI](https://github.com/Shozab-110/restaurantflow/actions/runs/39275185992): image build, initialization, DB/Gunicorn health, HTTP login, owner creation and production check passed |

## Open verification items

| Item | What is known | Exact next action |
|---|---|---|
| Desktop/tablet browser rendering and screenshots | HTTP and DOM checks pass; the original automation environment exposed no browser surface | Follow `SCREENSHOTS.md` using an available browser and synthetic demonstration data |
| Physical receipt printer | Print-friendly HTML/CSS exists and receipt routes are tested | Print on the intended device/paper size and verify totals, margins, cutter behavior and legibility |
| Local Docker Desktop runtime | The original Windows engine returned connection/API errors; the full container stack passed on the Linux CI runner | Use the native PostgreSQL setup or repair/start the local Docker engine before choosing local Docker startup |
| Real HTTPS/VPS deployment | Caddy/Gunicorn/WhiteNoise configuration and production Django checks exist | Deploy with DNS/TLS, a restricted runtime DB role, health probes and a restore rehearsal per `DEPLOYMENT.md` |

## Deliberate product limitations

These are scoped MVP boundaries, not silently missing integrations:

- Payments/refunds are manually confirmed ledger entries; no external payment gateway or tax-authority integration is present.
- Inventory, formal cash-drawer shifts, split checks, offline mode, table transfers and delivery dispatch are deferred.
- Closed-order corrections need a controlled external accounting process; the MVP does not mutate closed sales.
- Tax/service are order-wide, exclusive percentages of the discounted subtotal; currency uses two decimal places and there is no FX conversion.
- HTML receipts support browser printing/Save as PDF. Dedicated PDF generation, kitchen sound and advanced analytics are deferred.

See [Operations](OPERATIONS.md) for accounting definitions and [Testing](TESTING.md) for the precise evidence and reproduction commands.
