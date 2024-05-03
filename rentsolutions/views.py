from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout 
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import login as auth_login
from django.shortcuts import redirect, resolve_url
from django.urls import reverse
from datetime import timedelta
from django.http import JsonResponse
from datetime import datetime
from django.contrib.auth.decorators import login_required,user_passes_test
from .models import CustomUser, Landlord, RentalProperty, RentalUnit, Tenant, RentalUnitMonthlyRentRate, RentPayment,RentalPropertyManager



def is_landlord(user):
    """
    Check if the user is a landlord.
    """
    return Landlord.objects.filter(user=user).exists()

def is_rental_property_manager(user):
    """
    Check if the user is a rental property manager.
    """
    return RentalPropertyManager.objects.filter(user=user).exists()

# Decorator to require login and check if the user is a landlord

def home(request):
  
    return render(request, 'rentsolutions/home.html')

def login_view(request):
    if request.method == 'POST':
        phone_number = request.POST['phone_number']
        password = request.POST['password']
        user = authenticate(request, phone_number=phone_number, password=password)
        if user is not None:
            login(request, user)
            if is_landlord(user):
                return redirect('land_lord_main_page')
            elif user.is_superuser:
                return redirect('admin:index')
            elif user.is_staff:
                return redirect('rent_easier')
            elif is_rental_property_manager(user):
                return redirect('propertymanagement:management_home')
            else:
                return redirect('home')
        else:
            message = "Invalid credentials"
            return render(request, 'rentsolutions/login.html', {'message': message})
    return render(request, 'rentsolutions/login.html')



def logout_view(request):
    logout(request)
    return redirect('home')


def register_as_landlord(request):
    if request.method == 'POST':
        with transaction.atomic():
            phone_number = request.POST.get('phone_number')
            password = request.POST.get('password')
            full_name = request.POST.get('full_name')
            address = request.POST.get('address')
            property_name = request.POST.get('property_name')
            location = request.POST.get('location')
            total_units = request.POST.get('total_units')
            amenities = request.POST.get('amenities')

            # Create the user
            user = CustomUser.objects.create(
                username=phone_number,
                phone_number=phone_number,
                full_name=full_name,
                address=address,
                password=password
            )

            # Create the landlord
            landlord = Landlord.objects.create(user=user)

            # Create the rental property
            rental_property = RentalProperty.objects.create(
                name=property_name,
                landlord=landlord,
                location=location,
                total_units=total_units,
                amenities=amenities
            )

            # Automatically log in the user
            login(request, user)

            return redirect('landlord_properties')
    return render(request, 'rentsolutions/register_landlord.html')





@login_required(login_url='login')
@user_passes_test(is_landlord)
def land_lord_main_page(request):
    landlord = Landlord.objects.get(user=request.user)
    properties = landlord.properties.all()

    current_month = datetime.now().month
    current_year = datetime.now().year
    selected_month = request.GET.get('month', current_month)
    selected_year = request.GET.get('year', current_year)

    property_data = []
    for property in properties:
        units = property.rentalunit_set.all()
        occupied_units = units.filter(occupied=True).count()
        total_units = units.count()

        intended_payments = RentPayment.objects.filter(
            rental_unit_paid_for__in=[unit.unit_identity for unit in units],
            intended_payment_month=str(selected_month).zfill(2),
            intended_payment_year=str(selected_year)
        ).aggregate(total_amount=Sum('amount_paid'))['total_amount'] or 0

        actual_payments = RentPayment.objects.filter(
            rental_unit_paid_for__in=[unit.unit_identity for unit in units],
            date_paid__month=int(selected_month),
            date_paid__year=int(selected_year)
        ).aggregate(total_amount=Sum('amount_paid'))['total_amount'] or 0

        tenants = Tenant.objects.filter(rental_unit_occupied__in=units)
        total_balance = sum(tenant.Tenant_Monthly_Rental_balances.get(f"{selected_year}-{str(selected_month).zfill(2)}", 0) for tenant in tenants)

        

        property_data.append({
            'property': property,
            'occupied_units': occupied_units,
            'total_units': total_units,
            'intended_payments': intended_payments,
            'actual_payments': actual_payments,
            'total_balance': total_balance
        })

    sorted_property_data = sorted(property_data, key=lambda x: x['intended_payments'], reverse=True)

    context = {
        'is_landlord': True,
        'property_data': sorted_property_data,
        'selected_month': selected_month,
        'selected_year': selected_year
    }
    return render(request, 'rentsolutions/landlordmainpage.html', context)



@login_required(login_url='login')
@user_passes_test(is_landlord)
def employ_property_manager(request):
    landlord = Landlord.objects.get(user=request.user)
    properties = landlord.properties.all()

    if request.method == 'POST':
        # Get the form data from the request
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')
        national_id_number = request.POST.get('national_id_number')
        management_start_date = request.POST.get('management_start_date')
        property_id = request.POST.get('property_id')  # Assuming property ID is submitted

        # Check if the user with the given phone number already exists
        existing_user = CustomUser.objects.filter(phone_number=phone_number).first()

        if existing_user:
            # If the user exists, create a manager entry without modifying the user
            manager = RentalPropertyManager.objects.create(
                user=existing_user,
                property_managed_id=property_id,
                national_id_number=national_id_number,
                management_start_date=management_start_date
            )
            messages.success(request, f"{existing_user.full_name} has been assigned as the manager for this property.")
        else:
            # If the user doesn't exist, create a new user and a manager entry
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    username=phone_number,
                    phone_number=phone_number,
                    full_name=full_name,
                    password=national_id_number  # Use the national_id_number as the initial password
                )

                manager = RentalPropertyManager.objects.create(
                    user=user,
                    property_managed_id=property_id,
                    national_id_number=national_id_number,
                    management_start_date=management_start_date
                )
                messages.success(request, f"User {user.full_name} has been created and assigned as the manager for this property.")

        return redirect('manage_property_managers')

    context = {
        'properties': properties,
        'is_landlord': True,
    }
    return render(request, 'rentsolutions/manage_property_managers.html', context)


@login_required(login_url='login')
@user_passes_test(is_landlord)
def fire_property_manager(request, manager_id):
    property_manager = get_object_or_404(RentalPropertyManager, pk=manager_id)
    property_managed = property_manager.property_managed

    if request.method == 'POST':
        # Set the management_end_date to the current date and time
        property_manager.management_end_date = timezone.now().date()
        property_manager.delete()

        messages.success(request, f"{property_manager.user.full_name} has been fired as the manager for {property_managed.name}.")
        return redirect('manage_property_managers')

    # No need to render a template for GET requests
    return redirect('manage_property_managers')


@login_required(login_url='login')
@user_passes_test(is_landlord or is_rental_property_manager)
def rental_units_in_property(request, pk):
    property = get_object_or_404(RentalProperty, pk=pk)
    rental_units = property.rentalunit_set.all()

    # Get the selected month and year from the query parameters
    selected_month = request.GET.get('month')
    selected_year = request.GET.get('year')

    # Provide default values if the query parameters are not present
    if not selected_month:
        selected_month = datetime.now().month
    if not selected_year:
        selected_year = datetime.now().year

    # Calculate the rental income for each unit
    rental_income = RentPayment.objects.filter(
        rental_unit_paid_for__in=[unit.unit_identity for unit in rental_units],
        intended_payment_month=str(selected_month).zfill(2),
        intended_payment_year=str(selected_year)
    ).values('rental_unit_paid_for').annotate(total_amount=Sum('amount_paid'))

    # Map the rental income to each unit
    rental_units_with_income = []
    for unit in rental_units:
        income_data = next((item for item in rental_income if item['rental_unit_paid_for'] == unit.unit_identity), None)
        unit_income = income_data['total_amount'] if income_data else 0
        rental_units_with_income.append((unit, unit_income))

    context = {
        'is_landlord': True,
        'property': property,
        'rental_units_with_income': rental_units_with_income,
        'selected_month': selected_month,
        'selected_year': selected_year
    }
    return render(request, 'rentsolutions/property_units.html', context)



@login_required
@user_passes_test(is_landlord)
def create_rent_rate(request, pk):
    rental_unit = get_object_or_404(RentalUnit, pk=pk)
    existing_rent_rates = RentalUnitMonthlyRentRate.objects.filter(unit_absolute_identity=rental_unit.id).order_by('start_date')

    if request.method == 'POST':
        rent_rate = request.POST.get('rent_rate')
        start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
        end_date = request.POST.get('end_date')
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None

        try:
            RentalUnitMonthlyRentRate.objects.create(
                rent_rate=rent_rate,
                start_date=start_date,
                end_date=end_date,
                rental_unit=rental_unit.unit_identity,
                unit_absolute_identity=rental_unit.id
            )
            return redirect('create_rent_rate', pk=rental_unit.pk)
        except ValidationError as e:
            error_message = str(e)

            context = {
                'error_message': error_message,
                'is_landlord': True,
                'rental_unit': rental_unit,
                'existing_rent_rates': existing_rent_rates
            }
            return render(request, 'rentsolutions/rent_rate_management.html', context)

    context = {
        'is_landlord': True,
        'rental_unit': rental_unit,
        'existing_rent_rates': existing_rent_rates
    }
    return render(request, 'rentsolutions/rent_rate_management.html', context)

@login_required
@user_passes_test(is_landlord)
def update_rent_rate(request, pk):
    rent_rate = get_object_or_404(RentalUnitMonthlyRentRate, pk=pk)
    rental_unit = RentalUnit.objects.get(id=rent_rate.unit_absolute_identity)
    existing_rent_rates = RentalUnitMonthlyRentRate.objects.filter(unit_absolute_identity=rental_unit.id).order_by('start_date')

    if request.method == 'POST':
        new_rent_rate = request.POST.get('rent_rate')
        new_start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
        new_end_date = request.POST.get('end_date')
        new_end_date = datetime.strptime(new_end_date, '%Y-%m-%d').date() if new_end_date else None

        try:
            rent_rate.rent_rate = new_rent_rate
            rent_rate.start_date = new_start_date
            rent_rate.end_date = new_end_date
            rent_rate.save()
            return redirect('update_rent_rate', pk=rent_rate.pk)
        except ValidationError as e:
            error_message = str(e)
            context = {
                'is_landlord': True,
                'rental_unit': rental_unit,
                'rent_rate': rent_rate,
                'existing_rent_rates': existing_rent_rates,
                'error_message': error_message
            }
            return render(request, 'rentsolutions/rent_rate_management.html', context)

    context = {
        'is_landlord': True,
        'rental_unit': rental_unit,
        'rent_rate': rent_rate,
        'existing_rent_rates': existing_rent_rates
    }
    return render(request, 'rentsolutions/rent_rate_management.html', context)


@login_required(login_url='login')
@user_passes_test(is_landlord)
def landlord_properties(request):
    landlord = Landlord.objects.get(user=request.user)
    properties = landlord.properties.all().prefetch_related('rentalunit_set')
    context = {
        'properties': properties,
        'is_landlord': True,
    }
    return render(request, 'rentsolutions/landlord_properties.html', context)



@login_required(login_url='login')
@user_passes_test(is_landlord)
def tenant_details(request, pk):
    tenant = get_object_or_404(Tenant, pk=pk)
    context = {
        'tenant': tenant,
        'is_landlord': True,
        
    }
    return render(request, 'rentsolutions/tenant_details.html', context) 


@login_required(login_url='login')
@user_passes_test(is_landlord or is_rental_property_manager)
def add_rental_property(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        location = request.POST.get('location')
        amenities = request.POST.get('amenities')

        # Get the Landlord instance associated with the current user
        landlord = Landlord.objects.get(user=request.user)

        property = RentalProperty(
            name=name,
            location=location,
            amenities=amenities,
            landlord=landlord  # Use the Landlord instance
        )
        property.save()
        return redirect('landlord_properties')
    context ={
        'is_landlord': True,
        'is_rental_property_manager': True,
    }
    return render(request, 'rentsolutions/add_rental_property.html', context)

@login_required(login_url='login')
@user_passes_test(is_landlord or is_rental_property_manager)
def update_property(request, pk):
    property = get_object_or_404(RentalProperty, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name')
        location = request.POST.get('location')
        amenities = request.POST.get('amenities')

        property.name = name
        property.location = location
        property.amenities = amenities
        property.save()

        return redirect('landlord_properties')

    context = {
        'property': property,
        'is_landlord': True,
        'is_rental_property_manager': True,
    }
    return render(request, 'rentsolutions/update_property.html', context)



@login_required(login_url='login')
@user_passes_test(is_landlord or is_rental_property_manager)
def delete_property(request, pk):
    property = get_object_or_404(RentalProperty, pk=pk)

    if request.method == 'POST':
        property.delete()
        return redirect('landlord_properties')

    context = {
        'property': property,
        'is_landlord': True,
        'is_rental_property_manager': True,
    }
    return render(request, 'rentsolutions/delete_property.html', context)



@login_required(login_url='login')
@user_passes_test(is_landlord or is_rental_property_manager)
def add_rental_unit(request, pk):
    property = get_object_or_404(RentalProperty, pk=pk)

    if request.method == 'POST':
        unit_identity = request.POST.get('unit_identity')
        rent_rate = request.POST.get('rent_rate')
        start_date_str = request.POST.get('start_date')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

        # Create a new RentalUnitMonthlyRentRate instance
        rent_rate_instance = RentalUnitMonthlyRentRate.objects.create(
            rent_rate=rent_rate,
            start_date=start_date,
        )

        # Create a new RentalUnit instance
        unit = RentalUnit(
            property_with_rental_unit=property,
            unit_identity=unit_identity,
            current_monthly_rent_rate=rent_rate_instance
        )
        unit.save()

        return redirect('landlord_properties')

    context = {
        'property': property,
        'is_landlord': True,
        'is_rental_property_manager': True,
    }
    return render(request, 'rentsolutions/add_rental_unit.html', context)


@login_required
@user_passes_test(is_landlord or is_rental_property_manager)
def update_rental_unit(request, pk):
    unit = get_object_or_404(RentalUnit, pk=pk)

    if request.method == 'POST':
        unit_identity = request.POST.get('unit_identity')
        rent_rate = request.POST.get('rent_rate')
        start_date_str = request.POST.get('start_date')  # Get the start_date as a string
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()  # Convert the string to a date object

        unit.unit_identity = unit_identity
        unit.current_monthly_rent_rate.rent_rate = rent_rate
        unit.current_monthly_rent_rate.start_date = start_date
        unit.current_monthly_rent_rate.save()
        unit.save()

        return redirect('landlord_properties')

    context = {
        'unit': unit,
        'is_landlord': is_landlord(request.user),
        'is_rental_property_manager': is_rental_property_manager(request.user),
    }
    return render(request, 'rentsolutions/update_rental_unit.html', context)



@login_required
@user_passes_test(is_landlord or is_rental_property_manager)
def delete_rental_unit(request, pk):
    rental_unit = get_object_or_404(RentalUnit, pk=pk)

    if request.method == 'POST':
        rental_unit.delete()
        return redirect('landlord_properties')

    context = {
        'is_landlord': is_landlord(request.user),
        'is_rental_property_manager': is_rental_property_manager(request.user),
    }
    return redirect('landlord_properties')










@login_required(login_url='login')
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def administration(request):
    context = {}
    return render(request, 'rentsolutions/admin_staff.html', context)








def home(request):
  
    return render(request, 'rentsolutions/home.html')