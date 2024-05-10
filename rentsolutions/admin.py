from django.contrib import admin
import calendar
from django.db.models import Sum, Q
from django.utils.html import format_html
from .models import CustomUser, Landlord, RentalProperty, RentalUnit, Tenant, RentalUnitMonthlyRentRate, RentPayment, RentalPropertyManager

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone_number', 'address', 'date_registered', 'date_updated']
    search_fields = ['full_name', 'phone_number', 'address']

admin.site.register(CustomUser, CustomUserAdmin)

class LandlordAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_phone_number', 'user_full_name']

    def user_phone_number(self, obj):
        return obj.user.phone_number

    def user_full_name(self, obj):
        return obj.user.full_name

    search_fields = ['user__full_name', 'user__phone_number']

admin.site.register(Landlord, LandlordAdmin)

@admin.register(RentalPropertyManager)
class RentalPropertyManagerAdmin(admin.ModelAdmin):
    list_display = ('user', 'property_managed', 'management_start_date', 'management_end_date')
    search_fields = ('user__full_name', 'property_managed__name')
    list_filter = ('management_start_date', 'management_end_date')

class RentalPropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'landlord', 'location', 'total_units', 'date_registered', 'date_updated']
    search_fields = ['name', 'location']

admin.site.register(RentalProperty, RentalPropertyAdmin)

class RentalUnitAdmin(admin.ModelAdmin):
    list_display = ['id', 'property_with_rental_unit', 'unit_identity', 'current_monthly_rent_rate', 'occupied', 'unit_notes']
    search_fields = ['unit_identity', 'property_with_rental_unit__name']
    fields = ['property_with_rental_unit', 'unit_identity', 'current_monthly_rent_rate', 'occupied', 'unit_notes']

admin.site.register(RentalUnit, RentalUnitAdmin)

class TenantAdmin(admin.ModelAdmin):
    list_display = [
        'tenant_name', 'rental_unit_occupied', 'date_tenancy_starts', 'date_tenancy_ends', 'national_id_number', 'phone', 'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship', 'display_rental_balances',
    ]

    def display_rental_balances(self, obj):
        balances = obj.Tenant_Monthly_Rental_balances
        if balances:
            balance_strings = [f"{month}: {balance}" for month, balance in balances.items()]
            return "\n".join(balance_strings)
        else:
            return "No rental balances found"

    display_rental_balances.short_description = 'Monthly Rental Balances'

admin.site.register(Tenant, TenantAdmin)

class RentalUnitMonthlyRentRateAdmin(admin.ModelAdmin):
    list_display = ('rent_rate', 'start_date', 'end_date', 'rental_unit', 'unit_absolute_identity')
    search_fields = ('rental_unit', 'unit_absolute_identity')

admin.site.register(RentalUnitMonthlyRentRate, RentalUnitMonthlyRentRateAdmin)

class RentPaymentAdmin(admin.ModelAdmin):
    list_display = ['tenant_name', 'rental_unit_paid_for', 'amount_paid', 'date_paid', 'intended_payment_month', 'intended_payment_year', 'date_recorded']
    search_fields = ['tenant_paying__tenant_name']

    def tenant_name(self, obj):
        return obj.tenant_paying.tenant_name if obj.tenant_paying else ''

admin.site.register(RentPayment, RentPaymentAdmin)