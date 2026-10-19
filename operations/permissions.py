from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q

ROLE_PERMISSIONS = {
    'Owner': ['view_dashboard', 'operate_pos', 'view_all_orders', 'operate_kitchen', 'fulfill_order', 'take_payment', 'cancel_order', 'apply_discount', 'manage_menu', 'manage_tables', 'manage_customers', 'view_reports', 'manage_staff', 'manage_settings', 'view_audit'],
    'Manager': ['view_dashboard', 'operate_pos', 'view_all_orders', 'operate_kitchen', 'fulfill_order', 'take_payment', 'cancel_order', 'apply_discount', 'manage_menu', 'manage_tables', 'manage_customers', 'view_reports', 'manage_staff', 'view_audit'],
    'Cashier': ['view_dashboard', 'operate_pos', 'view_all_orders', 'fulfill_order', 'take_payment', 'manage_customers'],
    'Waiter': ['operate_pos', 'fulfill_order'],
    'Kitchen Staff': ['operate_kitchen'],
}

def require(user, codename):
    if not user.is_active or not user.has_perm(f'operations.{codename}'):
        raise PermissionDenied('Your role does not permit this action.')

def permission_required(codename):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            require(request.user, codename)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator

def is_owner(user):
    return user.is_superuser or user.groups.filter(name='Owner').exists()

def visible_orders(user):
    from .models import Order
    if user.has_perm('operations.view_all_orders'):
        return Order.objects.all()
    if user.has_perm('operations.operate_pos'):
        return Order.objects.filter(Q(created_by=user) | Q(table__assigned_waiter=user))
    return Order.objects.none()

def require_order(user, order):
    if not visible_orders(user).filter(pk=order.pk).exists():
        raise PermissionDenied('This order is not assigned to you.')
