from zoneinfo import ZoneInfo
from django.utils import timezone
from django.db.utils import OperationalError, ProgrammingError

class RestaurantTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        if request.path == '/health/':
            return self.get_response(request)
        try:
            from .models import RestaurantSettings
            try:
                name = RestaurantSettings.objects.filter(pk=1).values_list('timezone', flat=True).first()
            except (OperationalError, ProgrammingError):
                name = None
            timezone.activate(ZoneInfo(name)) if name else timezone.deactivate()
            return self.get_response(request)
        finally:
            timezone.deactivate()
