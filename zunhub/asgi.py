import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack

# 1️⃣ Set the settings module before anything else
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zunhub.settings')

# 2️⃣ Initialize Django
django.setup()

# 3️⃣ Now it's safe to import your app‐specific routing
from p2p.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # (http->django views is added by default)
    "http": get_asgi_application(),

    # 4️⃣ WebSocket handler
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
