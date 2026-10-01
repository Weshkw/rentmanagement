"""Rent arithmetic: what a tenant owes, month by month.

These are pure functions over plain values so the rules can be tested without a
database. The rules:

- A rent rate applies from the first day of its start month until the next rate
  for the same unit starts. A rate entered with a mid-month date starts on the
  first of the following month.
- Rent is billed for every month from the month the tenancy starts up to the
  month it ends, or up to the current month while it is ongoing.
- The first month is prorated by the days the tenant lived in the unit; every
  later month is billed in full.
- A payment counts towards the month it was made for. Overpaying one month does
  not reduce what is owed for another.
- A month with no rent rate in force is not billed.
"""

import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def first_of_month(day):
    return day.replace(day=1)


def next_month(day):
    month_start = first_of_month(day)
    if month_start.month == 12:
        return month_start.replace(year=month_start.year + 1, month=1)
    return month_start.replace(month=month_start.month + 1)


def rate_start_for(day):
    """The date a rent rate entered for ``day`` takes effect."""
    return day if day.day == 1 else next_month(day)


def month_starts(first_day, last_day):
    """The first day of every month from ``first_day``'s month to ``last_day``'s, inclusive."""
    month = first_of_month(first_day)
    while month <= last_day:
        yield month
        month = next_month(month)


@dataclass(frozen=True)
class MonthlyRent:
    month: date
    rent_due: Decimal
    paid: Decimal

    @property
    def balance(self):
        return max(self.rent_due - self.paid, Decimal(0))


def rate_in_force(rates, month):
    """The amount of the latest rate starting on or before ``month``, or None."""
    starts = [(start, amount) for start, amount in rates if start <= month]
    return max(starts)[1] if starts else None


def prorated(amount, tenancy_starts):
    days_in_month = calendar.monthrange(tenancy_starts.year, tenancy_starts.month)[1]
    days_lived = days_in_month - tenancy_starts.day + 1
    return (amount * days_lived / days_in_month).quantize(CENT, rounding=ROUND_HALF_UP)


def monthly_rent(*, tenancy_starts, tenancy_ends, rates, payments, today):
    """Bill a tenancy month by month.

    ``rates`` is an iterable of ``(start_date, amount)`` and ``payments`` an
    iterable of ``(month, amount)`` where ``month`` is the first day of the month
    the payment was for. Returns a list of MonthlyRent, oldest first.
    """
    rates = list(rates)
    paid_by_month = defaultdict(Decimal)
    for month, amount in payments:
        paid_by_month[month] += amount

    last_billed_day = min(tenancy_ends, today) if tenancy_ends else today
    statement = []
    for month in month_starts(tenancy_starts, last_billed_day):
        amount = rate_in_force(rates, month)
        if amount is None:
            continue
        is_first_month = month == first_of_month(tenancy_starts)
        rent_due = prorated(amount, tenancy_starts) if is_first_month else amount
        statement.append(MonthlyRent(month, rent_due, paid_by_month[month]))
    return statement
