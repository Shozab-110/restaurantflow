def restaurant(request):
    from .models import RestaurantSettings
    return {'restaurant': RestaurantSettings.load()} if request.user.is_authenticated else {}
