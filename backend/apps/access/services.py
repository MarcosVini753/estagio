from apps.core.enums import DemoProfile

DEMO_PROFILE_SESSION_KEY = "demo_profile"
DEMO_USER_REFERENCES = {
    DemoProfile.ROOM_USER: "demo-room-user",
    DemoProfile.INTERN: "demo-intern",
    DemoProfile.LIBRARY_SUPERVISOR: "demo-library-supervisor",
    DemoProfile.SYSTEM_ADMIN: "demo-system-admin",
}


def get_demo_profile(request) -> str | None:
    value = request.session.get(DEMO_PROFILE_SESSION_KEY)
    return value if value in DemoProfile.values else None


def get_demo_user_reference(request) -> str | None:
    profile = get_demo_profile(request)
    return DEMO_USER_REFERENCES.get(profile)


def select_demo_profile(request, profile: str) -> str:
    if profile not in DemoProfile.values:
        raise ValueError("Perfil de demonstração inválido.")
    request.session[DEMO_PROFILE_SESSION_KEY] = profile
    request.session.modified = True
    return profile
