from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.computers.models import Computer
from apps.configuration.calendar import resolve_operating_day
from apps.configuration.models import OperatingSchedule, RoomNotice
from apps.occurrences.models import Occurrence
from apps.operations.models import UseSession

from ..http import service_error_message as _exception_message
from ..operational_state import reconcile_operational_state
from .common import _render_screen, management_profile_required
from .context import _screen_context


def _dashboard_context(request, *, screen_error=""):
    current = reconcile_operational_state()
    today = timezone.localdate(current)
    try:
        operating_day = resolve_operating_day(today)
    except APIException as error:
        operating_day = None
        screen_error = screen_error or _exception_message(error)
    context = _screen_context(request, screen="dashboard")
    context.update(
        {
            "operating_day": operating_day,
            "computer_count": Computer.objects.count(),
            "inactive_computer_count": Computer.objects.exclude(
                operational_state=Computer.OperationalState.AVAILABLE
            ).count(),
            "active_session_count": UseSession.objects.filter(
                status=UseSession.Status.ACTIVE
            ).count(),
            "pending_occurrence_count": Occurrence.objects.filter(
                status__in=[Occurrence.Status.OPEN, Occurrence.Status.IN_REVIEW]
            ).count(),
            "active_schedule_count": OperatingSchedule.objects.filter(
                is_active=True
            ).count(),
            "active_notice_count": RoomNotice.objects.filter(is_active=True).count(),
            "screen_error": screen_error,
        }
    )
    return context


@management_profile_required
def dashboard(request):
    return _render_screen(
        request,
        content_template="supervisor/partials/dashboard.html",
        context=_dashboard_context(request),
    )


__all__ = ["dashboard"]
