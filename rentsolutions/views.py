from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_protect
from .models import RentalUnit, PaymentScreeshot
from django.contrib import messages


def home(request):
    return render(request, 'rentsolutions/home.html')

def upload_payment_screenshot(request):
    if request.method == 'POST':
            rental_unit_id = request.POST['rental_unit']
            screenshot = request.FILES['screenshot']
            
            rental_unit = RentalUnit.objects.get(id=rental_unit_id)
            
            payment_screenshot = PaymentScreeshot(rentalUnit=rental_unit, screenshot=screenshot)
            payment_screenshot.save()
            messages.success(request, 'Payment screenshot uploaded successfully.')
            return redirect('home')
   
    
    rental_units = RentalUnit.objects.all()
    context = {'rental_units': rental_units}
    return render(request, 'rentsolutions/upload_screenshot.html',context)

@csrf_protect
def login_view(request):
    if request.method == 'POST':
        phone_number = request.POST['phone_number']
        password = request.POST['password']
        
        user = authenticate(request, phone_number=phone_number, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')  # Replace 'home' with the URL name of your home page
        else:
            # Authentication failed
            return render(request, 'login.html', {'error': 'Invalid credentials'})

    return render(request, 'rentsolutions/login.html')
