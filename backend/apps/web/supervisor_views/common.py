from django.urls import reverse

from apps.core.enums import DemoProfile

from ..http import redirect_url_response, render_staff_screen, require_profiles

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


management_profile_required = require_profiles(
    allowed_profiles=MANAGEMENT_PROFILES,
    message="Selecione o perfil Supervisor da Biblioteca para acessar esta área.",
)
_render_screen = render_staff_screen
_redirect = redirect_url_response


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
