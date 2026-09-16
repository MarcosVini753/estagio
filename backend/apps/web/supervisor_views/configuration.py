from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework import serializers
from rest_framework.exceptions import APIException

from apps.access.services import get_demo_profile
from apps.configuration.api.serializers import (
    BookingPolicyUpdateSerializer,
    RoomNoticeCreateSerializer,
    RoomNoticeUpdateSerializer,
    ShiftReplaceSerializer,
    ShiftSerializer,
)
from apps.configuration.models import ReportConfiguration, RoomNotice, Shift
from apps.configuration.services import (
    create_room_notice,
    create_shift,
    replace_shift,
    update_current_booking_policy,
    update_report_configuration,
    update_room_notice,
)
from apps.configuration.services import update_shift as update_shift_service

from ..http import service_error_message as _exception_message
from ..presenters import flatten_serializer_errors
from .common import (
    _configuration_redirect,
    _render_screen,
    management_profile_required,
)
from .context import _configuration_context, _configuration_error


class ReportConfigurationUpdateSerializer(serializers.Serializer):
    default_format = serializers.ChoiceField(
        choices=ReportConfiguration.ExportFormat.choices
    )
    group_by_shift = serializers.BooleanField()
    include_occurrences = serializers.BooleanField()


@management_profile_required
def configuration(request):
    return _render_screen(
        request,
        content_template="supervisor/partials/configuration.html",
        context=_configuration_context(request),
    )


@management_profile_required
@require_POST
def shifts(request):
    payload = {
        "name": request.POST.get("name", ""),
        "start_time": request.POST.get("start_time"),
        "end_time": request.POST.get("end_time"),
        "display_order": request.POST.get("display_order", 0),
        "valid_from": request.POST.get("valid_from"),
        "valid_until": request.POST.get("valid_until") or None,
        "is_active": "is_active" in request.POST,
    }
    serializer = ShiftSerializer(data=payload)
    if not serializer.is_valid():
        return _configuration_error(
            request,
            section="shifts",
            error=flatten_serializer_errors(serializer.errors),
            status=400,
            form_kind="shift-create",
        )
    try:
        create_shift(
            values=serializer.validated_data,
            actor_profile=get_demo_profile(request),
        )
    except APIException as error:
        return _configuration_error(
            request,
            section="shifts",
            error=_exception_message(error),
            status=error.status_code,
            form_kind="shift-create",
        )
    messages.success(request, "Turno criado sem alterar o calendário operacional.")
    return _configuration_redirect(request, "shifts")


@management_profile_required
@require_POST
def update_shift(request, pk):
    shift = get_object_or_404(Shift, pk=pk)
    if request.POST.get("intent") == "deactivate":
        payload = {"is_active": False}
    else:
        payload = {
            "name": request.POST.get("name", shift.name),
            "start_time": request.POST.get("start_time", shift.start_time),
            "end_time": request.POST.get("end_time", shift.end_time),
            "display_order": request.POST.get("display_order", shift.display_order),
            "valid_from": request.POST.get("valid_from", shift.valid_from),
            "valid_until": request.POST.get("valid_until") or None,
            "is_active": "is_active" in request.POST,
        }
    serializer = ShiftSerializer(shift, data=payload, partial=True)
    if not serializer.is_valid():
        return _configuration_error(
            request,
            section="shifts",
            error=flatten_serializer_errors(serializer.errors),
            status=400,
            form_kind=f"shift-edit-{shift.pk}",
        )
    try:
        update_shift_service(
            shift_id=shift.pk,
            values=serializer.validated_data,
            actor_profile=get_demo_profile(request),
        )
    except APIException as error:
        return _configuration_error(
            request,
            section="shifts",
            error=_exception_message(error),
            status=error.status_code,
            form_kind=f"shift-edit-{shift.pk}",
        )
    messages.success(request, "Turno atualizado.")
    return _configuration_redirect(request, "shifts")


@management_profile_required
@require_POST
def replace_shift_view(request, pk):
    get_object_or_404(Shift, pk=pk)
    serializer = ShiftReplaceSerializer(data=request.POST)
    if not serializer.is_valid():
        return _configuration_error(
            request,
            section="shifts",
            error=flatten_serializer_errors(serializer.errors),
            status=400,
            form_kind=f"shift-replace-{pk}",
        )
    try:
        replace_shift(
            shift_id=pk,
            actor_profile=get_demo_profile(request),
            **serializer.validated_data,
        )
    except APIException as error:
        return _configuration_error(
            request,
            section="shifts",
            error=_exception_message(error),
            status=error.status_code,
            form_kind=f"shift-replace-{pk}",
        )
    messages.success(request, "Nova versão do turno criada.")
    return _configuration_redirect(request, "shifts")


@management_profile_required
@require_POST
def notices(request):
    payload = {
        "notice_type": request.POST.get("notice_type"),
        "title": request.POST.get("title", ""),
        "message": request.POST.get("message", ""),
        "effective_from": request.POST.get("effective_from"),
        "effective_until": request.POST.get("effective_until"),
        "visible_from": request.POST.get("visible_from"),
        "visible_until": request.POST.get("visible_until") or None,
        "is_active": "is_active" in request.POST,
    }
    serializer = RoomNoticeCreateSerializer(data=payload)
    if not serializer.is_valid():
        return _configuration_error(
            request,
            section="notices",
            error=flatten_serializer_errors(serializer.errors),
            status=400,
            form_kind="notice-create",
        )
    try:
        create_room_notice(
            values=serializer.validated_data,
            actor_profile=get_demo_profile(request),
        )
    except APIException as error:
        return _configuration_error(
            request,
            section="notices",
            error=_exception_message(error),
            status=error.status_code,
            form_kind="notice-create",
        )
    messages.success(request, "Aviso publicado.")
    return _configuration_redirect(request, "notices")


@management_profile_required
@require_POST
def update_notice_state(request, pk):
    notice = get_object_or_404(RoomNotice, pk=pk)
    is_active = request.POST.get("is_active", "false").lower() in {
        "1",
        "true",
        "on",
        "yes",
    }
    serializer = RoomNoticeUpdateSerializer(data={"is_active": is_active})
    serializer.is_valid(raise_exception=True)
    update_room_notice(
        notice_id=notice.pk,
        values=serializer.validated_data,
        actor_profile=get_demo_profile(request),
    )
    messages.success(
        request,
        "Aviso ativado." if is_active else "Aviso desativado.",
    )
    return _configuration_redirect(request, "notices")


@management_profile_required
@require_POST
def configurations(request):
    kind = request.POST.get("kind")
    if kind == "booking":
        serializer = BookingPolicyUpdateSerializer(
            data={
                "cancellation_limit_minutes": request.POST.get(
                    "cancellation_limit_minutes"
                ),
                "max_future_reservations_per_user": request.POST.get(
                    "max_future_reservations_per_user"
                ),
            }
        )
        success_message = "Política de reservas versionada."
    elif kind == "report":
        serializer = ReportConfigurationUpdateSerializer(
            data={
                "default_format": request.POST.get("default_format"),
                "group_by_shift": "group_by_shift" in request.POST,
                "include_occurrences": "include_occurrences" in request.POST,
            }
        )
        success_message = "Parâmetros de relatório atualizados e auditados."
    else:
        return _configuration_error(
            request,
            section="policies",
            error="Tipo de configuração inválido.",
            status=400,
            form_kind="policies",
        )
    if not serializer.is_valid():
        return _configuration_error(
            request,
            section="policies",
            error=flatten_serializer_errors(serializer.errors),
            status=400,
            form_kind=f"{kind}-configuration",
        )
    if kind == "booking":
        policy = update_current_booking_policy(
            values=serializer.validated_data,
            actor_profile=get_demo_profile(request),
        )
        if policy.valid_from > timezone.localdate():
            formatted_date = policy.valid_from.strftime("%d/%m/%Y")
            success_message = (
                "Política de reservas versionada. A nova versão "
                f"vigorará a partir de {formatted_date}."
            )
        else:
            success_message = "Política de reservas atualizada."
    else:
        update_report_configuration(
            values=serializer.validated_data,
            actor_profile=get_demo_profile(request),
        )
    messages.success(request, success_message)
    return _configuration_redirect(request, "policies")


__all__ = [
    "configuration",
    "configurations",
    "notices",
    "replace_shift_view",
    "shifts",
    "update_notice_state",
    "update_shift",
]
