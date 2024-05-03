from django.urls import path
from .views import management_home, collect_rent,payment_history,edit_payment,add_tenant,tenant_details,edit_tenant,delete_tenant

app_name = 'propertymanagement'

urlpatterns = [
    path('management_home/', management_home, name='management_home'),
    path('collect_rent/<int:pk>/', collect_rent, name='collect_rent'),
    path('payment_history/<int:tenant_id>/', payment_history, name='payment_history'),
    path('edit_payment/<int:payment_id>/', edit_payment, name='edit_payment'),
    path('add_tenant/<int:unit_id>/',add_tenant, name='add_tenant'),
    path('tenant_details/<int:pk>/',tenant_details, name='tenant_details'),
    path('propertymanagement/edit_tenant/<int:tenant_id>/', edit_tenant, name='edit_tenant'),
    path('propertymanagement/delete_tenant/<int:tenant_id>/', delete_tenant, name='delete_tenant'),

]