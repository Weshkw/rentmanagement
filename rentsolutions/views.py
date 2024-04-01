from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout 
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from dateutil.relativedelta import relativedelta
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
    
   # View for user login.
    
    if request.method == 'POST':
        phone_number = request.POST['phone_number']
        password = request.POST['password']

        # Authenticate user
        user = authenticate(request, phone_number=phone_number, password=password)

        if user is not None:
            login(request, user)
            if is_landlord(user):
                return redirect('land_lord_main_page')
            elif user.is_staff or user.is_superuser:
                return redirect('rent_easier')
            elif is_rental_property_manager(user):
                return redirect('property_manager_page')
            else:
                return redirect('home')
        else:
            # Authentication failed, render login page with error message
            message = "Invalid credentials"
            return render(request, 'rentsolutions/login.html', {'message': message})

    # Render login page for GET requests
    return render(request, 'rentsolutions/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')


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

        property_data.append({
            'property': property,
            'occupied_units': occupied_units,
            'total_units': total_units,
            'intended_payments': intended_payments,
            'actual_payments': actual_payments
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
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def administration(request):
    context = {}
    return render(request, 'rentsolutions/admin_staff.html', context)




@login_required(login_url='login')
@user_passes_test(is_rental_property_manager)
def property_manager_page(request):
    context = {
        'is_landlord': is_landlord(request.user),
        'is_rental_property_manager': True,
    }
    return render(request, 'rentsolutions/propertymanager.html', context)



def home(request):
  
    return render(request, 'rentsolutions/home.html')