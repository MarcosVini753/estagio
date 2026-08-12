from functools import wraps

from django.contrib import messages
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework.exceptions import APIException

from apps.access.services import get_demo_profile, get_demo_user_reference
from apps.computers.api.serializers import ComputerOperationalStateSerializer
from apps.computers.models import Computer
from apps.configuration.calendar import resolve_operating_day
from apps.configuration.selectors import get_active_room_notices
from apps.core.enums import DemoProfile
from apps.occurrences.api.serializers import (
    OccurrenceCreateSerializer,
    OccurrenceUpdateSerializer,
)
from apps.occurrences.models import Occurrence
from apps.occurrences.services import create_occurrence, transition_occurrence
from apps.operations.api.serializers import UsageSessionCorrectionSerializer
from apps.operations.availability import get_computers_availability
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.services import correct_usage_session
from apps.operations.services.computer_state import (
    change_computer_operational_state,
)

from .presenters import computer_rows, flatten_serializer_errors, normalize_search
from .views import _exception_message, _is_htmx

OPERATIONAL_PROFILES = {
    DemoProfile.ROOM_MONITOR,
    DemoProfile.LIBRARY_SUPERVISOR,
    DemoProfile.SYSTEM_ADMIN,
}

MONITOR_NAV_ITEMS = [
    {"key": "dashboard", "label": "Painel", "url_name": "web:monitor-dashboard"},
    {
        "key": "computers",
        "label": "Computadores",
        "url_name": "web:monitor-computers",
    },
    {
        "key": "occurrences",
        "label": "Ocorrências",
        "url_name": "web:monitor-occurrences",
    },
    {"key": "history", "label": "Histórico", "url_name": "web:monitor-history"},
]

MONITOR_SCREEN_META = {
    "dashboard": ("Operação da sala", "Painel operacional", ""),
    "computers": (
        "Operação da sala",
        "Computadores",
        "Pesquisar computador ou estado…",
    ),
    "occurrences": (
        "Operação da sala",
        "Ocorrências",
        "Pesquisar ocorrência, usuário ou computador…",
    ),
    "history": (
        "Operação da sala",
        "Histórico de uso",
        "Pesquisar sessão, usuário ou computador…",
    ),
}


def operational_profile_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if get_demo_profile(request) not in OPERATIONAL_PROFILES:
            messages.warning(
                request,
                "Selecione o perfil Monitor da Sala ou um perfil superior para "
                "acessar esta área.",
            )
            return redirect("web:home")
        return view(request, *args, **kwargs)

    return wrapped


def _allocations_queryset():
    return ComputerAllocation.objects.select_related("computer").order_by("sequence")


def _sessions_queryset():
    return UseSession.objects.select_related(
        "reservation", "start_shift"
    ).prefetch_related(
        Prefetch("allocations", queryset=_allocations_queryset()),
    )


def _decorate_sessions(sessions):
    values = list(sessions)
    for session in values:
        allocations = list(session.allocations.all())
        session.current_allocation = next(
            (allocation for allocation in allocations if allocation.ended_at is None),
            allocations[-1] if allocations else None,
        )
        session.status_label = session.get_status_display()
    return values


def _screen_context(request, *, screen, query="", search_url_name=None):
    nav_items = [
        {**item, "url": reverse(item["url_name"])} for item in MONITOR_NAV_ITEMS
    ]
    title, section_title, search_placeholder = MONITOR_SCREEN_META[screen]
    profile = get_demo_profile(request)
    return {
        "area": "monitor",
        "screen": screen,
        "screen_title": title,
        "section_title": section_title,
        "search_placeholder": search_placeholder,
        "search_url": reverse(search_url_name) if search_url_name else "",
        "query": query,
        "nav_items": nav_items,
        "current_profile_label": DemoProfile(profile).label,
        "current_user_reference": get_demo_user_reference(request),
        "active_notices": get_active_room_notices(),
        "area_switch_url": (
            reverse("web:supervisor-dashboard")
            if profile in {DemoProfile.LIBRARY_SUPERVISOR, DemoProfile.SYSTEM_ADMIN}
            else ""
        ),
        "area_switch_label": "Gestão da biblioteca",
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


def _redirect(request, name, **kwargs):
    url = reverse(name, kwargs=kwargs or None)
    if _is_htmx(request):
        response = render(request, "staff/partials/empty.html", status=200)
        response["HX-Redirect"] = url
        return response
    return redirect(name, **kwargs)


def _dashboard_context(request, *, screen_error=""):
    today = timezone.localdate()
    try:
        operating_day = resolve_operating_day(today)
    except APIException as error:
        operating_day = None
        screen_error = screen_error or _exception_message(error)
    active_sessions = _decorate_sessions(
        _sessions_queryset().filter(status=UseSession.Status.ACTIVE)
    )
    context = _screen_context(request, screen="dashboard")
    context.update(
        {
            "operating_day": operating_day,
            "active_sessions": active_sessions,
            "active_session_count": len(active_sessions),
            "open_occurrence_count": Occurrence.objects.filter(
                status__in=[Occurrence.Status.OPEN, Occurrence.Status.IN_REVIEW]
            ).count(),
            "confirmed_reservation_count": Reservation.objects.filter(
                status=Reservation.Status.CONFIRMED,
                starts_at__date=today,
            ).count(),
            "available_computer_count": Computer.objects.filter(
                operational_state=Computer.OperationalState.AVAILABLE
            ).count(),
            "screen_error": screen_error,
        }
    )
    return context


@operational_profile_required
def dashboard(request):
    return _render_screen(
        request,
        content_template="monitor/partials/dashboard.html",
        context=_dashboard_context(request),
    )


def _computers_context(request, *, screen_error=""):
    query = request.GET.get("q", "").strip()
    computers = list(Computer.objects.all())
    rows = []
    room = None
    try:
        room, _ = get_computers_availability(
            target_date=timezone.localdate(),
            computers=computers,
            user_reference=None,
        )
        rows = computer_rows(summary=room, computers=computers, query=query)
    except APIException as error:
        screen_error = screen_error or _exception_message(error)
    states = list(Computer.OperationalState.choices)
    context = _screen_context(
        request,
        screen="computers",
        query=query,
        search_url_name="web:monitor-computers",
    )
    context.update(
        {
            "computers": rows,
            "room": room,
            "state_choices": states,
            "screen_error": screen_error,
            "state_impact": request.session.pop("monitor_state_impact", None),
        }
    )
    return context


@operational_profile_required
def computers(request):
    return _render_screen(
        request,
        content_template="monitor/partials/computers.html",
        context=_computers_context(request),
    )


@operational_profile_required
@require_POST
def change_computer_state(request, pk):
    computer = get_object_or_404(Computer, pk=pk)
    serializer = ComputerOperationalStateSerializer(
        data={
            "operational_state": request.POST.get("operational_state"),
            "reason": request.POST.get("reason", ""),
        }
    )
    if not serializer.is_valid():
        return _render_screen(
            request,
            content_template="monitor/partials/computers.html",
            context=_computers_context(
                request,
                screen_error=flatten_serializer_errors(serializer.errors),
            ),
            status=400,
        )
    try:
        result = change_computer_operational_state(
            computer_id=computer.pk,
            new_state=serializer.validated_data["operational_state"],
            actor_profile=get_demo_profile(request),
            reason=serializer.validated_data.get("reason", ""),
        )
    except APIException as error:
        return _render_screen(
            request,
            content_template="monitor/partials/computers.html",
            context=_computers_context(
                request,
                screen_error=_exception_message(error),
            ),
            status=error.status_code,
        )
    request.session["monitor_state_impact"] = {
        **result.impact,
        "computer_code": result.computer.code,
        "new_state": result.computer.get_operational_state_display(),
        "reason": serializer.validated_data.get("reason", ""),
    }
    messages.success(request, f"Estado operacional de {computer.code} atualizado.")
    return _redirect(request, "web:monitor-computers")


def _occurrences_context(request, *, form_error="", form_data=None):
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    occurrences = Occurrence.objects.select_related("computer", "session", "allocation")
    if status_filter in Occurrence.Status.values:
        occurrences = occurrences.filter(status=status_filter)
    if query:
        occurrences = occurrences.filter(
            Q(description__icontains=query)
            | Q(reported_by_reference__icontains=query)
            | Q(computer__code__icontains=query)
        )
    occurrence_list = list(occurrences)
    for occurrence in occurrence_list:
        occurrence.status_label = occurrence.get_status_display()
        if occurrence.status == Occurrence.Status.OPEN:
            occurrence.transition_choices = [
                (Occurrence.Status.IN_REVIEW, Occurrence.Status.IN_REVIEW.label),
                (Occurrence.Status.CANCELLED, Occurrence.Status.CANCELLED.label),
            ]
        elif occurrence.status == Occurrence.Status.IN_REVIEW:
            occurrence.transition_choices = [
                (Occurrence.Status.RESOLVED, Occurrence.Status.RESOLVED.label),
                (Occurrence.Status.CANCELLED, Occurrence.Status.CANCELLED.label),
            ]
        else:
            occurrence.transition_choices = []
    context = _screen_context(
        request,
        screen="occurrences",
        query=query,
        search_url_name="web:monitor-occurrences",
    )
    context.update(
        {
            "occurrences": occurrence_list,
            "computer_choices": Computer.objects.all(),
            "status_choices": Occurrence.Status.choices,
            "status_filter": status_filter,
            "form_error": form_error,
            "form_data": form_data or {},
        }
    )
    return context


@operational_profile_required
def occurrences(request):
    if request.method == "POST":
        payload = {"description": request.POST.get("description", "")}
        for field in ("computer_id", "session_id", "allocation_id"):
            if request.POST.get(field):
                payload[field] = request.POST[field]
        serializer = OccurrenceCreateSerializer(data=payload)
        if not serializer.is_valid():
            return _render_screen(
                request,
                content_template="monitor/partials/occurrences.html",
                context=_occurrences_context(
                    request,
                    form_error=flatten_serializer_errors(serializer.errors),
                    form_data=payload,
                ),
                status=400,
            )
        data = serializer.validated_data
        try:
            create_occurrence(
                actor_profile=get_demo_profile(request),
                actor_reference=get_demo_user_reference(request),
                description=data["description"],
                computer=(
                    get_object_or_404(Computer, pk=data["computer_id"])
                    if data.get("computer_id")
                    else None
                ),
                session=(
                    get_object_or_404(UseSession, pk=data["session_id"])
                    if data.get("session_id")
                    else None
                ),
                allocation=(
                    get_object_or_404(ComputerAllocation, pk=data["allocation_id"])
                    if data.get("allocation_id")
                    else None
                ),
            )
        except APIException as error:
            return _render_screen(
                request,
                content_template="monitor/partials/occurrences.html",
                context=_occurrences_context(
                    request,
                    form_error=_exception_message(error),
                    form_data=payload,
                ),
                status=error.status_code,
            )
        messages.success(request, "Ocorrência registrada para acompanhamento.")
        return _redirect(request, "web:monitor-occurrences")

    return _render_screen(
        request,
        content_template="monitor/partials/occurrences.html",
        context=_occurrences_context(request),
    )


@operational_profile_required
@require_POST
def transition_occurrence_view(request, pk):
    get_object_or_404(Occurrence, pk=pk)
    serializer = OccurrenceUpdateSerializer(
        data={
            "status": request.POST.get("status"),
            "resolution_notes": request.POST.get("resolution_notes", ""),
        }
    )
    if not serializer.is_valid():
        error = flatten_serializer_errors(serializer.errors)
        status_code = 400
    else:
        try:
            transition_occurrence(
                occurrence_id=pk,
                actor_profile=get_demo_profile(request),
                **serializer.validated_data,
            )
        except APIException as api_error:
            error = _exception_message(api_error)
            status_code = api_error.status_code
        else:
            messages.success(request, "Ocorrência atualizada.")
            return _redirect(request, "web:monitor-occurrences")
    return _render_screen(
        request,
        content_template="monitor/partials/occurrences.html",
        context=_occurrences_context(request, form_error=error),
        status=status_code,
    )


def _history_context(request):
    query = request.GET.get("q", "").strip()
    sessions = _sessions_queryset().exclude(status=UseSession.Status.ACTIVE)
    if query:
        normalized = normalize_search(query)
        sessions = [
            session
            for session in sessions
            if normalized
            in normalize_search(
                " ".join(
                    [
                        str(session.pk),
                        session.user_reference,
                        session.status,
                        " ".join(
                            allocation.computer.code
                            for allocation in session.allocations.all()
                        ),
                    ]
                )
            )
        ]
    sessions = _decorate_sessions(sessions)
    context = _screen_context(
        request,
        screen="history",
        query=query,
        search_url_name="web:monitor-history",
    )
    context["sessions"] = sessions
    return context


@operational_profile_required
def history(request):
    return _render_screen(
        request,
        content_template="monitor/partials/history.html",
        context=_history_context(request),
    )


def _datetime_input(value):
    return timezone.localtime(value).strftime("%Y-%m-%dT%H:%M") if value else ""


def _history_detail_context(request, session, *, form_error="", form_data=None):
    session = _decorate_sessions([session])[0]
    context = _screen_context(request, screen="history")
    context.update(
        {
            "session": session,
            "form_error": form_error,
            "form_data": form_data
            or {
                "started_at": _datetime_input(session.started_at),
                "ended_at": _datetime_input(session.ended_at),
                "last_allocation_started_at": "",
                "last_allocation_ended_at": "",
                "reason": "",
            },
        }
    )
    return context


def _history_session(pk, *, include_active=False):
    sessions = _sessions_queryset()
    if not include_active:
        sessions = sessions.exclude(status=UseSession.Status.ACTIVE)
    return get_object_or_404(sessions, pk=pk)


@operational_profile_required
def history_detail(request, pk):
    return _render_screen(
        request,
        content_template="monitor/partials/history_detail.html",
        context=_history_detail_context(
            request,
            _history_session(pk, include_active=True),
        ),
    )


@operational_profile_required
@require_POST
def correct_history(request, pk):
    session = _history_session(pk)
    payload = {"reason": request.POST.get("reason", "")}
    for field in (
        "started_at",
        "ended_at",
        "last_allocation_started_at",
        "last_allocation_ended_at",
    ):
        if request.POST.get(field):
            payload[field] = request.POST[field]
    serializer = UsageSessionCorrectionSerializer(data=payload)
    if not serializer.is_valid():
        return _render_screen(
            request,
            content_template="monitor/partials/history_detail.html",
            context=_history_detail_context(
                request,
                session,
                form_error=flatten_serializer_errors(serializer.errors),
                form_data=request.POST.dict(),
            ),
            status=400,
        )
    try:
        correct_usage_session(
            session_id=session.pk,
            actor_profile=get_demo_profile(request),
            **serializer.validated_data,
        )
    except APIException as error:
        session = _history_session(pk)
        return _render_screen(
            request,
            content_template="monitor/partials/history_detail.html",
            context=_history_detail_context(
                request,
                session,
                form_error=_exception_message(error),
                form_data=request.POST.dict(),
            ),
            status=error.status_code,
        )
    messages.success(request, "Histórico corrigido com justificativa auditada.")
    return _redirect(request, "web:monitor-history-detail", pk=session.pk)
