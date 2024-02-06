from django.contrib import admin
from .models import CustomUser, Property, Ownership, RentalUnit, Payment

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'address', 'date_created', 'date_updated')
    search_fields = ('full_name', 'phone_number')

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'total_units', 'amenities')
    search_fields = ('name', 'location')

@admin.register(Ownership)
class OwnershipAdmin(admin.ModelAdmin):
    list_display = ('landlord', 'property', 'date_registered')
    search_fields = ('landlord__full_name', 'property__name')

@admin.register(RentalUnit)
class RentalUnitAdmin(admin.ModelAdmin):
    list_display = ('property', 'unit_identity', 'monthly_rent', 'is_occupied', 'date_occupied', 'occupant_name','occupant_phone')
    search_fields = ('property__name', 'unit_identity')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('rental_unit', 'amount_paid', 'date_paid', 'receipt_generated', 'intended_payment_month', 'intended_payment_year')
    search_fields = ('rental_unit__unit_identity', 'date_paid')

# Register other models if needed
