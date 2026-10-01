from datetime import date, timedelta
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from rentsolutions.models import RentPayment
from rentsolutions.testing import (
    create_landlord_with_property,
    create_tenant,
    create_unit,
    employ_manager,
)


class ManagerAccessTests(TestCase):
    """Managers reach the properties they run, and nothing else."""

    def setUp(self):
        _, self.managed_property = create_landlord_with_property("0700000001")
        _, self.other_property = create_landlord_with_property("0700000002", "Other Court")
        self.manager = employ_manager(self.managed_property, "0700000003")
        self.client.force_login(self.manager.user)

        self.other_unit = create_unit(self.other_property)
        self.other_tenant = create_tenant(self.other_unit)
        self.other_payment = self.other_tenant.payments.create(
            amount_paid=Decimal("100"),
            date_paid=date(2024, 1, 5),
            intended_payment_month=1,
            intended_payment_year=2024,
        )

    def test_other_properties_records_are_not_found(self):
        urls = [
            reverse("propertymanagement:unit_detail", args=[self.other_unit.pk]),
            reverse("propertymanagement:tenant_create", args=[self.other_unit.pk]),
            reverse("propertymanagement:tenant_detail", args=[self.other_tenant.pk]),
            reverse("propertymanagement:tenant_edit", args=[self.other_tenant.pk]),
            reverse("propertymanagement:tenant_end", args=[self.other_tenant.pk]),
            reverse("propertymanagement:collect_rent", args=[self.other_tenant.pk]),
            reverse("propertymanagement:payment_edit", args=[self.other_payment.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url).status_code, 404)

    def test_management_home_lists_only_managed_properties(self):
        response = self.client.get(reverse("propertymanagement:management_home"))

        self.assertContains(response, "Sunrise Court")
        self.assertNotContains(response, "Other Court")

    def test_managers_cannot_use_landlord_pages(self):
        self.assertEqual(self.client.get(reverse("property_list")).status_code, 403)

    def test_a_manager_whose_employment_has_not_started_has_no_access(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        future_manager = employ_manager(self.managed_property, "0700000004", starts=tomorrow)
        self.client.force_login(future_manager.user)

        response = self.client.get(reverse("propertymanagement:management_home"))

        self.assertEqual(response.status_code, 403)


class TenancyAndRentTests(TestCase):
    def setUp(self):
        landlord, rental_property = create_landlord_with_property("0700000001")
        self.unit = create_unit(rental_property, rent="10000", rent_from=date(2024, 1, 1))
        self.client.force_login(landlord.user)

    def test_adding_a_tenant_occupies_the_unit(self):
        self.client.post(
            reverse("propertymanagement:tenant_create", args=[self.unit.pk]),
            {"tenant_name": "Jane Tenant", "date_tenancy_starts": "2024-01-01"},
        )

        self.assertEqual(self.unit.current_tenant.tenant_name, "Jane Tenant")

    def test_overlapping_tenancies_are_rejected(self):
        create_tenant(self.unit, starts=date(2024, 1, 1))

        response = self.client.post(
            reverse("propertymanagement:tenant_create", args=[self.unit.pk]),
            {"tenant_name": "Second Tenant", "date_tenancy_starts": "2024-06-01"},
        )

        self.assertFalse(response.context["form"].is_valid())
        self.assertEqual(self.unit.tenants.count(), 1)

    def test_tenancy_cannot_end_before_it_starts(self):
        response = self.client.post(
            reverse("propertymanagement:tenant_create", args=[self.unit.pk]),
            {
                "tenant_name": "Jane",
                "date_tenancy_starts": "2024-05-01",
                "date_tenancy_ends": "2024-04-01",
            },
        )

        self.assertTrue(response.context["form"].has_error("date_tenancy_ends"))

    def test_recording_rent_reduces_the_balance(self):
        tenant = create_tenant(self.unit, starts=date(2024, 1, 1), ends=date(2024, 2, 29))

        self.client.post(
            reverse("propertymanagement:collect_rent", args=[tenant.pk]),
            {
                "amount_paid": "10000",
                "date_paid": "2024-01-03",
                "intended_payment_month": "1",
                "intended_payment_year": "2024",
            },
        )

        response = self.client.get(reverse("propertymanagement:tenant_detail", args=[tenant.pk]))
        self.assertEqual(response.context["total_balance"], Decimal("10000"))
        self.assertEqual(RentPayment.objects.get().period, date(2024, 1, 1))

    def test_ending_a_tenancy_keeps_history_and_frees_the_unit(self):
        tenant = create_tenant(self.unit, starts=date(2024, 1, 1))
        yesterday = timezone.localdate() - timedelta(days=1)

        self.client.post(
            reverse("propertymanagement:tenant_end", args=[tenant.pk]),
            {"date_tenancy_ends": yesterday.isoformat()},
        )

        tenant.refresh_from_db()
        self.assertEqual(tenant.date_tenancy_ends, yesterday)
        self.assertIsNone(self.unit.current_tenant)

    def test_unit_notes_require_a_csrf_token(self):
        url = reverse("propertymanagement:unit_detail", args=[self.unit.pk])
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.unit.property_with_rental_unit.landlord.user)

        self.assertEqual(csrf_client.post(url, {"unit_notes": "Leaking tap"}).status_code, 403)

        self.client.post(url, {"unit_notes": "Leaking tap"})
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.unit_notes, "Leaking tap")

    def test_management_home_uses_a_fixed_number_of_queries(self):
        for name in ["B1", "B2", "B3"]:
            tenant = create_tenant(create_unit(self.unit.property_with_rental_unit, name))
            tenant.payments.create(
                amount_paid=Decimal("1"),
                date_paid=date(2024, 1, 1),
                intended_payment_month=1,
                intended_payment_year=2024,
            )

        # session, user, landlord role, manager role, properties, units, rates, tenants,
        # payments, active managers - however many units and tenants exist.
        with self.assertNumQueries(10):
            self.client.get(reverse("propertymanagement:management_home"))
