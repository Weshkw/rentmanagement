import secrets

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.db import transaction

from .billing import rate_start_for
from .models import (
    Landlord,
    RentalProperty,
    RentalPropertyManager,
    RentalUnit,
    RentalUnitMonthlyRentRate,
)

DATE_INPUT = forms.DateInput(attrs={"type": "date"})


def phone_number_in_use(phone_number):
    return get_user_model().objects.filter(phone_number=phone_number).exists()


class LandlordRegistrationForm(forms.Form):
    """Creates a landlord account together with their first property."""

    full_name = forms.CharField(max_length=255)
    phone_number = forms.CharField(max_length=15, help_text="You will sign in with this number.")
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
    password = forms.CharField(widget=forms.PasswordInput, strip=False)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput, strip=False)
    property_name = forms.CharField(max_length=255)
    location = forms.CharField(max_length=255)
    amenities = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"].strip()
        if phone_number_in_use(phone_number):
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        if password and password != cleaned_data.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        elif password:
            candidate = get_user_model()(
                full_name=cleaned_data.get("full_name", ""),
                phone_number=cleaned_data.get("phone_number", ""),
            )
            try:
                password_validation.validate_password(password, candidate)
            except forms.ValidationError as error:
                self.add_error("password", error)
        return cleaned_data

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        user = get_user_model().objects.create_user(
            data["phone_number"],
            data["password"],
            full_name=data["full_name"],
            address=data["address"],
        )
        landlord = Landlord.objects.create(user=user)
        RentalProperty.objects.create(
            landlord=landlord,
            name=data["property_name"],
            location=data["location"],
            amenities=data["amenities"],
        )
        return user


class RentalPropertyForm(forms.ModelForm):
    class Meta:
        model = RentalProperty
        fields = ["name", "location", "amenities"]
        widgets = {"amenities": forms.Textarea(attrs={"rows": 3})}


class RentalUnitForm(forms.ModelForm):
    """Names a unit; unit names are unique within a property."""

    class Meta:
        model = RentalUnit
        fields = ["unit_identity"]

    def __init__(self, *args, rental_property, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.property_with_rental_unit = rental_property

    def clean_unit_identity(self):
        unit_identity = self.cleaned_data["unit_identity"].strip()
        clashes = RentalUnit.objects.filter(
            property_with_rental_unit=self.instance.property_with_rental_unit,
            unit_identity__iexact=unit_identity,
        ).exclude(pk=self.instance.pk)
        if clashes.exists():
            raise forms.ValidationError("This property already has a unit with that name.")
        return unit_identity


class NewRentalUnitForm(RentalUnitForm):
    """Creates a unit together with its first monthly rent."""

    rent_rate = forms.DecimalField(label="Monthly rent (Ksh)", max_digits=10, decimal_places=2)
    start_date = forms.DateField(
        label="Rent applies from",
        widget=DATE_INPUT,
        help_text="Rent starts on the first of a month; a mid-month date starts next month.",
    )

    @transaction.atomic
    def save(self):
        unit = super().save()
        unit.rent_rates.create(
            rent_rate=self.cleaned_data["rent_rate"], start_date=self.cleaned_data["start_date"]
        )
        return unit


class RentRateForm(forms.ModelForm):
    class Meta:
        model = RentalUnitMonthlyRentRate
        fields = ["rent_rate", "start_date"]
        labels = {"rent_rate": "Monthly rent (Ksh)", "start_date": "Applies from"}
        widgets = {"start_date": DATE_INPUT}

    def __init__(self, *args, rental_unit, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.rental_unit = rental_unit

    def clean_start_date(self):
        start_date = rate_start_for(self.cleaned_data["start_date"])
        clashes = self.instance.rental_unit.rent_rates.filter(start_date=start_date).exclude(
            pk=self.instance.pk
        )
        if clashes.exists():
            raise forms.ValidationError(
                f"There is already a rate starting {start_date:%B %Y}. Edit that rate instead."
            )
        return start_date


class HireManagerForm(forms.Form):
    property_managed = forms.ModelChoiceField(queryset=RentalProperty.objects.none())
    full_name = forms.CharField(max_length=255)
    phone_number = forms.CharField(
        max_length=15, help_text="If this number already has an account, it is reused."
    )
    national_id_number = forms.CharField(max_length=50)
    management_start_date = forms.DateField(widget=DATE_INPUT)

    def __init__(self, *args, landlord_properties, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["property_managed"].queryset = landlord_properties

    def clean(self):
        cleaned_data = super().clean()
        rental_property = cleaned_data.get("property_managed")
        phone_number = cleaned_data.get("phone_number", "").strip()
        already_managing = RentalPropertyManager.objects.active().filter(
            property_managed=rental_property, user__phone_number=phone_number
        )
        if rental_property and already_managing.exists():
            raise forms.ValidationError("This person already manages that property.")
        return cleaned_data

    @transaction.atomic
    def save(self):
        """Employ the manager; returns it and, for a new account, its temporary password."""
        data = self.cleaned_data
        user_model = get_user_model()
        user = user_model.objects.filter(phone_number=data["phone_number"].strip()).first()
        temporary_password = None
        if user is None:
            temporary_password = secrets.token_urlsafe(9)
            user = user_model.objects.create_user(
                data["phone_number"].strip(), temporary_password, full_name=data["full_name"]
            )
        manager = RentalPropertyManager.objects.create(
            user=user,
            property_managed=data["property_managed"],
            national_id_number=data["national_id_number"],
            management_start_date=data["management_start_date"],
        )
        return manager, temporary_password
