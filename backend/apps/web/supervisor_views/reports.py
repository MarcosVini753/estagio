from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.configuration.models import ReportConfiguration
from apps.reports.api.serializers import (
    AnnualReportQuerySerializer,
    DailyReportQuerySerializer,
    IndicatorsReportQuerySerializer,
    MonthlyReportQuerySerializer,
)
from apps.reports.reporting import generate_report

from ..http import service_error_message as _exception_message
from ..presenters import flatten_serializer_errors
from .common import _render_screen, management_profile_required
from .context import _report_configuration, _screen_context

REPORT_KINDS = ("daily", "monthly", "annual", "indicators")
REPORT_LABELS = {
    "daily": "Diário",
    "monthly": "Mensal",
    "annual": "Anual",
    "indicators": "Indicadores",
}
REPORT_TITLES = {
    "daily": "Relatório diário",
    "monthly": "Relatório mensal",
    "annual": "Relatório anual",
    "indicators": "Indicadores gerenciais",
}
EXPORT_URL_NAMES = {
    "daily": "report-daily-export",
    "monthly": "report-monthly-export",
    "annual": "report-annual-export",
    "indicators": "report-indicators-export",
}
ROOM_STATUS_LABELS = {
    "OPEN": "Aberta",
    "CLOSED": "Fechada",
    "SPECIAL_HOURS": "Horário especial",
}
CALENDAR_SOURCE_LABELS = {
    "CALENDAR_EXCEPTION": "Exceção de calendário",
    "TEMPORARY_SCHEDULE": "Calendário temporário",
    "REGULAR_SCHEDULE": "Calendário regular",
}


def _display_filters(values):
    return {
        key: value.isoformat() if hasattr(value, "isoformat") else value
        for key, value in values.items()
    }


def _default_filters(today):
    return {
        "date": today.isoformat(),
        "year": today.year,
        "month": today.month,
        "starts_on": today.replace(day=1).isoformat(),
        "ends_on": today.isoformat(),
    }


def _query_for(request, report_kind, defaults):
    if report_kind == "daily":
        values = {"date": request.GET.get("date", defaults["date"])}
        return DailyReportQuerySerializer(data=values), values
    if report_kind == "annual":
        values = {"year": request.GET.get("year", defaults["year"])}
        return AnnualReportQuerySerializer(data=values), values
    if report_kind == "indicators":
        values = {
            "starts_on": request.GET.get("starts_on", defaults["starts_on"]),
            "ends_on": request.GET.get("ends_on", defaults["ends_on"]),
        }
        return IndicatorsReportQuerySerializer(data=values), values
    values = {
        "year": request.GET.get("year", defaults["year"]),
        "month": request.GET.get("month", defaults["month"]),
    }
    return MonthlyReportQuerySerializer(data=values), values


def _decorate_calendar_labels(report_kind, report):
    if report_kind == "daily":
        report["calendar"]["status_label"] = ROOM_STATUS_LABELS[
            report["calendar"]["status"]
        ]
        report["calendar"]["source_label"] = CALENDAR_SOURCE_LABELS[
            report["calendar"]["source"]
        ]
    elif report_kind == "monthly":
        for day in report["days"]:
            day["calendar_status_label"] = ROOM_STATUS_LABELS[day["calendar_status"]]
            day["calendar_source_label"] = CALENDAR_SOURCE_LABELS[
                day["calendar_source"]
            ]


def _export_links(report_kind, values, configuration):
    base_url = reverse(EXPORT_URL_NAMES[report_kind])
    return [
        {
            "value": value,
            "label": label,
            "is_default": value == configuration.default_format,
            "url": f"{base_url}?{urlencode({**values, 'format': value})}",
        }
        for value, label in ReportConfiguration.ExportFormat.choices
    ]


def _navigation(defaults, selected):
    query_by_kind = {
        "daily": {"report": "daily", "date": defaults["date"]},
        "monthly": {
            "report": "monthly",
            "year": defaults["year"],
            "month": defaults["month"],
        },
        "annual": {"report": "annual", "year": defaults["year"]},
        "indicators": {
            "report": "indicators",
            "starts_on": defaults["starts_on"],
            "ends_on": defaults["ends_on"],
        },
    }
    base_url = reverse("web:supervisor-reports")
    return [
        {
            "key": kind,
            "label": REPORT_LABELS[kind],
            "is_current": kind == selected,
            "url": f"{base_url}?{urlencode(query_by_kind[kind])}",
        }
        for kind in REPORT_KINDS
    ]


def _reports_context(request, *, screen_error=""):
    today = timezone.localdate()
    defaults = _default_filters(today)
    report_kind = request.GET.get("report", "monthly")
    if report_kind not in REPORT_KINDS:
        screen_error = "Escolha uma visão de relatório válida."
        report_kind = "monthly"

    query, raw_filters = _query_for(request, report_kind, defaults)
    report = None
    export_links = []
    configuration = _report_configuration() or ReportConfiguration()
    if not screen_error and query.is_valid():
        try:
            raw_filters = _display_filters(query.validated_data)
            report = generate_report(
                report_kind,
                query.validated_data,
                now=timezone.now(),
            )
            _decorate_calendar_labels(report_kind, report)
            export_links = _export_links(
                report_kind,
                query.validated_data,
                configuration,
            )
        except APIException as error:
            screen_error = _exception_message(error)
    elif not screen_error:
        screen_error = flatten_serializer_errors(query.errors)

    context = _screen_context(request, screen="reports")
    context.update(
        {
            "report": report,
            "report_kind": report_kind,
            "report_kind_label": REPORT_LABELS[report_kind],
            "report_title": REPORT_TITLES[report_kind],
            "report_filters": raw_filters,
            "report_navigation": _navigation(defaults, report_kind),
            "export_links": export_links,
            "month_choices": [(value, f"{value:02d}") for value in range(1, 13)],
            "report_configuration": configuration,
            "screen_error": screen_error,
        }
    )
    return context


@management_profile_required
def reports(request):
    context = _reports_context(request)
    return _render_screen(
        request,
        content_template="supervisor/partials/reports.html",
        context=context,
        status=400 if context["screen_error"] else 200,
    )


__all__ = ["reports"]
