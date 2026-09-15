from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.operations.models import ComputerAllocation, Reservation, UseSession


class SeedFrontendE2EDataTest(TestCase):
    def run_seed(self):
        call_command(
            "seed_frontend_e2e_data",
            verbosity=0,
            stdout=StringIO(),
        )

    def test_creates_idempotent_modal_fixtures_without_changing_demo_seed_contract(
        self,
    ):
        self.run_seed()

        session = UseSession.objects.get(user_reference="e2e-modal-user")
        self.assertEqual(session.status, UseSession.Status.ACTIVE)
        self.assertEqual(session.allocations.count(), 1)
        self.assertTrue(
            Reservation.objects.filter(
                user_reference="e2e-modal-user",
                status=Reservation.Status.CONFIRMED,
            ).exists()
        )

        self.run_seed()

        self.assertEqual(
            UseSession.objects.filter(user_reference="e2e-modal-user").count(),
            1,
        )
        self.assertEqual(
            ComputerAllocation.objects.filter(
                session__user_reference="e2e-modal-user"
            ).count(),
            1,
        )
        self.assertEqual(
            Reservation.objects.filter(user_reference="e2e-modal-user").count(),
            1,
        )
