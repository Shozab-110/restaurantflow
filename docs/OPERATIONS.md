# Restaurant operations and accounting

## Administration

The sidebar exposes only the current role's business capabilities. Owners use **Staff & Roles** to add staff, choose a role, deactivate/reactivate an account, or replace its password. Managers can manage cashier/waiter/kitchen accounts and cannot assign Owner/Manager or alter those accounts. Owners cannot remove their own owner role or deactivate themselves. At least one active owner is retained.

**Menu management** supports images, descriptions, price, prep target, availability, active state, vegetarian/spicy flags, category, and display order. Uploads accept JPEG/PNG/WebP up to 5 MB / 20 megapixels and are re-encoded to JPEG with a random filename. SVG and executable uploads are rejected. Use deactivation to remove a product from service while preserving history.

**Tables & areas** provides a floor view and edit lists. Available, reserved, and cleaning states are operator-controlled. Occupied is driven by an active order and cannot be manually cleared. Assigned waiters see their assigned tables and unassigned tables. New dine-in orders lock table rows and require an active available table. A database constraint also prevents overlapping active sessions. Tables/areas cannot be deactivated while open orders use them.

**Settings** controls restaurant identity, logo, currency code, timezone, receipt footer, tax/service percentages, operating-hours text, and order prefix. Currency changes require settling or cancelling all open orders. New-order settings are snapshotted, so an existing bill does not change. Prefix changes apply only to new orders and never reset the sequence. Timezone changes affect display and report date boundaries, not stored UTC instants. Operating hours are informational in this MVP; the owner determines when to stop taking orders.

## Order and kitchen lifecycle

Order: `open → closed` or `open → cancelled`. Closed and cancelled records cannot accept item changes or collections. Fulfillment is `pending → served` for dine-in and `pending → handed_over` for takeaway/delivery. A pending order can have multiple kitchen tickets.

Kitchen: `new → preparing → ready → completed`. Kitchen staff starts and marks ready; authorized floor/POS staff serves or hands over, which completes ready tickets. Takeaway/delivery requires full payment before handoff. A dine-in table stays occupied after serving until the bill is fully paid. Repeated preparing/ready/fulfillment requests are safe. Backward/skipped transitions are rejected.

Draft lines can change quantity/instructions or be removed with quantity zero. Once submitted to a kitchen ticket, they cannot be silently removed or edited. Owner/manager can void a sent line with a reason. Its history and kitchen entry remain visible. If every line on a ticket is voided, that ticket is cancelled. A change that reduces the total below money already collected is rejected.

## Money rules

All stored money uses Decimal and two decimal places. For each bill:

```text
subtotal = sum(non-void quantity × snapshot unit price)
taxable base = subtotal − fixed discount
tax = round_half_up(taxable base × snapshot tax percent / 100, 2)
service = round_half_up(taxable base × snapshot service percent / 100, 2)
grand total = taxable base + tax + service
net paid = collections − refunds
outstanding = grand total − net paid (zero for cancelled orders)
```

Cash over-tender and change are not recorded: enter the amount retained against the bill. The application rejects overpayments. For a digital collection, obtain external confirmation first and enter its reference. It is not an external payment processor. Partial payments do not close an unfulfilled or underpaid order. A complimentary zero-total order closes when fulfilled without a fictitious payment record.

Cancelling an **open** order requires Owner/Manager and a reason. Collected money must first be returned manually using original methods, then explicitly confirmed. The application adds one full refund per original collection, cancels unfinished tickets, clears net-paid/outstanding state, and releases the table in one transaction. Duplicate cancellation requests return the existing state. Closed orders cannot be cancelled in this MVP.

## Reports

- **Sales:** grand totals of fully paid, fulfilled, closed orders, using `closed_at` in the restaurant timezone.
- **Collections/refunds:** gross positive ledger amounts by their own payment timestamps. Net collections subtract refunds. Collections can differ from sales because of deposits, open orders, and timing.
- **Outstanding:** current unsettled balances of all open orders in the selected currency, irrespective of date filter.
- **Item/category:** non-void line gross on recognized orders, before discount/tax/service. These should reconcile to recognized order **subtotals**, not grand totals.
- **Cashier:** recognized order grand totals attributed to the cashier who recorded the final collection; complimentary orders are a separate no-payment row.
- **Discounts:** fixed discounts on recognized closed orders. Cancelled order discounts are not counted as realized discounts.
- **Kitchen:** tickets marked ready in the period; received-to-ready minutes include queue time.

Reports select one currency at a time and perform no exchange-rate conversion. Default currency is the restaurant's current setting; choose an old currency to view historical bills after changing settings. CSV values that could be interpreted as spreadsheet formulas are neutralized.

## Recommended business acceptance session

Before real service, owners should run all four documented workflows with their own tax policy, currency, receipt printer, staff/table assignments, and payment references. Test two simultaneous POS operators on the same table and two retries of one payment. Verify a sample day's sales, collections, refunds, and open balances against the payment ledger. Print an actual receipt on the intended printer.
