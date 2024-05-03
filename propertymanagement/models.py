from django.db import models
from rentsolutions.models import CustomUser
from django.db.models import Sum
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import timedelta
import calendar
from dateutil.relativedelta import relativedelta
from datetime import datetime
from django.db.models import Sum, Q
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
