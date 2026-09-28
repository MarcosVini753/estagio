from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from rest_framework.exceptions import APIException

from apps.access.services import get_demo_profile
from apps.configuration.api.serializers import (
    CalendarExceptionSerializer,
    OperatingScheduleCreateSerializer,
    OperatingScheduleImpactSerializer,
    OperatingScheduleReplaceSerializer,
)
from apps.configuration.models import CalendarException, OperatingSchedule
from apps.configuration.services import (
    apply_calendar_exception,
    create_operating_schedule,
    preview_calendar_exception_impact,
    preview_operating_schedule_impact,
    replace_operating_schedule,
)
from apps.core.api.errors import ScheduleChangeAffectsReservations

from ..http import service_error_message as _exception_message
from ..presenters import flatten_serializer_errors
from .common import (
    _configuration_redirect,
    _render_screen,
    management_profile_required,
)
from .context import (
    _configuration_context,
    _configuration_error,
    _parse_schedule_days,
)
from .previews import (
    EXCEPTION_PREVIEW_SESSION_KEY,
    SCHEDULE_PREVIEW_SESSION_KEY,
    matching_preview,
    remember_preview,
)


def _schedule_proposal(data):
    return {
        key: data.get(key)
        for key in (
            "name",
            "schedule_type",
            "valid_from",
            "valid_until",
            "reason",
            "days",
        )
    }


def _schedule_payload(request, *, replacement=None):
    days = _parse_schedule_days(request.POST)
    if replacement is not None:
        return {
            "effective_from": request.POST.get("effective_from"),
            "name": request.POST.get("name", replacement.name),
            "reason": request.POST.get("reason", replacement.reason),
            "days": days,
            "confirm_cancellation": "confirm_cancellation" in request.POST,
        }
    return {
        "name": request.POST.get("name", ""),
        "schedule_type": request.POST.get("schedule_type"),
        "valid_from": request.POST.get("valid_from"),
        "valid_until": request.POST.get("valid_until") or None,
        "reason": request.POST.get("reason", ""),
        "days": days,
        "confirm_cancellation": "confirm_cancellation" in request.POST,
    }


@management_profile_required
@require_POST
def create_schedule(request):
    try:
        payload = _schedule_payload(request)
    except ValueError as error:
        return _configuration_error(
            request,
            section="schedules",
            error=str(error),
            status=400,
            form_kind="schedule-create",
        )
    intent = request.POST.get("intent", "preview")
    serializer_class = (
        OperatingScheduleImpactSerializer
        if intent == "preview"
        else OperatingScheduleCreateSerializer
    )
    serializer = serializer_class(data=payload)
    if not serializer.is_valid():
        return _configuration_error(
            request,
            section="schedules",
            error=flatten_serializer_errors(serializer.errors),
            status=400,
            form_kind="schedule-create",
        )
    proposal = _schedule_proposal(serializer.validated_data)
    if intent == "preview":
        preview_values = dict(proposal)
        preview_values.pop("name")
        preview_values.pop("reason")
        try:
            impact = preview_operating_schedule_impact(**preview_values)
        except APIException as error:
            return _configuration_error(
                request,
                section="schedules",
                error=_exception_message(error),
                status=error.status_code,
                form_kind="schedule-create",
            )
        remember_preview(
            request,
            key="create",
            values=proposal,
            impact=impact,
        )
        return _render_screen(
            request,
            content_template="supervisor/partials/configuration.html",
            context=_configuration_context(
                request,
                section="schedules",
                form_data=request.POST,
                form_kind="schedule-create",
                preview_result=impact,
            ),
        )

    preview = matching_preview(request, key="create", values=proposal)
    if preview is None:
        return _configuration_error(
            request,
            section="schedules",
            error=(
                "Visualize o impacto antes de confirmar. Se a proposta foi alterada, "
                "faça uma nova prévia."
            ),
            status=400,
            form_kind="schedule-create",
        )
    if preview["total"] and not serializer.validated_data["confirm_cancellation"]:
        return _configuration_error(
            request,
            section="schedules",
            error="Confirme explicitamente o cancelamento das reservas listadas.",
            status=400,
            form_kind="schedule-create",
        )
    try:
        create_operating_schedule(
            actor_profile=get_demo_profile(request),
            expected_conflict_ids=preview["reservation_ids"],
            **serializer.validated_data,
        )
    except APIException as error:
        impact = None
        error_message = _exception_message(error)
        if isinstance(error, ScheduleChangeAffectsReservations):
            preview_values = dict(proposal)
            preview_values.pop("name")
            preview_values.pop("reason")
            impact = preview_operating_schedule_impact(**preview_values)
            remember_preview(
                request,
                key="create",
                values=proposal,
                impact=impact,
            )
            error_message = (
                "O impacto mudou desde a prévia. Revise a lista atualizada e "
                "confirme novamente."
            )
        return _configuration_error(
            request,
            section="schedules",
            error=error_message,
            status=error.status_code,
            form_kind="schedule-create",
            preview_result=impact,
        )
    request.session.pop(SCHEDULE_PREVIEW_SESSION_KEY, None)
    messages.success(request, "Calendário criado com impacto confirmado.")
    return _configuration_redirect(request, "schedules")


@management_profile_required
@require_POST
def replace_schedule(request, pk):
    schedule = get_object_or_404(
        OperatingSchedule.objects.prefetch_related("days__windows"), pk=pk
    )
    try:
        payload = _schedule_payload(request, replacement=schedule)
    except ValueError as error:
        return _configuration_error(
            request,
            section="schedules",
            error=str(error),
            status=400,
            form_kind=f"schedule-replace-{pk}",
            preview_schedule_id=pk,
        )
    serializer = OperatingScheduleReplaceSerializer(data=payload)
    if not serializer.is_valid():
        return _configuration_error(
            request,
            section="schedules",
            error=flatten_serializer_errors(serializer.errors),
            status=400,
            form_kind=f"schedule-replace-{pk}",
            preview_schedule_id=pk,
        )
    data = serializer.validated_data
    proposal = {
        "name": data.get("name", schedule.name),
        "schedule_type": schedule.schedule_type,
        "valid_from": data["effective_from"],
        "valid_until": schedule.valid_until,
        "reason": data.get("reason", schedule.reason),
        "days": data.get("days") or _parse_schedule_days(request.POST),
    }
    key = f"replace:{schedule.pk}"
    if request.POST.get("intent", "preview") == "preview":
        preview_values = dict(proposal)
        preview_values.pop("name")
        preview_values.pop("reason")
        try:
            impact = preview_operating_schedule_impact(**preview_values)
        except APIException as error:
            return _configuration_error(
                request,
                section="schedules",
                error=_exception_message(error),
                status=error.status_code,
                form_kind=f"schedule-replace-{pk}",
                preview_schedule_id=pk,
            )
        remember_preview(request, key=key, values=proposal, impact=impact)
        return _render_screen(
            request,
            content_template="supervisor/partials/configuration.html",
            context=_configuration_context(
                request,
                section="schedules",
                form_data=request.POST,
                form_kind=f"schedule-replace-{pk}",
                preview_result=impact,
                preview_schedule_id=pk,
            ),
        )
    preview = matching_preview(request, key=key, values=proposal)
    if preview is None:
        return _configuration_error(
            request,
            section="schedules",
            error="A proposta foi alterada. Visualize o impacto novamente.",
            status=400,
            form_kind=f"schedule-replace-{pk}",
            preview_schedule_id=pk,
        )
    if preview["total"] and not data["confirm_cancellation"]:
        return _configuration_error(
            request,
            section="schedules",
            error="Confirme explicitamente o cancelamento das reservas listadas.",
            status=400,
            form_kind=f"schedule-replace-{pk}",
            preview_schedule_id=pk,
        )
    try:
        replace_operating_schedule(
            schedule_id=schedule.pk,
            actor_profile=get_demo_profile(request),
            expected_conflict_ids=preview["reservation_ids"],
            **data,
        )
    except APIException as error:
        impact = None
        error_message = _exception_message(error)
        if isinstance(error, ScheduleChangeAffectsReservations):
            preview_values = dict(proposal)
            preview_values.pop("name")
            preview_values.pop("reason")
            impact = preview_operating_schedule_impact(**preview_values)
            remember_preview(
                request,
                key=key,
                values=proposal,
                impact=impact,
            )
            error_message = (
                "O impacto mudou desde a prévia. Revise a lista atualizada e "
                "confirme novamente."
            )
        return _configuration_error(
            request,
            section="schedules",
            error=error_message,
            status=error.status_code,
            form_kind=f"schedule-replace-{pk}",
            preview_schedule_id=pk,
            preview_result=impact,
        )
    request.session.pop(SCHEDULE_PREVIEW_SESSION_KEY, None)
    messages.success(request, "Nova versão do calendário criada.")
    return _configuration_redirect(request, "schedules")


def _exception_payload(request, instance=None):
    payload = {
        "date": request.POST.get("date", instance.date if instance else ""),
        "exception_type": request.POST.get(
            "exception_type", instance.exception_type if instance else ""
        ),
        "description": request.POST.get("description", ""),
        "confirm_cancellation": "confirm_cancellation" in request.POST,
    }
    if request.POST.get("opens_at"):
        payload["opens_at"] = request.POST["opens_at"]
    if request.POST.get("closes_at"):
        payload["closes_at"] = request.POST["closes_at"]
    return payload


@management_profile_required
@require_POST
def exceptions(request):
    instance = None
    if request.POST.get("exception_id"):
        instance = get_object_or_404(CalendarException, pk=request.POST["exception_id"])
    payload = _exception_payload(request, instance)
    serializer = CalendarExceptionSerializer(instance, data=payload)
    if not serializer.is_valid():
        return _configuration_error(
            request,
            section="exceptions",
            error=flatten_serializer_errors(serializer.errors),
            status=400,
            form_kind="exception",
        )
    values = dict(serializer.validated_data)
    values.pop("confirm_cancellation", None)
    values.pop("notify_users", None)
    values.pop("notice", None)
    key = f"exception:{instance.pk if instance else 'new'}"
    if request.POST.get("intent", "preview") == "preview":
        try:
            impact = preview_calendar_exception_impact(values=values)
        except APIException as error:
            return _configuration_error(
                request,
                section="exceptions",
                error=_exception_message(error),
                status=error.status_code,
                form_kind="exception",
            )
        remember_preview(
            request,
            key=key,
            values=values,
            impact=impact,
            session_key=EXCEPTION_PREVIEW_SESSION_KEY,
        )
        return _render_screen(
            request,
            content_template="supervisor/partials/configuration.html",
            context=_configuration_context(
                request,
                section="exceptions",
                form_data=request.POST,
                form_kind="exception",
                preview_result=impact,
            ),
        )
    preview = matching_preview(
        request,
        key=key,
        values=values,
        session_key=EXCEPTION_PREVIEW_SESSION_KEY,
    )
    if preview is None:
        return _configuration_error(
            request,
            section="exceptions",
            error="A proposta foi alterada. Visualize o impacto novamente.",
            status=400,
            form_kind="exception",
        )
    confirmed = "confirm_cancellation" in request.POST
    if preview["total"] and not confirmed:
        return _configuration_error(
            request,
            section="exceptions",
            error="Confirme explicitamente o cancelamento das reservas listadas.",
            status=400,
            form_kind="exception",
        )
    try:
        apply_calendar_exception(
            exception_id=instance.pk if instance else None,
            values=values,
            actor_profile=get_demo_profile(request),
            confirm_cancellation=confirmed,
            expected_conflict_ids=preview["reservation_ids"],
        )
    except APIException as error:
        impact = None
        error_message = _exception_message(error)
        if isinstance(error, ScheduleChangeAffectsReservations):
            impact = preview_calendar_exception_impact(values=values)
            remember_preview(
                request,
                key=key,
                values=values,
                impact=impact,
                session_key=EXCEPTION_PREVIEW_SESSION_KEY,
            )
            error_message = (
                "O impacto mudou desde a prévia. Revise a lista atualizada e "
                "confirme novamente."
            )
        return _configuration_error(
            request,
            section="exceptions",
            error=error_message,
            status=error.status_code,
            form_kind="exception",
            preview_result=impact,
        )
    request.session.pop(EXCEPTION_PREVIEW_SESSION_KEY, None)
    messages.success(request, "Exceção de calendário aplicada com impacto confirmado.")
    return _configuration_redirect(request, "exceptions")


__all__ = ["create_schedule", "exceptions", "replace_schedule"]
