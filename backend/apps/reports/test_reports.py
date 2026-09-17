from datetime import date, datetime, time
from io import BytesIO
from zipfile import ZipFile
from zoneinfo import ZoneInfo

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase

from apps.computers.models import Computer, ComputerOperationalStateChange
from apps.configuration.models import (
    CalendarException,
    OperatingSchedule,
    ReportConfiguration,
    Shift,
    Weekday,
)
from apps.configuration.tests.factories import create_operating_schedule
from apps.core.enums import AffiliationType
from apps.operations.models import ComputerAllocation, UseSession
from apps.operations.tests.factories import create_use_session
from apps.reports.projections import year_bounds
from apps.reports.selectors import load_report_data

REPORT_TZ = ZoneInfo("America/Rio_Branco")


def at(target_date, hour=0, minute=0):
    return datetime.combine(target_date, time(hour, minute), tzinfo=REPORT_TZ)


class ConsolidatedReportsAPITest(APITestCase):
    report_date = date(2026, 2, 10)

    def setUp(self):
        OperatingSchedule.objects.all().delete()
        create_operating_schedule(
            valid_from=date(2025, 1, 1),
            weekday_windows={
                weekday: [(time(7), time(22))] for weekday in Weekday.values
            },
        )
        self.shift = Shift.objects.create(
            name="Manhã",
            start_time=time(7),
            end_time=time(13),
            display_order=1,
            valid_from=date(2025, 1, 1),
        )
        self.computer = Computer.objects.create(code="PC-01")
        Computer.objects.filter(pk=self.computer.pk).update(
            created_at=at(date(2025, 1, 1))
        )
        session = create_use_session(
            user_reference="aluno-relatorio",
            affiliation_type=AffiliationType.STUDENT,
            institutional_unit="Sistemas de Informação",
            started_at=at(self.report_date, 8),
            ended_at=at(self.report_date, 9),
            status=UseSession.Status.FINISHED,
            start_shift=self.shift,
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=self.computer,
            sequence=1,
            started_at=at(self.report_date, 8),
            ended_at=at(self.report_date, 9),
            end_reason=ComputerAllocation.EndReason.SESSION_FINISHED,
        )
        self.client.post(
            "/api/demo/select-profile/",
            {"profile": "LIBRARY_SUPERVISOR"},
            format="json",
        )

    def test_daily_report_uses_the_shared_summary_and_calendar(self):
        response = self.client.get(
            "/api/reports/daily/",
            {"date": self.report_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["period"]["date"], self.report_date.isoformat())
        self.assertEqual(response.data["calendar"]["status"], "OPEN")
        self.assertEqual(response.data["summary"]["visits"], 1)
        self.assertEqual(response.data["summary"]["distinct_users"], 1)
        self.assertEqual(response.data["occupancy"]["allocated_minutes"], 60)

    def test_annual_report_always_returns_twelve_months(self):
        response = self.client.get("/api/reports/annual/", {"year": 2026})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["months"]), 12)
        self.assertEqual(response.data["months"][1]["summary"]["visits"], 1)
        self.assertEqual(response.data["summary"]["visits"], 1)
        self.assertEqual(response.data["summary"]["distinct_users"], 1)
        self.assertEqual(
            response.data["summary"]["visits"],
            sum(month["summary"]["visits"] for month in response.data["months"]),
        )
        self.assertEqual(
            response.data["summary"]["allocated_minutes"],
            sum(
                month["summary"]["allocated_minutes"]
                for month in response.data["months"]
            ),
        )

    def test_indicators_group_usage_without_exposing_user_references(self):
        response = self.client.get(
            "/api/reports/indicators/",
            {
                "starts_on": self.report_date.isoformat(),
                "ends_on": self.report_date.isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["by_affiliation"][0]["key"], "STUDENT")
        self.assertEqual(
            response.data["by_institutional_unit"][0]["key"],
            "Sistemas de Informação",
        )
        self.assertEqual(response.data["by_computer"][0]["code"], "PC-01")
        self.assertEqual(
            response.data["by_shift"][0]["key"],
            str(self.shift.series_key),
        )
        self.assertEqual(response.data["by_day"][0]["visits"], 1)
        self.assertEqual(response.data["by_time_slot"][4]["starts_at"], "08:00")
        self.assertNotContains(response, "aluno-relatorio")

    def test_indicators_keep_logical_shift_for_allocation_crossing_period(self):
        historical_shift = Shift.objects.create(
            name="Plantão anterior",
            start_time=time(23),
            end_time=time(23, 59),
            display_order=9,
            valid_from=date(2025, 1, 1),
            valid_until=self.report_date.replace(day=9),
            is_active=False,
        )
        crossing_session = create_use_session(
            user_reference="aluno-periodo-anterior",
            started_at=at(self.report_date.replace(day=9), 23, 30),
            ended_at=at(self.report_date, 0, 30),
            status=UseSession.Status.FINISHED,
            start_shift=historical_shift,
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=crossing_session,
            computer=self.computer,
            sequence=1,
            started_at=at(self.report_date.replace(day=9), 23, 30),
            ended_at=at(self.report_date, 0, 30),
            end_reason=ComputerAllocation.EndReason.SESSION_FINISHED,
        )

        response = self.client.get(
            "/api/reports/indicators/",
            {
                "starts_on": self.report_date.isoformat(),
                "ends_on": self.report_date.isoformat(),
            },
        )

        historical_row = next(
            row
            for row in response.data["by_shift"]
            if row["key"] == str(historical_shift.series_key)
        )
        self.assertEqual(historical_row["visits"], 0)
        self.assertEqual(historical_row["allocated_minutes"], 30)

    def test_daily_report_handles_closed_days_and_not_informed_shift(self):
        CalendarException.objects.create(
            date=self.report_date,
            exception_type=CalendarException.ExceptionType.CLOSED,
            description="Fechamento excepcional",
        )
        UseSession.objects.update(start_shift=None)

        response = self.client.get(
            "/api/reports/daily/",
            {"date": self.report_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["calendar"]["status"], "CLOSED")
        self.assertEqual(response.data["calendar"]["operating_minutes"], 0)
        self.assertEqual(response.data["visits_by_shift"]["NOT_INFORMED"], 1)
        self.assertEqual(response.data["occupancy"]["available_minutes"], 0)
        self.assertIsNone(response.data["occupancy"]["rate_percent"])

    def test_daily_special_hours_define_the_occupancy_denominator(self):
        CalendarException.objects.create(
            date=self.report_date,
            exception_type=CalendarException.ExceptionType.SPECIAL_HOURS,
            opens_at=time(8),
            closes_at=time(10),
            description="Atendimento reduzido",
        )

        response = self.client.get(
            "/api/reports/daily/",
            {"date": self.report_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["calendar"]["status"], "SPECIAL_HOURS")
        self.assertEqual(response.data["occupancy"]["available_minutes"], 120)
        self.assertEqual(response.data["occupancy"]["rate_percent"], 50.0)

    def test_indicator_period_is_limited_to_366_inclusive_days(self):
        response = self.client.get(
            "/api/reports/indicators/",
            {"starts_on": "2025-01-01", "ends_on": "2026-01-02"},
        )

        self.assertEqual(response.status_code, 400)

    def test_monitor_cannot_read_or_export_reports(self):
        self.client.post(
            "/api/demo/select-profile/",
            {"profile": "ROOM_MONITOR"},
            format="json",
        )

        report = self.client.get(
            "/api/reports/daily/",
            {"date": self.report_date.isoformat()},
        )
        exported = self.client.get(
            "/api/reports/daily/export/",
            {"date": self.report_date.isoformat(), "format": "CSV"},
        )

        self.assertEqual(report.status_code, 403)
        self.assertEqual(exported.status_code, 403)

    def test_state_history_limits_capacity_to_available_intervals(self):
        maintenance = ComputerOperationalStateChange.objects.create(
            computer=self.computer,
            previous_state=Computer.OperationalState.AVAILABLE,
            new_state=Computer.OperationalState.MAINTENANCE,
            actor_profile="ROOM_MONITOR",
        )
        available = ComputerOperationalStateChange.objects.create(
            computer=self.computer,
            previous_state=Computer.OperationalState.MAINTENANCE,
            new_state=Computer.OperationalState.AVAILABLE,
            actor_profile="ROOM_MONITOR",
        )
        ComputerOperationalStateChange.objects.filter(pk=maintenance.pk).update(
            changed_at=at(self.report_date, 10)
        )
        ComputerOperationalStateChange.objects.filter(pk=available.pk).update(
            changed_at=at(self.report_date, 12)
        )

        response = self.client.get(
            "/api/reports/daily/",
            {"date": self.report_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["occupancy"]["available_minutes"], 780)
        self.assertEqual(response.data["occupancy"]["allocated_minutes"], 60)
        self.assertEqual(
            response.data["warnings"]["computers_without_reliable_state_history"],
            [],
        )

    def test_inconsistent_state_history_is_excluded_and_warned(self):
        change = ComputerOperationalStateChange.objects.create(
            computer=self.computer,
            previous_state=Computer.OperationalState.AVAILABLE,
            new_state=Computer.OperationalState.MAINTENANCE,
            actor_profile="ROOM_MONITOR",
        )
        ComputerOperationalStateChange.objects.filter(pk=change.pk).update(
            changed_at=at(self.report_date, 10)
        )

        response = self.client.get(
            "/api/reports/daily/",
            {"date": self.report_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["occupancy"]["rate_percent"])
        self.assertEqual(response.data["occupancy"]["allocated_minutes"], 0)
        self.assertEqual(
            response.data["warnings"]["computers_without_reliable_state_history"],
            ["PC-01"],
        )

    def test_each_report_exports_csv_with_a_predictable_filename(self):
        cases = [
            (
                "/api/reports/daily/export/",
                {"date": "2026-02-10", "format": "CSV"},
                "relatorio-diario-2026-02-10.csv",
            ),
            (
                "/api/reports/monthly/export/",
                {"year": 2026, "month": 2, "format": "CSV"},
                "relatorio-mensal-2026-02.csv",
            ),
            (
                "/api/reports/annual/export/",
                {"year": 2026, "format": "CSV"},
                "relatorio-anual-2026.csv",
            ),
            (
                "/api/reports/indicators/export/",
                {
                    "starts_on": "2026-02-10",
                    "ends_on": "2026-02-10",
                    "format": "CSV",
                },
                "indicadores-2026-02-10-a-2026-02-10.csv",
            ),
        ]

        for path, query, filename in cases:
            with self.subTest(path=path):
                response = self.client.get(path, query)
                decoded = response.content.decode("utf-8-sig")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
                self.assertIn(filename, response["Content-Disposition"])
                self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
                self.assertIn("Seção;Indicador;Valor", decoded)
                self.assertNotIn("aluno-relatorio", decoded)
                if "indicators" in path:
                    self.assertIn("Computadores", decoded)
                    self.assertIn("Reservas por situação", decoded)

    def test_xlsx_and_pdf_are_real_documents(self):
        query = {"date": self.report_date.isoformat()}
        xlsx = self.client.get(
            "/api/reports/daily/export/",
            {**query, "format": "XLSX"},
        )
        pdf = self.client.get(
            "/api/reports/daily/export/",
            {**query, "format": "PDF"},
        )

        self.assertEqual(xlsx.status_code, 200)
        self.assertTrue(xlsx.content.startswith(b"PK"))
        with ZipFile(BytesIO(xlsx.content)) as workbook:
            self.assertIn("xl/workbook.xml", workbook.namelist())
            self.assertIn(b"Resumo", workbook.read("xl/workbook.xml"))
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertIn(b"/Author (Biblioteca UFAC)", pdf.content)
        self.assertIn(".pdf", pdf["Content-Disposition"])

        indicators_xlsx = self.client.get(
            "/api/reports/indicators/export/",
            {
                "starts_on": self.report_date.isoformat(),
                "ends_on": self.report_date.isoformat(),
                "format": "XLSX",
            },
        )
        with ZipFile(BytesIO(indicators_xlsx.content)) as workbook:
            workbook_xml = workbook.read("xl/workbook.xml")
            self.assertIn(b"Turnos", workbook_xml)
            self.assertIn(b"Computadores", workbook_xml)
            self.assertIn(b"Reservas por situa", workbook_xml)

    def test_export_uses_the_configured_default_when_format_is_omitted(self):
        ReportConfiguration.objects.filter(is_active=True).delete()
        ReportConfiguration.objects.create(
            default_format=ReportConfiguration.ExportFormat.XLSX,
            is_active=True,
        )

        response = self.client.get(
            "/api/reports/daily/export/",
            {"date": self.report_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"PK"))
        self.assertIn(".xlsx", response["Content-Disposition"])

    def test_computer_created_during_period_only_adds_later_capacity(self):
        Computer.objects.filter(pk=self.computer.pk).update(
            created_at=at(self.report_date, 12)
        )

        response = self.client.get(
            "/api/reports/daily/",
            {"date": self.report_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["occupancy"]["available_minutes"], 600)
        self.assertEqual(response.data["occupancy"]["allocated_minutes"], 0)

    def test_leap_year_uses_all_366_operating_days(self):
        response = self.client.get("/api/reports/annual/", {"year": 2028})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["months"][1]["summary"]["operating_minutes"],
            26100,
        )
        self.assertEqual(response.data["summary"]["operating_minutes"], 329400)

    def test_year_data_is_loaded_with_a_bounded_query_count(self):
        starts_at, ends_at = year_bounds(2026)
        with CaptureQueriesContext(connection) as queries:
            data = load_report_data(
                starts_at=starts_at,
                ends_at=ends_at,
                starts_on=date(2026, 1, 1),
                ends_on=date(2027, 1, 1),
            )

        self.assertEqual(len(data.operating_days), 365)
        self.assertLessEqual(len(queries), 12)
