from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.computers.api.serializers import ComputerCreateSerializer, ComputerSerializer
from apps.computers.models import Computer

from ..presenters import flatten_serializer_errors
from .common import _redirect, _render_screen, management_profile_required
from .context import _screen_context


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


__all__ = ["computers", "update_computer"]
