from django import forms
from django.db.models import Q
from django.utils import timezone

from rentsolutions.forms import DATE_INPUT
from rentsolutions.models import RentalUnit, RentPayment, Tenant


class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = [
            "tenant_name",
            "phone",
            "national_id_number",
            "date_tenancy_starts",
            "date_tenancy_ends",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relationship",
        ]
        widgets = {"date_tenancy_starts": DATE_INPUT, "date_tenancy_ends": DATE_INPUT}

    def __init__(self, *args, rental_unit, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.rental_unit_occupied = rental_unit

    def clean(self):
        cleaned_data = super().clean()
        starts = cleaned_data.get("date_tenancy_starts")
        if starts:
            ends = cleaned_data.get("date_tenancy_ends")
            other_tenants = self.instance.rental_unit_occupied.tenants.exclude(pk=self.instance.pk)
            overlapping = other_tenants.filter(
                Q(date_tenancy_ends__isnull=True) | Q(date_tenancy_ends__gte=starts)
            )
            if ends:
                overlapping = overlapping.filter(date_tenancy_starts__lte=ends)
            if overlapping.exists():
                raise forms.ValidationError(
                    "Another tenant lives in this unit during those dates. End their tenancy first."
                )
        return cleaned_data


class EndTenancyForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ["date_tenancy_ends"]
        widgets = {"date_tenancy_ends": DATE_INPUT}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date_tenancy_ends"].required = True
        self.fields["date_tenancy_ends"].initial = timezone.localdate()


class RentPaymentForm(forms.ModelForm):
    intended_payment_year = forms.IntegerField(
        label="Paying for year", min_value=2000, max_value=2100
    )

    class Meta:
        model = RentPayment
        fields = [
            "amount_paid",
            "date_paid",
            "intended_payment_month",
            "intended_payment_year",
            "payment_details",
        ]
        labels = {"amount_paid": "Amount paid (Ksh)"}
        widgets = {"date_paid": DATE_INPUT, "payment_details": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            today = timezone.localdate()
            self.initial.setdefault("date_paid", today)
            self.initial.setdefault("intended_payment_month", today.month)
            self.initial.setdefault("intended_payment_year", today.year)


class UnitNotesForm(forms.ModelForm):
    class Meta:
        model = RentalUnit
        fields = ["unit_notes"]
        widgets = {"unit_notes": forms.Textarea(attrs={"rows": 4})}
