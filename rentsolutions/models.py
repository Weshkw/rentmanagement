from datetime import date
from decimal import Decimal

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .billing import ZERO, monthly_rent, rate_start_for


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("A phone number is required.")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone_number, password, **extra_fields)


class CustomUser(AbstractUser):
    """A landlord, property manager or administrator who signs in with their phone number."""

    username = None
    first_name = None
    last_name = None
    phone_number = models.CharField(max_length=15, unique=True)
    full_name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    date_registered = models.DateField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return self.full_name

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split(" ")[0]


class Landlord(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="landlord")

    def __str__(self):
        return self.user.full_name


class RentalProperty(models.Model):
    name = models.CharField(max_length=255)
    landlord = models.ForeignKey(Landlord, on_delete=models.CASCADE, related_name="properties")
    location = models.CharField(max_length=255)
    amenities = models.TextField(blank=True)
    date_registered = models.DateField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "rental properties"

    def __str__(self):
        return self.name


class ActiveManagerQuerySet(models.QuerySet):
    def active(self, on=None):
        on = on or timezone.localdate()
        return self.filter(management_start_date__lte=on).filter(
            Q(management_end_date__isnull=True) | Q(management_end_date__gt=on)
        )


class RentalPropertyManager(models.Model):
    """A person employed by a landlord to run one property day to day."""

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="management_roles")
    property_managed = models.ForeignKey(
        RentalProperty, on_delete=models.CASCADE, related_name="managers"
    )
    national_id_number = models.CharField(max_length=50)
    management_start_date = models.DateField()
    management_end_date = models.DateField(
        null=True, blank=True, help_text="Access stops on this date."
    )

    objects = ActiveManagerQuerySet.as_manager()

    class Meta:
        ordering = ["-management_start_date"]

    def __str__(self):
        return f"{self.user.full_name} manages {self.property_managed.name}"


class RentalUnit(models.Model):
    property_with_rental_unit = models.ForeignKey(
        RentalProperty, on_delete=models.CASCADE, related_name="units"
    )
    unit_identity = models.CharField("unit", max_length=50)
    unit_notes = models.TextField("notes", blank=True)

    class Meta:
        ordering = ["unit_identity"]
        constraints = [
            models.UniqueConstraint(
                fields=["property_with_rental_unit", "unit_identity"],
                name="unique_unit_name_per_property",
            ),
        ]

    def __str__(self):
        return f"{self.unit_identity} in {self.property_with_rental_unit.name}"

    def rent_rate_on(self, day):
        """The monthly rent in force on ``day``, read from prefetched rates when available."""
        rates = [rate for rate in self.rent_rates.all() if rate.start_date <= day]
        return max(rates, key=lambda rate: rate.start_date) if rates else None

    @property
    def current_rent_rate(self):
        return self.rent_rate_on(timezone.localdate())

    def tenant_on(self, day):
        """The tenant living in the unit on ``day``, read from prefetched tenants when available."""
        return next((tenant for tenant in self.tenants.all() if tenant.is_resident_on(day)), None)

    @property
    def current_tenant(self):
        return self.tenant_on(timezone.localdate())

    @property
    def occupied(self):
        return self.current_tenant is not None


class RentalUnitMonthlyRentRate(models.Model):
    """The monthly rent of a unit from ``start_date`` until the next rate starts."""

    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE, related_name="rent_rates")
    rent_rate = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal(0))]
    )
    start_date = models.DateField(
        help_text="Rates start on the first of a month; a mid-month date starts next month."
    )

    class Meta:
        ordering = ["start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["rental_unit", "start_date"], name="one_rent_rate_per_unit_per_month"
            ),
        ]

    def __str__(self):
        return f"{self.rent_rate} from {self.start_date:%B %Y}"

    def save(self, *args, **kwargs):
        self.start_date = rate_start_for(self.start_date)
        super().save(*args, **kwargs)


class Tenant(models.Model):
    rental_unit_occupied = models.ForeignKey(
        RentalUnit, on_delete=models.CASCADE, related_name="tenants", verbose_name="rental unit"
    )
    tenant_name = models.CharField("name", max_length=255)
    national_id_number = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    date_tenancy_starts = models.DateField("tenancy starts")
    date_tenancy_ends = models.DateField("tenancy ends", null=True, blank=True)

    class Meta:
        ordering = ["-date_tenancy_starts"]

    def __str__(self):
        return f"{self.tenant_name} ({self.rental_unit_occupied.unit_identity})"

    def clean(self):
        ends = self.date_tenancy_ends
        if ends and self.date_tenancy_starts and ends < self.date_tenancy_starts:
            raise ValidationError({"date_tenancy_ends": "A tenancy cannot end before it starts."})

    def is_resident_on(self, day):
        ends = self.date_tenancy_ends
        return self.date_tenancy_starts <= day and (ends is None or ends >= day)

    def rent_statement(self, today=None):
        """Month-by-month rent for this tenancy, using prefetched rates and payments when loaded."""
        return monthly_rent(
            tenancy_starts=self.date_tenancy_starts,
            tenancy_ends=self.date_tenancy_ends,
            rates=[
                (rate.start_date, rate.rent_rate)
                for rate in self.rental_unit_occupied.rent_rates.all()
            ],
            payments=[(payment.period, payment.amount_paid) for payment in self.payments.all()],
            today=today or timezone.localdate(),
        )

    def balance_for(self, month, today=None):
        statement = self.rent_statement(today)
        return next((line.balance for line in statement if line.month == month), ZERO)

    @property
    def total_balance(self):
        return sum((line.balance for line in self.rent_statement()), ZERO)


class RentPayment(models.Model):
    MONTH_CHOICES = [(month, date(2000, month, 1).strftime("%B")) for month in range(1, 13)]

    tenant_paying = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="payments")
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    date_paid = models.DateField()
    intended_payment_month = models.PositiveSmallIntegerField(
        "paying for month", choices=MONTH_CHOICES
    )
    intended_payment_year = models.PositiveSmallIntegerField("paying for year")
    payment_details = models.TextField(blank=True)
    date_recorded = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-date_paid", "-pk"]

    def __str__(self):
        return f"{self.amount_paid} from {self.tenant_paying.tenant_name} on {self.date_paid}"

    @property
    def period(self):
        """The first day of the month this payment is for."""
        return date(self.intended_payment_year, self.intended_payment_month, 1)
