# import os
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from django.urls import path
# from embedded_system import consumers

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'embedded_system.settings')

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter([
#             path("ws/current-sensor-data/", consumers.SensorDataConsumer.as_asgi()),
#             path("ws/alerts/", consumers.AlertConsumer.as_asgi()),
#             path("ws/recent-route/", consumers.RecentRouteConsumer.as_asgi()),
#         ])
#     ),
# })
