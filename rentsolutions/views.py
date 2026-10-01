from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .access import (
    is_landlord,
    is_manager,
    landlord_required,
    owned_properties,
)
from .forms import (
    HireManagerForm,
    LandlordRegistrationForm,
    NewRentalUnitForm,
    RentalPropertyForm,
    RentalUnitForm,
    RentRateForm,
)
from .models import RentalPropertyManager, RentalUnit
from .reports import property_month, selected_month, unit_income, with_units_and_tenancies


def render_form(request, form, *, title, submit_label, cancel_url, intro="", warning=""):
    context = {
        "form": form,
        "title": title,
        "submit_label": submit_label,
        "cancel_url": cancel_url,
        "intro": intro,
        "warning": warning,
    }
    return render(request, "form_page.html", context)


def render_confirm(request, *, title, message, confirm_label, cancel_url):
    context = {
        "title": title,
        "message": message,
        "confirm_label": confirm_label,
        "cancel_url": cancel_url,
    }
    return render(request, "confirm.html", context)


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "rentsolutions/home.html")


def register_landlord(request):
    form = LandlordRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        messages.success(request, "Welcome! Add the units in your property to get started.")
        return redirect("property_list")
    return render_form(
        request,
        form,
        title="Register as a landlord",
        submit_label="Create account",
        cancel_url="home",
        intro="Create your account and your first property.",
    )


@login_required
def dashboard(request):
    """Send each user to the page for their role."""
    if is_landlord(request.user):
        return redirect("landlord_dashboard")
    if is_manager(request.user):
        return redirect("propertymanagement:management_home")
    if request.user.is_staff:
        return redirect("admin:index")
    return render(request, "rentsolutions/no_role.html")


@landlord_required
def landlord_dashboard(request):
    month = selected_month(request)
    properties = with_units_and_tenancies(owned_properties(request.user))
    summaries = sorted(
        (property_month(rental_property, month) for rental_property in properties),
        key=lambda summary: summary.paid_for_month,
        reverse=True,
    )
    return render(
        request, "rentsolutions/landlord_dashboard.html", {"summaries": summaries, "month": month}
    )


@landlord_required
def property_list(request):
    properties = owned_properties(request.user).prefetch_related("units__rent_rates")
    return render(request, "rentsolutions/property_list.html", {"properties": properties})


@landlord_required
def property_create(request):
    form = RentalPropertyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.instance.landlord = request.user.landlord
        form.save()
        messages.success(request, f"{form.instance.name} was added.")
        return redirect("property_list")
    return render_form(
        request,
        form,
        title="Add a property",
        submit_label="Add property",
        cancel_url="property_list",
    )


@landlord_required
def property_edit(request, pk):
    rental_property = get_object_or_404(owned_properties(request.user), pk=pk)
    form = RentalPropertyForm(request.POST or None, instance=rental_property)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{rental_property.name} was updated.")
        return redirect("property_list")
    return render_form(
        request,
        form,
        title=f"Edit {rental_property.name}",
        submit_label="Save changes",
        cancel_url="property_list",
    )


@landlord_required
def property_delete(request, pk):
    rental_property = get_object_or_404(owned_properties(request.user), pk=pk)
    if request.method == "POST":
        rental_property.delete()
        messages.success(request, f"{rental_property.name} was deleted.")
        return redirect("property_list")
    return render_confirm(
        request,
        title=f"Delete {rental_property.name}?",
        message="This permanently deletes the property with all its units, tenants and payments.",
        confirm_label="Delete property",
        cancel_url="property_list",
    )


@landlord_required
def property_units(request, pk):
    month = selected_month(request)
    rental_property = get_object_or_404(
        with_units_and_tenancies(owned_properties(request.user)), pk=pk
    )
    units = [(unit, unit_income(unit, month)) for unit in rental_property.units.all()]
    context = {"rental_property": rental_property, "units": units, "month": month}
    return render(request, "rentsolutions/property_units.html", context)


def owned_units(user):
    return RentalUnit.objects.filter(property_with_rental_unit__in=owned_properties(user))


@landlord_required
def unit_create(request, property_pk):
    rental_property = get_object_or_404(owned_properties(request.user), pk=property_pk)
    form = NewRentalUnitForm(request.POST or None, rental_property=rental_property)
    if request.method == "POST" and form.is_valid():
        unit = form.save()
        messages.success(request, f"Unit {unit.unit_identity} was added.")
        return redirect("property_list")
    return render_form(
        request,
        form,
        title=f"Add a unit to {rental_property.name}",
        submit_label="Add unit",
        cancel_url="property_list",
    )


@landlord_required
def unit_edit(request, pk):
    unit = get_object_or_404(owned_units(request.user), pk=pk)
    form = RentalUnitForm(
        request.POST or None, instance=unit, rental_property=unit.property_with_rental_unit
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Unit {unit.unit_identity} was renamed.")
        return redirect("property_list")
    return render_form(
        request,
        form,
        title=f"Rename unit {unit.unit_identity}",
        submit_label="Save",
        cancel_url="property_list",
        intro="To change the rent, add a new rent rate from the unit's rent page.",
    )


@landlord_required
def unit_delete(request, pk):
    unit = get_object_or_404(owned_units(request.user), pk=pk)
    if request.method == "POST":
        unit.delete()
        messages.success(request, f"Unit {unit.unit_identity} was deleted.")
        return redirect("property_list")
    return render_confirm(
        request,
        title=f"Delete unit {unit.unit_identity}?",
        message="This permanently deletes the unit with its rent history, tenants and payments.",
        confirm_label="Delete unit",
        cancel_url="property_list",
    )


@landlord_required
def rent_rates(request, unit_pk, rate_pk=None):
    """A unit's rent history, with a form to add a rate or edit the one selected."""
    unit = get_object_or_404(owned_units(request.user), pk=unit_pk)
    rate = get_object_or_404(unit.rent_rates, pk=rate_pk) if rate_pk else None
    form = RentRateForm(request.POST or None, instance=rate, rental_unit=unit)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(
            request, f"Rent of {saved.rent_rate} applies from {saved.start_date:%B %Y}."
        )
        return redirect("rent_rates", unit_pk=unit.pk)
    context = {"unit": unit, "rate": rate, "form": form, "rates": unit.rent_rates.all()}
    return render(request, "rentsolutions/rent_rates.html", context)


@landlord_required
def managers(request):
    properties = owned_properties(request.user)
    form = HireManagerForm(request.POST or None, landlord_properties=properties)
    if request.method == "POST" and form.is_valid():
        manager, temporary_password = form.save()
        message = f"{manager.user.full_name} now manages {manager.property_managed.name}."
        if temporary_password:
            message += (
                f" They can sign in with {manager.user.phone_number} and the temporary password"
                f" {temporary_password} – share it with them privately."
            )
        messages.success(request, message)
        return redirect("managers")
    active_managers = (
        RentalPropertyManager.objects.active()
        .filter(property_managed__in=properties)
        .select_related("user", "property_managed")
    )
    return render(
        request, "rentsolutions/managers.html", {"form": form, "managers": active_managers}
    )


@landlord_required
@require_POST
def manager_end(request, pk):
    manager = get_object_or_404(
        RentalPropertyManager.objects.active().filter(
            property_managed__in=owned_properties(request.user)
        ),
        pk=pk,
    )
    manager.management_end_date = timezone.localdate()
    manager.save(update_fields=["management_end_date"])
    messages.success(
        request,
        f"{manager.user.full_name} no longer manages {manager.property_managed.name}.",
    )
    return redirect("managers")
