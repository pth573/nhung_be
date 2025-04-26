from rest_framework import serializers
from .models import Route, Alert

class SensorDataSerializer(serializers.Serializer):
    timestamp = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    AccX = serializers.FloatField()
    AccY = serializers.FloatField()
    AccZ = serializers.FloatField()
    GyroX = serializers.FloatField()
    GyroY = serializers.FloatField()
    GyroZ = serializers.FloatField()
    Temperature = serializers.FloatField()
    vibration_detected = serializers.BooleanField()

class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ['latitude', 'longitude', 'time']

class AlertSerializer(serializers.ModelSerializer):
    key = serializers.CharField(source='id', read_only=True)  

    class Meta:
        model = Alert
        fields = ['key', 'start_time', 'end_time', 'latitude', 'longitude', 'is_active']