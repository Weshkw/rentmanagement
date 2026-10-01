"""Monthly figures for properties, computed from prefetched data in a fixed number of queries."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Prefetch
from django.utils import timezone

from .billing import first_of_month
from .models import RentalPropertyManager, RentalUnit, Tenant


def with_units_and_tenancies(properties):
    """Load each property's units, rent rates, tenants, payments and active managers."""
    units = RentalUnit.objects.prefetch_related(
        "rent_rates", Prefetch("tenants", Tenant.objects.prefetch_related("payments"))
    )
    managers = RentalPropertyManager.objects.active().select_related("user")
    return properties.prefetch_related(
        Prefetch("units", units), Prefetch("managers", managers, to_attr="active_managers")
    )


def selected_month(request):
    """The month chosen with ?month=YYYY-MM, defaulting to the current month."""
    try:
        year, month = (int(part) for part in request.GET.get("month", "").split("-"))
        return date(year, month, 1)
    except ValueError:
        return first_of_month(timezone.localdate())


@dataclass(frozen=True)
class PropertyMonth:
    rental_property: object
    total_units: int
    occupied_units: int
    paid_in_month: Decimal
    paid_for_month: Decimal
    balance_for_month: Decimal


def property_month(rental_property, month):
    """A property's occupancy, takings and arrears for one month."""
    units = list(rental_property.units.all())
    tenants = [tenant for unit in units for tenant in unit.tenants.all()]
    payments = [payment for tenant in tenants for payment in tenant.payments.all()]
    return PropertyMonth(
        rental_property=rental_property,
        total_units=len(units),
        occupied_units=sum(1 for unit in units if unit.occupied),
        paid_in_month=sum(
            (p.amount_paid for p in payments if first_of_month(p.date_paid) == month), Decimal(0)
        ),
        paid_for_month=sum((p.amount_paid for p in payments if p.period == month), Decimal(0)),
        balance_for_month=sum((tenant.balance_for(month) for tenant in tenants), Decimal(0)),
    )


def unit_income(unit, month):
    """Rent paid for ``month`` across everyone who has rented the unit."""
    return sum(
        (
            payment.amount_paid
            for tenant in unit.tenants.all()
            for payment in tenant.payments.all()
            if payment.period == month
        ),
        Decimal(0),
    )
