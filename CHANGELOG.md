# Changelog

## 0.1.0 — 2026-10-19

Initial tested local MVP.

### Added

- PostgreSQL-backed restaurant POS, order management, kitchen batches, and polling display.
- Owner, manager, cashier, waiter, and kitchen permissions with custom business administration.
- Menu, category, table, area, customer, discount, staff, profile, and restaurant settings screens.
- Decimal billing, price/rate snapshots, partial payments, retry protection, confirmed refund/cancellation records, audit history, and printed HTML receipts.
- Dashboard, date/currency reports, CSV exports, demo seeding, owner initialization, and deployment/backup guidance.
- PostgreSQL workflow/concurrency tests and POS DOM interaction checks.

### Repository preparation

- Added safe environment generation, a host-accessible PostgreSQL development override, and complete fresh-clone instructions.
- Added architecture, database, testing, troubleshooting, and findings/solutions documentation.
- Added GitHub CI, issue/PR templates, contribution and security guidance, and a repository banner.

### Verification limits

The original Windows environment verified native PostgreSQL workflows and production Django/WhiteNoise settings. Browser screenshots/tablet layout/physical printer checks and a real HTTPS deployment are not certified by those results. GitHub CI separately verifies the container stack when its run completes; consult the Actions result and [Testing](docs/TESTING.md) for the current evidence.
