from django.urls import path
from . import views

urlpatterns = [
    path('buy-airtime/', views.buy_airtime, name='buy-airtime'),
    path('calculator/', views.calculator, name='calculator'),
    path('buy-data/', views.buy_data, name='buy_data'),
    path('api/get-data-plans/', views.get_data_plans_api, name='get_data_plans_api'),

    path('sell/step1/', views.sell_step1, name='sell_step1'),
    path('sell/step2/<int:order_id>/', views.sell_step2, name='sell_step2'),

    path('sell/done/<int:order_id>/', views.sell_done, name='sell_done'),
    path('sell/history/', views.sell_order_history, name='sell_order_history'),
    path('sell/credit-order/<int:order_id>/', views.admin_credit_order, name='admin_credit_order'),

    path('api/order-status/<int:order_id>/', views.order_status, name='order_status'),
    path('admin-dashboard-refresh/', views.admin_dashboard_refresh, name='admin_dashboard_refresh'),
    path('sell/awaiting/', views.awaiting_confirmation_list, name='awaiting_list'),
]