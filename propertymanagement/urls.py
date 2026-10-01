from django.urls import path

from . import views

app_name = "propertymanagement"

urlpatterns = [
    path("", views.management_home, name="management_home"),
    path("units/<int:pk>/", views.unit_detail, name="unit_detail"),
    path("units/<int:unit_pk>/tenants/new/", views.tenant_create, name="tenant_create"),
    path("tenants/<int:pk>/", views.tenant_detail, name="tenant_detail"),
    path("tenants/<int:pk>/edit/", views.tenant_edit, name="tenant_edit"),
    path("tenants/<int:pk>/end/", views.tenant_end, name="tenant_end"),
    path("tenants/<int:tenant_pk>/payments/new/", views.collect_rent, name="collect_rent"),
    path("payments/<int:pk>/edit/", views.payment_edit, name="payment_edit"),
]
