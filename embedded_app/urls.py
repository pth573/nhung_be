from django.urls import path
from . import views

urlpatterns = [
    path('current-sensor-data/', views.CurrentSensorDataView.as_view(), name='current_sensor_data'),
    path('sensor-data-history/', views.SensorDataHistoryView.as_view(), name='sensor_data_history'),
    path('route/', views.RouteView.as_view(), name='route'),
    path('recent-route/', views.RecentRouteView.as_view(), name='recent_route'),
    path('alerts/', views.AlertView.as_view(), name='alerts'),
    path('alerts/<str:start_time>/', views.AlertDetailView.as_view(), name='alert_detail'),
    path('delete-sensor-data/', views.DeleteSensorDataView.as_view(), name='delete_sensor_data'),
    path('delete-route-data/', views.DeleteRouteDataView.as_view(), name='delete_route_data'),
    path('delete-alert-data/', views.DeleteAlertDataView.as_view(), name='delete_alert_data'),

    #Trip
    path('trip/history/', views.TripView.as_view(), name='trip'),
    path('trip/start/', views.StartTripView.as_view(), name='create_trip'),
    path('trip/end/', views.EndTripView.as_view(), name='update_trip_end'),
]