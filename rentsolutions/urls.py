from django.urls import path
from .views import home,land_lord_main_page,login_view,property_manager_page,administration,logout_view

urlpatterns = [
     path('', home, name='home'),
     path('login/', login_view, name='login'),
     path('logout/', logout_view, name='logout'),
     path('rent_easier/', administration, name='rent_easier'),
     path('land_lord_main_page/', land_lord_main_page, name='land_lord_main_page'),
     path('property_manager_page/', property_manager_page, name='property_manager_page'),

]
