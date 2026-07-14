from apps.core.enums import DemoProfile

DEMO_PROFILE_SESSION_KEY = "demo_profile"


def get_demo_profile(request) -> str | None:
    value = request.session.get(DEMO_PROFILE_SESSION_KEY)
    return value if value in DemoProfile.values else None


def select_demo_profile(request, profile: str) -> str:
    if profile not in DemoProfile.values:
        raise ValueError("Perfil de demonstração inválido.")
    request.session[DEMO_PROFILE_SESSION_KEY] = profile
    request.session.modified = True
    return profile
