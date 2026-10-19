import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from .models import RestaurantSettings, RestaurantTable, Order, OrderItem, MenuItem, KitchenTicket, KitchenTicketItem, Payment, AuditLog, ZERO
from .permissions import require, require_order

def money(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError
        return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError('Enter a valid monetary amount.')

def key(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError('Invalid request token. Refresh the page and try again.')

def audit(user, action, obj, description):
    AuditLog.objects.create(actor=user, action=action, object_type=obj.__class__.__name__, object_id=str(obj.pk), description=description)

def recalculate(order):
    order.subtotal = sum((x.line_total for x in order.items.filter(is_void=False)), ZERO)
    if order.discount_amount > order.subtotal:
        raise ValidationError('The discount cannot exceed the item subtotal. Adjust the discount first.')
    base = order.subtotal - order.discount_amount
    order.tax_amount = money(base * order.tax_rate / 100)
    order.service_amount = money(base * order.service_rate / 100)
    order.total = base + order.tax_amount + order.service_amount
    if order.total < order.paid_amount:
        raise ValidationError('This change would reduce the bill below collected payments. Cancel with a confirmed refund instead.')
    order.save()
    return order

def editable(order):
    if order.status != Order.Status.OPEN or order.fulfillment != Order.Fulfillment.PENDING:
        raise ValidationError('This order no longer accepts item changes.')

def add_lines(order, lines):
    if not isinstance(lines, list) or not lines or len(lines) > 100:
        raise ValidationError('Add between 1 and 100 menu lines.')
    for line in lines:
        try:
            item = MenuItem.objects.select_for_update().select_related('category').get(pk=int(line['id']), is_active=True, is_available=True, category__is_active=True)
            qty = int(line['quantity'])
            if str(qty) != str(line['quantity']) or qty < 1 or qty > 99:
                raise ValueError
            notes = str(line.get('notes', '')).strip()
            if len(notes) > 500:
                raise ValidationError('Item instructions must be 500 characters or fewer.')
        except (MenuItem.DoesNotExist, KeyError, ValueError, TypeError):
            raise ValidationError('A menu item is unavailable or its quantity is invalid.')
        OrderItem.objects.create(order=order, menu_item=item, name=item.name, category_name=item.category.name,
                                 unit_price=item.price, tax_rate=order.tax_rate, quantity=qty, notes=notes)
    recalculate(order)

@transaction.atomic
def create_order(user, *, request_key, order_type, lines, table=None, customer=None, customer_name='', customer_phone='', delivery_address='', notes=''):
    require(user, 'operate_pos')
    token = key(request_key)
    # Serialize duplicate creation attempts even when the order row does not yet exist.
    from django.contrib.auth import get_user_model
    get_user_model().objects.select_for_update().get(pk=user.pk)
    existing = Order.objects.filter(request_key=token).first()
    if existing:
        require_order(user, existing)
        return existing
    if order_type not in Order.Type.values:
        raise ValidationError('Select a valid order type.')
    if user.groups.filter(name='Waiter').exists() and not user.has_perm('operations.take_payment') and order_type != Order.Type.DINE_IN:
        raise PermissionDenied('Waiters can create dine-in orders only.')
    if order_type == Order.Type.DINE_IN:
        if table is None:
            raise ValidationError('Select a table for dine-in.')
        table = RestaurantTable.objects.select_for_update().get(pk=table.pk)
        if not table.is_active or not table.area.is_active or table.status != RestaurantTable.Status.AVAILABLE or table.orders.filter(status='open').exists():
            raise ValidationError('This table is no longer available.')
        if not user.has_perm('operations.view_all_orders') and table.assigned_waiter_id not in [None, user.pk]:
            raise PermissionDenied('This table is assigned to another waiter.')
    elif table:
        raise ValidationError('Only dine-in orders can have a table.')
    if order_type == Order.Type.DELIVERY and not all([customer_name.strip(), customer_phone.strip(), delivery_address.strip()]):
        raise ValidationError('Delivery requires a customer name, phone number, and address.')
    config = RestaurantSettings.load()
    order = Order.objects.create(request_key=token, order_type=order_type, table=table, customer=customer,
        customer_name=customer_name[:120], customer_phone=customer_phone[:40], delivery_address=delivery_address[:2000],
        notes=notes[:2000], created_by=user, currency=config.currency, tax_rate=config.tax_rate, service_rate=config.service_rate)
    order.number = f'{config.order_prefix}-{order.pk:06d}'
    order.save(update_fields=['number'])
    add_lines(order, lines)
    if table:
        table.status = RestaurantTable.Status.OCCUPIED
        table.save(update_fields=['status', 'updated_at'])
    audit(user, 'order.created', order, f'{order.number} created with {order.items.count()} item lines.')
    return order

@transaction.atomic
def add_order_items(user, order_id, lines):
    require(user, 'operate_pos')
    order = Order.objects.select_for_update().get(pk=order_id)
    require_order(user, order)
    editable(order)
    if order.currency != RestaurantSettings.load().currency:
        raise ValidationError('Settle or cancel this order before adding items after a currency change.')
    add_lines(order, lines)
    audit(user, 'order.items_added', order, 'Added draft items; awaiting kitchen submission.')
    return order

@transaction.atomic
def change_item(user, order_id, item_id, *, quantity=None, notes='', void_reason=''):
    require(user, 'operate_pos')
    order = Order.objects.select_for_update().get(pk=order_id)
    require_order(user, order)
    editable(order)
    item = order.items.select_for_update().get(pk=item_id, is_void=False)
    if item.sent:
        require(user, 'cancel_order')
        if not void_reason.strip():
            raise ValidationError('A reason is required to void a kitchen item.')
        item.is_void, item.void_reason, item.voided_by, item.voided_at = True, void_reason[:250], user, timezone.now()
        item.save()
        ticket = item.ticket_item.ticket
        if not ticket.items.filter(order_item__is_void=False).exists():
            ticket.status = KitchenTicket.Status.CANCELLED
            ticket.save()
        audit(user, 'item.voided', item, void_reason)
    elif str(quantity) == '0':
        audit(user, 'item.removed', item, f'Draft item {item.name} removed from {order.number}.')
        item.delete()
    else:
        try:
            qty = int(quantity)
            if qty < 1 or qty > 99:
                raise ValueError
        except (ValueError, TypeError):
            raise ValidationError('Quantity must be between 1 and 99 (or 0 to remove a draft item).')
        item.quantity, item.notes = qty, notes[:500]
        item.save()
        audit(user, 'item.updated', item, f'{item.name}: quantity {qty}.')
    recalculate(order)
    return order

@transaction.atomic
def send_to_kitchen(user, order_id, request_key):
    require(user, 'operate_pos')
    order = Order.objects.select_for_update().get(pk=order_id)
    require_order(user, order)
    editable(order)
    token = key(request_key)
    existing = KitchenTicket.objects.filter(request_key=token).first()
    if existing:
        if existing.order_id != order.pk:
            raise ValidationError('This kitchen request token belongs to another order.')
        return existing
    items = list(order.items.filter(is_void=False, ticket_item__isnull=True).select_related('menu_item'))
    if not items:
        raise ValidationError('There are no new items to send.')
    ticket = KitchenTicket.objects.create(order=order, request_key=token, expected_minutes=max(x.menu_item.preparation_minutes for x in items))
    KitchenTicketItem.objects.bulk_create([KitchenTicketItem(ticket=ticket, order_item=x) for x in items])
    audit(user, 'kitchen.sent', order, f'Ticket #{ticket.pk}: {len(items)} lines sent to kitchen.')
    return ticket

@transaction.atomic
def advance_ticket(user, ticket_id, target):
    require(user, 'operate_kitchen')
    order_id = KitchenTicket.objects.values_list('order_id', flat=True).get(pk=ticket_id)
    order = Order.objects.select_for_update().get(pk=order_id)
    ticket = KitchenTicket.objects.select_for_update().get(pk=ticket_id)
    if order.status != 'open':
        raise ValidationError('This order is no longer open.')
    expected = {'new': 'preparing', 'preparing': 'ready'}
    if ticket.status == target and target in ['preparing', 'ready']:
        return ticket
    if expected.get(ticket.status) != target:
        raise ValidationError('Invalid kitchen transition. Start preparation, then mark ready.')
    ticket.status = target
    if target == 'preparing':
        ticket.started_at = timezone.now()
    else:
        ticket.ready_at = timezone.now()
    ticket.save()
    audit(user, 'kitchen.status', ticket, f'{order.number}: {target}.')
    return ticket

def close_if_complete(order):
    if order.fulfillment != 'pending' and order.paid_amount == order.total:
        order.status, order.closed_at = 'closed', timezone.now()
        order.save(update_fields=['status', 'closed_at', 'updated_at'])
        if order.table_id:
            table = RestaurantTable.objects.select_for_update().get(pk=order.table_id)
            table.status = 'available'
            table.save(update_fields=['status', 'updated_at'])

@transaction.atomic
def fulfill_order(user, order_id):
    require(user, 'fulfill_order')
    order = Order.objects.select_for_update().get(pk=order_id)
    require_order(user, order)
    if order.fulfillment != 'pending' and order.status != 'cancelled':
        return order
    if order.status != 'open' or not order.items.filter(is_void=False).exists():
        raise ValidationError('Only an open order with items can be fulfilled.')
    if order.items.filter(is_void=False, ticket_item__isnull=True).exists() or not order.tickets.exists() or order.tickets.exclude(status__in=['ready', 'completed', 'cancelled']).exists():
        raise ValidationError('Send all items to the kitchen and wait until every ticket is ready.')
    if order.order_type != 'dine_in' and order.outstanding > 0:
        raise ValidationError('Collect full payment before handing over takeaway or delivery.')
    order.fulfillment = 'served' if order.order_type == 'dine_in' else 'handed_over'
    order.save(update_fields=['fulfillment', 'updated_at'])
    order.tickets.filter(status='ready').update(status='completed', completed_at=timezone.now())
    close_if_complete(order)
    audit(user, 'order.fulfilled', order, order.get_fulfillment_display())
    return order

@transaction.atomic
def record_payment(user, order_id, *, amount, method, reference, request_key):
    require(user, 'take_payment')
    order = Order.objects.select_for_update().get(pk=order_id)
    require_order(user, order)
    amount, token = money(amount), key(request_key)
    # A singleton row also serializes token collisions across different orders.
    RestaurantSettings.objects.select_for_update().get(pk=1)
    existing = Payment.objects.filter(request_key=token).first()
    if existing:
        if existing.order_id != order.pk or existing.amount != amount or existing.method != method or existing.reference != reference or existing.kind != 'collection':
            raise ValidationError('This payment token was already used for a different payment.')
        return existing
    if order.status != 'open' or order.total <= 0:
        raise ValidationError('Only open orders with a bill can accept payments.')
    if amount <= 0 or amount > order.outstanding:
        raise ValidationError(f'Payment must be positive and no greater than {order.currency} {order.outstanding}.')
    if method not in Payment.Method.values:
        raise ValidationError('Select a valid payment method.')
    if method != 'cash' and not reference.strip():
        raise ValidationError('A confirmation reference is required for digital payments.')
    payment = Payment.objects.create(order=order, amount=amount, method=method, reference=reference[:120], request_key=token, recorded_by=user)
    order.paid_amount += amount
    order.save(update_fields=['paid_amount', 'updated_at'])
    close_if_complete(order)
    audit(user, 'payment.recorded', order, f'{order.currency} {amount} via {method}; reference {reference or "—"}.')
    return payment

@transaction.atomic
def apply_discount(user, order_id, amount, reason):
    require(user, 'apply_discount')
    order = Order.objects.select_for_update().get(pk=order_id)
    require_order(user, order)
    if order.status != 'open':
        raise ValidationError('Only open orders can be discounted.')
    amount = money(amount)
    if amount < 0 or amount > order.subtotal or not reason.strip():
        raise ValidationError('Enter a valid discount no greater than the subtotal and a reason.')
    order.discount_amount, order.discount_reason = amount, reason[:250]
    recalculate(order)
    audit(user, 'order.discounted', order, f'{order.currency} {amount}: {reason}')
    return order

@transaction.atomic
def cancel_order(user, order_id, reason, refund_confirmed=False):
    require(user, 'cancel_order')
    order = Order.objects.select_for_update().get(pk=order_id)
    require_order(user, order)
    if order.status == 'cancelled':
        return order
    if order.status != 'open':
        raise ValidationError('Closed orders cannot be cancelled. Use the documented reconciliation process.')
    if not reason.strip():
        raise ValidationError('A cancellation reason is required.')
    if order.paid_amount and not refund_confirmed:
        raise ValidationError('Return the collected money first, then confirm the manual refund.')
    for payment in order.payments.filter(kind='collection'):
        Payment.objects.get_or_create(original_payment=payment, defaults={
            'order': order, 'amount': payment.amount, 'method': payment.method, 'kind': 'refund',
            'reference': f'Cancellation: {reason[:100]}', 'recorded_by': user})
    order.status, order.cancellation_reason = 'cancelled', reason[:2000]
    order.cancelled_by, order.cancelled_at, order.paid_amount = user, timezone.now(), ZERO
    order.save()
    order.tickets.exclude(status='completed').update(status='cancelled')
    if order.table_id:
        table = RestaurantTable.objects.select_for_update().get(pk=order.table_id)
        table.status = 'available'
        table.save(update_fields=['status', 'updated_at'])
    audit(user, 'order.cancelled', order, f'{reason}; manual refunds confirmed: {refund_confirmed}.')
    return order
