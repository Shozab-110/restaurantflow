# Screenshot and device-verification guide

The original automation environment did not provide a connected browser. The repository banner is an illustration, not a screenshot. HTTP/DOM test results do not prove visual layout. No fabricated application screenshots are included.

To add a real gallery, use a separate seeded demonstration database, open the app in an available browser, and capture:

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
