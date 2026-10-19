import os
import uuid
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone
from operations.models import RestaurantSettings, RestaurantArea, RestaurantTable, MenuCategory, MenuItem, Customer, Discount, Order, KitchenTicket, Payment, AuditLog
from operations import services

MENU = {
    'Starters': [('Crispy Calamari','Golden rings, citrus aioli, fresh lemon',850,12),('Loaded Fries','Crisp fries, cheese sauce, house seasoning',590,10),('Chicken Wings','Smoky wings with our signature glaze',790,15),('Garden Bruschetta','Toasted sourdough, tomatoes, fresh basil',520,8),('Creamy Mushroom Soup','Roasted mushrooms, cream, warm bread',650,10)],
    'Burgers & Sandwiches': [('The House Burger','Grilled beef, aged cheddar, house sauce',1250,18),('Crispy Chicken Burger','Buttermilk chicken, slaw, pickles',990,15),('Mushroom Melt','Grilled mushrooms, cheese, herb mayo',890,15),('Club Sandwich','Chicken, egg, lettuce, toasted bread',950,12),('Steak Sandwich','Tender beef strips, caramelized onions',1450,20)],
    'Main Plates': [('Grilled Chicken','Herb chicken, roasted vegetables, jus',1690,22),('Alfredo Pasta','Creamy parmesan sauce, grilled chicken',1350,18),('Spicy Arrabbiata','Penne, rich tomato sauce, chilli flakes',1090,15),('Pan Seared Fish','Seasonal fish, lemon butter, potato mash',1890,25),('Beef Steak','Grilled beef, peppercorn sauce, fries',2490,30)],
    'Drinks': [('Fresh Lime','Fresh lime, mint, soda',350,5),('Iced Latte','Espresso, chilled milk, ice',590,5),('Mango Cooler','Mango, citrus, a little sunshine',450,5),('Peach Iced Tea','Brewed tea, peach, fresh lemon',390,5),('Mineral Water','Chilled bottled water',150,1)],
    'Desserts': [('Chocolate Brownie','Warm chocolate brownie, vanilla cream',650,10),('New York Cheesecake','Classic baked cheesecake, berry sauce',790,8),('Vanilla Ice Cream','Two scoops of creamy vanilla',390,3),('Caramel Pudding','Silky custard, golden caramel',550,8),('Seasonal Fruit Bowl','Fresh seasonal fruit, mint',490,5)],
}
def token(name):
    return uuid.uuid5(uuid.NAMESPACE_URL, f'https://restaurantflow.local/demo/{name}')

class Command(BaseCommand):
    help = 'Seed an idempotent demonstration restaurant, staff, menu, and operational records. Never run on a live restaurant database.'
    def add_arguments(self, parser):
        parser.add_argument('--confirm-demo', action='store_true')
    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirm_demo'] or not settings.DEBUG:
            raise CommandError('Demo seeding requires DJANGO_DEBUG=true and --confirm-demo. Use create_owner for production.')
        password = os.getenv('RESTAURANTFLOW_DEMO_PASSWORD')
        if not password:
            raise CommandError('Set RESTAURANTFLOW_DEMO_PASSWORD to a strong, temporary demonstration password.')
        password_validation.validate_password(password)
        call_command('bootstrap_roles', verbosity=0)
        config = RestaurantSettings.load()
        if config.name == 'RestaurantFlow Kitchen':
            config.name, config.address, config.phone = 'The Olive Table', '24 Garden Avenue, Gulberg, Lahore', '+92 42 3571 2400'
            config.service_rate = Decimal('2.00')
            config.save()
        User = get_user_model()
        staff = {}
        for username, first, last, role in [('owner','Ayesha','Khan','Owner'),('manager','Hamza','Ali','Manager'),('cashier','Sara','Ahmed','Cashier'),('waiter','Bilal','Hassan','Waiter'),('kitchen','Zain','Chef','Kitchen Staff')]:
            user, created = User.objects.get_or_create(username=username, defaults={'first_name':first,'last_name':last})
            if created:
                user.set_password(password)
                user.save()
                user.groups.set([Group.objects.get(name=role)])
            elif not user.groups.filter(name=role).exists():
                raise CommandError(f'Existing username {username} does not match the demo role. Use a separate demo database.')
            staff[username]=user
        areas = [RestaurantArea.objects.get_or_create(name=name)[0] for name in ['Main Dining','Garden Terrace','Private Lounge']]
        tables=[]
        for i in range(1,13):
            table,_ = RestaurantTable.objects.get_or_create(number=f'{i:02}', defaults={'area':areas[(i-1)//4], 'capacity':2 if i%3==0 else 4, 'assigned_waiter':staff['waiter']})
            tables.append(table)
        products=[]
        for index,(category,entries) in enumerate(MENU.items()):
            cat,_ = MenuCategory.objects.get_or_create(name=category, defaults={'display_order':index})
            for j,(name,description,price,minutes) in enumerate(entries):
                item,_ = MenuItem.objects.get_or_create(name=name,category=cat,defaults={'description':description,'price':Decimal(price),'preparation_minutes':minutes,'display_order':j,'is_vegetarian':name in ['Garden Bruschetta','Loaded Fries','Mushroom Melt','Spicy Arrabbiata'] or category in ['Drinks','Desserts'],'is_spicy':name in ['Chicken Wings','Spicy Arrabbiata']})
                products.append(item)
        customers=[]
        for name,phone,address in [('Ali Raza','03001234567','12 Park Road, Lahore'),('Fatima Noor','03219876543','8 Model Town, Lahore'),('Omar Shah','03335550101','42 Canal View, Lahore'),('Hina Malik','03006661234','15 Garden Road, Lahore')]:
            customers.append(Customer.objects.get_or_create(name=name,phone=phone,defaults={'address':address})[0])
        Discount.objects.get_or_create(name='Team welcome', defaults={'percent':Decimal('10')})
        now=timezone.now()
        for i in range(30):
            request_key=token(f'order/{i}')
            if Order.objects.filter(request_key=request_key).exists():
                continue
            mode=['dine_in','takeaway','delivery'][i%3]
            closed=i<24
            if not closed: mode='dine_in' if i<28 else 'takeaway'
            table=tables[i%12] if mode=='dine_in' else None
            if table and table.status!='available':
                continue
            customer=customers[i%len(customers)]
            order=services.create_order(staff['cashier'] if mode!='dine_in' else staff['waiter'], request_key=request_key, order_type=mode, table=table,
                customer=customer, customer_name=customer.name, customer_phone=customer.phone, delivery_address=customer.address if mode=='delivery' else '',
                notes='Guest prefers a quiet table.' if i==25 else '', lines=[{'id':products[i%15].pk,'quantity':1+(i%2),'notes':'No chilli, please' if i%5==0 else ''},{'id':products[15+i%5].pk,'quantity':2,'notes':''}])
            ticket=services.send_to_kitchen(staff['cashier'],order.pk,token(f'ticket/{i}'))
            if closed or i%3>0:
                services.advance_ticket(staff['kitchen'],ticket.pk,'preparing')
            if closed or i%3==2:
                services.advance_ticket(staff['kitchen'],ticket.pk,'ready')
            if closed:
                if i%5==0:
                    services.apply_discount(staff['manager'],order.pk,'100','Welcome offer')
                order.refresh_from_db()
                services.record_payment(staff['cashier'],order.pk,amount=order.total,method=['cash','card','bank'][i%3],reference='' if i%3==0 else f'DEMO-{i:04}',request_key=token(f'payment/{i}'))
                services.fulfill_order(staff['waiter'] if mode=='dine_in' else staff['cashier'],order.pk)
                when=now-timedelta(days=i%7,hours=1+(i%4),minutes=i*2)
                Order.objects.filter(pk=order.pk).update(created_at=when,closed_at=when+timedelta(minutes=25))
                Payment.objects.filter(order=order).update(created_at=when+timedelta(minutes=24))
                KitchenTicket.objects.filter(pk=ticket.pk).update(created_at=when,started_at=when+timedelta(minutes=2),ready_at=when+timedelta(minutes=12+i%11),completed_at=when+timedelta(minutes=25))
            else:
                when=now-timedelta(minutes=7+(i-24)*5)
                Order.objects.filter(pk=order.pk).update(created_at=when)
                KitchenTicket.objects.filter(pk=ticket.pk).update(created_at=when,started_at=when+timedelta(minutes=1) if ticket.status!='new' else None,ready_at=now if ticket.status=='ready' else None)
                if i==27:
                    services.record_payment(staff['cashier'],order.pk,amount='500',method='cash',reference='',request_key=token('partial'))
                if i==29:
                    services.cancel_order(staff['manager'],order.pk,'Demo: guest changed plans')
        self.stdout.write(self.style.SUCCESS('Demo restaurant ready: 12 tables, 5 categories, 25 items, 5 staff roles, and realistic orders. Existing demo records were preserved.'))
