# sensors/routing.py
from django.urls import re_path
from .consumers import SensorDataConsumer, AlertConsumer, RecentRouteConsumer

websocket_urlpatterns = [
    re_path(r'ws/sensor-data/$', SensorDataConsumer.as_asgi()),
    re_path(r'ws/alerts/$', AlertConsumer.as_asgi()),
    re_path(r'ws/recent-route/$', RecentRouteConsumer.as_asgi()),
]
