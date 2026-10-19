from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from operations.permissions import ROLE_PERMISSIONS

class Command(BaseCommand):
    help = 'Idempotently create RestaurantFlow business roles and permissions.'
    @transaction.atomic
    def handle(self, *args, **options):
        for name, permissions in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=name)
            group.permissions.set(Permission.objects.filter(content_type__app_label='operations', codename__in=permissions))
        self.stdout.write(self.style.SUCCESS('Business roles synchronized.'))
