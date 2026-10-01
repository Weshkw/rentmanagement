"""Who may see and change what.

Landlords own properties. Managers run the properties they are currently
employed on. Views load every object through the querysets below, so a URL that
points at someone else's property, unit, tenant or payment returns 404.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import RentalProperty, RentalPropertyManager, RentalUnit, RentPayment, Tenant


def is_landlord(user):
    return user.is_authenticated and hasattr(user, "landlord")


def is_manager(user):
    return (
        user.is_authenticated and RentalPropertyManager.objects.active().filter(user=user).exists()
    )


def owned_properties(user):
    return RentalProperty.objects.filter(landlord__user=user)


def operated_properties(user):
    """Properties the user owns or currently manages."""
    managed = RentalPropertyManager.objects.active().filter(user=user).values("property_managed")
    return RentalProperty.objects.filter(Q(landlord__user=user) | Q(pk__in=managed))


def operated_units(user):
    return RentalUnit.objects.filter(property_with_rental_unit__in=operated_properties(user))


def operated_tenants(user):
    return Tenant.objects.filter(rental_unit_occupied__in=operated_units(user))


def operated_payments(user):
    return RentPayment.objects.filter(tenant_paying__in=operated_tenants(user))


def role_required(test):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not test(request.user):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


landlord_required = role_required(is_landlord)
operator_required = role_required(lambda user: is_landlord(user) or is_manager(user))
