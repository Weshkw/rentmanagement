"""Builders for test data shared by the rentsolutions and propertymanagement test suites."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from .models import Landlord, RentalProperty, RentalPropertyManager, Tenant

PASSWORD = "a-strong-pass-123"


def create_user(phone_number, full_name="Test User"):
    return get_user_model().objects.create_user(phone_number, PASSWORD, full_name=full_name)


def create_landlord_with_property(phone_number, property_name="Sunrise Court"):
    landlord = Landlord.objects.create(user=create_user(phone_number, f"Landlord {phone_number}"))
    rental_property = RentalProperty.objects.create(
        landlord=landlord, name=property_name, location="Nairobi"
    )
    return landlord, rental_property


def create_unit(rental_property, name="A1", rent="10000", rent_from=date(2024, 1, 1)):
    unit = rental_property.units.create(unit_identity=name)
    unit.rent_rates.create(rent_rate=Decimal(rent), start_date=rent_from)
    return unit


def create_tenant(unit, starts=date(2024, 1, 1), ends=None, name="Jane Tenant"):
    return Tenant.objects.create(
        rental_unit_occupied=unit,
        tenant_name=name,
        date_tenancy_starts=starts,
        date_tenancy_ends=ends,
    )


def employ_manager(rental_property, phone_number, starts=date(2024, 1, 1), ends=None):
    return RentalPropertyManager.objects.create(
        user=create_user(phone_number, f"Manager {phone_number}"),
        property_managed=rental_property,
        national_id_number="12345678",
        management_start_date=starts,
        management_end_date=ends,
    )
