from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
from django.db.models import Sum
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging
from datetime import timedelta
import calendar
from dateutil.relativedelta import relativedelta
from datetime import datetime
from django.db.models import Sum, Q
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(phone_number, password, **extra_fields)


class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True)
    full_name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    date_registered = models.DateField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    objects = CustomUserManager()
    groups = models.ManyToManyField(Group, related_name='custom_user_set', blank=True)
    user_permissions = models.ManyToManyField(
        Permission, related_name='custom_user_set', blank=True
    )

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']

    def save(self, *args, **kwargs):
        if not self.password.startswith(('pbkdf2_sha256$', 'bcrypt', 'argon2')):
            self.set_password(self.password)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name
    



class Landlord(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='landlords')

    def __str__(self):
        return self.user.full_name
    




class RentalProperty(models.Model):
    name = models.CharField(max_length=255)
    landlord = models.ForeignKey('Landlord', on_delete=models.CASCADE, related_name='properties')
    location = models.TextField()
    total_units = models.PositiveIntegerField(default=0)
    amenities = models.TextField(blank=True, null=True)
    date_registered = models.DateField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    



    

class RentalPropertyManager(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='rental_property_managers')
    property_managed = models.ForeignKey(RentalProperty, on_delete=models.CASCADE, related_name='propertys_managed')
    national_id_number= models.CharField(max_length=255)
    management_start_date= models.DateField()
    management_end_date=models.DateField(blank=True, null=True)

    def __str__(self):
        return f'{self.user.full_name} manages {self.property_managed.name}'


class RentalUnit(models.Model):
    property_with_rental_unit = models.ForeignKey(RentalProperty, on_delete=models.CASCADE)
    unit_identity = models.CharField(max_length=255)
    current_monthly_rent_rate = models.ForeignKey('RentalUnitMonthlyRentRate', on_delete=models.PROTECT,
                                                  related_name='monthly_rent')
    occupied = models.BooleanField(default=False)
    unit_notes= models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)  # Save the RentalUnit first
        self.update_total_units()
        if created and self.current_monthly_rent_rate:
            self.current_monthly_rent_rate.rental_unit = self.unit_identity
            self.current_monthly_rent_rate.unit_absolute_identity = self.id
            self.current_monthly_rent_rate.save() 


    def update_total_units(self):
        rental_property = self.property_with_rental_unit
        rental_property.total_units = rental_property.rentalunit_set.count()
        rental_property.save()

    def __str__(self):
        return f'{self.unit_identity} in {self.property_with_rental_unit.name}'
    

logger = logging.getLogger(__name__)

@receiver(post_delete, sender=RentalUnit)
def update_rental_property_total_units(sender, instance, **kwargs):
    rental_property = instance.property_with_rental_unit
    rental_property.total_units = rental_property.rentalunit_set.count()
    rental_property.save()


class Tenant(models.Model):
    rental_unit_occupied = models.ForeignKey(RentalUnit, on_delete=models.CASCADE, related_name='rental_units',
                                              verbose_name="Rental unit assigned")
    date_tenancy_starts = models.DateField()
    date_tenancy_ends = models.DateField(blank=True, null=True)
    tenant_name = models.CharField(max_length=255)
    national_id_number = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=15, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    emergency_contact_relationship = models.CharField(max_length=15, blank=True, null=True)


    @property
    def Tenant_Monthly_Rental_balances(self):
        balances = {}
        today = timezone.now().date()

        # Get the applicable rent rates for the tenant's rental unit
        applicable_rent_rates = RentalUnitMonthlyRentRate.objects.filter(
            unit_absolute_identity=self.rental_unit_occupied.id
        ).order_by('start_date')

        # Determine the start and end dates for rent calculation
        start_date = self.date_tenancy_starts
        end_date = self.date_tenancy_ends or today

        # Calculate the prorated rent for the first month
        first_month = start_date.month
        first_year = start_date.year
        _, days_in_first_month = calendar.monthrange(first_year, first_month)
        occupied_days_first_month = days_in_first_month - start_date.day + 1

        rent_rate_first_month = applicable_rent_rates.filter(
            start_date__lte=datetime(first_year, first_month, 1)
        ).order_by('-start_date').first()

        if rent_rate_first_month:
            prorated_rent_first_month = rent_rate_first_month.rent_rate * occupied_days_first_month / days_in_first_month

            # Calculate the intended payments for the first month
            total_payments_first_month = RentPayment.objects.filter(
                tenant_paying=self,
                intended_payment_month=str(first_month).zfill(2),
                intended_payment_year=str(first_year)
            ).aggregate(total_amount=Sum('amount_paid'))['total_amount'] or 0

            # Calculate the rent balance for the first month
            rent_balance_first_month = prorated_rent_first_month - total_payments_first_month

            # Round the rent balance to two decimal places
            balances[f"{first_year}-{str(first_month).zfill(2)}"] = round(max(Decimal(0), rent_balance_first_month), 2)

        # Iterate over the remaining full months
        current_date = start_date + relativedelta(months=1)
        while current_date < end_date:
            month = current_date.month
            year = current_date.year

            # Calculate the intended payments for this month
            total_payments = RentPayment.objects.filter(
                tenant_paying=self,
                intended_payment_month=str(month).zfill(2),
                intended_payment_year=str(year)
            ).aggregate(total_amount=Sum('amount_paid'))['total_amount'] or 0

            # Get the applicable rent rate for the current month
            rent_rate = applicable_rent_rates.filter(
                start_date__lte=datetime(year, month, 1)
            ).order_by('-start_date').first()

            if rent_rate:
                # Calculate the full month's rent
                full_month_rent = rent_rate.rent_rate

                # Calculate the rent balance for this month
                rent_balance = full_month_rent - total_payments

                # Round the rent balance to two decimal places
                balances[f"{year}-{str(month).zfill(2)}"] = round(max(Decimal(0), rent_balance), 2)

            # Move to the next month
            current_date += relativedelta(months=1)

        # Calculate the rent balance for the last month
        if end_date != today:
            last_month = end_date.month
            last_year = end_date.year

            rent_rate_last_month = applicable_rent_rates.filter(
                start_date__lte=datetime(last_year, last_month, 1)
            ).order_by('-start_date').first()

            if rent_rate_last_month:
                # Calculate the full month's rent
                full_month_rent = rent_rate_last_month.rent_rate

                # Calculate the intended payments for the last month
                total_payments_last_month = RentPayment.objects.filter(
                    tenant_paying=self,
                    intended_payment_month=str(last_month).zfill(2),
                    intended_payment_year=str(last_year)
                ).aggregate(total_amount=Sum('amount_paid'))['total_amount'] or 0

                # Calculate the rent balance for the last month
                rent_balance_last_month = full_month_rent - total_payments_last_month

                # Round the rent balance to two decimal places
                balances[f"{last_year}-{str(last_month).zfill(2)}"] = round(max(Decimal(0), rent_balance_last_month), 2)

        # Calculate the rent balance for the current month
        if end_date == today:
            current_month = today.month
            current_year = today.year

            rent_rate_current_month = applicable_rent_rates.filter(
                start_date__lte=datetime(current_year, current_month, 1)
            ).order_by('-start_date').first()

            if rent_rate_current_month:
                # Calculate the full month's rent
                full_month_rent = rent_rate_current_month.rent_rate

                # Calculate the intended payments for the current month
                total_payments_current_month = RentPayment.objects.filter(
                    tenant_paying=self,
                    intended_payment_month=str(current_month).zfill(2),
                    intended_payment_year=str(current_year)
                ).aggregate(total_amount=Sum('amount_paid'))['total_amount'] or 0

                # Calculate the rent balance for the current month
                rent_balance_current_month = full_month_rent - total_payments_current_month

                # Round the rent balance to two decimal places
                balances[f"{current_year}-{str(current_month).zfill(2)}"] = round(max(Decimal(0), rent_balance_current_month), 2)

        return balances
        
   
    def save(self, *args, **kwargs):
        if self.pk is None:  # Only when the instance is newly created
            self.rental_unit_occupied.occupied = True
            self.rental_unit_occupied.save(update_fields=['occupied'])
        super().save(*args, **kwargs)

    

    def __str__(self):
        if self.tenant_name:
            return f'{self.tenant_name}, rental_unit:{self.rental_unit_occupied.unit_identity}'
        else:
            return f'Tenant {self.pk}, rental_unit:{self.rental_unit_occupied.unit_identity}'
        

@receiver(post_delete, sender=Tenant)
def set_rental_unit_unoccupied(sender, instance, **kwargs):
    rental_unit = instance.rental_unit_occupied
    rental_unit.occupied = False
    rental_unit.save(update_fields=['occupied'])


class RentalUnitMonthlyRentRate(models.Model):
    rent_rate = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    rental_unit = models.CharField(max_length=255, blank=True)
    unit_absolute_identity = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Rent rate: {self.rent_rate} - Start Date: {self.start_date}"

    def save(self, *args, **kwargs):
        if self.start_date:
            if self.start_date.day != 1:
                _, last_day_of_month = calendar.monthrange(self.start_date.year, self.start_date.month)
                next_month = self.start_date.replace(day=1) + timedelta(days=last_day_of_month)
                self.start_date = next_month.replace(day=1)

        previous_rate = RentalUnitMonthlyRentRate.objects.filter(
            rental_unit=self.rental_unit,
            unit_absolute_identity=self.unit_absolute_identity
        ).order_by('-start_date').first()

        if previous_rate and self.start_date < previous_rate.start_date:
            raise ValidationError("Start date cannot be earlier than the start date of the previous rate.")

        if previous_rate:
            previous_rate_end_date = self.start_date - timedelta(days=1)
            RentalUnitMonthlyRentRate.objects.filter(pk=previous_rate.pk).update(end_date=previous_rate_end_date)

        super().save(*args, **kwargs)


class RentPayment(models.Model):
    tenant_paying = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, related_name='tenant_payments')
    rental_unit_paid_for = models.CharField(max_length=255, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateField()
    INTENDED_PAYMENT_MONTH_CHOICES = [
        ('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
        ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
        ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ]
    INTENDED_PAYMENT_YEAR_CHOICES = [(str(year), str(year)) for year in range(2020, 2050)]

    intended_payment_month = models.CharField(
        max_length=2,
        choices=INTENDED_PAYMENT_MONTH_CHOICES,
        help_text="Select the intended payment month",
    )

    intended_payment_year = models.CharField(
        max_length=4,
        choices=INTENDED_PAYMENT_YEAR_CHOICES,
        help_text="Select the intended payment year",
    )
    payment_details = models.TextField(blank=True, null=True)
    date_recorded = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.tenant_paying:
            self.rental_unit_paid_for = self.tenant_paying.rental_unit_occupied.unit_identity
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Payment - {self.date_paid} unit- {self.rental_unit_paid_for}" 