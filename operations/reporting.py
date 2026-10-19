from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper, Q
from django.utils import timezone
from .models import Order, Payment, OrderItem, KitchenTicket, RestaurantSettings, ZERO

def date_range(params, default_days=1):
    today = timezone.localdate()
    try:
        start = datetime.strptime(params.get('start', ''), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        start = today - timedelta(days=default_days - 1)
    try:
        end = datetime.strptime(params.get('end', ''), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        end = today
    if end < start:
        start, end = end, start
    if (end - start).days > 366:
        start = end - timedelta(days=366)
    tz = timezone.get_current_timezone()
    return start, end, timezone.make_aware(datetime.combine(start, time.min), tz), timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), tz)

def summary(params):
    start, end, since, until = date_range(params, 7)
    currency = params.get('currency') or RestaurantSettings.load().currency
    # Sales are recognized only when fulfilled and fully paid (closed_at).
    sales = Order.objects.filter(status='closed', currency=currency, closed_at__gte=since, closed_at__lt=until)
    collections = Payment.objects.filter(order__currency=currency, created_at__gte=since, created_at__lt=until)
    gross = collections.filter(kind='collection').aggregate(v=Sum('amount'))['v'] or ZERO
    refunds = collections.filter(kind='refund').aggregate(v=Sum('amount'))['v'] or ZERO
    total_sales = sales.aggregate(v=Sum('total'))['v'] or ZERO
    discounts = sales.aggregate(v=Sum('discount_amount'))['v'] or ZERO
    outstanding = Order.objects.filter(status='open', currency=currency).aggregate(v=Sum(F('total') - F('paid_amount')))['v'] or ZERO
    def order_groups(field):
        return sales.values(field).annotate(total=Sum('total'), count=Count('id')).order_by('-total')
    items = OrderItem.objects.filter(order__in=sales, is_void=False)
    line_value = ExpressionWrapper(F('quantity') * F('unit_price'), output_field=DecimalField(max_digits=16, decimal_places=2))
    def item_groups(field):
        grouped = items.values(field).annotate(quantity_sold=Sum('quantity'), total=Sum(line_value)).order_by('-total')
        return [{field: x[field], 'quantity': x['quantity_sold'], 'total': x['total']} for x in grouped]
    by_method = []
    for value, label in Payment.Method.choices:
        method_rows = collections.filter(method=value)
        collected = method_rows.filter(kind='collection').aggregate(v=Sum('amount'))['v'] or ZERO
        refunded = method_rows.filter(kind='refund').aggregate(v=Sum('amount'))['v'] or ZERO
        by_method.append({'name': label, 'collections': collected, 'refunds': refunded, 'net': collected - refunded})
    days = defaultdict(lambda: ZERO)
    for order in sales:
        days[timezone.localtime(order.closed_at).date().isoformat()] += order.total
    daily = [{'date': d.isoformat(), 'total': days[d.isoformat()]} for d in (start + timedelta(days=i) for i in range((end-start).days+1))]
    tickets = KitchenTicket.objects.filter(ready_at__gte=since, ready_at__lt=until).select_related('order')
    durations = [Decimal(str((t.ready_at - t.created_at).total_seconds())) / 60 for t in tickets]
    cashier_sales = {}
    for order in sales.prefetch_related('payments__recorded_by'):
        last_payment = next((p for p in order.payments.all() if p.kind == 'collection'), None)
        name = last_payment.recorded_by.username if last_payment else 'Complimentary (no payment)'
        cashier_sales.setdefault(name, {'name': name, 'count': 0, 'total': ZERO})
        cashier_sales[name]['count'] += 1
        cashier_sales[name]['total'] += order.total
    return {'start': start, 'end': end, 'currency': currency,
            'currencies': sorted(set(Order.objects.values_list('currency', flat=True)) | {RestaurantSettings.load().currency}),
            'sales': total_sales, 'sales_count': sales.count(), 'discounts': discounts,
            'collections': gross, 'refunds': refunds, 'net_collections': gross-refunds, 'outstanding': outstanding,
            'average': total_sales/sales.count() if sales.count() else ZERO, 'by_cashier': order_groups('created_by__username'),
            'by_item': item_groups('name'), 'by_category': item_groups('category_name'), 'by_method': by_method, 'daily': daily,
            'cashier_sales': sorted(cashier_sales.values(), key=lambda x: x['total'], reverse=True),
            'cancelled': Order.objects.filter(status='cancelled', currency=currency, cancelled_at__gte=since, cancelled_at__lt=until).select_related('cancelled_by'),
            'discounted': sales.filter(discount_amount__gt=0), 'outstanding_orders': Order.objects.filter(status='open', currency=currency, total__gt=F('paid_amount')),
            'tickets': tickets, 'prep_average': sum(durations, ZERO)/len(durations) if durations else ZERO,
            'orders': sales}
