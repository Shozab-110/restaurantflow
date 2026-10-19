from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from .forms import LoginForm

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(authentication_form=LoginForm, redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password/change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change.html', success_url='/profile/'), name='password_change'),
    path('profile/', views.profile, name='profile'),
    path('pos/', views.pos, name='pos'), path('pos/<int:order_id>/', views.pos, name='pos_add'),
    path('orders/', views.orders, name='orders'), path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/receipt/', views.receipt, name='receipt'),
    path('orders/<int:pk>/action/<str:action>/', views.order_action, name='order_action'),
    path('kitchen/', views.kitchen, name='kitchen'), path('kitchen/board/', views.kitchen_board, name='kitchen_board'),
    path('kitchen/<int:pk>/advance/', views.kitchen_action, name='kitchen_action'),
    path('tables/', views.tables, name='tables'),
    path('manage/<str:kind>/', views.resource_list, name='resource_list'),
    path('manage/<str:kind>/new/', views.resource_edit, name='resource_create'),
    path('manage/<str:kind>/<int:pk>/', views.resource_edit, name='resource_edit'),
    path('manage/<str:kind>/<int:pk>/deactivate/', views.resource_deactivate, name='resource_deactivate'),
    path('payments/', views.payments, name='payments'), path('reports/', views.reports, name='reports'),
    path('staff/', views.staff, name='staff'), path('staff/new/', views.staff_edit, name='staff_create'),
    path('staff/<int:pk>/', views.staff_edit, name='staff_edit'),
    path('settings/', views.settings_view, name='settings'), path('audit/', views.audit_logs, name='audit'),
    path('health/', views.health, name='health'),
]
