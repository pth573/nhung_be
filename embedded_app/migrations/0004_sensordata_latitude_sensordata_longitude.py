# Generated by Django 4.2.20 on 2025-04-29 01:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("embedded_app", "0003_sensordata"),
    ]

    operations = [
        migrations.AddField(
            model_name="sensordata",
            name="latitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sensordata",
            name="longitude",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
