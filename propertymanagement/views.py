from django.shortcuts import render
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout 
from django.core.exceptions import ValidationError
from django.contrib import messages
import calendar
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from django.http import JsonResponse
from datetime import datetime
from django.contrib.auth.decorators import login_required,user_passes_test
from rentsolutions.models import CustomUser, Landlord, RentalProperty, RentalUnit, Tenant, RentalUnitMonthlyRentRate, RentPayment,RentalPropertyManager
from rentsolutions.views import is_landlord,is_rental_property_manager


@login_required(login_url='login')
@user_passes_test(is_rental_property_manager)
def management_home(request):
    # Get all rental property managers associated with the current user
    managers = RentalPropertyManager.objects.filter(user=request.user)
    
    # Retrieve all rental properties managed by the current manager(s)
    rental_properties = RentalProperty.objects.filter(propertys_managed__in=managers)

    # Retrieve all occupied units managed by the current manager(s)
    rental_units = RentalUnit.objects.filter(property_with_rental_unit__in=rental_properties)

    success_message = request.session.pop('success_message', None)

    context = {
        'success_message': success_message,
        'rental_properties': rental_properties,
        'rental_units': rental_units,
        'is_rental_property_manager': True,
        'managers': managers
    }
    return render(request, 'propertymanagement/management_home.html', context)



@login_required(login_url='login')
@user_passes_test(is_rental_property_manager)
def collect_rent(request, pk):
    rental_unit = get_object_or_404(RentalUnit, pk=pk)
    tenant = rental_unit.rental_units.first()
    rental_property = rental_unit.property_with_rental_unit  # Retrieve the rental property

    if request.method == 'POST':
        amount_paid = Decimal(request.POST.get('amount_paid'))
        date_paid = request.POST.get('date_paid')
        intended_payment_month = request.POST.get('intended_payment_month')
        intended_payment_year = request.POST.get('intended_payment_year')
        payment_details = request.POST.get('payment_details')

        if amount_paid and date_paid and intended_payment_month and intended_payment_year:
            rent_payment = RentPayment(
                tenant_paying=tenant,
                amount_paid=amount_paid,
                date_paid=date_paid,
                intended_payment_month=intended_payment_month,
                intended_payment_year=intended_payment_year,
                payment_details=payment_details
            )
            rent_payment.save()
            message = f'Rent payment of KSH {amount_paid} paid by {tenant} for rental unit {rental_unit} recorded successfully.'
            request.session['success_message'] = message
            return redirect('propertymanagement:management_home')
            

    payment_month_choices = RentPayment.INTENDED_PAYMENT_MONTH_CHOICES
    payment_year_choices = [str(year) for year in range(datetime.now().year, datetime.now().year + 5)]

    context = {
        'tenant': tenant,
        'rental_unit': rental_unit,
        'rental_property': rental_property,
        'payment_month_choices': payment_month_choices,
        'payment_year_choices': payment_year_choices,
        'is_rental_property_manager': True,
    }
    return render(request, 'propertymanagement/rent_collection.html', context)


@login_required(login_url='login')
@user_passes_test(is_rental_property_manager)
def payment_history(request, tenant_id):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    payments = RentPayment.objects.filter(tenant_paying=tenant).order_by('-date_paid')
    context = {
        'tenant': tenant,
        'payments': payments,
        'is_rental_property_manager': True,
    }
    return render(request, 'propertymanagement/payment_history.html', context)


@login_required(login_url='login')
@user_passes_test(is_rental_property_manager)
def edit_payment(request, payment_id):
    payment = get_object_or_404(RentPayment, id=payment_id)
    tenant_id = payment.tenant_paying.id  # Get the tenant_id from the payment instance

    if request.method == 'POST':
        amount_paid = Decimal(request.POST.get('amount_paid'))
        intended_payment_month = request.POST.get('intended_payment_month')
        intended_payment_year = request.POST.get('intended_payment_year')
        payment_details = request.POST.get('payment_details')

        # Update the payment instance with the new values
        payment.amount_paid = amount_paid
        payment.intended_payment_month = intended_payment_month
        payment.intended_payment_year = intended_payment_year
        payment.payment_details = payment_details
        payment.save()

        # Redirect to the payment_history view with the tenant_id
        return redirect('propertymanagement:payment_history', tenant_id=tenant_id)

    context = {
        'message': 'Payment updated successfully.',
        'payment': payment,
        'is_rental_property_manager': True,
    }
    return render(request, 'propertymanagement/edit_payment.html', context)

@login_required(login_url='login')
@user_passes_test(is_rental_property_manager)
def add_tenant(request, unit_id):
    rental_unit = get_object_or_404(RentalUnit, pk=unit_id)

    if request.method == 'POST':
        tenant_name = request.POST.get('tenant_name')
        national_id_number = request.POST.get('national_id_number')
        phone = request.POST.get('phone')
        date_tenancy_starts = request.POST.get('date_tenancy_starts')
        date_tenancy_ends = request.POST.get('date_tenancy_ends')
        emergency_contact_name = request.POST.get('emergency_contact_name')
        emergency_contact_phone = request.POST.get('emergency_contact_phone')
        emergency_contact_relationship = request.POST.get('emergency_contact_relationship')

        if tenant_name and date_tenancy_starts:
            tenant = Tenant(
                rental_unit_occupied=rental_unit,
                tenant_name=tenant_name,
                national_id_number=national_id_number,
                phone=phone,
                date_tenancy_starts=date_tenancy_starts,
                date_tenancy_ends=date_tenancy_ends,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone,
                emergency_contact_relationship=emergency_contact_relationship
            )
            tenant.save()
            return redirect('propertymanagement:management_home')

    context = {
        'rental_unit': rental_unit,
        'is_rental_property_manager': True,
    }
    return render(request, 'propertymanagement/add_tenant.html', context)


@login_required(login_url='login')
@user_passes_test(is_rental_property_manager)
def tenant_details(request, pk):
    tenant = get_object_or_404(Tenant, pk=pk)
    context = {
        'tenant': tenant,
        'is_rental_property_manager': True,
    }
    return render(request, 'propertymanagement/tenant.html', context)


@login_required(login_url='login')
@user_passes_test(is_rental_property_manager)
def edit_tenant(request, tenant_id):
    tenant = get_object_or_404(Tenant, pk=tenant_id)

    if request.method == 'POST':
        tenant_name = request.POST.get('tenant_name')
        national_id_number = request.POST.get('national_id_number')
        phone = request.POST.get('phone')
        date_tenancy_starts = request.POST.get('date_tenancy_starts')
        date_tenancy_ends = request.POST.get('date_tenancy_ends')
        emergency_contact_name = request.POST.get('emergency_contact_name')
        emergency_contact_phone = request.POST.get('emergency_contact_phone')
        emergency_contact_relationship = request.POST.get('emergency_contact_relationship')

        if tenant_name and date_tenancy_starts:
            tenant.tenant_name = tenant_name
            tenant.national_id_number = national_id_number
            tenant.phone = phone
            tenant.date_tenancy_starts = date_tenancy_starts
            tenant.date_tenancy_ends = date_tenancy_ends
            tenant.emergency_contact_name = emergency_contact_name
            tenant.emergency_contact_phone = emergency_contact_phone
            tenant.emergency_contact_relationship = emergency_contact_relationship
            tenant.save()
            return redirect('propertymanagement:management_home')

    context = {
        'tenant': tenant,
        'is_rental_property_manager': True,
    }
    return render(request, 'propertymanagement/edit_tenant.html', context)


@login_required(login_url='login')
@user_passes_test(is_rental_property_manager)
def delete_tenant(request, tenant_id):
    tenant = get_object_or_404(Tenant, pk=tenant_id)

    if request.method == 'POST':
        tenant.delete()
        return redirect('propertymanagement:management_home')

    context = {
        'tenant': tenant,
        'is_rental_property_manager': True,
    }
    return render(request, 'propertymanagement/delete_tenant.html', context)


