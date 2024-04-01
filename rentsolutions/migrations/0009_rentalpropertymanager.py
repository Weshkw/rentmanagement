# Generated by Django 4.2.9 on 2024-03-30 08:08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rentsolutions', '0008_alter_tenant_rental_unit_occupied'),
    ]

    operations = [
        migrations.CreateModel(
            name='RentalPropertyManager',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('national_id_number', models.CharField(max_length=255)),
                ('management_start_date', models.DateField()),
                ('management_end_date', models.DateField(blank=True, null=True)),
                ('property_managed', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='propertys_managed', to='rentsolutions.rentalproperty')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rental_property_managers', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]