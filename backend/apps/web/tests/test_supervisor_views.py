from datetime import datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.computers.models import Computer
from apps.configuration.models import (
    BookingPolicy,
    CalendarException,
    OperatingSchedule,
    ReportConfiguration,
    RoomNotice,
    Shift,
    Weekday,
)
from apps.configuration.tests.factories import create_operating_schedule
from apps.occurrences.models import Occurrence
from apps.operations.models import Reservation
from apps.operations.tests.factories import create_reservation, create_use_session


class LibrarySupervisorWebTest(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)
        self.computer = Computer.objects.create(
            code="PC-01",
            asset_number="UFAC-001",
            description="Computador 01",
        )
        OperatingSchedule.objects.all().delete()
        create_operating_schedule(
            valid_from=self.today.replace(day=1) - timedelta(days=1),
            weekday_windows={
                weekday: [(time(7), time(22))] for weekday in Weekday.values
            },
        )
        BookingPolicy.objects.create(valid_from=self.today - timedelta(days=1))

    def aware(self, target_date, target_time):
        return timezone.make_aware(
            datetime.combine(target_date, target_time),
            timezone.get_current_timezone(),
        )

    def select_supervisor(self):
        response = self.client.post("/", {"profile": "LIBRARY_SUPERVISOR"})
        self.assertRedirects(response, "/supervisor/")

    def weekly_windows(self, value="08:00-12:00,13:00-18:00"):
        return {f"windows_{weekday}": value for weekday in Weekday.values}

    def test_supervisor_area_requires_management_profile(self):
        anonymous = self.client.get("/supervisor/")
        self.assertRedirects(anonymous, "/")

        self.client.post("/", {"profile": "ROOM_MONITOR"})
        monitor = self.client.get("/supervisor/")
        self.assertRedirects(monitor, "/")

    def test_supervisor_can_create_and_edit_computer_inventory(self):
        self.select_supervisor()

        created = self.client.post(
            "/supervisor/computadores/",
            {
                "code": "PC-02",
                "asset_number": "UFAC-002",
                "description": "Computador acessível",
                "operational_state": Computer.OperationalState.AVAILABLE,
                "notes": "Mesa com maior espaço.",
            },
        )
        computer = Computer.objects.get(code="PC-02")
        updated = self.client.post(
            f"/supervisor/computadores/{computer.pk}/editar/",
            {
                "code": "PC-02",
                "asset_number": "UFAC-002",
                "description": "Computador acessível atualizado",
                "notes": "Próximo à entrada.",
            },
        )

        self.assertRedirects(created, "/supervisor/computadores/")
        self.assertRedirects(updated, "/supervisor/computadores/")
        computer.refresh_from_db()
        self.assertEqual(computer.description, "Computador acessível atualizado")
        page = self.client.get("/supervisor/computadores/?q=acessível")
        self.assertContains(page, "PC-02")
        self.assertContains(page, "Próximo à entrada")

    def test_supervisor_manages_shifts_without_changing_calendar(self):
        self.select_supervisor()
        schedule_count = OperatingSchedule.objects.count()

        created = self.client.post(
            "/supervisor/turnos/",
            {
                "name": "Manhã",
                "start_time": "07:00",
                "end_time": "13:00",
                "display_order": 1,
                "valid_from": self.today.isoformat(),
                "is_active": "on",
            },
        )
        shift = Shift.objects.get(name="Manhã")
        replacement_date = self.today + timedelta(days=7)
        replaced = self.client.post(
            f"/supervisor/turnos/{shift.pk}/substituir/",
            {
                "effective_from": replacement_date.isoformat(),
                "name": "Manhã estendida",
                "start_time": "07:00",
                "end_time": "14:00",
                "display_order": 1,
            },
        )

        self.assertRedirects(created, "/supervisor/funcionamento/?section=shifts")
        self.assertRedirects(replaced, "/supervisor/funcionamento/?section=shifts")
        shift.refresh_from_db()
        self.assertEqual(shift.valid_until, replacement_date - timedelta(days=1))
        self.assertTrue(
            Shift.objects.filter(
                series_key=shift.series_key,
                name="Manhã estendida",
                valid_from=replacement_date,
            ).exists()
        )
        self.assertEqual(OperatingSchedule.objects.count(), schedule_count)

    def test_schedule_requires_matching_preview_before_creation(self):
        self.select_supervisor()
        payload = {
            "name": "Semana de treinamento",
            "schedule_type": OperatingSchedule.ScheduleType.TEMPORARY,
            "valid_from": self.tomorrow.isoformat(),
            "valid_until": (self.tomorrow + timedelta(days=2)).isoformat(),
            "reason": "Treinamento da equipe",
            **self.weekly_windows("09:00-17:00"),
        }

        without_preview = self.client.post(
            "/supervisor/calendarios/novo/",
            {**payload, "intent": "apply"},
        )
        self.assertEqual(without_preview.status_code, 400)
        self.assertContains(
            without_preview,
            "Visualize o impacto",
            status_code=400,
        )

        preview = self.client.post(
            "/supervisor/calendarios/novo/",
            {**payload, "intent": "preview"},
        )
        self.assertEqual(preview.status_code, 200)
        self.assertContains(preview, "Nenhuma reserva será cancelada")
        self.assertFalse(
            OperatingSchedule.objects.filter(name="Semana de treinamento").exists()
        )

        applied = self.client.post(
            "/supervisor/calendarios/novo/",
            {**payload, "intent": "apply"},
        )
        self.assertRedirects(
            applied,
            "/supervisor/funcionamento/?section=schedules",
        )
        self.assertTrue(
            OperatingSchedule.objects.filter(name="Semana de treinamento").exists()
        )

    def test_schedule_preview_cannot_confirm_a_changed_proposal(self):
        self.select_supervisor()
        payload = {
            "name": "Horário temporário",
            "schedule_type": OperatingSchedule.ScheduleType.TEMPORARY,
            "valid_from": self.tomorrow.isoformat(),
            "valid_until": (self.tomorrow + timedelta(days=1)).isoformat(),
            "reason": "Atividade interna",
            **self.weekly_windows("09:00-17:00"),
        }
        self.client.post(
            "/supervisor/calendarios/novo/",
            {**payload, "intent": "preview"},
        )

        changed = self.client.post(
            "/supervisor/calendarios/novo/",
            {
                **payload,
                "intent": "apply",
                "windows_0": "10:00-17:00",
            },
        )

        self.assertEqual(changed.status_code, 400)
        self.assertContains(changed, "proposta foi alterada", status_code=400)
        self.assertFalse(
            OperatingSchedule.objects.filter(name="Horário temporário").exists()
        )

    def test_new_conflict_after_preview_requires_a_fresh_confirmation(self):
        self.select_supervisor()
        payload = {
            "name": "Horário reduzido",
            "schedule_type": OperatingSchedule.ScheduleType.TEMPORARY,
            "valid_from": self.tomorrow.isoformat(),
            "valid_until": self.tomorrow.isoformat(),
            "reason": "Atividade interna",
            **self.weekly_windows("09:00-17:00"),
        }
        preview = self.client.post(
            "/supervisor/calendarios/novo/",
            {**payload, "intent": "preview"},
        )
        self.assertContains(preview, "Nenhuma reserva será cancelada")

        reservation = create_reservation(
            user_reference="aluno-conflito-novo",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(8)),
            ends_at=self.aware(self.tomorrow, time(9)),
            created_by_profile="ROOM_USER",
        )
        applied = self.client.post(
            "/supervisor/calendarios/novo/",
            {**payload, "intent": "apply"},
        )

        self.assertEqual(applied.status_code, 409)
        self.assertContains(applied, "impacto mudou", status_code=409)
        self.assertContains(applied, f"Reserva #{reservation.pk}", status_code=409)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
        self.assertFalse(
            OperatingSchedule.objects.filter(name="Horário reduzido").exists()
        )

    def test_used_shift_can_be_deactivated_without_editing_history(self):
        self.select_supervisor()
        shift = Shift.objects.create(
            name="Noite",
            start_time=time(18),
            end_time=time(22),
            valid_from=self.today - timedelta(days=5),
        )
        create_use_session(
            user_reference="aluno-turno",
            start_shift=shift,
            started_at=self.aware(self.today, time(18)),
            planned_starts_at=self.aware(self.today, time(18)),
            planned_ends_at=self.aware(self.today, time(19)),
            exit_deadline_at=self.aware(self.today, time(19, 3)),
            ended_at=self.aware(self.today, time(19)),
            status="FINISHED",
            entry_recorded_by_profile="ROOM_MONITOR",
            exit_recorded_by_profile="ROOM_MONITOR",
        )

        page = self.client.get("/supervisor/funcionamento/?section=shifts")
        response = self.client.post(
            f"/supervisor/turnos/{shift.pk}/editar/",
            {},
        )

        self.assertContains(page, "Apenas a desativação é permitida")
        self.assertRedirects(
            response,
            "/supervisor/funcionamento/?section=shifts",
        )
        shift.refresh_from_db()
        self.assertFalse(shift.is_active)

    def test_exception_preview_and_confirmation_cancel_affected_booking(self):
        self.select_supervisor()
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(9)),
            ends_at=self.aware(self.tomorrow, time(10)),
            created_by_profile="ROOM_USER",
        )
        payload = {
            "date": self.tomorrow.isoformat(),
            "exception_type": CalendarException.ExceptionType.CLOSED,
            "description": "Manutenção elétrica programada",
        }

        preview = self.client.post(
            "/supervisor/excecoes/",
            {**payload, "intent": "preview"},
        )
        self.assertContains(preview, "1 reserva será cancelada")
        self.assertFalse(CalendarException.objects.filter(date=self.tomorrow).exists())

        applied = self.client.post(
            "/supervisor/excecoes/",
            {**payload, "intent": "apply", "confirm_cancellation": "on"},
        )

        self.assertRedirects(
            applied,
            "/supervisor/funcionamento/?section=exceptions",
        )
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CANCELLED)
        self.assertTrue(CalendarException.objects.filter(date=self.tomorrow).exists())

    def test_exception_preview_rejects_past_date(self):
        self.select_supervisor()
        past_date = self.today - timedelta(days=1)

        response = self.client.post(
            "/supervisor/excecoes/",
            {
                "date": past_date.isoformat(),
                "exception_type": CalendarException.ExceptionType.CLOSED,
                "description": "Tentativa retroativa",
                "intent": "preview",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Exceções de calendário só podem ser criadas ou alteradas para hoje",
            status_code=400,
        )
        self.assertFalse(CalendarException.objects.filter(date=past_date).exists())

    def test_supervisor_publishes_and_deactivates_notices(self):
        self.select_supervisor()
        visible_from = timezone.localtime().replace(second=0, microsecond=0)
        created = self.client.post(
            "/supervisor/avisos/",
            {
                "notice_type": RoomNotice.NoticeType.SPECIAL_HOURS,
                "title": "Atendimento especial",
                "message": "A sala abrirá às 9h.",
                "effective_from": self.tomorrow.isoformat(),
                "effective_until": self.tomorrow.isoformat(),
                "visible_from": visible_from.isoformat(),
                "is_active": "on",
            },
        )
        notice = RoomNotice.objects.get(title="Atendimento especial")
        deactivated = self.client.post(
            f"/supervisor/avisos/{notice.pk}/estado/",
            {"is_active": "false"},
        )

        self.assertRedirects(created, "/supervisor/funcionamento/?section=notices")
        self.assertRedirects(
            deactivated,
            "/supervisor/funcionamento/?section=notices",
        )
        notice.refresh_from_db()
        self.assertFalse(notice.is_active)

    def test_report_parameters_are_audited_and_applied_to_monthly_view(self):
        self.select_supervisor()
        Occurrence.objects.create(
            reported_by_reference="aluno-si-001",
            computer=self.computer,
            description="Mouse substituído.",
        )

        configured = self.client.post(
            "/supervisor/configuracoes/",
            {
                "kind": "report",
                "default_format": ReportConfiguration.ExportFormat.XLSX,
                "include_occurrences": "on",
            },
        )
        report = self.client.get(
            "/supervisor/relatorios/",
            {"year": self.today.year, "month": self.today.month},
        )

        self.assertRedirects(
            configured,
            "/supervisor/funcionamento/?section=policies",
        )
        configuration = ReportConfiguration.objects.get(is_active=True)
        self.assertEqual(
            configuration.default_format,
            ReportConfiguration.ExportFormat.XLSX,
        )
        self.assertFalse(configuration.group_by_shift)
        self.assertTrue(configuration.include_occurrences)
        self.assertContains(report, "Relatório mensal")
        self.assertContains(report, "Ocorrências")
        self.assertContains(report, "Preferência de exportação: Planilha")
        self.assertTrue(
            AuditEvent.objects.filter(action="REPORT_CONFIGURATION_UPDATED").exists()
        )
