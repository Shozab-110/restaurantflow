# Troubleshooting

Start with the failing command and its actual error. Use synthetic records in reports; redact credentials, session cookies, addresses and payment references before sharing diagnostics.

## PostgreSQL will not open in my browser

Ports 5432/5433 speak the PostgreSQL protocol. Use **http://127.0.0.1:8000** for RestaurantFlow. Use a PostgreSQL client for raw tables; the original checkout's optional pgAdmin viewer is **http://127.0.0.1:5050**. See [Database guide](DATABASE.md).

## Connection refused / database does not exist / password failed

Check `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and your private password in `.env`. Check that the selected server is running and that the database/login exists. These errors have different causes; do not reset a live database to resolve an incorrect port or password.

- Full Compose app: internal database host is `db:5432`.
- Native Python + Docker DB: use the development override so `127.0.0.1:${POSTGRES_PORT}` is published.
- Original portable Windows setup: run `.venv/Scripts/python.exe scripts/local_postgres.py start`; its configured port is 5433.
- Existing server: use its actual configured host/port rather than assuming 5433.

Changing `POSTGRES_PASSWORD` in `.env` does not rotate the password in an already initialized PostgreSQL volume. Update the existing role through an authorized database-administration process, then update the app connection consistently. Preserve data and take a backup before maintenance.

## Windows reports a socket permission error on a seemingly unused port

Windows can reserve port ranges. Inspect them with `netsh interface ipv4 show excludedportrange protocol=tcp` and choose an available port. The original installation found 55432 reserved and used 5433 instead. This does not require disabling a firewall or changing reserved ranges.

## Docker commands cannot connect / engine returns HTTP 500

Open Docker Desktop and wait for its Linux engine to report running. `docker info` should complete successfully before running Compose. Account sign-in is normally optional unless an organization enforces it; sign-in alone does not fix a stopped engine. If Docker requires platform prerequisites, resolve those using Docker's official Windows/WSL instructions rather than changing unrelated security settings.

Native PostgreSQL remains a supported development path. Configuration validation can pass while engine startup fails; do not describe a validated YAML file as a running container deployment.

## Config helper says `.env` already exists

That is intentional. `scripts/configure_local.py` preserves working secrets/configuration and will not overwrite the file. Review/update it intentionally, or generate a separate file with `--output` for comparison. Never commit generated environment files.

## A fresh installation has no owner / login does not work

Run `migrate`, then `bootstrap_roles`, then `create_owner --username owner` using the appropriate native/Compose commands. Set a new password at the hidden prompt. A cloned repository has no default password and does not contain the original build's account database.

For seeded demonstrations, use the password you supplied in `RESTAURANTFLOW_DEMO_PASSWORD`. Seeding does not reset existing passwords. Owners/managers can reset permitted staff accounts in the custom **Staff & Roles** screen. Inactive staff cannot sign in.

After repeated failed login attempts, the account/IP pair cools down for 15 minutes. Legitimate administrators can inspect `python manage.py axes_reset --help` for recovery; do not disable the limiter as a routine fix.

## Table unavailable / cannot mark order served or handed over

- A dine-in table must be active, in an active area, available, and assigned to you or unassigned when using a waiter role.
- Only one open order can use a table. It remains occupied after service until the bill is fully settled.
- Send all draft items, then wait until every active kitchen ticket is ready before serving.
- Collect the complete takeaway/delivery balance before handoff.
- Use authorized cancellation with a reason rather than manually clearing an occupied table.

These are validated business rules, not a reason to edit database rows directly.

## A payment was rejected

Enter a positive amount no greater than the outstanding balance. Record the retained amount rather than cash tender/change. Digital methods need a manually verified confirmation reference. Reusing a payment token with a different amount/method/reference is rejected. A duplicate identical request returns the existing payment.

Discounts/voids that reduce a bill below already collected money are rejected. See [Operations](OPERATIONS.md) for the allowed cancellation/refund workflow and closed-order limits.

## Static files are missing or collectstatic fails

```bash
npm ci
npm run build
python manage.py collectstatic --noinput
```

Do not move `assets/input.css` into the served static directory: its Tailwind imports are build inputs. Production templates use the generated manifest; stale assets must be rebuilt/collected after source changes. Uploaded media has a separate storage/proxy path.

## CSRF error / HTTPS redirect loop

Use the actual browser origin in `CSRF_TRUSTED_ORIGINS`. In production, the proxy must preserve Host and provide a trusted HTTPS header. Trust proxy headers only when untrusted clients cannot reach the app port directly. Local development uses explicit HTTP/nonsecure-cookie settings from the development helper; production uses HTTPS/secure cookies. Do not weaken production settings to imitate local development.

## Tests cannot create a database

Use a development/test PostgreSQL account with CREATEDB. Django tests target an isolated `test_<name>` database. Keep tests away from a live restaurant database and keep CREATEDB out of production runtime credentials.

For a supported business-rule change, run the targeted regression first and then relevant workflow/concurrency tests. For environment fixes, record the failing command, root cause, fix and actual verification in [Findings](FINDINGS_AND_SOLUTIONS.md).
