# Offline laptop and phone/tablet demo

RestaurantFlow can run without internet **after the application, Python packages, PostgreSQL, migrations, and demo accounts are installed once**. All runtime CSS/JavaScript libraries are local. GitHub and paid APIs are not needed for orders, kitchen tickets, login, bills, or manually recorded payments.

This setup uses your Windows laptop as the server. Bring that laptop with you; this is not a standalone phone app or a portable installer for an unprepared computer.

## Show it on several devices

1. Connect the laptop and phones/tablets to the **same local Wi-Fi router or hotspot**. The local network can have no internet connection. Hotspot support depends on the device; if Windows will not start its hotspot without an upstream connection, use an existing router or a phone hotspot that permits local clients.
2. Double-click **Start Offline Demo.cmd** in the project folder. Keep its window open. It starts the installed portable PostgreSQL when available and starts the demo on port **8001**, leaving the existing laptop-only port 8000 unchanged.
3. The window prints private addresses such as `http://192.168.18.13:8001/`. On another device, open the laptop's **Wi-Fi address**, not `127.0.0.1`. If several addresses appear, ignore WSL/Docker/VPN interfaces and try the one belonging to your connected Wi-Fi.
4. On Windows, double-click **Enable LAN Access.cmd** once and approve the administrator prompt if the firewall blocks other devices. This permits only the Python interpreter's TCP port 8001 from the local subnet on Private/Public profiles. PostgreSQL port 5433 is not opened; the firewall is not disabled.
5. Sign in on each device with a separate account: cashier on POS, kitchen on `/kitchen/`, waiter on tables. Use **Staff & Roles** on the owner account to add/reset demonstration staff accounts. Existing demo passwords remain in ignored `.local/demo-access.txt` in the original checkout; they are not in GitHub.
6. Create an order on the cashier device, send it to the kitchen, and watch it appear on the kitchen device within about five seconds. Prepare/mark ready, serve/handoff, then record payment and view the receipt.

The laptop must remain awake, with the server running. Internet is optional; the shared local Wi-Fi connection is required. Stop the demo with **Ctrl+C** in its window. Confirmed records remain in the laptop database. If you change Wi-Fi/hotspot, restart the demo to discover and allow the new address.

The HTTP LAN launcher is for demonstration using disposable accounts on a trusted local network. It refuses production settings; use [HTTPS deployment](DEPLOYMENT.md) for a live VPS. It does not enable router port forwarding, public internet hosting, or remote database access.

## Terminal alternative

```powershell
cd D:\restaurantflow
.\.venv\Scripts\python.exe scripts/demo_server.py
# Explicit laptop Wi-Fi address if automatic discovery shows virtual interfaces:
.\.venv\Scripts\python.exe scripts/demo_server.py --host-ip 192.168.18.13
# Validate without starting a server or opening a browser:
.\.venv\Scripts\python.exe scripts/demo_server.py --check --no-browser
```

The address above is an example and changes between networks. The launcher makes temporary child-process settings for explicit allowed hosts and same-origin CSRF origins. It never rewrites `.env`, credentials, menu records, or database connections, and rejects a public/remote database host for offline use. Keep any VPS configuration separate. The default firewall helper is for port 8001; a custom `--port` needs its own appropriately scoped firewall rule.

## Where data goes

Every device talks to the **same laptop Django server and PostgreSQL database**. In the original checkout, data is under ignored `.local/pgdata`; a Docker installation uses its PostgreSQL volume. Phone browsers do not hold independent order databases. Staff changes, menu prices, orders, and payments are database changes and do not require a GitHub push.

Back up before travel using [Deployment / backups](DEPLOYMENT.md). A source-code GitHub push does not back up restaurant records. Copying `.venv` to an unrelated computer is not a reliable installation; prepare and verify that computer first using [Getting started](GETTING_STARTED.md).

## If a phone cannot connect

- Open the exact `http://<laptop-wifi-ip>:8001/` address. Phone `localhost` points to the phone itself.
- Keep all devices on the same network. Guest Wi-Fi, AP/client isolation, VPNs, or some hotspots can block devices from talking; use a network that permits local clients.
- Keep the demo window open, laptop awake, and run the LAN firewall helper with Windows administrator approval.
- A changed IP requires a demo restart. The launcher deliberately avoids wildcard allowed hosts.
- If port 8001 is busy, stop the old demo window before restarting. An existing healthy demo is detected instead of starting duplicates.
- A missing database is reported; the launcher refuses to silently create an empty replacement for missing portable database data.

## VPS versus offline demo

| Local laptop / LAN | VPS / public HTTPS |
|---|---|
| Works with internet disconnected when local Wi-Fi remains connected | Devices need internet to reach the VPS |
| Laptop must be on and nearby | Laptop can be off; VPS keeps serving |
| Laptop Wi-Fi address changes between networks | Stable domain/link after deployment |
| Data stays in laptop PostgreSQL | Data stays in VPS PostgreSQL |
| Suitable for an in-person demo | Suitable for remote demos and a configured online deployment |

The same source can run in either place, but separate databases do **not** synchronize automatically. Seamless offline/online order synchronization, conflict resolution, and queued payments are outside the current MVP.

## Verification boundary

Automated checks exercise the dine-in workflow while Python socket connections are blocked and inspect rendered runtime assets for external dependencies. Launcher configuration tests cover address filtering and unchanged database settings. A real LAN-address HTTP login verifies the server's host/CSRF/session configuration. These checks do not replace a final connection from your own phone or tablet; Windows administrator approval and the router's client-isolation settings are outside the application.
