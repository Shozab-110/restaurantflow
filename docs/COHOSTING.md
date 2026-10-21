# Cohosting beside an existing ERPNext installation

Do not run the base Compose HTTPS profile blindly on a shared VPS: it publishes ports 80/443 and the native app port can conflict with an existing ERP backend. Inspect the host first and keep the existing application's databases, configuration, ports, and processes intact.

If a host proxy now owns both public ports, use the [existing shared proxy layout](SHARED_PROXY.md). Do not stop that proxy or rerun the first-install script to force the original layout.

## Prepared deployment layout

The cohost configuration is intended for an audited Ubuntu 24.04 server where an existing application uses HTTP port 80 and HTTPS port 443 is free:

| Component | Exposure / isolation |
|---|---|
| Existing ERPNext/nginx/MariaDB | Existing host services and configuration remain in place |
| RestaurantFlow source | Dedicated `/opt/restaurantflow` checkout |
| Application + initialization | Dedicated Compose project `restaurantflow`, no host backend port |
| PostgreSQL 17 | Dedicated container/volume; no published database port |
| HTTPS | Dedicated Caddy container; TCP/UDP 443 only |
| Media/static/certificate state | Separate project volumes |
| Runtime privileges | Separate non-superuser database login; no CREATEDB/CREATEROLE/schema CREATE |

`docker-compose.cohost.yml` caps application, initialization and PostgreSQL memory/CPU separately. Caddy is capped too. Preserve headroom for ERPNext and inspect load before building images; resource caps do not replace host monitoring.

## HTTPS without a purchased domain

[Let's Encrypt supports public IP certificates](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability). These certificates are short-lived, so automatic renewal is essential. The pinned Caddy version uses the `shortlived` ACME profile and TLS-ALPN validation on port 443. The cohost Caddyfile disables HTTP validation and automatic HTTP redirects, so it does not claim the existing application's port 80. Certificate and ACME account state persist in its own volume.

The intended URLs are `http://<VPS-IP>/` for the existing ERP and `https://<VPS-IP>/` for RestaurantFlow. Separate session/CSRF cookie names avoid ordinary name collisions. A dedicated domain/subdomain is a stronger long-term separation because cookies otherwise share the IP host. IP literals are not HSTS hosts under [RFC 6797](https://www.rfc-editor.org/rfc/rfc6797.html), so do not assume an IP certificate provides domain HSTS protection.

Port 443 must be reachable through the provider's firewall as well as the host. No router/DNS account or paid API is needed for the prepared IP certificate approach. Verify the actual certificate chain, expiry, health, login and renewability before handing over a public deployment; configuration alone is not a successful certificate issuance.

## Credentials and initialization

The installer generates three ignored, mode-600 files on the server:

- `.env`: application/runtime credentials and HTTPS configuration.
- `.env.database`: PostgreSQL initialization/migration account credentials.
- `.env.migration`: credentials supplied only to the one-shot initialization container, plus the restricted role it provisions.

The web container receives only `.env`. `scripts/initialize_cohost.py` applies migrations/roles/static collection with migration credentials, then grants the runtime role data/sequence access and default privileges for future migrations. The runtime role cannot create databases, roles or schema objects.

A new demo deployment uses a new database with synthetic records. Each demo staff account receives its own generated password. Initial access is stored in a root-only server result file and a private ignored local handover file; it is never committed. Laptop data and ERPNext records are not transferred by this process.

## Guarded installer

`deploy/install_cohost.py` is a **first-install** tool for a specifically authorized, inspected server. It is not an unattended updater. Run it with the public IP and an exact reviewed Git commit after establishing SSH access:

```bash
python3 deploy/install_cohost.py --public-ip YOUR_VPS_IP --source-ref FULL_40_CHARACTER_COMMIT
```

It validates free ports/resources, checks ERPNext HTTP health, fingerprints nginx configuration, prepares Docker using its [official Ubuntu repository](https://docs.docker.com/engine/install/ubuntu/), and aborts if installation would remove/upgrade existing packages. It requests list-only restart handling to avoid restarting existing services. Conflicting existing container-runtime packages cause an abort rather than an automatic uninstall.

It creates only the RestaurantFlow deployment and its new containers/volumes, validates Caddy without prematurely initializing media-volume ownership, waits for application health, checks production Django configuration, prepares the demo, verifies trusted HTTPS, then rechecks ERPNext and nginx fingerprints. It never issues a reboot, an nginx/ERP restart, global Docker prune, or database replacement.

If a step fails, inspect its output and the RestaurantFlow state before resuming. The installer deliberately refuses to overwrite an existing `/opt/restaurantflow`; review a partial deployment rather than deleting/recreating data. Root SSH access is administrative: passwords should be entered locally in the SSH console, not stored in this repository or pasted into chat. No persistent deployment SSH key is required.

## Operate only this stack

```bash
cd /opt/restaurantflow
docker compose -p restaurantflow -f docker-compose.cohost.yml ps
docker compose -p restaurantflow -f docker-compose.cohost.yml logs --tail=80 web
docker compose -p restaurantflow -f docker-compose.cohost.yml exec web python manage.py check --deploy --fail-level WARNING
```

For an update, back up the RestaurantFlow database/media, review and check out the intended commit, rebuild its image, run its one initialization job, and recreate only this stack. Do not run host-wide service restarts or Docker cleanup. Keep ERPNext health and nginx configuration checks before/after changes.

Use the backup/restore principles in [Deployment](DEPLOYMENT.md), replacing the Compose command with the cohost file above. Keep database and media backups off-host and rehearse restoration separately. Existing ERPNext backup policies remain a separate responsibility.

## Verification status

The Compose model has a regression check for published ports and migration-secret isolation. The initialization/runtime role has been exercised against an isolated local PostgreSQL database, including actual demo order/payment writes and privilege checks. Actual VPS installation, certificate issuance, role logins and ERPNext preservation must be recorded in [Progress](../PROGRESS.md); this guide does not imply they have already completed.
