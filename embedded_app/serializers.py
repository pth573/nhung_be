from rest_framework import serializers
from .models import Route, Alert, SensorData

class SensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorData
        fields = [
            'timestamp', 'latitude', 'longitude', 
            'AccX', 'AccY', 'AccZ', 
            'GyroX', 'GyroY', 'GyroZ', 
            'temperature', 'vibration_detected'
        ]

class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ['latitude', 'longitude', 'time']

class AlertSerializer(serializers.ModelSerializer):
    key = serializers.CharField(source='id', read_only=True)  

    class Meta:
        model = Alert
        fields = ['key', 'start_time', 'end_time', 'latitude', 'longitude', 'is_active']