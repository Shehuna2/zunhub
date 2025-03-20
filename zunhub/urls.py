from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('p2p.urls')),
    path('', include('gasfee.urls')),
]
