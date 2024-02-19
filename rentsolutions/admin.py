from django.contrib import admin
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, Property, Ownership, RentalUnit, Payment, PaymentScreeshot

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




class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0

class RentalUnitAdmin(admin.ModelAdmin):
    inlines = [PaymentInline]

    list_display = ['unit_identity', 'get_all_rent_balances','monthly_rent']
    search_fields = ['unit_identity']
    readonly_fields = ['get_all_rent_balances']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('payments')
        return queryset

    def get_all_rent_balances(self, obj):
        balances = obj.get_rent_balances_by_month()
        return ', '.join([f'{month_year}: {balance}' for month_year, balance in balances.items()])

    get_all_rent_balances.short_description = _('Rent Balances for Each Month')

admin.site.register(RentalUnit, RentalUnitAdmin)



class PaymentAdmin(admin.ModelAdmin):
    list_display = ('date_paid', 'rental_unit', 'amount_paid', 'intended_payment_month', 'intended_payment_year', 'total_payments_month')
    search_fields = ('rental_unit__unit_identity',)

    def total_payments_month(self, obj):
        total = Payment.objects.filter(intended_payment_month=obj.intended_payment_month,
                                       intended_payment_year=obj.intended_payment_year)\
                               .aggregate(total_payments=Sum('amount_paid'))['total_payments']
        month_year = f"{obj.get_intended_payment_month_display()} {obj.intended_payment_year}"
        return f"{month_year}: {total}" if total is not None else f"{month_year}: 0"

    total_payments_month.short_description = 'Total Payments for Month'

admin.site.register(Payment, PaymentAdmin)

@admin.register(PaymentScreeshot)
class PaymentScreeshotAdmin(admin.ModelAdmin):
    list_display = ('rentalUnit', 'screenshot')
    
# Register other models if needed
