# Ubuntu deployment, health, backup, and restore

## Before deployment

Provision Ubuntu with Docker Engine and Compose v2. Configure DNS to the VPS. Keep ports 80/443 available to the reverse proxy; the default app port binds to VPS loopback and PostgreSQL has no published port. Use a dedicated deployment directory and restrict `.env` to the service administrator (`chmod 600 .env`).

Copy `.env.example` to `.env`. Set a unique random 60+ character Django secret and a strong PostgreSQL password, `DJANGO_DEBUG=false`, actual `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS=https://your-domain`, `DJANGO_SECURE_SSL_REDIRECT=true`, `TRUST_PROXY_HEADERS=true`, and `RESTAURANT_DOMAIN=your-domain`. Never use wildcard hosts or local/demo credentials in production.

```bash
docker compose config --quiet
docker compose --profile https up -d --build
docker compose logs init
docker compose exec web python manage.py check --deploy --fail-level WARNING
docker compose exec web python manage.py create_owner --username owner --email owner@example.com
curl --fail https://your-domain/health/
```

The one-shot `init` service waits for PostgreSQL health, applies migrations, synchronizes business roles, and collects static files. Gunicorn starts only after successful initialization. **Do not run multiple migration jobs simultaneously.** Assets are built in a Node build stage; Python runs as UID 10001. WhiteNoise serves collected static files. Caddy serves the separate media volume read-only with nosniff and a restrictive media CSP; only re-encoded raster images are accepted by the frontend.

Caddy obtains/renews HTTPS certificates and passes `X-Forwarded-Proto`. Trust proxy headers only when the app port is not reachable from an untrusted network. If using a host Nginx or another reverse proxy instead, configure HTTPS, preserve Host, set X-Forwarded-Proto, allow up to 6 MB request bodies, and serve `/media/` as static content without executable handlers. Do not serve uploads through Django runserver in production.

Application/database logs go to container output. Configure log rotation and disk/uptime monitoring. Do not include request bodies, passwords, or `.env` in diagnostic exports. The app's login limiter uses database-backed Axes counters; inspect `python manage.py axes_reset --help` only for legitimate administrative lockout recovery.

## Runtime checks

```bash
docker compose ps
docker compose logs --tail=100 web
docker compose exec web python scripts/healthcheck.py
docker compose exec web python manage.py showmigrations
docker compose exec web python manage.py makemigrations --check --dry-run
```

`/health/` performs a database query and returns 200 JSON or 503 without credentials or database error details. The internal health probe supplies the configured Host and HTTPS proxy header. Check the actual public HTTPS endpoint as well; a healthy internal container does not prove certificate or DNS configuration.

Create the first owner through `create_owner`; use the custom Staff & Roles screen afterward. Do not run `seed_demo` on production. A technical superuser is optional for maintenance and should not be the daily business account.

## Database privilege separation

The Compose PostgreSQL image creates an initialization/migration user using POSTGRES_USER; that role is a cluster administrator. For a real deployment, create a separate restricted runtime role, grant only the application's schema/sequence/table permissions, and run web with that runtime role while migration/backup jobs retain appropriately scoped credentials. The default Compose file is a straightforward single-server baseline; complete this separation and verify grants before handling live customer data. Tests need a separate disposable PostgreSQL environment with CREATEDB; production runtime does not.

## Backups

Back up the database, uploaded media, and the encrypted/restricted secrets needed for restoration. Store backups outside the VPS with retention and encryption. PostgreSQL data volumes are not backups. Take a backup before every schema update.

```bash
mkdir -p backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backups/restaurantflow.dump
docker compose cp web:/app/media backups/media
```

The database archive includes customer/staff/transaction data. Restrict access and never commit or send it to GitHub. Back up media separately on a defined schedule. Configure an external scheduler and verify backup exit codes and archive sizes. The MVP does not automatically schedule or remotely store backups.

## Restore rehearsal

Always practice in a separate stack/database first. The following overwrites database objects and is a **destructive operation**: use it only after confirming the intended target and stopping application writers.

```bash
docker compose stop web
cat backups/restaurantflow.dump | docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --exit-on-error'
docker compose cp backups/media/. web:/app/media/
docker compose run --rm init
docker compose up -d web
```

Verify media ownership (UID 10001), sign-in, sample receipts, order/payment totals, audit records, and `/health/` after restoration. `--clean` affects the target database: never run these commands against a production database without an approved restore plan.

## Updates and rollback

Build a new image, back up data/media, review pending migrations, run one initialization job, and restart web. Review database migrations before rolling back; restoring an old image cannot reverse a destructive schema migration. Keep the previous image/tag and tested database backup. Rotate deployment secrets outside Git.

## Required go-live verification

Local execution is separate from production verification. Validate HTTPS/host/header handling, restricted runtime database privileges, restore rehearsal, receipt printing, staff access, upload serving, concurrency under expected load, and business accounting acceptance. Docker image startup and proxy operation must be tested on the actual target platform. See `PROGRESS.md` for which checks were executed in the build environment and which require that deployment environment.
