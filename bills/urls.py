from django.urls import path
from . import views

urlpatterns = [
    # ... existing paths ...
    path('buy-airtime/', views.buy_airtime, name='buy-airtime'),
    path('calculator/', views.calculator, name='calculator'),
    path('buy-data/', views.buy_data, name='buy_data'),
    path('api/get-data-plans/', views.get_data_plans_api, name='get_data_plans_api'),

    path('sell/step1/', views.sell_step1, name='sell_step1'),
    path('sell/step2/<int:order_id>/', views.sell_step2, name='sell_step2'),
    path('sell/done/<int:order_id>/', views.sell_done, name='sell_done'),
]