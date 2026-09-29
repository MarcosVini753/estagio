from datetime import time, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.access.models import AccessAccount, LoginIdentifier
from apps.computers.models import Computer
from apps.configuration.models import OperatingSchedule, Shift, Weekday
from apps.configuration.services import replace_operating_schedule, replace_shift
from apps.core.enums import DemoProfile


class SeedDemoDataTest(TestCase):
    def run_seed(self):
        call_command("seed_demo_data", verbosity=0, stdout=StringIO())

    def regular_schedules(self):
        return OperatingSchedule.objects.filter(
            schedule_type=OperatingSchedule.ScheduleType.REGULAR
        )

    def test_reseed_preserves_replaced_regular_schedule_versions(self):
        self.run_seed()
        original = self.regular_schedules().get()
        effective_from = timezone.localdate() + timedelta(days=1)
        replacement = replace_operating_schedule(
            schedule_id=original.pk,
            effective_from=effective_from,
            actor_profile=DemoProfile.SYSTEM_ADMIN,
        )

        self.run_seed()

        original.refresh_from_db()
        replacement.refresh_from_db()
        self.assertEqual(self.regular_schedules().count(), 2)
        self.assertEqual(original.valid_until, effective_from - timedelta(days=1))
        self.assertEqual(replacement.valid_from, effective_from)
        self.assertIsNone(replacement.valid_until)

    def test_reseed_does_not_reopen_closed_regular_schedule(self):
        self.run_seed()
        schedule = self.regular_schedules().get()
        closed_on = timezone.localdate() - timedelta(days=1)
        schedule.valid_until = closed_on
        schedule.is_active = False
        schedule.save(update_fields=["valid_until", "is_active", "updated_at"])
        window = schedule.days.get(weekday=Weekday.MONDAY).windows.get()
        window.closes_at = time(12)
        window.save(update_fields=["closes_at", "updated_at"])

        self.run_seed()

        schedule.refresh_from_db()
        window.refresh_from_db()
        self.assertEqual(self.regular_schedules().count(), 1)
        self.assertEqual(schedule.valid_until, closed_on)
        self.assertFalse(schedule.is_active)
        self.assertEqual(window.closes_at, time(12))

    def test_reseed_preserves_existing_computer_configuration(self):
        self.run_seed()
        computer = Computer.objects.get(code="PC-01")
        computer.description = "Estação acessível"
        computer.operational_state = Computer.OperationalState.MAINTENANCE
        computer.notes = "Aguardando substituição do monitor."
        computer.save()

        self.run_seed()

        computer.refresh_from_db()
        self.assertEqual(computer.description, "Estação acessível")
        self.assertEqual(
            computer.operational_state,
            Computer.OperationalState.MAINTENANCE,
        )
        self.assertEqual(computer.notes, "Aguardando substituição do monitor.")

    def test_reseed_preserves_replaced_shift_versions(self):
        self.run_seed()
        original = Shift.objects.get(name="1º Turno")
        effective_from = timezone.localdate() + timedelta(days=1)
        replacement = replace_shift(
            shift_id=original.pk,
            effective_from=effective_from,
            name="1º Turno atualizado",
            start_time=time(7, 30),
            end_time=time(13),
            display_order=1,
            actor_profile=DemoProfile.SYSTEM_ADMIN,
        )

        self.run_seed()

        original.refresh_from_db()
        replacement.refresh_from_db()
        self.assertEqual(Shift.objects.count(), 4)
        self.assertEqual(original.valid_until, effective_from - timedelta(days=1))
        self.assertEqual(replacement.valid_from, effective_from)
        self.assertIsNone(replacement.valid_until)

    def test_reseed_does_not_restore_existing_shifts(self):
        self.run_seed()
        shift = Shift.objects.get(name="1º Turno")
        shift.name = "Turno matutino personalizado"
        shift.is_active = False
        shift.valid_until = timezone.localdate() - timedelta(days=1)
        shift.save()

        self.run_seed()

        shift.refresh_from_db()
        self.assertEqual(Shift.objects.count(), 3)
        self.assertEqual(shift.name, "Turno matutino personalizado")
        self.assertFalse(shift.is_active)
        self.assertEqual(
            shift.valid_until,
            timezone.localdate() - timedelta(days=1),
        )

    def test_seed_creates_three_demo_accounts_without_resetting_them(self):
        self.run_seed()
        accounts = AccessAccount.objects.select_related("user").order_by("profile")

        self.assertEqual(accounts.count(), 3)
        expected = {
            "99999999991": "ROOM_USER",
            "99999999992": "ROOM_MONITOR",
            "99999999993": "LIBRARY_SUPERVISOR",
        }
        for cpf, profile in expected.items():
            identifier = LoginIdentifier.objects.select_related("account__user").get(
                normalized_value=cpf
            )
            self.assertEqual(identifier.kind, LoginIdentifier.Kind.CPF)
            self.assertEqual(identifier.account.profile, profile)
            self.assertTrue(identifier.account.user.check_password("Senha123."))

        monitor = AccessAccount.objects.get(profile="ROOM_MONITOR")
        monitor.display_name = "Monitor personalizado"
        monitor.user.set_password("SenhaNova123!")
        monitor.user.save(update_fields=["password"])
        monitor.save(update_fields=["display_name"])
        self.run_seed()

        monitor.refresh_from_db()
        monitor.user.refresh_from_db()
        self.assertEqual(monitor.display_name, "Monitor personalizado")
        self.assertTrue(monitor.user.check_password("SenhaNova123!"))
        self.assertEqual(get_user_model().objects.count(), 3)

    @override_settings(DEMO_ACCOUNTS_ENABLED=False)
    def test_seed_does_not_create_demo_accounts_when_disabled(self):
        self.run_seed()

        self.assertEqual(AccessAccount.objects.count(), 0)
        self.assertEqual(Computer.objects.count(), 8)
