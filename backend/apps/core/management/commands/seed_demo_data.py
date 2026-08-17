from datetime import date, time

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.computers.models import Computer
from apps.configuration.models import (
    BookingPolicy,
    OperatingSchedule,
    OperatingScheduleDay,
    OperatingWindow,
    ReportConfiguration,
    Shift,
    Weekday,
)
from apps.core.enums import DemoProfile

BASE_VALID_FROM = date(2025, 1, 1)


def ensure_regular_operating_schedule():
    schedule = (
        OperatingSchedule.objects.filter(
            schedule_type=OperatingSchedule.ScheduleType.REGULAR
        )
        .order_by("-valid_from", "-pk")
        .first()
    )
    if schedule is not None:
        return schedule

    schedule = OperatingSchedule.objects.create(
        schedule_type=OperatingSchedule.ScheduleType.REGULAR,
        valid_from=BASE_VALID_FROM,
        name="Horário regular da Sala de Informática",
        reason="Horário regular inicial do ambiente de demonstração.",
        created_by_profile=DemoProfile.SYSTEM_ADMIN,
    )
    for weekday in Weekday.values:
        is_open = weekday != Weekday.SUNDAY
        day, _ = OperatingScheduleDay.objects.update_or_create(
            schedule=schedule,
            weekday=weekday,
            defaults={"is_open": is_open},
        )
        if not is_open:
            day.windows.all().delete()
            continue
        window, _ = OperatingWindow.objects.update_or_create(
            schedule_day=day,
            display_order=0,
            defaults={
                "opens_at": time(7, 15),
                "closes_at": time(13) if weekday == Weekday.SATURDAY else time(21),
            },
        )
        day.windows.exclude(pk=window.pk).delete()
    return schedule


class Command(BaseCommand):
    help = "Cria os dados fictícios mínimos para executar o ambiente de demonstração."

    @transaction.atomic
    def handle(self, *args, **options):
        for number in range(1, 9):
            Computer.objects.get_or_create(
                code=f"PC-{number:02d}",
                defaults={
                    "description": "Computador da Sala de Informática",
                    "operational_state": Computer.OperationalState.AVAILABLE,
                    "notes": "Dado fictício do ambiente de demonstração.",
                },
            )

        if not Shift.objects.exists():
            shifts = [
                ("1º Turno", time(7, 15), time(13, 0), 1),
                ("2º Turno", time(13, 0), time(17, 0), 2),
                ("3º Turno", time(17, 0), time(21, 0), 3),
            ]
            for name, start_time, end_time, display_order in shifts:
                Shift.objects.create(
                    name=name,
                    start_time=start_time,
                    end_time=end_time,
                    display_order=display_order,
                    valid_from=BASE_VALID_FROM,
                )

        ensure_regular_operating_schedule()

        if not BookingPolicy.objects.exists():
            BookingPolicy.objects.create(
                cancellation_limit_minutes=0,
                max_future_reservations_per_user=1,
                valid_from=BASE_VALID_FROM,
            )

        if not ReportConfiguration.objects.filter(is_active=True).exists():
            ReportConfiguration.objects.create(is_active=True)

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Dados de demonstração disponíveis: 8 computadores, "
                    "3 turnos, 1 calendário semanal e configurações padrão."
                )
            )
        )
