from datetime import datetime, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

from rest_framework.test import APITestCase

from apps.computers.models import Computer
from apps.configuration.models import (
    CalendarException,
    OperatingSchedule,
    Shift,
    Weekday,
)
from apps.configuration.tests.factories import create_operating_schedule
from apps.occurrences.models import Occurrence
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.tests.factories import create_reservation, create_use_session
from apps.reports.projections import NOT_INFORMED, overlap_minutes

REPORT_TZ = ZoneInfo("America/Rio_Branco")


def report_datetime(month, day, hour=0, minute=0):
    return datetime(2026, month, day, hour, minute, tzinfo=REPORT_TZ)


class MonthlyReportAPITest(APITestCase):
    def select_profile(self, profile="LIBRARY_SUPERVISOR"):
        self.client.post(
            "/api/demo/select-profile/",
            {"profile": profile},
            format="json",
        )

    def create_session(
        self,
        *,
        reference,
        started_at,
        ended_at,
        shift=None,
        status=UseSession.Status.FINISHED,
    ):
        return create_use_session(
            user_reference=reference,
            started_at=started_at,
            ended_at=ended_at,
            status=status,
            start_shift=shift,
            entry_recorded_by_profile="ROOM_USER",
        )

    def test_monthly_report_aggregates_operational_data(self):
        computers = [
            Computer.objects.create(code="PC-01"),
            Computer.objects.create(code="PC-02"),
            Computer.objects.create(code="PC-03"),
        ]
        shifts = [
            Shift.objects.create(
                name="1º Turno",
                start_time="07:15",
                end_time="13:00",
                display_order=1,
            ),
            Shift.objects.create(
                name="2º Turno",
                start_time="13:00",
                end_time="17:00",
                display_order=2,
            ),
            Shift.objects.create(
                name="3º Turno",
                start_time="17:00",
                end_time="21:00",
                display_order=3,
            ),
        ]
        first = self.create_session(
            reference="demo-report-user-a",
            started_at=report_datetime(2, 10, 8),
            ended_at=report_datetime(2, 10, 10),
            shift=shifts[0],
        )
        ComputerAllocation.objects.create(
            session=first,
            computer=computers[0],
            sequence=1,
            started_at=report_datetime(2, 10, 8),
            ended_at=report_datetime(2, 10, 9),
            end_reason=ComputerAllocation.EndReason.SWITCH,
        )
        ComputerAllocation.objects.create(
            session=first,
            computer=computers[1],
            sequence=2,
            started_at=report_datetime(2, 10, 9),
            ended_at=report_datetime(2, 10, 10),
            end_reason=ComputerAllocation.EndReason.SESSION_FINISHED,
        )
        second = self.create_session(
            reference="demo-report-user-a",
            started_at=report_datetime(2, 11, 13),
            ended_at=report_datetime(2, 11, 14),
            shift=shifts[1],
        )
        ComputerAllocation.objects.create(
            session=second,
            computer=computers[0],
            sequence=1,
            started_at=report_datetime(2, 11, 13),
            ended_at=report_datetime(2, 11, 14),
            end_reason=ComputerAllocation.EndReason.SESSION_FINISHED,
        )
        active = self.create_session(
            reference="demo-report-user-b",
            started_at=report_datetime(2, 12, 18),
            ended_at=None,
            shift=shifts[2],
            status=UseSession.Status.ACTIVE,
        )
        ComputerAllocation.objects.create(
            session=active,
            computer=computers[0],
            sequence=1,
            started_at=report_datetime(2, 12, 18),
        )
        without_shift = self.create_session(
            reference="demo-report-user-c",
            started_at=report_datetime(2, 13, 10),
            ended_at=report_datetime(2, 13, 10, 30),
        )
        ComputerAllocation.objects.create(
            session=without_shift,
            computer=computers[1],
            sequence=1,
            started_at=report_datetime(2, 13, 10),
            ended_at=report_datetime(2, 13, 10, 30),
            end_reason=ComputerAllocation.EndReason.SESSION_FINISHED,
        )
        cancelled = self.create_session(
            reference="demo-report-cancelled",
            started_at=report_datetime(2, 14, 10),
            ended_at=report_datetime(2, 14, 11),
            shift=shifts[0],
            status=UseSession.Status.CANCELLED,
        )
        ComputerAllocation.objects.create(
            session=cancelled,
            computer=computers[2],
            sequence=1,
            started_at=report_datetime(2, 14, 10),
            ended_at=report_datetime(2, 14, 11),
            end_reason=ComputerAllocation.EndReason.CANCELLED,
        )

        create_reservation(
            user_reference="demo-report-user-a",
            computer=computers[0],
            starts_at=report_datetime(2, 20, 8),
            ends_at=report_datetime(2, 20, 9),
            status=Reservation.Status.USED,
            created_by_profile="ROOM_USER",
        )
        create_reservation(
            user_reference="demo-report-user-a",
            computer=computers[0],
            starts_at=report_datetime(3, 1, 8),
            ends_at=report_datetime(3, 1, 9),
            status=Reservation.Status.CANCELLED,
            created_by_profile="ROOM_USER",
        )
        occurrence_in_month = Occurrence.objects.create(
            reported_by_reference="demo-report-user-a",
            description="Falha no teclado.",
        )
        Occurrence.objects.filter(pk=occurrence_in_month.pk).update(
            created_at=report_datetime(2, 17, 9)
        )
        occurrence_outside = Occurrence.objects.create(
            reported_by_reference="demo-report-user-a",
            description="Fora do mês.",
        )
        Occurrence.objects.filter(pk=occurrence_outside.pk).update(
            created_at=report_datetime(3, 1, 9)
        )
        CalendarException.objects.create(
            date=report_datetime(2, 9).date(),
            exception_type=CalendarException.ExceptionType.CLOSED,
        )
        CalendarException.objects.create(
            date=report_datetime(2, 15).date(),
            exception_type=CalendarException.ExceptionType.SPECIAL_HOURS,
            opens_at="09:00",
            closes_at="12:00",
        )
        self.select_profile()

        with patch(
            "apps.reports.projections.timezone.now",
            return_value=report_datetime(2, 12, 19),
        ):
            response = self.client.get("/api/reports/monthly/?year=2026&month=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["days"]), 28)
        self.assertEqual(response.data["days"][0]["calendar_status"], "CLOSED")
        self.assertEqual(
            response.data["days"][0]["calendar_source"],
            "REGULAR_SCHEDULE",
        )
        self.assertEqual(response.data["days"][0]["operating_minutes"], 0)
        self.assertEqual(response.data["days"][6]["operating_minutes"], 345)
        self.assertEqual(response.data["days"][8]["calendar_status"], "CLOSED")
        self.assertEqual(response.data["days"][14]["calendar_status"], "SPECIAL_HOURS")
        first_key = str(shifts[0].series_key)
        self.assertEqual(response.data["days"][9]["visits_by_shift"][first_key], 1)
        self.assertEqual(response.data["days"][12]["visits_by_shift"][NOT_INFORMED], 1)
        self.assertEqual(response.data["summary"]["visits"], 4)
        self.assertEqual(
            response.data["summary"]["visits"],
            sum(response.data["totals_by_shift"].values()),
        )
        self.assertEqual(response.data["summary"]["distinct_users"], 3)
        self.assertEqual(response.data["summary"]["reservations"], 1)
        self.assertEqual(
            response.data["summary"]["reservations_by_status"]["CANCELLED"],
            0,
        )
        self.assertEqual(response.data["summary"]["occurrences"], 1)
        self.assertEqual(response.data["summary"]["computers_used"], 2)
        self.assertEqual(response.data["summary"]["allocated_minutes"], 270)
        self.assertEqual(response.data["summary"]["average_stay_minutes"], 70)
        self.assertEqual(response.data["warnings"]["active_session_ids"], [active.pk])
        self.assertEqual(
            response.data["warnings"]["sessions_without_shift"],
            [without_shift.pk],
        )

    def test_versions_of_same_shift_share_one_column(self):
        old = Shift.objects.create(
            name="1º Turno",
            start_time="07:15",
            end_time="13:00",
            display_order=1,
            valid_from="2025-01-01",
            valid_until="2026-02-14",
        )
        new = Shift.objects.create(
            series_key=old.series_key,
            name="1º Turno",
            start_time="07:30",
            end_time="13:00",
            display_order=1,
            valid_from="2026-02-15",
        )
        self.create_session(
            reference="demo-report-old",
            started_at=report_datetime(2, 10, 8),
            ended_at=report_datetime(2, 10, 9),
            shift=old,
        )
        self.create_session(
            reference="demo-report-new",
            started_at=report_datetime(2, 20, 8),
            ended_at=report_datetime(2, 20, 9),
            shift=new,
        )
        self.select_profile()

        response = self.client.get("/api/reports/monthly/?year=2026&month=2")

        key = str(old.series_key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["shifts"]), 1)
        self.assertEqual(response.data["totals_by_shift"][key], 2)

    def test_period_boundaries_and_crossing_allocation_are_clipped(self):
        computer = Computer.objects.create(code="PC-01")
        prior_session = self.create_session(
            reference="demo-report-prior",
            started_at=report_datetime(1, 31, 23, 30),
            ended_at=report_datetime(2, 1, 0, 30),
        )
        ComputerAllocation.objects.create(
            session=prior_session,
            computer=computer,
            sequence=1,
            started_at=report_datetime(1, 31, 23, 30),
            ended_at=report_datetime(2, 1, 0, 30),
            end_reason=ComputerAllocation.EndReason.SESSION_FINISHED,
        )
        self.create_session(
            reference="demo-report-start",
            started_at=report_datetime(2, 1),
            ended_at=report_datetime(2, 1, 0, 15),
        )
        self.create_session(
            reference="demo-report-end",
            started_at=report_datetime(3, 1),
            ended_at=report_datetime(3, 1, 0, 15),
        )
        self.select_profile()

        response = self.client.get("/api/reports/monthly/?year=2026&month=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["visits"], 1)
        self.assertEqual(response.data["summary"]["allocated_minutes"], 30)

    def test_permissions_query_validation_and_interval_helper(self):
        self.select_profile("ROOM_MONITOR")
        forbidden = self.client.get("/api/reports/monthly/?year=2026&month=2")
        self.select_profile()
        invalid = self.client.get("/api/reports/monthly/?year=2026&month=13")
        self.select_profile("SYSTEM_ADMIN")
        allowed = self.client.get("/api/reports/monthly/?year=2028&month=2")

        minutes = overlap_minutes(
            report_datetime(2, 10, 12, 30),
            report_datetime(2, 10, 13, 30),
            report_datetime(2, 10, 13),
            report_datetime(2, 10, 17),
            now=report_datetime(2, 10, 14),
        )

        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(len(allowed.data["days"]), 29)
        self.assertEqual(minutes, 30)

    def test_temporary_schedule_changes_operating_denominator(self):
        create_operating_schedule(
            schedule_type=OperatingSchedule.ScheduleType.TEMPORARY,
            valid_from=report_datetime(2, 2).date(),
            valid_until=report_datetime(2, 6).date(),
            weekday_windows={
                weekday: [(time(8), time(13))] for weekday in Weekday.values
            },
            name="Recesso de fevereiro",
        )
        self.select_profile()

        response = self.client.get("/api/reports/monthly/?year=2026&month=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["days"][1]["calendar_status"], "SPECIAL_HOURS")
        self.assertEqual(
            response.data["days"][1]["calendar_source"],
            "TEMPORARY_SCHEDULE",
        )
        self.assertEqual(response.data["days"][1]["operating_minutes"], 300)
