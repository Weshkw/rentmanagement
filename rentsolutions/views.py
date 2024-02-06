from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse

def home(request):
    return render(request, 'rentsolutions/home.html')

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
