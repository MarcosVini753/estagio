from functools import wraps

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.access.services import get_demo_profile
from apps.core.enums import DemoProfile

from ..http import is_htmx as _is_htmx

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

EXCEPTION_PREVIEW_SESSION_KEY = "supervisor_exception_preview"


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


__all__ = [
    "MANAGEMENT_PROFILES",
    "SCREEN_META",
    "SUPERVISOR_NAV_ITEMS",
    "_configuration_redirect",
    "_redirect",
    "_render_screen",
    "management_profile_required",
]

