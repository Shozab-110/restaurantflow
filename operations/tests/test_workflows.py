import json
import uuid
from decimal import Decimal
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction, close_old_connections
from django.test import TestCase, TransactionTestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from operations import services, reporting, forms
from operations.models import RestaurantSettings, RestaurantArea, RestaurantTable, MenuCategory, MenuItem, Order, Payment, KitchenTicket, AuditLog

User = get_user_model()
PASSWORD = 'Workflow-Only-Strong!9264'

class Fixtures:
    def make_fixtures(self):
        call_command('bootstrap_roles', verbosity=0)
        self.users={}
        for role in ['Owner','Manager','Cashier','Waiter','Kitchen Staff']:
            user=User.objects.create_user(username=role.lower().replace(' ','_'),password=PASSWORD,first_name=role)
            user.groups.add(Group.objects.get(name=role))
            self.users[role]=user
        self.owner=self.users['Owner'];self.manager=self.users['Manager'];self.cashier=self.users['Cashier'];self.waiter=self.users['Waiter'];self.chef=self.users['Kitchen Staff']
        config=RestaurantSettings.load();config.tax_rate=Decimal('5');config.service_rate=Decimal('2');config.save()
        self.area=RestaurantArea.objects.create(name='Main Dining')
        self.table=RestaurantTable.objects.create(number='01',area=self.area,assigned_waiter=self.waiter)
        self.category=MenuCategory.objects.create(name='Main Plates')
        self.item=MenuItem.objects.create(name='House Burger',category=self.category,price='100.00',preparation_minutes=15)
    def new_order(self, user=None, mode='dine_in', **kwargs):
        return services.create_order(user or self.waiter,request_key=uuid.uuid4(),order_type=mode,table=self.table if mode=='dine_in' else None,lines=[{'id':self.item.pk,'quantity':2,'notes':'No chilli'}],**kwargs)
    def ready(self,order):
        ticket=services.send_to_kitchen(self.cashier,order.pk,uuid.uuid4())
        services.advance_ticket(self.chef,ticket.pk,'preparing')
        services.advance_ticket(self.chef,ticket.pk,'ready')
        return ticket
    def pay(self,order,amount=None,**kwargs):
        order.refresh_from_db()
        return services.record_payment(self.cashier,order.pk,amount=amount or order.outstanding,method='cash',reference='',request_key=kwargs.pop('request_key',uuid.uuid4()),**kwargs)

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.InMemoryStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class WorkflowTests(Fixtures, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.make_fixtures(cls)
    def test_workflow_a_dine_in(self):
        order=self.new_order()
        self.assertEqual(order.total,Decimal('214.00'))
        self.table.refresh_from_db();self.assertEqual(self.table.status,'occupied')
        ticket=self.ready(order)
        services.fulfill_order(self.waiter,order.pk)
        order.refresh_from_db();self.assertEqual(order.fulfillment,'served');self.assertEqual(order.status,'open')
        self.table.refresh_from_db();self.assertEqual(self.table.status,'occupied')
        self.pay(order)
        order.refresh_from_db();self.assertEqual(order.status,'closed');self.assertEqual(order.outstanding,0)
        self.table.refresh_from_db();self.assertEqual(self.table.status,'available')
        ticket.refresh_from_db();self.assertEqual(ticket.status,'completed')
        self.client.force_login(self.cashier)
        self.assertContains(self.client.get(reverse('receipt',args=[order.pk])),order.number)
    def test_workflow_b_takeaway(self):
        order=self.new_order(self.cashier,mode='takeaway')
        self.ready(order)
        with self.assertRaises(ValidationError):services.fulfill_order(self.cashier,order.pk)
        self.pay(order)
        services.fulfill_order(self.cashier,order.pk)
        order.refresh_from_db();self.assertEqual(order.status,'closed');self.assertEqual(order.fulfillment,'handed_over')
    def test_delivery_requires_customer_details(self):
        with self.assertRaises(ValidationError):self.new_order(self.cashier,mode='delivery')
        order=self.new_order(self.cashier,mode='delivery',customer_name='Guest',customer_phone='03001234567',delivery_address='42 Park Road')
        self.ready(order);self.pay(order);services.fulfill_order(self.cashier,order.pk)
        order.refresh_from_db();self.assertEqual(order.fulfillment,'handed_over')
    def test_workflow_c_owner_frontend_administration(self):
        self.client.force_login(self.owner)
        response=self.client.post(reverse('resource_create',args=['categories']),{'name':'Desserts','display_order':2,'is_active':'on'})
        self.assertEqual(response.status_code,302)
        category=MenuCategory.objects.get(name='Desserts')
        data={'name':'Brownie','category':category.pk,'description':'Warm chocolate','price':'550.00','preparation_minutes':10,'display_order':1,'is_active':'on','is_available':'on'}
        self.assertEqual(self.client.post(reverse('resource_create',args=['menu']),data).status_code,302)
        brownie=MenuItem.objects.get(name='Brownie');data['price']='650.00'
        self.assertEqual(self.client.post(reverse('resource_edit',args=['menu',brownie.pk]),data).status_code,302)
        brownie.refresh_from_db();self.assertEqual(brownie.price,Decimal('650'))
        self.assertEqual(self.client.post(reverse('staff_create'),{'username':'new_cashier','first_name':'New','last_name':'Staff','email':'','is_active':'on','role':'Cashier','password':PASSWORD}).status_code,302)
        self.assertTrue(User.objects.get(username='new_cashier').groups.filter(name='Cashier').exists())
        self.assertEqual(self.client.get('/').status_code,200)
        export=self.client.get('/reports/?export=daily');self.assertEqual(export.status_code,200);self.assertIn('text/csv',export['Content-Type'])
    def test_workflow_d_cancellation_and_refund_retry(self):
        order=self.new_order();self.ready(order);self.pay(order,'50')
        with self.assertRaises(PermissionDenied):services.cancel_order(self.cashier,order.pk,'Guest left')
        with self.assertRaises(ValidationError):services.cancel_order(self.manager,order.pk,'')
        with self.assertRaises(ValidationError):services.cancel_order(self.manager,order.pk,'Guest left')
        services.cancel_order(self.manager,order.pk,'Guest left',True)
        services.cancel_order(self.manager,order.pk,'Guest left',True)
        order.refresh_from_db();self.table.refresh_from_db()
        self.assertEqual(order.status,'cancelled');self.assertEqual(order.paid_amount,0);self.assertEqual(order.outstanding,0)
        self.assertEqual(self.table.status,'available');self.assertEqual(order.payments.filter(kind='refund').count(),1)
        self.assertTrue(AuditLog.objects.filter(action='order.cancelled',object_id=str(order.pk)).exists())
    def test_partial_payments_idempotency_overpayment_and_token_conflict(self):
        order=self.new_order();token=uuid.uuid4()
        self.pay(order,'100',request_key=token);self.pay(order,'100',request_key=token)
        order.refresh_from_db();self.assertEqual(order.paid_amount,100);self.assertEqual(order.outstanding,Decimal('114'));self.assertEqual(order.payment_status,'Partial')
        with self.assertRaises(ValidationError):self.pay(order,'101',request_key=token)
        with self.assertRaises(ValidationError):self.pay(order,'115')
        with self.assertRaises(ValidationError):self.pay(order,'-1')
        with self.assertRaises(ValidationError):services.record_payment(self.cashier,order.pk,amount='1',method='card',reference='',request_key=uuid.uuid4())
        self.pay(order,'114');self.assertEqual(order.payments.count(),2)
    def test_discount_decimal_rounding_and_zero_bill(self):
        order=self.new_order()
        with self.assertRaises(PermissionDenied):services.apply_discount(self.cashier,order.pk,'10','Offer')
        services.apply_discount(self.manager,order.pk,'33.33','Offer')
        order.refresh_from_db();self.assertEqual(order.tax_amount,Decimal('8.33'));self.assertEqual(order.service_amount,Decimal('3.33'));self.assertEqual(order.total,Decimal('178.33'))
        services.apply_discount(self.owner,order.pk,'200','Complimentary')
        self.ready(order);services.fulfill_order(self.waiter,order.pk)
        order.refresh_from_db();self.assertEqual(order.total,0);self.assertEqual(order.status,'closed');self.assertEqual(order.payment_status,'Paid')
    def test_historical_prices_taxes_categories_preserved(self):
        order=self.new_order()
        self.item.price=Decimal('999');self.item.name='New Burger';self.item.save()
        config=RestaurantSettings.load();config.tax_rate=Decimal('20');config.currency='USD';config.save()
        services.recalculate(order)
        item=order.items.get();self.assertEqual(item.unit_price,100);self.assertEqual(item.name,'House Burger');self.assertEqual(item.tax_rate,5)
        order.refresh_from_db();self.assertEqual(order.total,214);self.assertEqual(order.currency,'PKR')
    def test_table_conflicts_and_assignment(self):
        self.new_order()
        with self.assertRaises(ValidationError):self.new_order()
        second=User.objects.create_user('second_waiter',password=PASSWORD);second.groups.add(Group.objects.get(name='Waiter'))
        other=RestaurantTable.objects.create(number='02',area=self.area,assigned_waiter=second)
        with self.assertRaises(PermissionDenied):services.create_order(self.waiter,request_key=uuid.uuid4(),order_type='dine_in',table=other,lines=[{'id':self.item.pk,'quantity':1}])
    def test_invalid_kitchen_transitions_and_duplicate_dispatch(self):
        order=self.new_order();key=uuid.uuid4()
        ticket=services.send_to_kitchen(self.waiter,order.pk,key)
        again=services.send_to_kitchen(self.waiter,order.pk,key);self.assertEqual(ticket.pk,again.pk)
        with self.assertRaises(ValidationError):services.send_to_kitchen(self.waiter,order.pk,uuid.uuid4())
        with self.assertRaises(ValidationError):services.advance_ticket(self.chef,ticket.pk,'ready')
        with self.assertRaises(ValidationError):services.fulfill_order(self.waiter,order.pk)
        with self.assertRaises(PermissionDenied):services.advance_ticket(self.waiter,ticket.pk,'preparing')
        services.advance_ticket(self.chef,ticket.pk,'preparing');services.advance_ticket(self.chef,ticket.pk,'ready')
        with self.assertRaises(ValidationError):services.advance_ticket(self.chef,ticket.pk,'new')
    def test_new_items_create_separate_kitchen_tickets(self):
        order=self.new_order();first=self.ready(order)
        services.add_order_items(self.cashier,order.pk,[{'id':self.item.pk,'quantity':1,'notes':'Extra sauce'}])
        with self.assertRaises(ValidationError):services.fulfill_order(self.waiter,order.pk)
        second=services.send_to_kitchen(self.cashier,order.pk,uuid.uuid4());self.assertNotEqual(first.pk,second.pk)
        self.assertEqual(second.items.count(),1);self.assertEqual(first.items.count(),1)
    def test_draft_edit_and_safe_kitchen_void(self):
        order=self.new_order();line=order.items.get()
        services.change_item(self.waiter,order.pk,line.pk,quantity=3,notes='Allergy')
        order.refresh_from_db();self.assertEqual(order.total,321)
        self.ready(order)
        with self.assertRaises(PermissionDenied):services.change_item(self.waiter,order.pk,line.pk,void_reason='Mistake')
        services.change_item(self.manager,order.pk,line.pk,void_reason='Guest allergy')
        line.refresh_from_db();self.assertTrue(line.is_void);self.assertTrue(line.sent);self.assertEqual(line.ticket_item.ticket.status,'cancelled')
    def test_cannot_reduce_bill_below_collections_or_modify_closed_order(self):
        order=self.new_order();self.pay(order,'200')
        with self.assertRaises(ValidationError):services.apply_discount(self.owner,order.pk,'100','Offer')
        self.ready(order);self.pay(order);services.fulfill_order(self.waiter,order.pk)
        with self.assertRaises(ValidationError):services.add_order_items(self.cashier,order.pk,[{'id':self.item.pk,'quantity':1}])
        with self.assertRaises(ValidationError):services.cancel_order(self.owner,order.pk,'Too late')
    def test_reports_reconcile_sales_collections_refunds_outstanding(self):
        completed=self.new_order();self.ready(completed);self.pay(completed);services.fulfill_order(self.waiter,completed.pk)
        partial=self.new_order(self.cashier,mode='takeaway');self.pay(partial,'50')
        cancelled=self.new_order(self.cashier,mode='takeaway');self.pay(cancelled,'25');services.cancel_order(self.manager,cancelled.pk,'Changed mind',True)
        data=reporting.summary({})
        self.assertEqual(data['sales'],214);self.assertEqual(data['collections'],289);self.assertEqual(data['refunds'],25);self.assertEqual(data['net_collections'],264);self.assertEqual(data['outstanding'],164)
        self.assertEqual(sum(x['total'] for x in data['daily']),214)
        self.assertEqual(sum(x['net'] for x in data['by_method']),264)
    def test_business_constraints(self):
        order=self.new_order()
        with self.assertRaises(IntegrityError),transaction.atomic():Order.objects.create(order_type='dine_in',table=self.table,created_by=self.owner)
        with self.assertRaises(IntegrityError),transaction.atomic():Payment.objects.create(order=order,amount='-1',method='cash',recorded_by=self.owner)
        with self.assertRaises(IntegrityError),transaction.atomic():Order.objects.create(order_type='takeaway',table=self.table,created_by=self.owner)
    def test_role_enforcement_and_isolation(self):
        order=self.new_order()
        for user,url in [(self.waiter,'/reports/'),(self.waiter,'/manage/menu/'),(self.chef,'/pos/'),(self.cashier,'/staff/'),(self.manager,'/settings/')]:
            self.client.force_login(user);self.assertEqual(self.client.get(url).status_code,403)
        self.client.force_login(self.waiter)
        self.assertEqual(self.client.post(reverse('order_action',args=[order.pk,'payment']),{'request_key':uuid.uuid4(),'amount':'10','method':'cash'}).status_code,403)
        stranger=User.objects.create_user('stranger',password=PASSWORD);stranger.groups.add(Group.objects.get(name='Waiter'));self.client.force_login(stranger)
        self.assertEqual(self.client.get(reverse('order_detail',args=[order.pk])).status_code,404)
    def test_authentication_deactivation_throttle_csrf_and_logout(self):
        self.assertEqual(self.client.get('/orders/').status_code,302)
        self.assertEqual(self.client.post('/login/',{'username':self.owner.username,'password':PASSWORD}).status_code,302)
        self.client.post('/logout/');self.assertEqual(self.client.get('/orders/').status_code,302)
        self.owner.is_active=False;self.owner.save();self.assertEqual(self.client.post('/login/',{'username':self.owner.username,'password':PASSWORD}).status_code,200)
        secure=Client(enforce_csrf_checks=True);secure.force_login(self.cashier)
        self.assertEqual(secure.post('/orders/1/action/payment/',{'amount':'1'}).status_code,403)
        brute=Client()
        for _ in range(5):brute.post('/login/',{'username':'unknown','password':'incorrect'})
        self.assertEqual(brute.post('/login/',{'username':'unknown','password':'incorrect'}).status_code,429)
        self.assertEqual(Client().post('/login/',{'username':self.cashier.username,'password':PASSWORD}).status_code,302)
    def test_manager_cannot_escalate_staff_and_owner_cannot_lock_self_out(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse('staff_edit',args=[self.owner.pk])).status_code,403)
        response=self.client.post(reverse('staff_create'),{'username':'evil','role':'Owner','password':PASSWORD,'is_active':'on'})
        self.assertEqual(response.status_code,200);self.assertFalse(User.objects.filter(username='evil').exists())
        self.client.force_login(self.owner)
        response=self.client.post(reverse('staff_edit',args=[self.owner.pk]),{'username':self.owner.username,'role':'Cashier','password':'','is_active':'on'})
        self.assertContains(response,'cannot deactivate yourself')
    def test_table_cannot_be_manually_released_or_deactivated_while_open(self):
        order=self.new_order();self.client.force_login(self.owner)
        response=self.client.post(reverse('resource_edit',args=['tables',self.table.pk]),{'number':'01','area':self.area.pk,'capacity':4,'status':'available','assigned_waiter':self.waiter.pk})
        self.assertEqual(response.status_code,302)
        self.table.refresh_from_db();self.assertEqual(self.table.status,'occupied');self.assertTrue(self.table.is_active)
        self.client.post(reverse('resource_deactivate',args=['tables',self.table.pk]));self.table.refresh_from_db();self.assertTrue(self.table.is_active)
    def test_image_validation_reencodes_safe_uploads(self):
        out=BytesIO();Image.new('RGB',(10,10),'red').save(out,'PNG')
        upload=SimpleUploadedFile('image.png',out.getvalue(),content_type='image/png')
        form=forms.MenuItemForm(data={'name':'Salad','category':self.category.pk,'price':'100','preparation_minutes':5,'display_order':1,'is_active':'on'},files={'image':upload})
        self.assertTrue(form.is_valid(),form.errors);self.assertTrue(form.cleaned_data['image'].name.endswith('.jpg'))
        bad=SimpleUploadedFile('evil.svg',b'<svg><script>alert(1)</script></svg>',content_type='image/svg+xml')
        form=forms.MenuItemForm(data={'name':'Bad','category':self.category.pk,'price':'100','preparation_minutes':5,'display_order':1},files={'image':bad});self.assertFalse(form.is_valid())
    def test_every_primary_page_and_forms_render(self):
        order=self.new_order();self.client.force_login(self.owner)
        urls=['/','/pos/','/orders/',f'/orders/{order.pk}/',f'/orders/{order.pk}/receipt/','/kitchen/','/kitchen/board/','/tables/','/payments/','/reports/','/staff/','/staff/new/','/settings/','/audit/','/profile/','/password/change/']
        for kind in ['menu','categories','areas','tables','customers','discounts']:
            urls += [f'/manage/{kind}/',f'/manage/{kind}/new/']
        for url in urls:
            with self.subTest(url=url):self.assertEqual(self.client.get(url).status_code,200)
    def test_pos_form_creates_order_and_retries_are_safe(self):
        self.client.force_login(self.cashier);token=uuid.uuid4()
        payload={'request_key':str(token),'order_type':'takeaway','cart':json.dumps([{'id':self.item.pk,'quantity':2,'notes':'No onion'}])}
        response=self.client.post('/pos/',payload);self.assertEqual(response.status_code,302)
        self.client.post('/pos/',payload);self.assertEqual(Order.objects.filter(request_key=token).count(),1)
    def test_frontend_dine_in_end_to_end(self):
        self.assertEqual(self.client.post('/login/',{'username':self.waiter.username,'password':PASSWORD}).status_code,302)
        self.assertContains(self.client.get('/tables/'),'Table 01')
        response=self.client.post('/pos/',{'request_key':uuid.uuid4(),'order_type':'dine_in','table':self.table.pk,'cart':json.dumps([{'id':self.item.pk,'quantity':2,'notes':'No chilli'}])})
        self.assertEqual(response.status_code,302);order=Order.objects.get()
        self.assertEqual(self.client.post(reverse('order_action',args=[order.pk,'send']),{'request_key':uuid.uuid4()}).status_code,302)
        ticket=order.tickets.get()
        self.client.force_login(self.chef)
        self.assertContains(self.client.get('/kitchen/board/'),order.number)
        for status in ['preparing','ready']:
            self.assertEqual(self.client.post(reverse('kitchen_action',args=[ticket.pk]),{'status':status}).status_code,302)
        self.client.force_login(self.waiter)
        self.client.post(reverse('order_action',args=[order.pk,'fulfill']))
        self.client.post(reverse('order_action',args=[order.pk,'bill']))
        self.client.force_login(self.cashier)
        self.assertContains(self.client.get(reverse('receipt',args=[order.pk])),'214.00')
        self.client.post(reverse('order_action',args=[order.pk,'payment']),{'request_key':uuid.uuid4(),'amount':'214.00','method':'cash','reference':''})
        order.refresh_from_db();self.table.refresh_from_db()
        self.assertEqual(order.status,'closed');self.assertEqual(self.table.status,'available')
    def test_password_change_and_staff_reset(self):
        self.client.force_login(self.waiter)
        response=self.client.post('/password/change/',{'old_password':PASSWORD,'new_password1':'A-Different-Strong!5512','new_password2':'A-Different-Strong!5512'})
        self.assertEqual(response.status_code,302)
        self.waiter.refresh_from_db();self.assertTrue(self.waiter.check_password('A-Different-Strong!5512'))
        self.client.force_login(self.owner)
        self.client.post(reverse('staff_edit',args=[self.waiter.pk]),{'username':self.waiter.username,'role':'Waiter','password':PASSWORD,'is_active':'on'})
        self.waiter.refresh_from_db();self.assertTrue(self.waiter.check_password(PASSWORD))
    def test_reporting_does_not_mix_currencies(self):
        order=self.new_order();self.ready(order);self.pay(order);services.fulfill_order(self.waiter,order.pk)
        config=RestaurantSettings.load();config.currency='USD';config.save()
        self.assertEqual(reporting.summary({})['sales'],0)
        self.assertEqual(reporting.summary({'currency':'PKR'})['sales'],214)
    def test_currency_change_requires_settled_orders(self):
        order=self.new_order()
        form=forms.SettingsForm(instance=RestaurantSettings.load())
        form.cleaned_data={'currency':'USD'}
        with self.assertRaises(ValidationError):form.clean_currency()
        config=RestaurantSettings.load();config.currency='USD';config.save()
        with self.assertRaises(ValidationError):services.add_order_items(self.cashier,order.pk,[{'id':self.item.pk,'quantity':1}])
    def test_demo_seeding_is_idempotent(self):
        import os
        from unittest.mock import patch
        with override_settings(DEBUG=True),patch.dict(os.environ,{'RESTAURANTFLOW_DEMO_PASSWORD':PASSWORD}):
            # Existing workflow users have the expected demo roles but different usernames for kitchen.
            call_command('seed_demo',confirm_demo=True,verbosity=0)
            counts=(Order.objects.count(),Payment.objects.count(),KitchenTicket.objects.count(),MenuItem.objects.count())
            call_command('seed_demo',confirm_demo=True,verbosity=0)
            self.assertEqual(counts,(Order.objects.count(),Payment.objects.count(),KitchenTicket.objects.count(),MenuItem.objects.count()))

class ConcurrencyTests(Fixtures, TransactionTestCase):
    def setUp(self):self.make_fixtures()
    def test_parallel_payment_retry_records_once(self):
        order=self.new_order();token=uuid.uuid4()
        def pay():
            close_old_connections()
            try:
                user=User.objects.get(pk=self.cashier.pk)
                return services.record_payment(user,order.pk,amount='100',method='cash',reference='',request_key=token).pk
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(lambda _:pay(),range(2)))
        self.assertEqual(ids[0],ids[1]);self.assertEqual(Payment.objects.filter(order=order).count(),1)
        order.refresh_from_db();self.assertEqual(order.paid_amount,100)
    def test_parallel_table_assignment_allows_one_active_order(self):
        def create(index):
            close_old_connections()
            try:
                user=User.objects.get(pk=[self.cashier.pk,self.owner.pk][index]);table=RestaurantTable.objects.get(pk=self.table.pk)
                try:
                    services.create_order(user,request_key=uuid.uuid4(),order_type='dine_in',table=table,lines=[{'id':self.item.pk,'quantity':1}]);return True
                except ValidationError:return False
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(create,range(2)))
        self.assertEqual(sum(results),1);self.assertEqual(Order.objects.filter(table=self.table,status='open').count(),1)
