# Generated by Django 4.2.9 on 2024-02-05 19:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentsolutions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentalunit',
            name='occupant_phone',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
    ]