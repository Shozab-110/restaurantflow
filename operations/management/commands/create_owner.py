import getpass
import os
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from operations.models import RestaurantSettings
from operations.services import audit

class Command(BaseCommand):
    help = 'Safely create an initial owner. Password is read from a hidden prompt or RESTAURANTFLOW_OWNER_PASSWORD.'
    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--email', default='')
    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(groups__name='Owner', is_active=True).exists():
            raise CommandError('An active owner already exists. Manage accounts through Staff & Roles.')
        if User.objects.filter(username=options['username']).exists():
            raise CommandError('That username already exists. Choose a new owner username.')
        password = os.getenv('RESTAURANTFLOW_OWNER_PASSWORD') or getpass.getpass('Owner password (hidden): ')
        user = User(username=options['username'], email=options['email'])
        try:
            user.full_clean(exclude=['password'])
            password_validation.validate_password(password, user)
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages))
        call_command('bootstrap_roles', verbosity=0)
        user.set_password(password)
        user.save()
        user.groups.add(Group.objects.get(name='Owner'))
        RestaurantSettings.load()
        audit(user, 'owner.initialized', user, 'Initial business owner created securely.')
        self.stdout.write(self.style.SUCCESS(f'Owner {user.username} created. Sign in through /login/.'))
