from django.urls import path
from .views import login_view,home,upload_payment_screenshot

urlpatterns = [
    # Other URL patterns
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('uploadpayment/', upload_payment_screenshot, name='upload_payment'),
    # Other URL patterns
]
