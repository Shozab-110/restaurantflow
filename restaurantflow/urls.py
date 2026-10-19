from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [path('technical-admin/', admin.site.urls), path('', include('operations.urls'))]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
handler403 = 'operations.views.permission_denied'
handler404 = 'operations.views.not_found'
handler500 = 'operations.views.server_error'
