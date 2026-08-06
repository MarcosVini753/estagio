from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.operations.services.deadlines import (
    expire_overdue_sessions,
    mark_overdue_reservations_as_no_show,
)


class Command(BaseCommand):
    help = "Reconcilia reservas não utilizadas e sessões com prazo expirado."

    def handle(self, *args, **options):
        now = timezone.now()
        expired_sessions = expire_overdue_sessions(now)
        no_shows = mark_overdue_reservations_as_no_show(now)
        self.stdout.write(
            self.style.SUCCESS(
                f"Reconciliação concluída: {expired_sessions} sessão(ões) "
                f"expirada(s) e {no_shows} reserva(s) sem comparecimento."
            )
        )
