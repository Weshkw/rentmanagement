from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .billing import MonthlyRent, monthly_rent, rate_start_for
from .models import CustomUser, RentalProperty, RentalPropertyManager, RentalUnit
from .testing import (
    PASSWORD,
    create_landlord_with_property,
    create_tenant,
    create_unit,
    create_user,
    employ_manager,
)

JAN, FEB, MAR, APR = (date(2024, month, 1) for month in range(1, 5))


def bill(**overrides):
    arguments = {
        "tenancy_starts": JAN,
        "tenancy_ends": None,
        "rates": [(JAN, Decimal("10000"))],
        "payments": [],
        "today": date(2024, 3, 15),
    }
    arguments.update(overrides)
    return monthly_rent(**arguments)


class BillingRuleTests(SimpleTestCase):
    def test_every_month_up_to_today_is_billed(self):
        self.assertEqual([line.month for line in bill()], [JAN, FEB, MAR])

    def test_first_month_is_prorated_by_days_lived(self):
        first = bill(tenancy_starts=date(2024, 1, 22))[0]

        # 10 of January's 31 days: 10000 * 10 / 31
        self.assertEqual(first.rent_due, Decimal("3225.81"))

    def test_rate_changes_apply_from_their_start_month(self):
        rates = [(JAN, Decimal("10000")), (MAR, Decimal("12000"))]

        dues = [line.rent_due for line in bill(rates=rates)]

        self.assertEqual(dues, [Decimal("10000"), Decimal("10000"), Decimal("12000")])

    def test_payments_count_towards_the_month_they_were_for(self):
        statement = bill(payments=[(FEB, Decimal("4000")), (FEB, Decimal("6000"))])

        self.assertEqual([line.balance for line in statement], [10000, 0, 10000])

    def test_overpaying_one_month_does_not_reduce_another(self):
        statement = bill(payments=[(JAN, Decimal("15000"))])

        self.assertEqual(statement[0].balance, 0)
        self.assertEqual(statement[1].balance, Decimal("10000"))

    def test_billing_stops_at_the_end_of_the_tenancy(self):
        self.assertEqual([line.month for line in bill(tenancy_ends=date(2024, 2, 10))], [JAN, FEB])

    def test_a_future_end_date_does_not_bill_months_not_yet_reached(self):
        self.assertEqual([line.month for line in bill(tenancy_ends=date(2025, 6, 30))][-1], MAR)

    def test_months_without_a_rate_are_not_billed(self):
        self.assertEqual([line.month for line in bill(rates=[(FEB, Decimal("9000"))])], [FEB, MAR])

    def test_a_tenancy_starting_in_the_future_owes_nothing(self):
        self.assertEqual(bill(tenancy_starts=APR), [])

    def test_rates_entered_mid_month_start_the_next_month(self):
        self.assertEqual(rate_start_for(date(2024, 1, 15)), FEB)
        self.assertEqual(rate_start_for(date(2024, 12, 2)), date(2025, 1, 1))
        self.assertEqual(rate_start_for(FEB), FEB)

    def test_balance_is_never_negative(self):
        self.assertEqual(MonthlyRent(JAN, Decimal(100), Decimal(300)).balance, 0)


class RegistrationAndLoginTests(TestCase):
    def test_registration_creates_landlord_and_property_and_signs_in(self):
        response = self.client.post(
            reverse("register_landlord"),
            {
                "full_name": "Amina Odhiambo",
                "phone_number": "0711000111",
                "password": PASSWORD,
                "password2": PASSWORD,
                "property_name": "Garden Flats",
                "location": "Kisumu",
            },
        )

        self.assertRedirects(response, reverse("property_list"))
        user = CustomUser.objects.get(phone_number="0711000111")
        self.assertEqual(user.landlord.properties.get().name, "Garden Flats")
        self.assertTrue(user.check_password(PASSWORD))

    def test_registration_rejects_a_phone_number_in_use(self):
        create_user("0711000111")

        response = self.client.post(reverse("register_landlord"), {"phone_number": "0711000111"})

        self.assertTrue(response.context["form"].has_error("phone_number"))

    def test_login_with_phone_number_routes_by_role(self):
        create_landlord_with_property("0700000001")
        employ_manager(create_landlord_with_property("0700000002")[1], "0700000003")

        for phone_number, expected in [
            ("0700000001", reverse("landlord_dashboard")),
            ("0700000003", reverse("propertymanagement:management_home")),
        ]:
            with self.subTest(phone_number=phone_number):
                self.client.post(reverse("login"), {"username": phone_number, "password": PASSWORD})
                self.assertRedirects(self.client.get(reverse("dashboard")), expected)
                self.client.post(reverse("logout"))


class LandlordIsolationTests(TestCase):
    """A landlord can never reach another landlord's records."""

    def setUp(self):
        self.landlord, self.own_property = create_landlord_with_property("0700000001")
        _, self.other_property = create_landlord_with_property("0700000002", "Other Court")
        self.other_unit = create_unit(self.other_property)
        self.client.force_login(self.landlord.user)

    def test_other_landlords_pages_are_not_found(self):
        urls = [
            reverse("property_edit", args=[self.other_property.pk]),
            reverse("property_delete", args=[self.other_property.pk]),
            reverse("property_units", args=[self.other_property.pk]),
            reverse("unit_create", args=[self.other_property.pk]),
            reverse("unit_edit", args=[self.other_unit.pk]),
            reverse("unit_delete", args=[self.other_unit.pk]),
            reverse("rent_rates", args=[self.other_unit.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(RentalProperty.objects.filter(pk=self.other_property.pk).exists())
        self.assertTrue(RentalUnit.objects.filter(pk=self.other_unit.pk).exists())

    def test_dashboards_only_show_own_properties(self):
        for name in ["landlord_dashboard", "property_list"]:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, "Sunrise Court")
                self.assertNotContains(response, "Other Court")

    def test_cannot_employ_a_manager_for_another_landlords_property(self):
        response = self.client.post(
            reverse("managers"),
            {
                "property_managed": self.other_property.pk,
                "full_name": "Sneaky",
                "phone_number": "0799999999",
                "national_id_number": "1",
                "management_start_date": "2024-01-01",
            },
        )

        self.assertTrue(response.context["form"].has_error("property_managed"))
        self.assertFalse(RentalPropertyManager.objects.exists())

    def test_landlord_pages_are_forbidden_to_users_who_are_not_landlords(self):
        self.client.force_login(create_user("0700000009"))

        self.assertEqual(self.client.get(reverse("property_list")).status_code, 403)

    def test_landlord_pages_require_login(self):
        self.client.logout()
        url = reverse("property_list")

        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")


class PropertyManagementTests(TestCase):
    def setUp(self):
        self.landlord, self.rental_property = create_landlord_with_property("0700000001")
        self.client.force_login(self.landlord.user)

    def test_adding_a_unit_sets_its_first_rent(self):
        self.client.post(
            reverse("unit_create", args=[self.rental_property.pk]),
            {"unit_identity": "B2", "rent_rate": "8500", "start_date": "2024-03-01"},
        )

        unit = self.rental_property.units.get()
        self.assertEqual(unit.rent_rates.get().rent_rate, Decimal("8500.00"))

    def test_unit_names_are_unique_within_a_property(self):
        create_unit(self.rental_property, "A1")

        response = self.client.post(
            reverse("unit_create", args=[self.rental_property.pk]),
            {"unit_identity": "a1", "rent_rate": "8500", "start_date": "2024-03-01"},
        )

        self.assertTrue(response.context["form"].has_error("unit_identity"))

    def test_a_mid_month_rent_rate_starts_next_month(self):
        unit = create_unit(self.rental_property)

        self.client.post(
            reverse("rent_rates", args=[unit.pk]),
            {"rent_rate": "11000", "start_date": "2024-05-15"},
        )

        self.assertEqual(unit.rent_rates.last().start_date, date(2024, 6, 1))

    def test_only_one_rent_rate_per_month(self):
        unit = create_unit(self.rental_property, rent_from=date(2024, 1, 1))

        response = self.client.post(
            reverse("rent_rates", args=[unit.pk]),
            {"rent_rate": "11000", "start_date": "2024-01-01"},
        )

        self.assertTrue(response.context["form"].has_error("start_date"))

    def test_employing_a_new_manager_creates_an_account_they_can_sign_in_to(self):
        response = self.client.post(
            reverse("managers"),
            {
                "property_managed": self.rental_property.pk,
                "full_name": "Brian Mwangi",
                "phone_number": "0722000222",
                "national_id_number": "30111222",
                "management_start_date": "2024-01-01",
            },
            follow=True,
        )

        message = str(list(response.context["messages"])[0])
        temporary_password = message.rsplit("temporary password ", 1)[1].split(" ")[0]
        self.assertNotEqual(temporary_password, "30111222")
        self.assertTrue(
            CustomUser.objects.get(phone_number="0722000222").check_password(temporary_password)
        )

    def test_employing_an_existing_user_reuses_their_account(self):
        existing = create_user("0722000222", "Brian Mwangi")

        self.client.post(
            reverse("managers"),
            {
                "property_managed": self.rental_property.pk,
                "full_name": "Ignored",
                "phone_number": "0722000222",
                "national_id_number": "30111222",
                "management_start_date": "2024-01-01",
            },
        )

        self.assertEqual(RentalPropertyManager.objects.get().user, existing)
        self.assertTrue(existing.check_password(PASSWORD))

    def test_ending_employment_keeps_the_record_but_removes_access(self):
        manager = employ_manager(self.rental_property, "0722000222")

        self.client.post(reverse("manager_end", args=[manager.pk]))

        manager.refresh_from_db()
        self.assertIsNotNone(manager.management_end_date)
        self.client.force_login(manager.user)
        response = self.client.get(reverse("propertymanagement:management_home"))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_totals_for_a_month(self):
        unit = create_unit(self.rental_property, rent="10000")
        tenant = create_tenant(unit, starts=date(2024, 1, 1))
        tenant.payments.create(
            amount_paid=Decimal("6000"),
            date_paid=date(2024, 3, 2),
            intended_payment_month=2,
            intended_payment_year=2024,
        )

        response = self.client.get(reverse("landlord_dashboard"), {"month": "2024-02"})

        summary = response.context["summaries"][0]
        self.assertEqual(summary.occupied_units, 1)
        self.assertEqual(summary.paid_for_month, Decimal("6000"))
        self.assertEqual(summary.paid_in_month, 0)
        self.assertEqual(summary.balance_for_month, Decimal("4000"))

    def test_deleting_a_property_requires_confirmation(self):
        url = reverse("property_delete", args=[self.rental_property.pk])

        self.assertContains(self.client.get(url), "Delete Sunrise Court?")
        self.assertRedirects(self.client.post(url), reverse("property_list"))
        self.assertFalse(RentalProperty.objects.exists())


class AdminTests(TestCase):
    def test_user_admin_pages_work_with_phone_number_accounts(self):
        admin_user = CustomUser.objects.create_superuser("0700000000", PASSWORD, full_name="Admin")
        self.client.force_login(admin_user)

        for url in [
            reverse("admin:rentsolutions_customuser_changelist"),
            reverse("admin:rentsolutions_customuser_add"),
            reverse("admin:rentsolutions_customuser_change", args=[admin_user.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

        response = self.client.post(
            reverse("admin:rentsolutions_customuser_add"),
            {
                "phone_number": "0733000333",
                "full_name": "New Staff",
                "password1": PASSWORD,
                "password2": PASSWORD,
                "usable_password": "true",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomUser.objects.get(phone_number="0733000333").check_password(PASSWORD))
