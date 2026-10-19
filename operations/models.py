import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

ZERO = Decimal('0.00')

class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class RestaurantSettings(Timestamped):
    name = models.CharField(max_length=120, default='RestaurantFlow Kitchen')
    logo = models.ImageField(upload_to='logos/', blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    currency = models.CharField(max_length=3, default='PKR', validators=[RegexValidator(r'^[A-Z]{3}$', 'Use a three-letter currency code.')])
    timezone = models.CharField(max_length=60, default='Asia/Karachi')
    receipt_footer = models.CharField(max_length=250, default='Thank you for dining with us. See you again soon!')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('5'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    service_rate = models.DecimalField(max_digits=5, decimal_places=2, default=ZERO, validators=[MinValueValidator(0), MaxValueValidator(100)])
    operating_hours = models.TextField(default='Daily 12:00 – 23:00')
    order_prefix = models.CharField(max_length=8, default='ORD', validators=[RegexValidator(r'^[A-Z0-9]{1,8}$', 'Use up to 8 capital letters or digits.')])
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(id=1), name='single_restaurant_settings')]
    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]
    def __str__(self):
        return self.name

class UserProfile(Timestamped):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=40, blank=True)
    def __str__(self):
        return str(self.user)

class RestaurantArea(Timestamped):
    name = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['name']
    def __str__(self):
        return self.name

class RestaurantTable(Timestamped):
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        OCCUPIED = 'occupied', 'Occupied'
        RESERVED = 'reserved', 'Reserved'
        CLEANING = 'cleaning', 'Cleaning'
    number = models.CharField(max_length=20, unique=True)
    area = models.ForeignKey(RestaurantArea, on_delete=models.PROTECT, related_name='tables')
    capacity = models.PositiveSmallIntegerField(default=4, validators=[MinValueValidator(1), MaxValueValidator(50)])
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    assigned_waiter = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tables')
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['area__name', 'number']
        constraints = [models.CheckConstraint(condition=Q(capacity__gte=1), name='table_capacity_positive')]
    def __str__(self):
        return f'Table {self.number} · {self.area.name}'

class MenuCategory(Timestamped):
    name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=250, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name_plural = 'menu categories'
    def __str__(self):
        return self.name

class MenuItem(Timestamped):
    category = models.ForeignKey(MenuCategory, on_delete=models.PROTECT, related_name='items')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='menu/%Y/%m/', blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    preparation_minutes = models.PositiveSmallIntegerField(default=15, validators=[MinValueValidator(1), MaxValueValidator(240)])
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_vegetarian = models.BooleanField(default=False)
    is_spicy = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    class Meta:
        ordering = ['display_order', 'name']
        constraints = [models.CheckConstraint(condition=Q(price__gt=0), name='menu_price_positive')]
    def __str__(self):
        return self.name

class Customer(Timestamped):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40, blank=True, db_index=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['name']
    def __str__(self):
        return f'{self.name} · {self.phone}' if self.phone else self.name

class Discount(Timestamped):
    name = models.CharField(max_length=80, unique=True)
    percent = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(100)])
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['name']
    def __str__(self):
        return f'{self.name} ({self.percent}%)'

class Order(Timestamped):
    class Type(models.TextChoices):
        DINE_IN = 'dine_in', 'Dine-in'
        TAKEAWAY = 'takeaway', 'Takeaway'
        DELIVERY = 'delivery', 'Delivery'
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        CLOSED = 'closed', 'Closed'
        CANCELLED = 'cancelled', 'Cancelled'
    class Fulfillment(models.TextChoices):
        PENDING = 'pending', 'In progress'
        SERVED = 'served', 'Served'
        HANDED_OVER = 'handed_over', 'Handed over'
    number = models.CharField(max_length=30, unique=True, null=True, blank=True)
    request_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order_type = models.CharField(max_length=12, choices=Type.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN, db_index=True)
    fulfillment = models.CharField(max_length=15, choices=Fulfillment.choices, default=Fulfillment.PENDING)
    table = models.ForeignKey(RestaurantTable, null=True, blank=True, on_delete=models.PROTECT, related_name='orders')
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.PROTECT, related_name='orders')
    customer_name = models.CharField(max_length=120, blank=True)
    customer_phone = models.CharField(max_length=40, blank=True)
    delivery_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    currency = models.CharField(max_length=3, default='PKR')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=ZERO)
    service_rate = models.DecimalField(max_digits=5, decimal_places=2, default=ZERO)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    discount_reason = models.CharField(max_length=250, blank=True)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    service_amount = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='cancelled_orders')
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['created_at', 'status']), models.Index(fields=['created_by', 'created_at'])]
        constraints = [
            models.UniqueConstraint(fields=['table'], condition=Q(status='open', table__isnull=False), name='one_open_order_per_table'),
            models.CheckConstraint(condition=(Q(order_type='dine_in', table__isnull=False) | Q(order_type__in=['takeaway', 'delivery'], table__isnull=True)), name='order_type_table_consistent'),
            models.CheckConstraint(condition=Q(total__gte=0, paid_amount__gte=0, discount_amount__gte=0), name='order_nonnegative_money'),
            models.CheckConstraint(condition=Q(paid_amount__lte=models.F('total')), name='no_order_overpayment'),
        ]
        permissions = [
            ('view_dashboard', 'View dashboard'), ('operate_pos', 'Operate POS'), ('view_all_orders', 'View all orders'),
            ('operate_kitchen', 'Operate kitchen'), ('fulfill_order', 'Serve or hand over orders'),
            ('take_payment', 'Record payments'), ('cancel_order', 'Cancel orders and confirm refunds'),
            ('apply_discount', 'Apply discounts'), ('manage_menu', 'Manage menu'), ('manage_tables', 'Manage tables'),
            ('manage_customers', 'Manage customers'), ('view_reports', 'View reports'),
            ('manage_staff', 'Manage staff'), ('manage_settings', 'Manage restaurant settings'), ('view_audit', 'View audit history'),
        ]
    @property
    def outstanding(self):
        return ZERO if self.status == self.Status.CANCELLED else self.total - self.paid_amount
    @property
    def payment_status(self):
        if self.status == self.Status.CANCELLED:
            return 'Refunded' if self.payments.filter(kind='refund').exists() else 'Cancelled'
        return 'Paid' if self.paid_amount == self.total and self.items.filter(is_void=False).exists() else ('Partial' if self.paid_amount else 'Unpaid')
    def __str__(self):
        return self.number or f'Order {self.pk}'

class OrderItem(Timestamped):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name='order_items')
    name = models.CharField(max_length=100)
    category_name = models.CharField(max_length=80)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(99)])
    notes = models.CharField(max_length=500, blank=True)
    is_void = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=250, blank=True)
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    voided_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['id']
        constraints = [models.CheckConstraint(condition=Q(quantity__gte=1, quantity__lte=99, unit_price__gt=0), name='valid_order_item')]
    @property
    def line_total(self):
        return self.unit_price * self.quantity
    @property
    def sent(self):
        return hasattr(self, 'ticket_item')

class KitchenTicket(Timestamped):
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        PREPARING = 'preparing', 'Preparing'
        READY = 'ready', 'Ready'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='tickets')
    request_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expected_minutes = models.PositiveSmallIntegerField(default=15)
    class Meta:
        ordering = ['created_at']
    @property
    def elapsed_minutes(self):
        return max(0, int(((self.ready_at or timezone.now()) - self.created_at).total_seconds() / 60))
    @property
    def overdue(self):
        return self.status in ['new', 'preparing'] and self.elapsed_minutes >= self.expected_minutes

class KitchenTicketItem(models.Model):
    ticket = models.ForeignKey(KitchenTicket, on_delete=models.PROTECT, related_name='items')
    order_item = models.OneToOneField(OrderItem, on_delete=models.PROTECT, related_name='ticket_item')

class Payment(Timestamped):
    class Method(models.TextChoices):
        CASH = 'cash', 'Cash'
        CARD = 'card', 'Card'
        BANK = 'bank', 'Bank transfer'
        OTHER = 'other', 'Other digital'
    class Kind(models.TextChoices):
        COLLECTION = 'collection', 'Collection'
        REFUND = 'refund', 'Refund'
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=12, choices=Method.choices)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.COLLECTION)
    reference = models.CharField(max_length=120, blank=True)
    request_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payments')
    original_payment = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='refund')
    class Meta:
        ordering = ['-created_at']
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name='payment_amount_positive'),
                       models.CheckConstraint(condition=(Q(kind='collection', original_payment__isnull=True) | Q(kind='refund', original_payment__isnull=False)), name='refund_has_original_payment')]

class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=60)
    object_id = models.CharField(max_length=60)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta:
        ordering = ['-created_at']
