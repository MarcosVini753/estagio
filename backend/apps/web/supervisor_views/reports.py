from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.configuration.models import ReportConfiguration
from apps.reports.api.serializers import MonthlyReportQuerySerializer
from apps.reports.projections import build_monthly_report, month_bounds
from apps.reports.selectors import (
    get_allocations_for_period,
    get_occurrences_for_period,
    get_operating_days_for_period,
    get_reservations_for_period,
    get_sessions_for_period,
    get_shifts_for_period,
)

from ..http import service_error_message as _exception_message
from ..operational_state import reconcile_operational_state
from ..presenters import flatten_serializer_errors
from .common import _render_screen, management_profile_required
from .context import _report_configuration, _screen_context


def _reports_context(request, *, screen_error=""):
    current = timezone.localdate()
    query = MonthlyReportQuerySerializer(
        data={
            "year": request.GET.get("year", current.year),
            "month": request.GET.get("month", current.month),
        }
    )
    report = None
    year = current.year
    month = current.month
    if query.is_valid():
        year = query.validated_data["year"]
        month = query.validated_data["month"]
        starts_at, ends_at = month_bounds(year, month)
        report_now = reconcile_operational_state(period=(starts_at, ends_at))
        try:
            report = build_monthly_report(
                year=year,
                month=month,
                sessions=get_sessions_for_period(starts_at, ends_at),
                allocations=get_allocations_for_period(starts_at, ends_at),
                reservations=get_reservations_for_period(starts_at, ends_at),
                occurrences=get_occurrences_for_period(starts_at, ends_at),
                shifts=get_shifts_for_period(starts_at.date(), ends_at.date()),
                operating_days=get_operating_days_for_period(
                    starts_at.date(), ends_at.date()
                ),
                now=report_now,
            )
        except APIException as error:
            screen_error = _exception_message(error)
    else:
        screen_error = flatten_serializer_errors(query.errors)
    configuration = _report_configuration() or ReportConfiguration()
    context = _screen_context(request, screen="reports")
    context.update(
        {
            "report": report,
            "report_year": year,
            "report_month": month,
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

