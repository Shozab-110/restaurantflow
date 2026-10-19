import csv
import json
import uuid
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError, connection
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from . import forms, services, reporting
from .models import RestaurantSettings, RestaurantArea, RestaurantTable, MenuCategory, MenuItem, Customer, Discount, Order, OrderItem, KitchenTicket, Payment, AuditLog, ZERO
from .permissions import permission_required, require, require_order, visible_orders, is_owner

User = get_user_model()

def validation_message(exc):
    return ' '.join(exc.messages) if isinstance(exc, ValidationError) else 'The record changed during this request. Refresh and try again.'

@login_required
def home(request):
    if not request.user.has_perm('operations.view_dashboard'):
        if request.user.has_perm('operations.operate_pos'):
            return redirect('tables')
        if request.user.has_perm('operations.operate_kitchen'):
            return redirect('kitchen')
        raise PermissionDenied('Your account has no operational role. Contact the owner.')
    start, end, since, until = reporting.date_range(request.GET)
    data = reporting.summary({'start': start.isoformat(), 'end': end.isoformat()})
    data.update({
        'title': 'Overview', 'active_orders': Order.objects.filter(status='open').count(),
        'pending_kitchen': KitchenTicket.objects.filter(status__in=['new', 'preparing']).count(),
        'occupied': RestaurantTable.objects.filter(is_active=True, status='occupied').count(),
        'available': RestaurantTable.objects.filter(is_active=True, area__is_active=True, status='available').count(),
        'recent_orders': Order.objects.select_related('table', 'created_by')[:7],
        'top_items': data['by_item'][:5],
        'chart_labels': [x['date'] for x in data['daily']], 'chart_values': [str(x['total']) for x in data['daily']],
        'shift_payments': Payment.objects.filter(recorded_by=request.user, created_at__gte=since, created_at__lt=until).select_related('order')[:6],
    })
    return render(request, 'operations/dashboard.html', data)

@permission_required('operate_pos')
def pos(request, order_id=None):
    existing = get_object_or_404(visible_orders(request.user), pk=order_id) if order_id else None
    if existing and (existing.status != 'open' or existing.fulfillment != 'pending'):
        messages.error(request, 'This order no longer accepts items.')
        return redirect('order_detail', pk=existing.pk)
    initial = {'request_key': uuid.uuid4(), 'order_type': 'dine_in' if request.GET.get('table') else 'takeaway', 'table': request.GET.get('table')}
    form = forms.OrderForm(request.POST or None, user=request.user, initial=initial)
    cart = []
    if request.method == 'POST':
        try:
            cart = json.loads(request.POST.get('cart', '[]'))
            if existing:
                services.add_order_items(request.user, existing.pk, cart)
                order = existing
            elif form.is_valid():
                order = services.create_order(request.user, lines=cart, **form.cleaned_data)
            else:
                order = None
            if order:
                messages.success(request, f'{order.number} saved. Send the new items to the kitchen when ready.')
                return redirect('order_detail', pk=order.pk)
        except (ValidationError, IntegrityError) as exc:
            messages.error(request, validation_message(exc))
        except (json.JSONDecodeError, TypeError):
            messages.error(request, 'The cart could not be read. Please add your items again.')
            cart = []
    categories = MenuCategory.objects.filter(is_active=True)
    menu = MenuItem.objects.filter(is_active=True, is_available=True, category__is_active=True).select_related('category')
    products = [{'id': x.pk, 'name': x.name, 'price': str(x.price), 'category': x.category_id, 'description': x.description} for x in menu]
    config = RestaurantSettings.load()
    rates = {'tax': str(existing.tax_rate if existing else config.tax_rate), 'service': str(existing.service_rate if existing else config.service_rate),
             'subtotal': str(existing.subtotal if existing else ZERO), 'discount': str(existing.discount_amount if existing else ZERO),
             'old_tax': str(existing.tax_amount if existing else ZERO), 'old_service': str(existing.service_amount if existing else ZERO)}
    return render(request, 'operations/pos.html', {'title': f'Add to {existing.number}' if existing else 'Point of sale', 'form': form, 'categories': categories,
        'menu': menu, 'products': products, 'initial_cart': cart if isinstance(cart, list) else [], 'existing': existing, 'pos_rates': rates})

@permission_required('operate_pos')
def orders(request):
    qs = visible_orders(request.user).select_related('table', 'created_by')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(customer_name__icontains=q) | Q(table__number__icontains=q))
    for field in ['status', 'order_type', 'created_by_id']:
        value = request.GET.get(field, '')
        if value:
            if field == 'created_by_id' and not value.isdigit():
                continue
            qs = qs.filter(**{field: value})
    if request.GET.get('start') or request.GET.get('end'):
        _, _, since, until = reporting.date_range(request.GET)
        qs = qs.filter(created_at__gte=since, created_at__lt=until)
    sort = request.GET.get('sort', '-created_at')
    if sort not in ['number', '-number', 'total', '-total', 'created_at', '-created_at', 'status']:
        sort = '-created_at'
    page = Paginator(qs.order_by(sort), 20).get_page(request.GET.get('page'))
    return render(request, 'operations/orders.html', {'title': 'All orders', 'page': page, 'types': Order.Type.choices, 'statuses': Order.Status.choices, 'staff': User.objects.filter(orders__isnull=False).distinct()})

@permission_required('operate_pos')
def order_detail(request, pk):
    order = get_object_or_404(visible_orders(request.user).select_related('table', 'created_by', 'customer'), pk=pk)
    items = order.items.select_related('menu_item', 'ticket_item__ticket')
    return render(request, 'operations/order_detail.html', {'title': order.number, 'order': order, 'items': items,
        'tickets': order.tickets.prefetch_related('items__order_item'), 'payments': order.payments.select_related('recorded_by'),
        'payment_form': forms.PaymentForm(initial={'request_key': uuid.uuid4(), 'amount': order.outstanding}), 'dispatch_key': uuid.uuid4(),
        'has_draft': order.items.filter(is_void=False, ticket_item__isnull=True).exists(),
        'discounts': Discount.objects.filter(is_active=True),
        'history': AuditLog.objects.filter(Q(object_type='Order', object_id=str(order.pk)) | Q(object_type='KitchenTicket', object_id__in=[str(x.pk) for x in order.tickets.all()]) | Q(object_type='OrderItem', object_id__in=[str(x.pk) for x in items])).select_related('actor')[:30]})

@require_POST
@permission_required('operate_pos')
def order_action(request, pk, action):
    order = get_object_or_404(visible_orders(request.user), pk=pk)
    try:
        if action == 'send':
            services.send_to_kitchen(request.user, pk, request.POST.get('request_key'))
            messages.success(request, 'New items sent to the kitchen.')
        elif action == 'fulfill':
            services.fulfill_order(request.user, pk)
            messages.success(request, 'Order fulfillment recorded.')
        elif action == 'payment':
            form = forms.PaymentForm(request.POST)
            if not form.is_valid():
                raise ValidationError([f'{field}: {" ".join(errors)}' for field, errors in form.errors.items()])
            services.record_payment(request.user, pk, **form.cleaned_data)
            messages.success(request, 'Payment recorded. The receipt has been updated.')
        elif action == 'discount':
            amount = request.POST.get('amount')
            if request.POST.get('discount_id'):
                promo = get_object_or_404(Discount, pk=request.POST['discount_id'], is_active=True)
                amount = services.money(order.subtotal * promo.percent / 100)
                reason = promo.name
            else:
                reason = request.POST.get('reason', '')
            services.apply_discount(request.user, pk, amount, reason)
            messages.success(request, 'Discount updated.')
        elif action == 'cancel':
            services.cancel_order(request.user, pk, request.POST.get('reason', ''), request.POST.get('refund_confirmed') == 'on')
            messages.success(request, 'Order cancelled and audit history preserved.')
        elif action == 'item':
            try:
                item_id = int(request.POST.get('item_id', ''))
            except ValueError:
                raise ValidationError('Invalid item.')
            get_object_or_404(order.items, pk=item_id)
            services.change_item(request.user, pk, item_id, quantity=request.POST.get('quantity'), notes=request.POST.get('notes', ''), void_reason=request.POST.get('void_reason', ''))
            messages.success(request, 'Order item updated.')
        elif action == 'bill':
            services.audit(request.user, 'bill.requested', order, 'Final bill requested by staff.')
            messages.success(request, 'Bill requested. The cashier can open the receipt and collect payment.')
        else:
            return not_found(request)
    except (ValidationError, IntegrityError) as exc:
        messages.error(request, validation_message(exc))
    return redirect('order_detail', pk=pk)

@permission_required('operate_pos')
def receipt(request, pk):
    order = get_object_or_404(visible_orders(request.user).select_related('table', 'created_by'), pk=pk)
    return render(request, 'operations/receipt.html', {'order': order, 'items': order.items.filter(is_void=False), 'payments': order.payments.all(), 'title': f'Receipt · {order.number}'})

@permission_required('operate_kitchen')
def kitchen(request):
    return render(request, 'operations/kitchen.html', {'title': 'Kitchen display', **kitchen_context()})

def kitchen_context():
    tickets = KitchenTicket.objects.filter(status__in=['new', 'preparing', 'ready'], order__status='open').select_related('order__table').prefetch_related('items__order_item')
    return {'tickets': tickets, 'new_count': tickets.filter(status='new').count(), 'preparing_count': tickets.filter(status='preparing').count(), 'ready_count': tickets.filter(status='ready').count(), 'refreshed_at': timezone.now()}

@permission_required('operate_kitchen')
def kitchen_board(request):
    response = render(request, 'operations/partials/kitchen_board.html', kitchen_context())
    response['Cache-Control'] = 'no-store'
    return response

@require_POST
@permission_required('operate_kitchen')
def kitchen_action(request, pk):
    get_object_or_404(KitchenTicket, pk=pk)
    try:
        services.advance_ticket(request.user, pk, request.POST.get('status'))
    except (ValidationError, IntegrityError) as exc:
        messages.error(request, validation_message(exc))
    return redirect('kitchen')

@login_required
def tables(request):
    if not request.user.has_perm('operations.operate_pos') and not request.user.has_perm('operations.manage_tables'):
        raise PermissionDenied
    qs = RestaurantTable.objects.select_related('area', 'assigned_waiter').prefetch_related('orders')
    if not request.user.has_perm('operations.view_all_orders'):
        qs = qs.filter(Q(assigned_waiter=request.user) | Q(assigned_waiter__isnull=True), is_active=True, area__is_active=True)
    area = request.GET.get('area')
    if area and area.isdigit():
        qs = qs.filter(area_id=area)
    visible = visible_orders(request.user).filter(status='open')
    current = {o.table_id: o.pk for o in visible if o.table_id}
    for table in qs:
        table.current_order_id = current.get(table.pk)
    return render(request, 'operations/tables.html', {'title': 'Tables & areas', 'tables': qs, 'areas': RestaurantArea.objects.all(), 'available': qs.filter(status='available', is_active=True).count(), 'occupied': qs.filter(status='occupied').count()})

CRUD = {
    'menu': (MenuItem, forms.MenuItemForm, 'manage_menu', 'Menu management', ['name', 'category', 'price', 'preparation_minutes', 'is_available', 'is_active']),
    'categories': (MenuCategory, forms.CategoryForm, 'manage_menu', 'Categories', ['name', 'description', 'display_order', 'is_active']),
    'areas': (RestaurantArea, forms.AreaForm, 'manage_tables', 'Dining areas', ['name', 'is_active']),
    'tables': (RestaurantTable, forms.TableForm, 'manage_tables', 'Restaurant tables', ['number', 'area', 'capacity', 'status', 'assigned_waiter', 'is_active']),
    'customers': (Customer, forms.CustomerForm, 'manage_customers', 'Customers', ['name', 'phone', 'address', 'is_active']),
    'discounts': (Discount, forms.DiscountForm, 'apply_discount', 'Discounts', ['name', 'percent', 'is_active']),
}

def crud_config(kind):
    if kind not in CRUD:
        from django.http import Http404
        raise Http404
    return CRUD[kind]

@login_required
def resource_list(request, kind):
    model, form_cls, permission, title, fields = crud_config(kind)
    require(request.user, permission)
    qs = model.objects.all()
    q = request.GET.get('q', '').strip()
    qs = qs.filter(**{f'{"number" if kind == "tables" else "name"}__icontains': q}) if q else qs
    if request.GET.get('active') in ['true', 'false']:
        qs = qs.filter(is_active=request.GET['active'] == 'true')
    sort = request.GET.get('sort', fields[0])
    if sort.lstrip('-') not in fields:
        sort = fields[0]
    page = Paginator(qs.order_by(sort), 20).get_page(request.GET.get('page'))
    labels = [model._meta.get_field(f).verbose_name.title() for f in fields]
    rows = []
    for obj in page:
        cells = []
        for f in fields:
            value = getattr(obj, f)
            if hasattr(obj, f'get_{f}_display'):
                value = getattr(obj, f'get_{f}_display')()
            cells.append({'value': 'Yes' if value is True else 'No' if value is False else value, 'bool': isinstance(value, bool), 'positive': value is True})
        rows.append({'object': obj, 'cells': cells})
    return render(request, 'operations/resource_list.html', {'title': title, 'kind': kind, 'singular': model._meta.verbose_name, 'headers': list(zip(fields, labels)), 'rows': rows, 'page': page})

@login_required
def resource_edit(request, kind, pk=None):
    model, form_cls, permission, title, fields = crud_config(kind)
    require(request.user, permission)
    obj = get_object_or_404(model, pk=pk) if pk else None
    form = form_cls(request.POST or None, request.FILES or None, instance=obj)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                if obj:
                    obj = model.objects.select_for_update().get(pk=obj.pk)
                    form = form_cls(request.POST, request.FILES, instance=obj)
                if form.is_valid():
                    if kind == 'areas' and not form.cleaned_data['is_active'] and obj and obj.tables.filter(orders__status='open').exists():
                        raise ValidationError('Complete active orders in this area before deactivating it.')
                    saved = form.save()
                    services.audit(request.user, f'{kind}.saved', saved, f'{saved} updated through business administration.')
                    messages.success(request, f'{saved} saved.')
                    return redirect('resource_list', kind=kind)
        except (ValidationError, IntegrityError) as exc:
            form.add_error(None, validation_message(exc))
    return render(request, 'operations/form.html', {'title': ('Edit ' if pk else 'New ') + model._meta.verbose_name, 'form': form, 'cancel_url': reverse('resource_list', kwargs={'kind': kind}), 'subtitle': 'Changes are saved to your restaurant. Deactivate records to preserve history.'})

@require_POST
@login_required
def resource_deactivate(request, kind, pk):
    model, _, permission, _, _ = crud_config(kind)
    require(request.user, permission)
    try:
        with transaction.atomic():
            obj = get_object_or_404(model.objects.select_for_update(), pk=pk)
            if kind == 'tables' and obj.orders.filter(status='open').exists():
                raise ValidationError('Complete the active order before deactivating this table.')
            if kind == 'areas' and obj.tables.filter(orders__status='open').exists():
                raise ValidationError('Complete orders in this area before deactivating it.')
            obj.is_active = False
            obj.save()
            services.audit(request.user, f'{kind}.deactivated', obj, f'{obj} deactivated; history retained.')
            messages.success(request, f'{obj} deactivated.')
    except ValidationError as exc:
        messages.error(request, validation_message(exc))
    return redirect('resource_list', kind=kind)

@permission_required('take_payment')
def payments(request):
    qs = Payment.objects.select_related('order', 'recorded_by')
    if not request.user.has_perm('operations.view_reports'):
        qs = qs.filter(recorded_by=request.user)
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(order__number__icontains=q) | Q(reference__icontains=q))
    if request.GET.get('method') in Payment.Method.values:
        qs = qs.filter(method=request.GET['method'])
    if request.GET.get('start') or request.GET.get('end'):
        _, _, since, until = reporting.date_range(request.GET)
        qs = qs.filter(created_at__gte=since, created_at__lt=until)
    sort = request.GET.get('sort', '-created_at')
    if sort not in ['amount', '-amount', 'created_at', '-created_at', 'method']:
        sort = '-created_at'
    return render(request, 'operations/payments.html', {'title': 'Payments', 'page': Paginator(qs.order_by(sort), 25).get_page(request.GET.get('page')), 'methods': Payment.Method.choices,
        'collected': qs.filter(kind='collection').aggregate(v=Sum('amount'))['v'] or ZERO,
        'refunded': qs.filter(kind='refund').aggregate(v=Sum('amount'))['v'] or ZERO})

@permission_required('view_reports')
def reports(request):
    data = reporting.summary(request.GET)
    if request.GET.get('export'):
        report = request.GET['export']
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="restaurantflow-{report}-{data["start"]}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        def write(row):
            writer.writerow(["'" + str(v) if str(v).startswith(('=', '+', '-', '@', '\t', '\r')) else v for v in row])
        write(['Currency', data['currency']])
        if report == 'daily':
            write(['Date', 'Recognized sales'])
            for x in data['daily']: write([x['date'], x['total']])
        elif report in ['items', 'categories']:
            field = 'name' if report == 'items' else 'category_name'
            write([report.title(), 'Quantity', 'Item gross before discount, tax, service'])
            for x in data['by_item' if report == 'items' else 'by_category']: write([x[field], x['quantity'], x['total']])
        elif report == 'methods':
            write(['Payment method', 'Collections', 'Refunds', 'Net collections'])
            for x in data['by_method']: write([x['name'], x['collections'], x['refunds'], x['net']])
        elif report == 'cashiers':
            write(['Final collecting cashier', 'Closed orders', 'Recognized sales'])
            for x in data['cashier_sales']: write([x['name'], x['count'], x['total']])
        elif report in ['cancelled', 'discounts', 'outstanding']:
            write(['Order', 'Status', 'Total', 'Discount', 'Paid net', 'Outstanding', 'Reason'])
            for o in data[{'cancelled':'cancelled', 'discounts':'discounted', 'outstanding':'outstanding_orders'}[report]]:
                write([o.number, o.status, o.total, o.discount_amount, o.paid_amount, o.outstanding, o.cancellation_reason or o.discount_reason])
        elif report == 'kitchen':
            write(['Order', 'Ticket', 'Received', 'Ready', 'Minutes', 'Target minutes'])
            for t in data['tickets']: write([t.order.number, t.pk, t.created_at.isoformat(), t.ready_at.isoformat(), t.elapsed_minutes, t.expected_minutes])
        else:
            write(['Metric', 'Amount'])
            for field in ['sales', 'collections', 'refunds', 'net_collections', 'discounts', 'outstanding']:
                write([field, data[field]])
        return response
    return render(request, 'operations/reports.html', {'title': 'Sales & reports', **data})

@permission_required('manage_staff')
def staff(request):
    qs = User.objects.prefetch_related('groups').order_by('username')
    if not is_owner(request.user):
        qs = qs.filter(is_superuser=False).exclude(groups__name__in=['Owner', 'Manager'])
    if request.GET.get('q'):
        qs = qs.filter(Q(username__icontains=request.GET['q']) | Q(first_name__icontains=request.GET['q']))
    return render(request, 'operations/staff.html', {'title': 'Staff & roles', 'page': Paginator(qs, 20).get_page(request.GET.get('page'))})

@permission_required('manage_staff')
def staff_edit(request, pk=None):
    obj = get_object_or_404(User, pk=pk) if pk else None
    if obj and not is_owner(request.user) and (obj.is_superuser or obj.groups.filter(name__in=['Owner', 'Manager']).exists()):
        raise PermissionDenied('Managers may manage cashier, waiter, and kitchen accounts only.')
    form = forms.StaffForm(request.POST or None, instance=obj, actor=request.user)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                # Serialize owner changes to protect the last active owner.
                Group.objects.select_for_update().get(name='Owner')
                if obj:
                    User.objects.select_for_update().get(pk=obj.pk)
                user = form.save(commit=False)
                role = form.cleaned_data['role']
                if obj and obj.pk == request.user.pk and (not user.is_active or role != 'Owner' and is_owner(request.user)):
                    raise ValidationError('You cannot deactivate yourself or remove your own owner role.')
                if obj and obj.groups.filter(name='Owner').exists() and (role != 'Owner' or not user.is_active):
                    if not User.objects.filter(groups__name='Owner', is_active=True).exclude(pk=obj.pk).exists():
                        raise ValidationError('Keep at least one active owner account.')
                if form.cleaned_data['password']:
                    user.set_password(form.cleaned_data['password'])
                user.save()
                user.groups.set([Group.objects.get(name=role)])
                services.audit(request.user, 'staff.saved', user, f'{user.username}: role {role}, active {user.is_active}; password changed: {bool(form.cleaned_data["password"])}.')
            messages.success(request, f'{user.username} saved.')
            return redirect('staff')
        except (ValidationError, IntegrityError) as exc:
            form.add_error(None, validation_message(exc))
    return render(request, 'operations/form.html', {'title': 'Edit staff account' if pk else 'New staff account', 'form': form, 'cancel_url': reverse('staff'), 'subtitle': 'Assign one role. Passwords are securely hashed. Managers can manage operational staff only.'})

@permission_required('manage_settings')
def settings_view(request):
    config = RestaurantSettings.load()
    form = forms.SettingsForm(request.POST or None, request.FILES or None, instance=config)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            config = form.save()
            services.audit(request.user, 'settings.updated', config, 'Restaurant identity, receipt, and default charge settings updated.')
        messages.success(request, 'Restaurant settings saved. Tax, currency, and charges apply to new orders.')
        return redirect('settings')
    return render(request, 'operations/form.html', {'title': 'Restaurant settings', 'form': form, 'cancel_url': reverse('home'), 'subtitle': 'Default tax and service charges apply to the discounted item subtotal. Existing order snapshots are preserved.'})

@permission_required('view_audit')
def audit_logs(request):
    qs = AuditLog.objects.select_related('actor')
    if request.GET.get('q'):
        qs = qs.filter(Q(action__icontains=request.GET['q']) | Q(description__icontains=request.GET['q']) | Q(actor__username__icontains=request.GET['q']))
    return render(request, 'operations/audit.html', {'title': 'Audit history', 'page': Paginator(qs, 30).get_page(request.GET.get('page'))})

@login_required
def profile(request):
    form = forms.ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your profile has been updated.')
        return redirect('profile')
    return render(request, 'operations/form.html', {'title': 'My profile', 'form': form, 'cancel_url': reverse('home'), 'subtitle': f'Signed in as {request.user.username}. Role: {", ".join(request.user.groups.values_list("name", flat=True))}', 'profile_page': True})

@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'status': 'ok', 'database': 'postgresql'})
    except Exception:
        return JsonResponse({'status': 'unavailable'}, status=503)

def permission_denied(request, exception=None):
    return render(request, 'operations/error.html', {'code': 403, 'error_title': 'Access restricted', 'detail': 'Your role cannot access this operation. Contact your restaurant owner if you need access.'}, status=403)

def not_found(request, exception=None):
    return render(request, 'operations/error.html', {'code': 404, 'error_title': 'Page not found', 'detail': 'This page or record could not be found.'}, status=404)

def server_error(request):
    return render(request, 'operations/error.html', {'code': 500, 'error_title': 'Something went wrong', 'detail': 'Please try again. If the issue continues, contact your administrator.'}, status=500)
