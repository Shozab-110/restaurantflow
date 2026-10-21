# Running behind an existing host Caddy

Use this layout when a host Caddy already owns ports 80/443 for other applications. It is an alternative to the dedicated-443 layout in [Cohosting](COHOSTING.md), not an extra public proxy to start alongside it. Inspect the live configuration and its controller before changing a shared server. Do not stop another application's proxy to free a port.

## Layout

| Listener | Purpose |
|---|---|
| Host Caddy, public 443 | Existing domain routes, kept unchanged |
| Host Caddy, public 8443 | Separate RestaurantFlow HTTPS IP listener |
| Host Caddy, public 80 | Explicit existing ERP IP route; domain HTTPS redirects still work |
| `127.0.0.1:18080` | RestaurantFlow container proxy, including uploaded media |
| `127.0.0.1:18081` | Optional, separate nginx ERP bridge using a copy of its audited site configuration |
| Container network only | RestaurantFlow Gunicorn and PostgreSQL |

The shared Compose file uses the same `restaurantflow` project, database and media volume names as the dedicated cohost file. Switching proxy layout must not recreate or empty those volumes. Only its proxy needs recreation:

```bash
cd /opt/restaurantflow
docker compose -p restaurantflow -f docker-compose.shared.yml config --quiet
docker compose -p restaurantflow -f docker-compose.shared.yml up -d --no-deps proxy
```

The internal proxy explicitly forwards HTTPS to Django because TLS terminates at the trusted host proxy. Its HTTP listener must stay bound to localhost. Keep the existing production environment, distinct cookie names and restricted runtime database role.

## Plan, validate, and apply

Back up the live Caddy JSON and the RestaurantFlow database before changing anything. Keep the JSON private: shared configurations may contain credentials. `deploy/shared_proxy.py` prepares an additive plan and never applies it or restarts a service:

```bash
umask 077
curl --fail http://127.0.0.1:2019/config/ --output caddy-before.json
python3 deploy/shared_proxy.py --current-json caddy-before.json \
  --public-ip YOUR_VPS_IP --output caddy-planned.json
caddy validate --config caddy-planned.json
```

This focused planner accepts one simple `:443` server and keeps that entire server unchanged. It adds a separate `:8443` HTTPS server, an IP-specific short-lived ACME policy, and an HTTP ERP route. Existing explicit HTTP listeners, occupied 8443 listeners or conflicting ownership of its named servers require manual review; the tool refuses to guess. The RestaurantFlow URL is `https://YOUR_VPS_IP:8443/`. Permit 8443 through the host/provider firewall; keep certificate validation reachable on 443. The same native Caddy process handles TLS-ALPN challenges and both TLS listeners.

If the old ERP nginx service was stopped by a later proxy installation, preserve its original files. The `nginx_bridge()` helper prepares a separate config from an audited HTTP-only site, changing only its listeners to localhost and adding its own PID/log files. Test it with `nginx -t -c ABSOLUTE_BRIDGE_CONFIG`, then run it under a separate `restaurantflow-erp-bridge.service`. Its original asset rules, Frappe site header, protected downloads and WebSocket routing remain in that private copy. Do not change the ERP database, original nginx files or running Gunicorn/MariaDB/Redis processes.

Validate the ERP bridge and RestaurantFlow locally before loading the shared plan. Immediately before the Caddy update, fetch the current configuration again and compare it to the saved baseline. Use the [Caddy API's `Etag`/`If-Match` mechanism](https://caddyserver.com/docs/api#concurrent-config-changes) for the single `/config/` update so a concurrent manager change cannot be overwritten. HTTP 412 means stop and rebuild the plan from the new live config. Invalid configurations are rejected by Caddy; retain a backup for a reviewed rollback if a health check fails after a successful load.

## Persistence and operational checks

The audited native Caddy service uses `--resume`, so API changes persist in its autosaved configuration. An empty/global-only `/etc/caddy/Caddyfile` is not the live routing source in this setup. A controller was observed comparing its managed 443 route list and replacing the whole configuration when a foreign route was appended there. The separate 8443 listener avoids changing that managed list. A manual Caddyfile reload or a future controller whole-config replacement can still remove added servers; coordinate configuration ownership for future changes and do not introduce a competing overwrite loop.

Verify all of the following after applying and again after the controller's polling interval:

- Original domain HTTP redirects, trusted HTTPS and expected page responses.
- ERP HTTP IP login, assets and protected routes, with its original configuration fingerprints unchanged.
- RestaurantFlow trusted HTTPS health/login, staff permissions, POS/KDS/payment workflow, reports and static/media responses.
- No public PostgreSQL/Gunicorn/bridge port; runtime DB account cannot administer roles/databases/schema.
- Proxy routes still present; service and application logs contain no new errors.

Record the active Compose filename in the deployment handover. Future RestaurantFlow updates must use `docker-compose.shared.yml`, not the original dedicated proxy file. Retain off-host backups and rehearse restoration. A passing configuration test does not certify public TLS, backups, another application's business workflows or a physical receipt printer.
