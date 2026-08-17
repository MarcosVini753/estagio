import hashlib
import json
from functools import wraps

from django.contrib import messages
from django.db.models import Exists, OuterRef, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework import serializers
from rest_framework.exceptions import APIException

from apps.access.services import get_demo_profile, get_demo_user_reference
from apps.computers.api.serializers import ComputerCreateSerializer, ComputerSerializer
from apps.computers.models import Computer
from apps.configuration.api.serializers import (
    BookingPolicyUpdateSerializer,
    CalendarExceptionSerializer,
    OperatingScheduleCreateSerializer,
    OperatingScheduleImpactSerializer,
    OperatingScheduleReplaceSerializer,
    RoomNoticeCreateSerializer,
    RoomNoticeUpdateSerializer,
    ShiftReplaceSerializer,
    ShiftSerializer,
)
from apps.configuration.calendar import resolve_operating_day
from apps.configuration.models import (
    CalendarException,
    OperatingSchedule,
    ReportConfiguration,
    RoomNotice,
    Shift,
    Weekday,
)
from apps.configuration.selectors import (
    get_active_room_notices,
    get_booking_policy_for_date,
)
from apps.configuration.services import (
    apply_calendar_exception,
    create_operating_schedule,
    create_room_notice,
    create_shift,
    preview_calendar_exception_impact,
    preview_operating_schedule_impact,
    replace_operating_schedule,
    replace_shift,
    update_current_booking_policy,
    update_report_configuration,
    update_room_notice,
)
from apps.configuration.services import (
    update_shift as update_shift_service,
)
from apps.core.api.errors import ScheduleChangeAffectsReservations
from apps.core.enums import DemoProfile
from apps.occurrences.models import Occurrence
from apps.operations.models import UseSession
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

from ..http import is_htmx as _is_htmx
from ..http import service_error_message as _exception_message
from ..presenters import flatten_serializer_errors

MANAGEMENT_PROFILES = {
    DemoProfile.LIBRARY_SUPERVISOR,
    DemoProfile.SYSTEM_ADMIN,
}

SUPERVISOR_NAV_ITEMS = [
    {
        "key": "dashboard",
        "label": "Visão geral",
        "url_name": "web:supervisor-dashboard",
    },
    {
        "key": "inventory",
        "label": "Inventário",
        "url_name": "web:supervisor-computers",
    },
    {
        "key": "calendar",
        "label": "Funcionamento",
        "url_name": "web:supervisor-configuration",
    },
    {
        "key": "reports",
        "label": "Relatórios",
        "url_name": "web:supervisor-reports",
    },
]

SCREEN_META = {
    "dashboard": ("Gestão da biblioteca", "Visão geral", ""),
    "inventory": (
        "Gestão da biblioteca",
        "Inventário de computadores",
        "Pesquisar código, patrimônio ou descrição…",
    ),
    "calendar": ("Gestão da biblioteca", "Funcionamento e parâmetros", ""),
    "reports": ("Gestão da biblioteca", "Relatórios e análises", ""),
}

SCHEDULE_PREVIEW_SESSION_KEY = "supervisor_schedule_preview"
EXCEPTION_PREVIEW_SESSION_KEY = "supervisor_exception_preview"


class ReportConfigurationUpdateSerializer(serializers.Serializer):
    default_format = serializers.ChoiceField(
        choices=ReportConfiguration.ExportFormat.choices
    )
    group_by_shift = serializers.BooleanField()
    include_occurrences = serializers.BooleanField()


def management_profile_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if get_demo_profile(request) not in MANAGEMENT_PROFILES:
            messages.warning(
                request,
                "Selecione o perfil Supervisor da Biblioteca para acessar esta área.",
            )
            return redirect("web:home")
        return view(request, *args, **kwargs)

    return wrapped


def _screen_context(request, *, screen, query="", search_url_name=None):
    profile = get_demo_profile(request)
    title, section_title, search_placeholder = SCREEN_META[screen]
    return {
        "area": "supervisor",
        "screen": screen,
        "screen_title": title,
        "section_title": section_title,
        "search_placeholder": search_placeholder,
        "search_url": reverse(search_url_name) if search_url_name else "",
        "query": query,
        "nav_items": [
            {**item, "url": reverse(item["url_name"])} for item in SUPERVISOR_NAV_ITEMS
        ],
        "current_profile_label": DemoProfile(profile).label,
        "current_user_reference": get_demo_user_reference(request),
        "active_notices": get_active_room_notices(),
        "area_switch_url": reverse("web:monitor-dashboard"),
        "area_switch_label": "Painel operacional",
    }


def _render_screen(request, *, content_template, context, status=200):
    context = {**context, "content_template": content_template}
    if request.headers.get("HX-Target") == "staff-content":
        template = "staff/partials/content.html"
    elif _is_htmx(request):
        template = "staff/partials/app.html"
    else:
        template = "staff/page.html"
    return render(request, template, context, status=status)


def _redirect(request, url):
    if _is_htmx(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url)


def _configuration_url(section):
    return f"{reverse('web:supervisor-configuration')}?section={section}"


def _configuration_redirect(request, section):
    return _redirect(request, _configuration_url(section))


def _dashboard_context(request, *, screen_error=""):
    today = timezone.localdate()
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


def _computers_context(request, *, form_error="", form_data=None, edit_id=None):
    query = request.GET.get("q", "").strip()
    computers = Computer.objects.all()
    if query:
        computers = computers.filter(
            Q(code__icontains=query)
            | Q(asset_number__icontains=query)
            | Q(description__icontains=query)
            | Q(notes__icontains=query)
        )
    context = _screen_context(
        request,
        screen="inventory",
        query=query,
        search_url_name="web:supervisor-computers",
    )
    context.update(
        {
            "computers": computers,
            "operational_states": Computer.OperationalState.choices,
            "form_error": form_error,
            "form_data": form_data or {},
            "edit_id": edit_id,
        }
    )
    return context


@management_profile_required
def computers(request):
    if request.method == "POST":
        payload = {
            "code": request.POST.get("code", ""),
            "asset_number": request.POST.get("asset_number") or None,
            "description": request.POST.get("description", ""),
            "operational_state": request.POST.get("operational_state"),
            "notes": request.POST.get("notes", ""),
        }
        serializer = ComputerCreateSerializer(data=payload)
        if not serializer.is_valid():
            return _render_screen(
                request,
                content_template="supervisor/partials/computers.html",
                context=_computers_context(
                    request,
                    form_error=flatten_serializer_errors(serializer.errors),
                    form_data=request.POST.dict(),
                ),
                status=400,
            )
        serializer.save()
        messages.success(request, "Computador incluído no inventário.")
        return _redirect(request, reverse("web:supervisor-computers"))
    return _render_screen(
        request,
        content_template="supervisor/partials/computers.html",
        context=_computers_context(request),
    )


@management_profile_required
@require_POST
def update_computer(request, pk):
    computer = get_object_or_404(Computer, pk=pk)
    serializer = ComputerSerializer(
        computer,
        data={
            "code": request.POST.get("code", computer.code),
            "asset_number": request.POST.get("asset_number") or None,
            "description": request.POST.get("description", ""),
            "notes": request.POST.get("notes", ""),
        },
        partial=True,
    )
    if not serializer.is_valid():
        return _render_screen(
            request,
            content_template="supervisor/partials/computers.html",
            context=_computers_context(
                request,
                form_error=flatten_serializer_errors(serializer.errors),
                form_data=request.POST.dict(),
                edit_id=computer.pk,
            ),
            status=400,
        )
    serializer.save()
    messages.success(request, f"Dados de {computer.code} atualizados.")
    return _redirect(request, reverse("web:supervisor-computers"))


def _window_string(day):
    if day is None or not day.is_open:
        return ""
    return ",".join(
        f"{window.opens_at:%H:%M}-{window.closes_at:%H:%M}"
        for window in day.windows.all()
    )


def _weekday_fields(*, post_data=None, schedule=None):
    existing = {day.weekday: day for day in schedule.days.all()} if schedule else {}
    return [
        {
            "weekday": value,
            "label": label,
            "name": f"windows_{value}",
            "value": (
                post_data.get(f"windows_{value}", "")
                if post_data is not None
                else _window_string(existing.get(value))
            ),
        }
        for value, label in Weekday.choices
    ]


def _parse_schedule_days(post_data):
    days = []
    for weekday in Weekday.values:
        raw_value = post_data.get(f"windows_{weekday}", "").strip()
        windows = []
        if raw_value:
            for display_order, raw_window in enumerate(raw_value.split(",")):
                pieces = [piece.strip() for piece in raw_window.split("-")]
                if len(pieces) != 2 or not all(pieces):
                    raise ValueError(
                        "Use o formato HH:MM-HH:MM, separando janelas por vírgula."
                    )
                windows.append(
                    {
                        "opens_at": pieces[0],
                        "closes_at": pieces[1],
                        "display_order": display_order,
                    }
                )
        days.append(
            {
                "weekday": weekday,
                "is_open": bool(windows),
                "windows": windows,
            }
        )
    return days


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


def _fingerprint(kind, values):
    serialized = json.dumps(
        {"kind": kind, "values": values},
        sort_keys=True,
        default=str,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def _remember_preview(request, *, key, values, impact):
    request.session[SCHEDULE_PREVIEW_SESSION_KEY] = {
        "key": key,
        "fingerprint": _fingerprint(key, values),
        "total": impact["total"],
        "reservation_ids": [
            reservation["id"] for reservation in impact["conflicting_reservations"]
        ],
    }


def _matching_preview(request, *, key, values):
    preview = request.session.get(SCHEDULE_PREVIEW_SESSION_KEY, {})
    return (
        preview
        if (
            preview.get("key") == key
            and preview.get("fingerprint") == _fingerprint(key, values)
            and isinstance(preview.get("reservation_ids"), list)
        )
        else None
    )


def _decorate_schedules(schedules, *, post_data=None, active_schedule_id=None):
    values = list(schedules)
    today = timezone.localdate()
    for schedule in values:
        schedule.type_label = schedule.get_schedule_type_display()
        schedule.can_replace = schedule.is_active and (
            schedule.valid_until is None
            or schedule.valid_until > max(today, schedule.valid_from)
        )
        schedule.weekday_fields = _weekday_fields(
            post_data=(
                post_data
                if active_schedule_id is not None and schedule.pk == active_schedule_id
                else None
            ),
            schedule=schedule,
        )
    return values


def _report_configuration():
    return ReportConfiguration.objects.filter(is_active=True).first()


def _configuration_context(
    request,
    *,
    section=None,
    form_error="",
    form_data=None,
    form_kind="",
    preview_result=None,
    preview_schedule_id=None,
):
    section = section or request.GET.get("section", "schedules")
    allowed_sections = {"schedules", "shifts", "exceptions", "notices", "policies"}
    if section not in allowed_sections:
        section = "schedules"
    active_schedule_id = int(preview_schedule_id) if preview_schedule_id else None
    schedules = _decorate_schedules(
        OperatingSchedule.objects.prefetch_related("days__windows"),
        post_data=form_data,
        active_schedule_id=active_schedule_id,
    )
    context = _screen_context(request, screen="calendar")
    context.update(
        {
            "configuration_section": section,
            "schedules": schedules,
            "schedule_types": OperatingSchedule.ScheduleType.choices,
            "new_weekday_fields": _weekday_fields(
                post_data=form_data if form_kind == "schedule-create" else None
            ),
            "shifts": Shift.objects.annotate(
                has_sessions=Exists(
                    UseSession.objects.filter(start_shift_id=OuterRef("pk"))
                )
            ),
            "exceptions": CalendarException.objects.all(),
            "exception_types": CalendarException.ExceptionType.choices,
            "notices": RoomNotice.objects.all(),
            "notice_types": RoomNotice.NoticeType.choices,
            "booking_policy": get_booking_policy_for_date(timezone.localdate()),
            "report_configuration": _report_configuration(),
            "report_formats": ReportConfiguration.ExportFormat.choices,
            "form_error": form_error,
            "form_data": form_data or {},
            "form_kind": form_kind,
            "preview_result": preview_result,
            "preview_schedule_id": active_schedule_id,
        }
    )
    return context


def _configuration_error(
    request,
    *,
    section,
    error,
    status,
    form_kind,
    form_data=None,
    preview_result=None,
    preview_schedule_id=None,
):
    return _render_screen(
        request,
        content_template="supervisor/partials/configuration.html",
        context=_configuration_context(
            request,
            section=section,
            form_error=error,
            form_data=form_data or request.POST,
            form_kind=form_kind,
            preview_result=preview_result,
            preview_schedule_id=preview_schedule_id,
        ),
        status=status,
    )


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
    if shift.use_sessions.exists() and "is_active" not in request.POST:
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
        _remember_preview(
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

    preview = _matching_preview(request, key="create", values=proposal)
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
            _remember_preview(
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
        _remember_preview(request, key=key, values=proposal, impact=impact)
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
    preview = _matching_preview(request, key=key, values=proposal)
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
            _remember_preview(
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
    fingerprint = _fingerprint(key, values)
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
        request.session[EXCEPTION_PREVIEW_SESSION_KEY] = {
            "key": key,
            "fingerprint": fingerprint,
            "total": impact["total"],
            "reservation_ids": [
                reservation["id"] for reservation in impact["conflicting_reservations"]
            ],
        }
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
    preview = request.session.get(EXCEPTION_PREVIEW_SESSION_KEY, {})
    if (
        preview.get("key") != key
        or preview.get("fingerprint") != fingerprint
        or not isinstance(preview.get("reservation_ids"), list)
    ):
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
            request.session[EXCEPTION_PREVIEW_SESSION_KEY] = {
                "key": key,
                "fingerprint": fingerprint,
                "total": impact["total"],
                "reservation_ids": [
                    reservation["id"]
                    for reservation in impact["conflicting_reservations"]
                ],
            }
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
        update_current_booking_policy(
            values=serializer.validated_data,
            actor_profile=get_demo_profile(request),
        )
    else:
        update_report_configuration(
            values=serializer.validated_data,
            actor_profile=get_demo_profile(request),
        )
    messages.success(request, success_message)
    return _configuration_redirect(request, "policies")


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
