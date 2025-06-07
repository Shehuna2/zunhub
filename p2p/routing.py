from django.urls import re_path
from .consumers import OrderConsumer

websocket_urlpatterns = [
    re_path(r"^ws/order/(?P<order_id>\d+)/$", OrderConsumer.as_asgi()),
]
