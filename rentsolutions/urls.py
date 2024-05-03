from django.urls import path, include
from .views import home,land_lord_main_page,login_view,administration,logout_view,create_rent_rate,update_rent_rate, rental_units_in_property,tenant_details,landlord_properties,add_rental_property,update_property, delete_property,add_rental_unit, update_rental_unit,delete_rental_unit,employ_property_manager,fire_property_manager,register_as_landlord

urlpatterns = [
     path('', home, name='home'),
     path('register_as_landlord/', register_as_landlord, name='register_as_landlord'),
     path('login/', login_view, name='login'),
     path('logout/', logout_view, name='logout'),
     path('rent_easier/', administration, name='rent_easier'),
     path('land_lord_main_page/', land_lord_main_page, name='land_lord_main_page'),
     path('rental_units_in_property/<int:pk>/',  rental_units_in_property, name='rental_units_in_property'),
     path('rental-units/<int:pk>/create-rent-rate/', create_rent_rate, name='create_rent_rate'),
     path('rent-rates/<int:pk>/update/', update_rent_rate, name='update_rent_rate'),
     path('tenant/<int:pk>/', tenant_details, name='tenant_details'),
     path('landlord/properties/', landlord_properties, name='landlord_properties'),

     path('add-rental-property/', add_rental_property, name='add_rental_property'),
     path('property/<int:pk>/update/', update_property, name='update_property'),
     path('property/<int:pk>/delete/', delete_property, name='delete_property'),


     path('property/<int:pk>/add-rental-unit/', add_rental_unit, name='add_rental_unit'),
     path('properties/units/<int:pk>/update/', update_rental_unit, name='update_rental_unit'),
     path('rental-units/<int:pk>/delete/', delete_rental_unit, name='delete_rental_unit'),


     path('manage-property-managers/', employ_property_manager, name='manage_property_managers'),
     path('fire-property-manager/<int:manager_id>/', fire_property_manager, name='fire_property_manager'),

]
