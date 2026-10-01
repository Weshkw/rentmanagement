from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from .models import (
    CustomUser,
    Landlord,
    RentalProperty,
    RentalPropertyManager,
    RentalUnit,
    RentalUnitMonthlyRentRate,
    RentPayment,
    Tenant,
)


class CustomUserCreationForm(BaseUserCreationForm):
    class Meta:
        model = CustomUser
        fields = ["phone_number", "full_name"]


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    list_display = ["full_name", "phone_number", "is_staff", "date_registered"]
    list_filter = ["is_staff", "is_superuser", "is_active"]
    search_fields = ["full_name", "phone_number"]
    ordering = ["full_name"]
    fieldsets = [
        (None, {"fields": ["phone_number", "password"]}),
        ("Personal info", {"fields": ["full_name", "address"]}),
        (
            "Permissions",
            {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]},
        ),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["phone_number", "full_name", "password1", "password2"],
            },
        ),
    ]


@admin.register(Landlord)
class LandlordAdmin(admin.ModelAdmin):
    list_display = ["user"]
    list_select_related = ["user"]
    search_fields = ["user__full_name", "user__phone_number"]


@admin.register(RentalProperty)
class RentalPropertyAdmin(admin.ModelAdmin):
    list_display = ["name", "landlord", "location", "date_registered"]
    list_select_related = ["landlord__user"]
    search_fields = ["name", "location"]


@admin.register(RentalPropertyManager)
class RentalPropertyManagerAdmin(admin.ModelAdmin):
    list_display = ["user", "property_managed", "management_start_date", "management_end_date"]
    list_select_related = ["user", "property_managed"]
    search_fields = ["user__full_name", "property_managed__name"]


class RentRateInline(admin.TabularInline):
    model = RentalUnitMonthlyRentRate
    extra = 0


@admin.register(RentalUnit)
class RentalUnitAdmin(admin.ModelAdmin):
    list_display = ["unit_identity", "property_with_rental_unit"]
    list_select_related = ["property_with_rental_unit"]
    search_fields = ["unit_identity", "property_with_rental_unit__name"]
    inlines = [RentRateInline]


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = [
        "tenant_name",
        "rental_unit_occupied",
        "date_tenancy_starts",
        "date_tenancy_ends",
    ]
    list_select_related = ["rental_unit_occupied__property_with_rental_unit"]
    search_fields = ["tenant_name", "phone", "national_id_number"]


@admin.register(RentPayment)
class RentPaymentAdmin(admin.ModelAdmin):
    list_display = [
        "tenant_paying",
        "amount_paid",
        "date_paid",
        "intended_payment_month",
        "intended_payment_year",
    ]
    list_select_related = ["tenant_paying__rental_unit_occupied"]
    list_filter = ["intended_payment_year", "intended_payment_month"]
    search_fields = ["tenant_paying__tenant_name"]
