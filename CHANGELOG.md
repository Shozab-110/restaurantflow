# Changelog

## Compact theme — 2026-10-21

- Reduced shared navigation, header, card, form and table spacing; introduced consistent theme tokens and shorter page headings.
- Added denser POS product cards, a sticky cart and responsive two-column forms.
- Preserved large touch controls and kitchen actions, local assets and receipt print rules.
- Inspected 13 browser viewport scenarios and added actual demo screenshots with explicit verification limits.

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
- Fixed threaded test connection cleanup exposed by fresh Linux test-database teardown; masked disposable CI secrets and enabled private vulnerability reporting.
- Verified all 38 automated tests and the complete Linux Docker startup/health/owner workflow in [GitHub CI](https://github.com/Shozab-110/restaurantflow/actions/runs/39275185992).

### Verification limits

Native Windows PostgreSQL workflows and the Linux Docker stack are verified. Browser screenshots/tablet layout/physical printer checks and a real HTTPS deployment remain outstanding; see [Testing](docs/TESTING.md) for the exact evidence.
