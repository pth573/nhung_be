from django.db import models

class Route(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    time = models.CharField(max_length=20)  

    class Meta:
        ordering = ['time']

class Alert(models.Model):
    start_time = models.CharField(max_length=20)
    end_time = models.CharField(max_length=20, null=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-start_time']

class SensorData(models.Model):
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    AccX = models.FloatField()
    AccY = models.FloatField()
    AccZ = models.FloatField()
    GyroX = models.FloatField()
    GyroY = models.FloatField()
    GyroZ = models.FloatField()
    temperature = models.FloatField()
    vibration_detected = models.BooleanField(default=False)
    timestamp = models.CharField(max_length=20)

    class Meta:
        ordering = ['-timestamp']  
