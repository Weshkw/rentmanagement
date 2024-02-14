from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
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
    date_created = models.DateTimeField(default=timezone.now, editable=False)
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

class Property(models.Model):
    name = models.CharField(max_length=255)
    location = models.TextField()
    total_units = models.PositiveIntegerField(default=1)
    amenities = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Ownership(models.Model):
    landlord = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    date_registered = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Check if the landlord already owns the property
        existing_ownership = Ownership.objects.filter(landlord=self.landlord, property=self.property).exists()
        if existing_ownership:
            raise ValueError('This landlord already owns the property.')

        super().save(*args, **kwargs)

    def __str__(self):
        return self.landlord.full_name

class RentalUnit(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='rental_units')
    unit_identity = models.CharField(max_length=255)
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    is_occupied = models.BooleanField(default=False)
    date_occupied = models.DateField(blank=True, null=True)
    date_previous_tenant_left = models.DateField(blank=True, null=True)
    occupant_name = models.CharField(max_length=255, blank=True, null=True)
    occupant_id = models.CharField(max_length=255, blank=True, null=True)
    occupant_phone= models.CharField(max_length=15,blank=True, null=True)

    def __str__(self):
        return self.unit_identity

class Payment(models.Model):
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.PROTECT, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateField()
    receipt_generated = models.BooleanField(default=False)

    INTENDED_PAYMENT_MONTH_CHOICES = [
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ]

    INTENDED_PAYMENT_YEAR_CHOICES = [
    (f'{year}',f'{year}') for year in range(2020, 2030)  
]

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
    payment_details=models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.rental_unit.unit_identity} - {self.date_paid}"

class PaymentScreeshot(models.Model):
    rentalUnit=models.ForeignKey(RentalUnit, on_delete=models.PROTECT)
    screenshot=models.ImageField(upload_to='screenshot_images/')

