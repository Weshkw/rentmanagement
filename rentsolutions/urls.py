from django.urls import path
from .views import login_view,home

urlpatterns = [
    # Other URL patterns
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    # Other URL patterns
]
