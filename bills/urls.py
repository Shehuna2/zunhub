from django.urls import path
from . import views

urlpatterns = [
    # ... existing paths ...
    path('buy-airtime/', views.buy_airtime, name='buy-airtime'),
    path('buy-data/', views.buy_data, name='buy_data'),
    path('api/get-data-plans/', views.get_data_plans_api, name='get_data_plans_api'),
]