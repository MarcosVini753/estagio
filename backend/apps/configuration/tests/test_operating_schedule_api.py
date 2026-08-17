from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.exceptions import APIException
from rest_framework.test import APITestCase

from apps.audit.models import AuditEvent
from apps.computers.models import Computer
from apps.configuration.models import (
    CalendarException,
    OperatingSchedule,
    RoomNotice,
    Weekday,
)
from apps.configuration.services import preview_calendar_exception_impact
from apps.operations.models import Reservation
from apps.operations.tests.factories import create_reservation

from .factories import create_operating_schedule


def days_payload(*, opens_at="08:00", closes_at="13:00"):
    return [
        {
            "weekday": Weekday(weekday).name,
            "is_open": weekday < Weekday.SATURDAY,
            "windows": (
                [{"opens_at": opens_at, "closes_at": closes_at}]
                if weekday < Weekday.SATURDAY
                else []
            ),
        }
        for weekday in Weekday.values
    ]


class OperatingScheduleAPITest(APITestCase):
    def select_profile(self, profile):
        payload = {"profile": profile}
        if profile == "ROOM_USER":
            payload.update(
                user_reference="aluno-calendario",
                affiliation_type="STUDENT",
                institutional_unit="Sistemas de Informação",
            )
        self.client.post("/api/demo/select-profile/", payload, format="json")

    def temporary_payload(self, **overrides):
        payload = {
            "name": "Recesso acadêmico 2026/2",
            "schedule_type": "TEMPORARY",
            "valid_from": "2026-12-21",
            "valid_until": "2027-01-31",
            "reason": "Funcionamento durante o recesso.",
            "days": days_payload(),
        }
        payload.update(overrides)
        return payload

    def test_public_room_status_explains_saturday_and_sunday(self):
        saturday = self.client.get("/api/room-status/?date=2026-08-08")
        sunday = self.client.get("/api/room-status/?date=2026-08-09")

        self.assertEqual(saturday.status_code, 200)
        self.assertEqual(saturday.data["status"], "OPEN")
        self.assertEqual(
            saturday.data["operating_windows"],
            [{"opens_at": "07:15:00", "closes_at": "13:00:00"}],
        )
        self.assertEqual(sunday.status_code, 200)
        self.assertEqual(sunday.data["status"], "CLOSED")
        self.assertIn("domingos", sunday.data["reason"])

    def test_room_user_reads_schedule_but_only_supervisor_creates(self):
        self.select_profile("ROOM_USER")
        listed = self.client.get("/api/operating-schedules/")
        forbidden = self.client.post(
            "/api/operating-schedules/",
            self.temporary_payload(),
            format="json",
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data[0]["days"][0]["weekday"], "MONDAY")
        self.assertEqual(forbidden.status_code, 403)

    def test_create_requires_exactly_seven_valid_days(self):
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            "/api/operating-schedules/",
            self.temporary_payload(days=days_payload()[:-1]),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "OPERATING_DAY_CONFIGURATION_INVALID")

    def test_calendar_exception_rejects_past_date_without_side_effects(self):
        past_date = timezone.localdate() - timedelta(days=1)
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            "/api/calendar-exceptions/",
            {
                "date": past_date.isoformat(),
                "exception_type": CalendarException.ExceptionType.CLOSED,
                "description": "Fechamento retroativo.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "CALENDAR_EXCEPTION_DATE_INVALID")
        self.assertFalse(CalendarException.objects.filter(date=past_date).exists())
        self.assertFalse(
            AuditEvent.objects.filter(action__startswith="CALENDAR_EXCEPTION_").exists()
        )

    def test_calendar_exception_rejects_preview_and_update_for_past_date(self):
        past_date = timezone.localdate() - timedelta(days=1)
        exception = CalendarException.objects.create(
            date=past_date,
            exception_type=CalendarException.ExceptionType.CLOSED,
            description="Registro histórico.",
        )
        self.select_profile("LIBRARY_SUPERVISOR")

        with self.assertRaisesMessage(
            APIException,
            "Exceções de calendário só podem ser criadas ou alteradas para hoje",
        ):
            preview_calendar_exception_impact(
                values={
                    "date": past_date,
                    "exception_type": CalendarException.ExceptionType.CLOSED,
                }
            )
        response = self.client.patch(
            f"/api/calendar-exceptions/{exception.pk}/",
            {"description": "Tentativa de alteração."},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "CALENDAR_EXCEPTION_DATE_INVALID")
        exception.refresh_from_db()
        self.assertEqual(exception.description, "Registro histórico.")

    def test_calendar_exception_accepts_today(self):
        today = timezone.localdate()
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            "/api/calendar-exceptions/",
            {
                "date": today.isoformat(),
                "exception_type": CalendarException.ExceptionType.CLOSED,
                "description": "Emergência no dia atual.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(CalendarException.objects.filter(date=today).exists())

    def test_create_rejects_schedule_starting_today(self):
        today = timezone.localdate()
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            "/api/operating-schedules/",
            self.temporary_payload(
                valid_from=today.isoformat(),
                valid_until=(today + timedelta(days=30)).isoformat(),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "OPERATING_SCHEDULE_START_INVALID")
        self.assertFalse(
            OperatingSchedule.objects.filter(
                schedule_type=OperatingSchedule.ScheduleType.TEMPORARY
            ).exists()
        )

    def test_create_rejects_schedule_starting_in_the_past(self):
        today = timezone.localdate()
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            "/api/operating-schedules/",
            self.temporary_payload(
                valid_from=(today - timedelta(days=1)).isoformat(),
                valid_until=(today + timedelta(days=30)).isoformat(),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "OPERATING_SCHEDULE_START_INVALID")
        self.assertFalse(
            OperatingSchedule.objects.filter(
                schedule_type=OperatingSchedule.ScheduleType.TEMPORARY
            ).exists()
        )

    def test_impact_preview_rejects_non_future_schedule(self):
        today = timezone.localdate()
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            "/api/operating-schedules/impact-preview/",
            self.temporary_payload(
                valid_from=today.isoformat(),
                valid_until=(today + timedelta(days=30)).isoformat(),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "OPERATING_SCHEDULE_START_INVALID")

    def test_preview_then_confirm_cancels_conflicting_reservation(self):
        computer = Computer.objects.create(code="PC-CAL-01")
        starts_at = timezone.make_aware(
            datetime(2026, 12, 22, 18),
            timezone.get_current_timezone(),
        )
        reservation = create_reservation(
            user_reference="aluno-afetado",
            computer=computer,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            created_by_profile="ROOM_USER",
        )
        self.select_profile("LIBRARY_SUPERVISOR")

        preview = self.client.post(
            "/api/operating-schedules/impact-preview/",
            self.temporary_payload(),
            format="json",
        )
        rejected = self.client.post(
            "/api/operating-schedules/",
            self.temporary_payload(),
            format="json",
        )
        confirmed = self.client.post(
            "/api/operating-schedules/",
            self.temporary_payload(confirm_cancellation=True),
            format="json",
        )

        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data["total"], 1)
        self.assertEqual(
            preview.data["conflicting_reservations"][0]["id"], reservation.pk
        )
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(
            rejected.data["code"],
            "SCHEDULE_CHANGE_AFFECTS_RESERVATIONS",
        )
        self.assertEqual(confirmed.status_code, 201)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CANCELLED)
        self.assertEqual(
            reservation.cancelled_by_profile,
            "LIBRARY_SUPERVISOR",
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action="RESERVATION_CANCELLED",
                entity_id=str(reservation.pk),
            ).exists()
        )

    def test_replace_preserves_history_and_series_key(self):
        today = timezone.localdate()
        schedule = create_operating_schedule(
            schedule_type=OperatingSchedule.ScheduleType.TEMPORARY,
            valid_from=today - timedelta(days=5),
            valid_until=today + timedelta(days=10),
            weekday_windows={
                weekday: [(time(8), time(13))] for weekday in Weekday.values
            },
            name="Recesso em andamento",
        )
        related_notice = RoomNotice.objects.create(
            notice_type=RoomNotice.NoticeType.SCHEDULE_CHANGE,
            title="Horário anterior",
            message="Atendimento até 13h.",
            effective_from=schedule.valid_from,
            effective_until=schedule.valid_until,
            visible_from=timezone.now() - timedelta(days=1),
            created_by_profile="LIBRARY_SUPERVISOR",
            operating_schedule=schedule,
        )
        effective_from = today + timedelta(days=1)
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            f"/api/operating-schedules/{schedule.pk}/replace/",
            {
                "effective_from": effective_from.isoformat(),
                "reason": "Redução do atendimento.",
                "days": days_payload(closes_at="12:00"),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        schedule.refresh_from_db()
        self.assertEqual(schedule.valid_until, effective_from - timedelta(days=1))
        self.assertEqual(response.data["series_key"], str(schedule.series_key))
        self.assertEqual(
            response.data["days"][0]["windows"][0]["closes_at"], "12:00:00"
        )
        self.assertTrue(
            AuditEvent.objects.filter(action="OPERATING_SCHEDULE_REPLACED").exists()
        )
        related_notice.refresh_from_db()
        self.assertFalse(related_notice.is_active)

    def test_schedule_and_notice_are_created_in_one_transaction(self):
        self.select_profile("LIBRARY_SUPERVISOR")
        visible_from = timezone.now()

        response = self.client.post(
            "/api/operating-schedules/",
            self.temporary_payload(
                notify_users=True,
                notice={
                    "title": "Horário de recesso",
                    "message": "Durante o recesso, a sala fecha às 13h.",
                    "visible_from": visible_from.isoformat(),
                },
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        notice = RoomNotice.objects.get()
        self.assertEqual(notice.operating_schedule_id, response.data["id"])
        self.assertEqual(notice.effective_from, date(2026, 12, 21))

    def test_schedule_rolls_back_when_linked_notice_fails(self):
        self.select_profile("LIBRARY_SUPERVISOR")
        payload = self.temporary_payload(
            notify_users=True,
            notice={
                "title": "Horário de recesso",
                "message": "Atendimento reduzido.",
                "visible_from": timezone.now().isoformat(),
            },
        )

        with (
            patch(
                "apps.configuration.services._implementation.create_room_notice",
                side_effect=RuntimeError("notice unavailable"),
            ),
            self.assertRaises(RuntimeError),
        ):
            self.client.post(
                "/api/operating-schedules/",
                payload,
                format="json",
            )

        self.assertFalse(
            OperatingSchedule.objects.filter(
                schedule_type=OperatingSchedule.ScheduleType.TEMPORARY
            ).exists()
        )


class RoomNoticeAPITest(APITestCase):
    def test_active_notices_are_public_and_filter_visibility(self):
        current = timezone.now()
        values = {
            "notice_type": RoomNotice.NoticeType.CLOSURE,
            "message": "Manutenção elétrica.",
            "effective_from": timezone.localdate(),
            "effective_until": timezone.localdate(),
            "created_by_profile": "LIBRARY_SUPERVISOR",
        }
        RoomNotice.objects.create(
            **values,
            title="Aviso ativo",
            visible_from=current - timedelta(hours=1),
        )
        RoomNotice.objects.create(
            **values,
            title="Aviso futuro",
            visible_from=current + timedelta(hours=1),
        )
        RoomNotice.objects.create(
            **values,
            title="Aviso expirado",
            visible_from=current - timedelta(days=2),
            visible_until=current - timedelta(days=1),
        )
        RoomNotice.objects.create(
            **values,
            title="Aviso inativo",
            visible_from=current - timedelta(hours=1),
            is_active=False,
        )
        RoomNotice.objects.create(
            notice_type=RoomNotice.NoticeType.CLOSURE,
            title="Efeito encerrado",
            message="Evento encerrado.",
            effective_from=timezone.localdate() - timedelta(days=2),
            effective_until=timezone.localdate() - timedelta(days=1),
            visible_from=current - timedelta(hours=1),
            created_by_profile="LIBRARY_SUPERVISOR",
        )

        response = self.client.get("/api/room-notices/active/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["title"] for item in response.data], ["Aviso ativo"])

    def test_monitor_cannot_publish_notice(self):
        self.client.post(
            "/api/demo/select-profile/",
            {"profile": "ROOM_MONITOR"},
            format="json",
        )

        response = self.client.post(
            "/api/room-notices/",
            {
                "notice_type": "CLOSURE",
                "title": "Fechamento",
                "message": "Sala fechada.",
                "effective_from": timezone.localdate().isoformat(),
                "effective_until": timezone.localdate().isoformat(),
                "visible_from": timezone.now().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
