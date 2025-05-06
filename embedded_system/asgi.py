# """
# ASGI config for embedded_system project.

# It exposes the ASGI callable as a module-level variable named ``application``.

# For more information on this file, see
# https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
# """

# import os

# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'embedded_system.settings')

# application = get_asgi_application()








import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from embedded_app import consumers
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'embedded_system.settings')
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/current-sensor-data/", consumers.SensorDataConsumer.as_asgi()),
            path("ws/alerts/", consumers.AlertConsumer.as_asgi()),
            path("ws/recent-route/", consumers.RecentRouteConsumer.as_asgi()),
        ])
    ),
})


