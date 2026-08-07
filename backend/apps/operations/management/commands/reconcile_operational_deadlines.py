from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.operations.services.deadlines import (
    cancel_overdue_reservations,
    expire_overdue_sessions,
)


class Command(BaseCommand):
    help = "Reconcilia reservas não utilizadas e sessões com prazo expirado."

    def handle(self, *args, **options):
        now = timezone.now()
        expired_sessions = expire_overdue_sessions(now)
        cancelled_reservations = cancel_overdue_reservations(now)
        self.stdout.write(
            self.style.SUCCESS(
                f"Reconciliação concluída: {expired_sessions} sessão(ões) "
                "expirada(s) e "
                f"{cancelled_reservations} reserva(s) cancelada(s) por prazo."
            )
        )
