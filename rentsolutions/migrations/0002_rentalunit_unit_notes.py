# Generated by Django 4.2.8 on 2024-05-09 09:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentsolutions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentalunit',
            name='unit_notes',
            field=models.TextField(blank=True, null=True),
        ),
    ]
