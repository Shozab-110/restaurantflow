# Screenshot and device-verification guide

The compact theme was inspected on 21 October 2026 using installed headless Chrome. The captures below are actual Django-rendered pages from a seeded development database, with the application's local CSS and JavaScript. The POS cart was populated through product-card clicks. They contain synthetic demonstration records.

- [Dashboard, 1440px](screenshots/dashboard.png)
- [POS, 1440px](screenshots/pos.png)

These are rendered local HTML fixtures, not screenshots of the VPS. Kitchen polling was disabled in the fixtures. Viewport and coarse-pointer emulation verified 13 page/width combinations at 390, 768, 1024, 1366 and 1440px: no document overflow, 44px touch controls, 48px kitchen actions, phone form stacking and POS item selection. The screenshot banner remains a separate illustration.

Physical device, networked browser interaction, live kitchen refresh and receipt-printer acceptance remain separate checks. The ignored local evidence is in `.local/theme-preview/verified-*.{png,json}`; see [PROGRESS.md](../PROGRESS.md).

To extend the gallery, use a separate seeded demonstration database, open the app in an available browser, and capture:

| Suggested filename | Page and scenario |
|---|---|
| `dashboard.png` | Owner overview with a meaningful date range and real synthetic sales |
| `pos.png` | POS with category/search and a populated cart with item notes |
| `kitchen.png` | New/preparing/ready tickets with clear instructions and elapsed times |
| `tables.png` | Dining floor with available/occupied/reserved/cleaning examples |
| `order-payment.png` | Order details showing a partial payment and remaining balance |
| `reports.png` | Date/currency-filtered reporting and available CSV exports |
| `receipt.png` | Print preview using the intended paper size |

Place approved captures under `docs/screenshots/` and add relative image links to the README. Remove customer/staff details, payment references, session data, tokens, development passwords and private addresses. Keep the original screenshot when annotating so evidence is not misrepresented.

Check desktop and tablet widths, touch targets, table overflow, validation messages, sidebar navigation, live kitchen refresh without disruptive full-page reloads, and the actual printer output. Record device/browser versions and issues found in `PROGRESS.md` or a sanitized bug report.
