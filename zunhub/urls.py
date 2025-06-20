from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('p2p.urls')),
    path('', include('gasfee.urls')),
    path('', include('bills.urls')),
    path('', include('accounts.urls')),
    path('', include('payments.urls')),
]

# ✅ Serve user-uploaded files (media)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ✅ Serve static files for JS/CSS during development with Daphne
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
