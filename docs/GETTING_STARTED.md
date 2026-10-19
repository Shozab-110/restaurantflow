# Getting started

Choose **one** path. The application always uses PostgreSQL; copying the repository does not copy your live data or local passwords.

| Path | Install on your computer | Where Python runs | Where PostgreSQL runs |
|---|---|---|---|
| A. Complete Docker stack | Git, Docker Engine/Desktop, Python 3 for the config helper | Container | Container |
| B. Native Django + Docker database | Git, Python 3.12, Docker | Your computer | Container |
| C. Native Django + existing PostgreSQL | Git, Python 3.12, PostgreSQL 14+ | Your computer | Existing PostgreSQL server |

PostgreSQL 17 is the tested major version. Node 22 is needed only to rebuild frontend assets or run POS DOM tests; compiled assets are already included.

## Clone the source

```bash
git clone https://github.com/Shozab-110/restaurantflow.git
cd restaurantflow
```

Private repositories require a GitHub login with access. Use your Git credential manager or GitHub CLI authentication; do not put tokens in a remote URL or paste them into issue reports.

## A. Complete Docker stack

Create a development configuration with generated secrets:

```bash
python scripts/configure_local.py
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
docker compose exec web python manage.py create_owner --username owner
```

The last command prompts for a new owner password without echoing it. Open **http://127.0.0.1:8000** and sign in with that owner account.

The `init` container applies migrations, creates business groups/permissions, and collects static files. Gunicorn starts after initialization. PostgreSQL stays inside the Compose network; it does not need a browser URL or a published database port. The application's `/health/` endpoint verifies the database connection.

To stop/start the stack while preserving named-volume data:

```bash
docker compose stop
docker compose start
```

For initialization failures, use `docker compose logs init db web`. The development `.env` enables HTTP on loopback. Follow [Deployment](DEPLOYMENT.md) for real HTTPS production settings.

### Optional demo instead of a new empty restaurant

On a separate development database, you can create demonstration accounts/data instead of the initial owner command. The seed command refuses production settings and never resets existing user passwords.

PowerShell:

```powershell
$env:RESTAURANTFLOW_DEMO_PASSWORD = Read-Host 'Choose a temporary demo password (10+ characters)'
docker compose exec -e RESTAURANTFLOW_DEMO_PASSWORD web python manage.py seed_demo --confirm-demo
Remove-Item Env:RESTAURANTFLOW_DEMO_PASSWORD
```

Bash:

```bash
read -rs -p 'Choose a temporary demo password (10+ characters): ' RESTAURANTFLOW_DEMO_PASSWORD
export RESTAURANTFLOW_DEMO_PASSWORD
docker compose exec -e RESTAURANTFLOW_DEMO_PASSWORD web python manage.py seed_demo --confirm-demo
unset RESTAURANTFLOW_DEMO_PASSWORD
```

Accounts are `owner`, `manager`, `cashier`, `waiter`, and `kitchen`; newly created demo accounts use the password you supplied. There is no published default password. The demo contains 3 areas, 12 tables, 5 categories, 25 menu items, synthetic customers, and realistic orders/tickets/payments.

## B. Native Django + a Docker PostgreSQL database

Generate `.env` once:

```bash
python scripts/configure_local.py
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db
python -m venv .venv
```

Activate your virtual environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
source .venv/bin/activate
```

Then:

```bash
python -m pip install -r requirements.lock
python manage.py migrate
python manage.py bootstrap_roles
python manage.py create_owner --username owner
python manage.py collectstatic --noinput
python manage.py runserver 127.0.0.1:8000
```

Open **http://127.0.0.1:8000**. The development override publishes PostgreSQL only to **127.0.0.1:5433** by default. Django reads the same password/database/port from `.env`. This override is for host-based development; omit it in production.

## C. Native Django + an existing PostgreSQL server

First provision a dedicated database and login using your database administrator. For development tests, that login needs permission to create an isolated test database. Do not grant production runtime accounts CREATEDB or cluster-superuser privileges.

Create the virtual environment and install `requirements.lock` as in path B, then generate connection settings using your actual host, port, database, and user:

```bash
python scripts/configure_local.py --existing-database --host 127.0.0.1 --port 5432 --database restaurantflow --user restaurantflow
```

Enter the existing database password at the hidden prompt. If `POSTGRES_PASSWORD` is already set in your shell, it is used instead. Continue with migrate, bootstrap_roles, create_owner, collectstatic, and runserver from path B.

The helper refuses to overwrite any existing output file, creates restrictive Unix file permissions, and never prints generated secrets. Update an existing `.env` intentionally when changing connection settings; generating a new file does not change an existing PostgreSQL role's password.

Existing-credential output is intended for this native Python path. Compose and python-dotenv handle backslash escaping differently; use the helper's generated URL-safe credentials for a new Docker database rather than repurposing a native connection file containing backslashes.

## Working with the original Windows checkout

The original build installed portable PostgreSQL under `.local/pg-runtime/pgsql` and stores its data under `.local/pgdata`. These are local runtime files and are intentionally absent from a fresh clone. If you already have that configured checkout, use `scripts/start.ps1`; `scripts/local_postgres.py start|stop` controls its database without changing Windows services.

The optional local pgAdmin viewer uses port 5050 and its own ignored configuration. It is not a prerequisite for RestaurantFlow and is not shipped as a public service. See [Database guide](DATABASE.md).

## Next steps

- Add staff in **Staff & Roles** and select Cashier, Waiter, Kitchen Staff, Manager, or Owner.
- Set restaurant identity/tax/service values, menu availability, dining areas, and tables in the custom frontend.
- Run a dine-in and takeaway through the [operations guide](OPERATIONS.md).
- Run the [test suite](TESTING.md) before changing billing or access controls.
- Use the [troubleshooting guide](TROUBLESHOOTING.md) for startup/connection errors.
