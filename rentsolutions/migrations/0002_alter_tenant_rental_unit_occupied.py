# Generated by Django 4.2.9 on 2024-03-23 11:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rentsolutions', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tenant',
            name='rental_unit_occupied',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rental_units', to='rentsolutions.rentalunit', verbose_name=' Rental unit assigned'),
        ),
    ]
