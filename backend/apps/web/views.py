from datetime import timedelta
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework.exceptions import APIException

from apps.access.api.serializers import DemoProfileSelectionSerializer
from apps.access.services import (
    get_demo_affiliation_type,
    get_demo_institutional_unit,
    get_demo_profile,
    get_demo_user_reference,
    select_demo_profile,
)
from apps.computers.models import Computer
from apps.configuration.selectors import get_active_room_notices
from apps.core.enums import AffiliationType, DemoProfile
from apps.occurrences.api.serializers import OccurrenceCreateSerializer
from apps.occurrences.models import Occurrence
from apps.occurrences.services import create_occurrence
from apps.operations.api.serializers import (
    ComputerSwitchSerializer,
    ReservationCancelSerializer,
    ReservationCreateSerializer,
    UsageSessionFinishSerializer,
    UsageSessionStartSerializer,
)
from apps.operations.availability import get_computers_availability
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.services import (
    cancel_reservation,
    create_reservation,
    finish_usage_session,
    start_usage_session,
    switch_computer,
)

from .presenters import (
    computer_rows,
    flatten_serializer_errors,
    immediate_duration_options,
    normalize_search,
    reservation_duration_options,
    slot_rows,
)

NAV_ITEMS = [
    {"key": "computers", "label": "Computadores", "url_name": "web:computers"},
    {"key": "agenda", "label": "Agenda", "url_name": "web:agenda"},
    {"key": "session", "label": "Sessão", "url_name": "web:session"},
    {"key": "problems", "label": "Problemas", "url_name": "web:problems"},
]

SCREEN_META = {
    "computers": {
        "title": "Sala de Informática",
        "section_title": "Computadores",
        "search_placeholder": "Pesquisar computador ou status…",
    },
    "agenda": {
        "title": "Sala de Informática",
        "section_title": "Agenda",
        "search_placeholder": "Pesquisar reserva ou computador…",
    },
    "session": {
        "title": "Sala de Informática",
        "section_title": "Sessão",
        "search_placeholder": "",
    },
    "problems": {
        "title": "Sala de Informática",
        "section_title": "Problemas",
        "search_placeholder": "Pesquisar problema ou computador…",
    },
}


def _is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _room_user_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if get_demo_profile(request) != DemoProfile.ROOM_USER:
            messages.warning(
                request,
                "Selecione o perfil Usuário da Sala para acessar esta área.",
            )
            return redirect("web:home")
        return view(request, *args, **kwargs)

    return wrapped


def _active_session(request):
    reference = get_demo_user_reference(request)
    if not reference:
        return None
    allocation_queryset = ComputerAllocation.objects.select_related(
        "computer"
    ).order_by("sequence")
    return (
        UseSession.objects.filter(
            user_reference=reference,
            status=UseSession.Status.ACTIVE,
        )
        .prefetch_related(Prefetch("allocations", queryset=allocation_queryset))
        .first()
    )


def _active_allocation(active_session):
    if active_session is None:
        return None
    return next(
        (
            allocation
            for allocation in active_session.allocations.all()
            if allocation.ended_at is None
        ),
        None,
    )


def _day_and_date(request):
    day = request.GET.get("day", "today")
    if day not in {"today", "tomorrow"}:
        day = "today"
    today = timezone.localdate()
    return day, today if day == "today" else today + timedelta(days=1)


def _exception_message(error: APIException) -> str:
    detail = error.detail
    if isinstance(detail, dict):
        detail = detail.get("detail", detail)
    if isinstance(detail, (list, tuple)):
        return " ".join(str(item) for item in detail)
    return str(detail)


def _redirect_response(request, url_name: str, **kwargs):
    url = reverse(url_name, kwargs=kwargs or None)
    if _is_htmx(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url_name, **kwargs)


def _screen_base_context(request, *, screen: str, query: str = ""):
    index = next(index for index, item in enumerate(NAV_ITEMS) if item["key"] == screen)
    nav_items = [{**item, "url": reverse(item["url_name"])} for item in NAV_ITEMS]
    meta = SCREEN_META[screen]
    return {
        "screen": screen,
        "screen_title": meta["title"],
        "section_title": meta["section_title"],
        "search_placeholder": meta["search_placeholder"],
        "query": query,
        "nav_items": nav_items,
        "nav_previous_key": nav_items[index - 1]["key"] if index > 0 else "",
        "nav_next_key": (
            nav_items[index + 1]["key"] if index < len(nav_items) - 1 else ""
        ),
        "current_profile_label": DemoProfile.ROOM_USER.label,
        "current_user_reference": get_demo_user_reference(request),
        "active_notices": get_active_room_notices(),
    }


def _render_screen(request, *, content_template: str, context: dict, status=200):
    context = {**context, "content_template": content_template}
    if request.headers.get("HX-Target") == "screen-content":
        template = "room_user/partials/screen.html"
    elif _is_htmx(request):
        template = "room_user/partials/app.html"
    else:
        template = "room_user/page.html"
    return render(request, template, context, status=status)


def home(request):
    form_data = {}
    form_error = ""
    if request.method == "POST":
        profile = request.POST.get("profile", "")
        payload = {"profile": profile}
        form_data = request.POST.dict()
        if profile == DemoProfile.ROOM_USER:
            for field in (
                "user_reference",
                "affiliation_type",
                "institutional_unit",
            ):
                if value := request.POST.get(field):
                    payload[field] = value
        serializer = DemoProfileSelectionSerializer(data=payload)
        if serializer.is_valid():
            selected = select_demo_profile(request, **serializer.validated_data)
            if selected == DemoProfile.ROOM_USER:
                return redirect("web:computers")
            return redirect("web:profile-unavailable")
        form_error = flatten_serializer_errors(serializer.errors)

    current_profile = get_demo_profile(request)
    current_profile_label = (
        DemoProfile(current_profile).label if current_profile else "Nenhum perfil"
    )
    profiles = [
        {
            "value": value,
            "label": label,
            "is_room_user": value == DemoProfile.ROOM_USER,
        }
        for value, label in DemoProfile.choices
    ]
    return render(
        request,
        "home.html",
        {
            "profiles": profiles,
            "affiliation_types": [
                (value, label)
                for value, label in AffiliationType.choices
                if value != AffiliationType.NOT_INFORMED
            ],
            "active_notices": get_active_room_notices(),
            "current_profile_label": current_profile_label,
            "form_data": form_data,
            "form_error": form_error,
        },
        status=400 if form_error else 200,
    )


def profile_unavailable(request):
    profile = get_demo_profile(request)
    if profile == DemoProfile.ROOM_USER:
        return redirect("web:computers")
    return render(
        request,
        "profile_unavailable.html",
        {
            "profile_label": (
                DemoProfile(profile).label if profile else "Perfil não selecionado"
            )
        },
    )


@_room_user_required
def computers(request):
    day, target_date = _day_and_date(request)
    query = request.GET.get("q", "").strip()
    computer_list = list(Computer.objects.all())
    screen_error = ""
    summary = None
    rows = []
    try:
        summary, _ = get_computers_availability(
            target_date=target_date,
            computers=computer_list,
            user_reference=get_demo_user_reference(request),
        )
        rows = computer_rows(summary=summary, computers=computer_list, query=query)
    except APIException as error:
        screen_error = _exception_message(error)

    context = _screen_base_context(request, screen="computers", query=query)
    context.update(
        {
            "day": day,
            "target_date": target_date,
            "summary": summary,
            "computers": rows,
            "screen_error": screen_error,
            "active_session": _active_session(request),
            "today_query": urlencode({"day": "today", "q": query}),
            "tomorrow_query": urlencode({"day": "tomorrow", "q": query}),
        }
    )
    return _render_screen(
        request,
        content_template="room_user/partials/computers.html",
        context=context,
    )


def _computer_detail_context(request, *, computer, day, selected_starts_at=""):
    today = timezone.localdate()
    target_date = today if day == "today" else today + timedelta(days=1)
    summary, slots_by_computer = get_computers_availability(
        target_date=target_date,
        computers=[computer],
        user_reference=get_demo_user_reference(request),
    )
    row = computer_rows(summary=summary, computers=[computer], query="")[0]
    raw_slots = slots_by_computer[computer.pk]
    active_session = _active_session(request)
    active_allocation = _active_allocation(active_session)
    return {
        "computer": computer,
        "computer_row": row,
        "day": day,
        "target_date": target_date,
        "slots": slot_rows(raw_slots, selected_starts_at),
        "selected_starts_at": selected_starts_at,
        "reservation_options": reservation_duration_options(
            raw_slots, selected_starts_at
        ),
        "immediate_options": immediate_duration_options(row["immediate_usage"]),
        "active_session": active_session,
        "active_allocation": active_allocation,
    }


def _render_computer_detail(request, context, *, status=200):
    template = (
        "room_user/modals/computer_detail.html"
        if _is_htmx(request)
        else "room_user/computer_detail_page.html"
    )
    return render(request, template, context, status=status)


def _computer_action_error_response(
    request,
    *,
    computer_id,
    day: str,
    form_error: str,
    status: int,
    selected_starts_at: str = "",
):
    try:
        computer = Computer.objects.get(pk=computer_id)
    except Computer.DoesNotExist, TypeError, ValueError:
        return _render_computer_detail(
            request,
            {"computer": None, "day": day, "form_error": form_error},
            status=status,
        )

    try:
        context = _computer_detail_context(
            request,
            computer=computer,
            day=day,
            selected_starts_at=selected_starts_at,
        )
    except APIException:
        context = {"computer": computer, "day": day}
    context["form_error"] = form_error
    return _render_computer_detail(request, context, status=status)


@_room_user_required
def computer_detail(request, pk):
    computer = get_object_or_404(Computer, pk=pk)
    day, _ = _day_and_date(request)
    try:
        context = _computer_detail_context(
            request,
            computer=computer,
            day=day,
            selected_starts_at=request.GET.get("starts_at", ""),
        )
    except APIException as error:
        context = {
            "computer": computer,
            "day": day,
            "form_error": _exception_message(error),
        }
        return _render_computer_detail(request, context, status=error.status_code)
    return _render_computer_detail(request, context)


@_room_user_required
@require_POST
def create_booking(request):
    payload = {
        field: request.POST.get(field)
        for field in ("computer_id", "starts_at", "slot_count")
    }
    serializer = ReservationCreateSerializer(data=payload)
    computer_id = request.POST.get("computer_id")
    day = request.POST.get("day", "today")
    day = day if day in {"today", "tomorrow"} else "today"
    selected_starts_at = request.POST.get("starts_at", "")
    if not serializer.is_valid():
        return _computer_action_error_response(
            request,
            computer_id=computer_id,
            day=day,
            selected_starts_at=selected_starts_at,
            form_error=flatten_serializer_errors(serializer.errors),
            status=400,
        )

    get_object_or_404(Computer, pk=serializer.validated_data["computer_id"])
    try:
        create_reservation(
            **serializer.validated_data,
            user_reference=get_demo_user_reference(request),
            affiliation_type=get_demo_affiliation_type(request),
            institutional_unit=get_demo_institutional_unit(request),
            created_by_profile=get_demo_profile(request),
        )
    except APIException as error:
        return _computer_action_error_response(
            request,
            computer_id=computer_id,
            day=day,
            selected_starts_at=selected_starts_at,
            form_error=_exception_message(error),
            status=error.status_code,
        )

    messages.success(request, "Reserva confirmada com sucesso.")
    return _redirect_response(request, "web:agenda")


def _user_reservation_or_404(request, pk):
    return get_object_or_404(
        Reservation.objects.select_related("computer", "booking_policy"),
        pk=pk,
        user_reference=get_demo_user_reference(request),
    )


@_room_user_required
@require_POST
def cancel_booking(request, pk):
    reservation = _user_reservation_or_404(request, pk)
    serializer = ReservationCancelSerializer(
        data={"reason": request.POST.get("reason", "")}
    )
    if not serializer.is_valid():
        return _render_screen(
            request,
            content_template="room_user/partials/agenda.html",
            context=_agenda_context(
                request,
                screen_error=flatten_serializer_errors(serializer.errors),
            ),
            status=400,
        )
    try:
        cancel_reservation(
            reservation_id=reservation.pk,
            actor_profile=get_demo_profile(request),
            actor_reference=get_demo_user_reference(request),
            **serializer.validated_data,
        )
    except APIException as error:
        return _render_screen(
            request,
            content_template="room_user/partials/agenda.html",
            context=_agenda_context(
                request,
                screen_error=_exception_message(error),
            ),
            status=error.status_code,
        )
    messages.success(request, "Reserva cancelada.")
    return _redirect_response(request, "web:agenda")


@_room_user_required
@require_POST
def check_in_booking(request, pk):
    reservation = _user_reservation_or_404(request, pk)
    serializer = UsageSessionStartSerializer(
        data={"computer_id": reservation.computer_id, "reservation_id": reservation.pk}
    )
    serializer.is_valid(raise_exception=True)
    try:
        start_usage_session(
            **serializer.validated_data,
            actor_profile=get_demo_profile(request),
            actor_reference=get_demo_user_reference(request),
            affiliation_type=get_demo_affiliation_type(request),
            institutional_unit=get_demo_institutional_unit(request),
        )
    except APIException as error:
        return _render_screen(
            request,
            content_template="room_user/partials/agenda.html",
            context=_agenda_context(
                request,
                screen_error=_exception_message(error),
            ),
            status=error.status_code,
        )
    messages.success(request, "Entrada registrada a partir da reserva.")
    return _redirect_response(request, "web:session")


def _agenda_context(request, *, screen_error=""):
    query = request.GET.get("q", "").strip()
    normalized_query = normalize_search(query)
    now = timezone.now()
    reservations = list(
        Reservation.objects.filter(user_reference=get_demo_user_reference(request))
        .select_related("computer", "booking_policy")
        .order_by("-starts_at")
    )
    visible = []
    for reservation in reservations:
        reservation.status_label = reservation.get_status_display()
        reservation.can_cancel_ui = (
            reservation.status == Reservation.Status.CONFIRMED
            and now < reservation.starts_at
        )
        reservation.can_check_in_ui = (
            reservation.status == Reservation.Status.CONFIRMED
            and reservation.starts_at <= now <= reservation.check_in_deadline_at
        )
        searchable = normalize_search(
            " ".join(
                [
                    reservation.computer.code,
                    reservation.computer.description,
                    reservation.status,
                    reservation.status_label,
                    reservation.cancellation_reason,
                ]
            )
        )
        if not normalized_query or normalized_query in searchable:
            visible.append(reservation)
    context = _screen_base_context(request, screen="agenda", query=query)
    context.update(
        {
            "reservations": visible,
            "confirmed_count": sum(
                reservation.status == Reservation.Status.CONFIRMED
                for reservation in reservations
            ),
            "screen_error": screen_error,
        }
    )
    return context


@_room_user_required
def agenda(request):
    return _render_screen(
        request,
        content_template="room_user/partials/agenda.html",
        context=_agenda_context(request),
    )


@_room_user_required
def session(request):
    return _render_screen(
        request,
        content_template="room_user/partials/session.html",
        context=_session_context(request),
    )


def _session_context(request, *, screen_error=""):
    active_session = _active_session(request)
    context = _screen_base_context(request, screen="session")
    context.update(
        {
            "active_session": active_session,
            "active_allocation": _active_allocation(active_session),
            "screen_error": screen_error,
        }
    )
    return context


@_room_user_required
@require_POST
def start_session(request):
    serializer = UsageSessionStartSerializer(
        data={
            "computer_id": request.POST.get("computer_id"),
            "slot_count": request.POST.get("slot_count"),
        }
    )
    if not serializer.is_valid():
        return _computer_action_error_response(
            request,
            computer_id=request.POST.get("computer_id"),
            day="today",
            form_error=flatten_serializer_errors(serializer.errors),
            status=400,
        )
    get_object_or_404(Computer, pk=serializer.validated_data["computer_id"])
    try:
        start_usage_session(
            **serializer.validated_data,
            actor_profile=get_demo_profile(request),
            actor_reference=get_demo_user_reference(request),
            affiliation_type=get_demo_affiliation_type(request),
            institutional_unit=get_demo_institutional_unit(request),
        )
    except APIException as error:
        return _computer_action_error_response(
            request,
            computer_id=serializer.validated_data["computer_id"],
            day="today",
            form_error=_exception_message(error),
            status=error.status_code,
        )
    messages.success(request, "Entrada registrada. Bom uso!")
    return _redirect_response(request, "web:session")


@_room_user_required
@require_POST
def switch_session_computer(request, pk):
    active_session = get_object_or_404(
        UseSession,
        pk=pk,
        status=UseSession.Status.ACTIVE,
        user_reference=get_demo_user_reference(request),
    )
    serializer = ComputerSwitchSerializer(
        data={
            "computer_id": request.POST.get("computer_id"),
            "reason": request.POST.get("reason", ""),
        }
    )
    if not serializer.is_valid():
        return _computer_action_error_response(
            request,
            computer_id=request.POST.get("computer_id"),
            day="today",
            form_error=flatten_serializer_errors(serializer.errors),
            status=400,
        )
    get_object_or_404(Computer, pk=serializer.validated_data["computer_id"])
    try:
        switch_computer(
            session_id=active_session.pk,
            actor_profile=get_demo_profile(request),
            actor_reference=get_demo_user_reference(request),
            **serializer.validated_data,
        )
    except APIException as error:
        return _computer_action_error_response(
            request,
            computer_id=serializer.validated_data["computer_id"],
            day="today",
            form_error=_exception_message(error),
            status=error.status_code,
        )
    messages.success(request, "Troca de computador registrada.")
    return _redirect_response(request, "web:session")


@_room_user_required
@require_POST
def finish_session(request, pk):
    active_session = get_object_or_404(
        UseSession,
        pk=pk,
        status=UseSession.Status.ACTIVE,
        user_reference=get_demo_user_reference(request),
    )
    serializer = UsageSessionFinishSerializer(
        data={"reason": request.POST.get("reason", "")}
    )
    if not serializer.is_valid():
        return _render_screen(
            request,
            content_template="room_user/partials/session.html",
            context=_session_context(
                request,
                screen_error=flatten_serializer_errors(serializer.errors),
            ),
            status=400,
        )
    try:
        finish_usage_session(
            session_id=active_session.pk,
            actor_profile=get_demo_profile(request),
            actor_reference=get_demo_user_reference(request),
            **serializer.validated_data,
        )
    except APIException as error:
        return _render_screen(
            request,
            content_template="room_user/partials/session.html",
            context=_session_context(
                request,
                screen_error=_exception_message(error),
            ),
            status=error.status_code,
        )
    messages.success(request, "Saída registrada e computador liberado.")
    return _redirect_response(request, "web:computers")


def _problems_context(request, *, form_error="", form_data=None):
    query = request.GET.get("q", "").strip()
    occurrences = Occurrence.objects.filter(
        reported_by_reference=get_demo_user_reference(request)
    ).select_related("computer", "session", "allocation")
    if query:
        occurrences = occurrences.filter(
            Q(description__icontains=query)
            | Q(computer__code__icontains=query)
            | Q(status__icontains=query)
        )
    occurrence_list = list(occurrences)
    for occurrence in occurrence_list:
        occurrence.status_label = occurrence.get_status_display()
    active_session = _active_session(request)
    active_allocation = _active_allocation(active_session)
    selected_computer_id = (
        (form_data or {}).get("computer_id")
        or request.GET.get("computer_id")
        or (active_allocation.computer_id if active_allocation else "")
    )
    context = _screen_base_context(request, screen="problems", query=query)
    context.update(
        {
            "occurrences": occurrence_list,
            "computer_choices": Computer.objects.all(),
            "selected_computer_id": str(selected_computer_id),
            "form_error": form_error,
            "form_description": (form_data or {}).get("description", ""),
            "active_allocation": active_allocation,
        }
    )
    return context


@_room_user_required
def problems(request):
    if request.method == "POST":
        response_status = 400
        payload = {
            "computer_id": request.POST.get("computer_id"),
            "description": request.POST.get("description"),
        }
        serializer = OccurrenceCreateSerializer(data=payload)
        if serializer.is_valid():
            data = serializer.validated_data
            computer = (
                get_object_or_404(Computer, pk=data["computer_id"])
                if data.get("computer_id")
                else None
            )
            active_session = _active_session(request)
            active_allocation = _active_allocation(active_session)
            link_active_session = bool(
                computer
                and active_allocation
                and active_allocation.computer_id == computer.pk
            )
            try:
                create_occurrence(
                    actor_profile=get_demo_profile(request),
                    actor_reference=get_demo_user_reference(request),
                    description=data["description"],
                    computer=computer,
                    session=active_session if link_active_session else None,
                    allocation=active_allocation if link_active_session else None,
                )
            except APIException as error:
                form_error = _exception_message(error)
                response_status = error.status_code
            else:
                messages.success(request, "Problema informado à equipe da sala.")
                return _redirect_response(request, "web:problems")
        else:
            form_error = flatten_serializer_errors(serializer.errors)
        context = _problems_context(
            request,
            form_error=form_error,
            form_data=payload,
        )
        return _render_screen(
            request,
            content_template="room_user/partials/problems.html",
            context=context,
            status=response_status,
        )

    return _render_screen(
        request,
        content_template="room_user/partials/problems.html",
        context=_problems_context(request),
    )
