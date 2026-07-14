from datetime import date, time

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.computers.models import Computer
from apps.configuration.models import BookingPolicy, ReportConfiguration, Shift

BASE_VALID_FROM = date(2025, 1, 1)


class Command(BaseCommand):
    help = "Cria os dados fictícios mínimos para executar o ambiente de demonstração."

    @transaction.atomic
    def handle(self, *args, **options):
        for number in range(1, 9):
            Computer.objects.update_or_create(
                code=f"PC-{number:02d}",
                defaults={
                    "description": "Computador da Sala de Informática",
                    "operational_state": Computer.OperationalState.AVAILABLE,
                    "notes": "Dado fictício do ambiente de demonstração.",
                },
            )

        shifts = [
            ("1º Turno", time(7, 15), time(13, 0), 1),
            ("2º Turno", time(13, 0), time(17, 0), 2),
            ("3º Turno", time(17, 0), time(21, 0), 3),
        ]
        for name, start_time, end_time, display_order in shifts:
            Shift.objects.update_or_create(
                name=name,
                valid_from=BASE_VALID_FROM,
                defaults={
                    "start_time": start_time,
                    "end_time": end_time,
                    "display_order": display_order,
                    "valid_until": None,
                    "is_active": True,
                },
            )

        if not BookingPolicy.objects.filter(is_active=True).exists():
            BookingPolicy.objects.create(
                slot_duration_minutes=60,
                check_in_tolerance_minutes=15,
                cancellation_limit_minutes=0,
                max_future_reservations_per_user=1,
                valid_from=BASE_VALID_FROM,
                is_active=True,
            )

        if not ReportConfiguration.objects.filter(is_active=True).exists():
            ReportConfiguration.objects.create(is_active=True)

        self.stdout.write(
            self.style.SUCCESS(
                "Dados de demonstração disponíveis: 8 computadores, 3 turnos e configurações padrão."
            )
        )
