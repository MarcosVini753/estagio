from datetime import datetime, time, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.computers.models import Computer
from apps.configuration.selectors import get_booking_policy_for_date
from apps.core.enums import AffiliationType, DemoProfile
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.rules import (
    LATE_CHECK_IN_TOLERANCE_MINUTES,
    LATE_CHECK_OUT_TOLERANCE_MINUTES,
)

E2E_USER_REFERENCE = "e2e-modal-user"


class Command(BaseCommand):
    help = (
        "Prepara dados determinísticos para o E2E do frontend. "
        "Use somente em banco descartável."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_demo_data", verbosity=0)

        UseSession.objects.filter(user_reference=E2E_USER_REFERENCE).delete()
        Reservation.objects.filter(user_reference=E2E_USER_REFERENCE).delete()

        now = timezone.now()
        session = UseSession.objects.create(
            user_reference=E2E_USER_REFERENCE,
            affiliation_type=AffiliationType.STUDENT,
            institutional_unit="Sistemas de Informação",
            started_at=now,
            planned_starts_at=now,
            planned_ends_at=now + timedelta(hours=2),
            exit_deadline_at=now
            + timedelta(
                hours=2,
                minutes=LATE_CHECK_OUT_TOLERANCE_MINUTES,
            ),
            status=UseSession.Status.ACTIVE,
            entry_recorded_by_profile=DemoProfile.ROOM_USER,
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=Computer.objects.get(code="PC-01"),
            sequence=1,
            started_at=now,
        )

        tomorrow = timezone.localdate() + timedelta(days=1)
        starts_at = timezone.make_aware(
            datetime.combine(tomorrow, time(10)),
            timezone.get_current_timezone(),
        )
        ends_at = starts_at + timedelta(minutes=15)
        Reservation.objects.create(
            user_reference=E2E_USER_REFERENCE,
            affiliation_type=AffiliationType.STUDENT,
            institutional_unit="Sistemas de Informação",
            computer=Computer.objects.get(code="PC-02"),
            booking_policy=get_booking_policy_for_date(tomorrow),
            starts_at=starts_at,
            ends_at=ends_at,
            check_in_deadline_at=starts_at
            + timedelta(minutes=LATE_CHECK_IN_TOLERANCE_MINUTES),
            exit_deadline_at=ends_at
            + timedelta(minutes=LATE_CHECK_OUT_TOLERANCE_MINUTES),
            status=Reservation.Status.CONFIRMED,
            created_by_profile=DemoProfile.ROOM_USER,
        )

        self.stdout.write(self.style.SUCCESS("Dados E2E de confirmação disponíveis."))
