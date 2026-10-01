# RentEasy – rent management for landlords

A web app that helps landlords run rental properties. Landlords set up their
properties, units and rent, and employ managers; managers move tenants in and
out and record rent as it is paid. Everyone sees accurate balances, month by
month. Built with Django.

## Features

**Landlords**

- Register with a phone number and a first property; add more properties and
  units at any time.
- Keep a rent history per unit – a new rate applies from the first of its month.
- See each property's occupancy, rent received, rent paid for the month and
  outstanding balances for any month.
- Employ managers per property (a new manager gets an account with a temporary
  password) and end their employment, which removes their access straight away.

**Managers** (and landlords, for their own properties)

- Move tenants in and end tenancies; overlapping tenancies are refused.
- Record rent payments against the month they are for, and correct them later.
- See each tenant's month-by-month statement and outstanding balance.
- Keep notes on each unit.

## How balances are worked out

The rules live in [`rentsolutions/billing.py`](rentsolutions/billing.py) as pure
functions with their own tests:

- the rent in force each month is the latest rate starting on or before it;
- the first month of a tenancy is prorated by the days lived there;
- rent is billed up to the end of the tenancy, or the current month;
- a payment counts towards the month it was made for.

## Access control

Landlords only ever see their own properties, and managers only the properties
they currently manage. Every view loads records through the scoped querysets in
[`rentsolutions/access.py`](rentsolutions/access.py), so a link to anyone else's
property, unit, tenant or payment returns *404 Not Found*.

## Project layout

| Path | What it holds |
| --- | --- |
| `rentsolutions/` | Accounts, properties, units, rent rates, managers and the landlord pages |
| `rentsolutions/billing.py` | Rent and balance rules |
| `rentsolutions/access.py` | Role checks and the per-user querysets every view uses |
| `rentsolutions/reports.py` | Monthly figures per property, computed in a fixed number of queries |
| `propertymanagement/` | Day-to-day pages: tenants, rent collection, payments and unit notes |
| `templates/` | Shared layout, form and confirmation pages |

## Getting started

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py runserver
```

Open http://localhost:8000/ and register as a landlord. Run
`python manage.py createsuperuser` for access to the Django admin.

## Configuration

Settings are read from environment variables. With none set, the app runs in
local development mode on SQLite. See [`.env.example`](.env.example) for the
full list, including the `DB_*` variables for MySQL or another database. The app
refuses to start with debug off and no secret key.

## Development

```bash
ruff check .               # lint
ruff format .              # format
python manage.py test      # run the test suite
```

The same checks run on every push through GitHub Actions.
