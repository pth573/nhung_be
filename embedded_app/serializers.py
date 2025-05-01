from rest_framework import serializers
from .models import Route, Alert, SensorData, Trip, DeviceToken

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
        fields = ['latitude', 'longitude', 'location' ,'time']

class TripSerializer(serializers.ModelSerializer):
    start_route = RouteSerializer()
    end_route = RouteSerializer(required=False, allow_null=True)

    class Meta:
        model = Trip
        fields = ['id', 'start_route', 'end_route', 'distance', 'duration']

class AlertSerializer(serializers.ModelSerializer):
    key = serializers.CharField(source='id', read_only=True)  

    class Meta:
        model = Alert
        fields = ['key', 'start_time', 'end_time', 'latitude', 'longitude', 'location', 'is_active']

class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ['token']
