from datetime import datetime, time, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.computers.models import Computer
from apps.core.enums import AffiliationType, DemoProfile
from apps.operations.models import Reservation, UseSession
from apps.operations.services import (
    create_reservation,
    start_usage_session,
)

E2E_USER_REFERENCE = "e2e-modal-user"


@transaction.atomic
def seed_frontend_e2e_data(*, now: datetime) -> None:
    """Cria o cenário descartável usando as mesmas regras da aplicação."""

    UseSession.objects.filter(user_reference=E2E_USER_REFERENCE).delete()
    Reservation.objects.filter(user_reference=E2E_USER_REFERENCE).delete()

    start_usage_session(
        computer_id=Computer.objects.get(code="PC-01").pk,
        planned_ends_at=timezone.make_aware(
            datetime.combine(timezone.localdate(now), time(10)),
            timezone.get_current_timezone(),
        ),
        actor_profile=DemoProfile.ROOM_USER,
        actor_reference=E2E_USER_REFERENCE,
        affiliation_type=AffiliationType.STUDENT,
        institutional_unit="Sistemas de Informação",
        now=now,
    )

    tomorrow = timezone.localdate(now) + timedelta(days=1)
    starts_at = timezone.make_aware(
        datetime.combine(tomorrow, time(10)),
        timezone.get_current_timezone(),
    )
    create_reservation(
        computer_id=Computer.objects.get(code="PC-02").pk,
        starts_at=starts_at,
        slot_count=1,
        user_reference=E2E_USER_REFERENCE,
        affiliation_type=AffiliationType.STUDENT,
        institutional_unit="Sistemas de Informação",
        created_by_profile=DemoProfile.ROOM_USER,
        now=now,
    )


class Command(BaseCommand):
    help = (
        "Prepara dados determinísticos para o E2E do frontend. "
        "Use somente em banco descartável."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--at",
            help=(
                "Instante ISO usado pelo cenário. Útil somente quando a aplicação "
                "também executa com o mesmo relógio controlado."
            ),
        )

    def handle(self, *args, **options):
        call_command("seed_demo_data", verbosity=0)
        current = timezone.now()
        if options["at"]:
            try:
                current = datetime.fromisoformat(options["at"])
            except ValueError as error:
                raise CommandError("--at deve ser um instante ISO válido.") from error
            if timezone.is_naive(current):
                current = timezone.make_aware(
                    current,
                    timezone.get_current_timezone(),
                )
        seed_frontend_e2e_data(now=current)

        self.stdout.write(self.style.SUCCESS("Dados E2E de confirmação disponíveis."))
