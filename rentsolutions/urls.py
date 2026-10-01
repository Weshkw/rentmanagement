from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_landlord, name="register_landlord"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("landlord/", views.landlord_dashboard, name="landlord_dashboard"),
    path("properties/", views.property_list, name="property_list"),
    path("properties/new/", views.property_create, name="property_create"),
    path("properties/<int:pk>/edit/", views.property_edit, name="property_edit"),
    path("properties/<int:pk>/delete/", views.property_delete, name="property_delete"),
    path("properties/<int:pk>/units/", views.property_units, name="property_units"),
    path("properties/<int:property_pk>/units/new/", views.unit_create, name="unit_create"),
    path("units/<int:pk>/edit/", views.unit_edit, name="unit_edit"),
    path("units/<int:pk>/delete/", views.unit_delete, name="unit_delete"),
    path("units/<int:unit_pk>/rent/", views.rent_rates, name="rent_rates"),
    path("units/<int:unit_pk>/rent/<int:rate_pk>/", views.rent_rates, name="rent_rate_edit"),
    path("managers/", views.managers, name="managers"),
    path("managers/<int:pk>/end/", views.manager_end, name="manager_end"),
]
