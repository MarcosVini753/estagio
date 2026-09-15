import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.operations.services.deadlines import reconcile_deadlines

RECONCILE_INTERVAL_SECONDS = 60


class Command(BaseCommand):
    help = "Reconcilia reservas não utilizadas e sessões com prazo expirado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Repete a reconciliação a cada 60 segundos até ser interrompido.",
        )

    def handle(self, *args, **options):
        if options["watch"]:
            self.watch()
            return
        self.run_once()

    def run_once(self) -> None:
        result = reconcile_deadlines(now=timezone.now())
        self.stdout.write(
            self.style.SUCCESS(
                f"Reconciliação concluída: {result.expired_sessions} sessão(ões) "
                "expirada(s) e "
                f"{result.cancelled_reservations} reserva(s) cancelada(s) por prazo."
            )
        )

    def watch(self) -> None:
        """Executa a reconciliação continuamente, sobrevivendo a falhas.

        Falhas de uma rodada são registradas e repetidas no ciclo seguinte para
        que um erro transitório não encerre o processo periódico. A interrupção
        por sinal encerra o laço com o código de saída normal.
        """

        self.stdout.write(
            f"Reconciliação contínua a cada {RECONCILE_INTERVAL_SECONDS}s. "
            "Interrompa com Ctrl+C."
        )
        while True:
            try:
                self.run_once()
            except Exception as error:
                self.stderr.write(self.style.ERROR(f"Falha na reconciliação: {error}"))
            time.sleep(RECONCILE_INTERVAL_SECONDS)
