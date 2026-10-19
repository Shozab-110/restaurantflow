import uuid
from decimal import Decimal
from io import BytesIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones
from PIL import Image, ImageOps
from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Q
from .models import RestaurantSettings, RestaurantArea, RestaurantTable, MenuCategory, MenuItem, Customer, Discount, Order, Payment
from .permissions import is_owner, ROLE_PERMISSIONS

User = get_user_model()

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username', 'placeholder': 'Your username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'placeholder': 'Your password'}))

class SafeImageMixin:
    def clean_image_file(self, field):
        uploaded = self.cleaned_data.get(field)
        if not uploaded or not hasattr(uploaded, 'content_type'):
            return uploaded
        if uploaded.size > 5 * 1024 * 1024:
            raise ValidationError('Images must be 5 MB or smaller.')
        try:
            img = Image.open(uploaded)
            if img.format not in ['JPEG', 'PNG', 'WEBP'] or img.width * img.height > 20_000_000:
                raise ValueError
            img = ImageOps.exif_transpose(img).convert('RGB')
            img.thumbnail((1600, 1600))
            output = BytesIO()
            img.save(output, 'JPEG', quality=88)
            return ContentFile(output.getvalue(), name=f'{uuid.uuid4().hex}.jpg')
        except Exception as exc:
            raise ValidationError('Upload a valid JPEG, PNG, or WebP image up to 20 megapixels.') from exc

class CategoryForm(forms.ModelForm):
    class Meta:
        model = MenuCategory
        fields = ['name', 'description', 'display_order', 'is_active']

class MenuItemForm(SafeImageMixin, forms.ModelForm):
    def clean_image(self):
        return self.clean_image_file('image')
    class Meta:
        model = MenuItem
        fields = ['name', 'category', 'description', 'image', 'price', 'preparation_minutes', 'display_order', 'is_available', 'is_active', 'is_vegetarian', 'is_spicy']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

class AreaForm(forms.ModelForm):
    class Meta:
        model = RestaurantArea
        fields = ['name', 'is_active']

class TableForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_waiter'].queryset = User.objects.filter(is_active=True, groups__name='Waiter')
        self.fields['status'].choices = [(k, v) for k, v in RestaurantTable.Status.choices if k != 'occupied']
        if self.instance.pk and self.instance.orders.filter(status='open').exists():
            self.fields['status'].choices = RestaurantTable.Status.choices
            for name in ['status', 'is_active', 'area']:
                self.fields[name].disabled = True
    def clean_status(self):
        value = self.cleaned_data['status']
        active = self.instance.pk and self.instance.orders.filter(status='open').exists()
        if value == 'occupied' and not active:
            raise ValidationError('Tables become occupied when an order is started.')
        if active and value != 'occupied':
            raise ValidationError('Complete or cancel the active order before changing this status.')
        return value
    class Meta:
        model = RestaurantTable
        fields = ['number', 'area', 'capacity', 'status', 'assigned_waiter', 'is_active']

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'address', 'is_active']
        widgets = {'address': forms.Textarea(attrs={'rows': 3})}

class DiscountForm(forms.ModelForm):
    class Meta:
        model = Discount
        fields = ['name', 'percent', 'is_active']

class SettingsForm(SafeImageMixin, forms.ModelForm):
    timezone = forms.ChoiceField(choices=[(x, x) for x in sorted(available_timezones())])
    def clean_logo(self):
        return self.clean_image_file('logo')
    def clean_currency(self):
        currency = self.cleaned_data['currency'].upper()
        if self.instance.pk and currency != RestaurantSettings.objects.get(pk=self.instance.pk).currency and Order.objects.filter(status='open').exists():
            raise ValidationError('Settle or cancel all open orders before changing currency.')
        return currency
    class Meta:
        model = RestaurantSettings
        fields = ['name', 'logo', 'address', 'phone', 'currency', 'timezone', 'receipt_footer', 'tax_rate', 'service_rate', 'operating_hours', 'order_prefix']
        widgets = {'address': forms.Textarea(attrs={'rows': 2}), 'operating_hours': forms.Textarea(attrs={'rows': 3})}

class OrderForm(forms.Form):
    request_key = forms.UUIDField(widget=forms.HiddenInput)
    order_type = forms.ChoiceField(choices=Order.Type.choices)
    table = forms.ModelChoiceField(queryset=RestaurantTable.objects.none(), required=False)
    customer = forms.ModelChoiceField(queryset=Customer.objects.filter(is_active=True), required=False)
    customer_name = forms.CharField(max_length=120, required=False)
    customer_phone = forms.CharField(max_length=40, required=False)
    delivery_address = forms.CharField(max_length=2000, required=False, widget=forms.Textarea(attrs={'rows': 2}))
    notes = forms.CharField(max_length=2000, required=False, widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Allergies, timing, or special requests…'}))
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        tables = RestaurantTable.objects.filter(is_active=True, area__is_active=True, status='available').select_related('area')
        if not user.has_perm('operations.view_all_orders'):
            tables = tables.filter(Q(assigned_waiter=user) | Q(assigned_waiter__isnull=True))
        self.fields['table'].queryset = tables
        if not user.has_perm('operations.take_payment') and user.groups.filter(name='Waiter').exists():
            self.fields['order_type'].choices = [('dine_in', 'Dine-in')]
    def clean(self):
        data = super().clean()
        if data.get('order_type') == 'dine_in' and not data.get('table'):
            self.add_error('table', 'Select an available table.')
        if data.get('order_type') != 'dine_in':
            data['table'] = None
        if data.get('order_type') == 'delivery':
            for field in ['customer_name', 'customer_phone', 'delivery_address']:
                if not data.get(field):
                    self.add_error(field, 'Required for delivery.')
        return data

class PaymentForm(forms.Form):
    request_key = forms.UUIDField(widget=forms.HiddenInput)
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'), widget=forms.NumberInput(attrs={'step': '0.01'}))
    method = forms.ChoiceField(choices=Payment.Method.choices)
    reference = forms.CharField(max_length=120, required=False, help_text='Required for manually confirmed digital payments.')
    def clean(self):
        data = super().clean()
        if data.get('method') != 'cash' and not data.get('reference'):
            self.add_error('reference', 'Enter the confirmation reference.')
        return data

class StaffForm(forms.ModelForm):
    role = forms.ChoiceField(choices=[(x, x) for x in ROLE_PERMISSIONS])
    password = forms.CharField(required=False, widget=forms.PasswordInput, help_text='At least 10 characters. Leave blank to keep the current password.')
    def __init__(self, *args, actor, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        if not is_owner(actor):
            self.fields['role'].choices = [(x, x) for x in ['Cashier', 'Waiter', 'Kitchen Staff']]
        if self.instance.pk:
            self.initial['role'] = self.instance.groups.values_list('name', flat=True).first()
    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if not self.instance.pk and not password:
            raise ValidationError('A password is required for a new staff account.')
        if password:
            password_validation.validate_password(password, self.instance)
        return password
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
