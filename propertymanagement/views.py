from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from rentsolutions.access import (
    operated_payments,
    operated_properties,
    operated_tenants,
    operated_units,
    operator_required,
)
from rentsolutions.reports import with_units_and_tenancies
from rentsolutions.views import render_form

from .forms import EndTenancyForm, RentPaymentForm, TenantForm, UnitNotesForm


@operator_required
def management_home(request):
    properties = with_units_and_tenancies(operated_properties(request.user))
    return render(request, "propertymanagement/management_home.html", {"properties": properties})


@operator_required
def unit_detail(request, pk):
    unit = get_object_or_404(
        operated_units(request.user)
        .select_related("property_with_rental_unit")
        .prefetch_related("rent_rates", "tenants"),
        pk=pk,
    )
    form = UnitNotesForm(request.POST or None, instance=unit)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Notes saved.")
        return redirect("propertymanagement:unit_detail", pk=unit.pk)
    return render(request, "propertymanagement/unit_detail.html", {"unit": unit, "form": form})


@operator_required
def tenant_create(request, unit_pk):
    unit = get_object_or_404(operated_units(request.user), pk=unit_pk)
    form = TenantForm(request.POST or None, rental_unit=unit)
    if request.method == "POST" and form.is_valid():
        tenant = form.save()
        messages.success(request, f"{tenant.tenant_name} moved into {unit.unit_identity}.")
        return redirect("propertymanagement:tenant_detail", pk=tenant.pk)
    return render_form(
        request,
        form,
        title=f"Add a tenant to {unit}",
        submit_label="Add tenant",
        cancel_url="propertymanagement:management_home",
    )


def tenant_with_history(user):
    return (
        operated_tenants(user)
        .select_related("rental_unit_occupied__property_with_rental_unit")
        .prefetch_related("rental_unit_occupied__rent_rates", "payments")
    )


@operator_required
def tenant_detail(request, pk):
    tenant = get_object_or_404(tenant_with_history(request.user), pk=pk)
    statement = tenant.rent_statement()
    context = {
        "tenant": tenant,
        "statement": reversed(statement),
        "total_balance": sum(line.balance for line in statement),
    }
    return render(request, "propertymanagement/tenant_detail.html", context)


@operator_required
def tenant_edit(request, pk):
    tenant = get_object_or_404(operated_tenants(request.user), pk=pk)
    form = TenantForm(
        request.POST or None, instance=tenant, rental_unit=tenant.rental_unit_occupied
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tenant details saved.")
        return redirect("propertymanagement:tenant_detail", pk=tenant.pk)
    return render_form(
        request,
        form,
        title=f"Edit {tenant.tenant_name}",
        submit_label="Save changes",
        cancel_url="propertymanagement:management_home",
    )


@operator_required
def tenant_end(request, pk):
    tenant = get_object_or_404(operated_tenants(request.user).filter(date_tenancy_ends=None), pk=pk)
    form = EndTenancyForm(request.POST or None, instance=tenant)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{tenant.tenant_name}'s tenancy has ended.")
        return redirect("propertymanagement:management_home")
    return render_form(
        request,
        form,
        title=f"End {tenant.tenant_name}'s tenancy",
        submit_label="End tenancy",
        cancel_url="propertymanagement:management_home",
        intro="The tenant and their payment history are kept; the unit becomes vacant "
        "after the last day.",
    )


@operator_required
def collect_rent(request, tenant_pk):
    tenant = get_object_or_404(
        operated_tenants(request.user).select_related("rental_unit_occupied"), pk=tenant_pk
    )
    form = RentPaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.instance.tenant_paying = tenant
        payment = form.save()
        messages.success(
            request,
            f"Recorded Ksh {payment.amount_paid} from {tenant.tenant_name} "
            f"for {payment.period:%B %Y}.",
        )
        return redirect("propertymanagement:tenant_detail", pk=tenant.pk)
    return render_form(
        request,
        form,
        title=f"Record rent from {tenant.tenant_name}",
        submit_label="Record payment",
        cancel_url="propertymanagement:management_home",
    )


@operator_required
def payment_edit(request, pk):
    payment = get_object_or_404(
        operated_payments(request.user).select_related("tenant_paying"), pk=pk
    )
    form = RentPaymentForm(request.POST or None, instance=payment)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Payment updated.")
        return redirect("propertymanagement:tenant_detail", pk=payment.tenant_paying.pk)
    return render_form(
        request,
        form,
        title=f"Edit payment from {payment.tenant_paying.tenant_name}",
        submit_label="Save payment",
        cancel_url="propertymanagement:management_home",
    )
