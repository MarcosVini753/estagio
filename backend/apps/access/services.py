from apps.core.enums import AffiliationType, DemoProfile

DEMO_PROFILE_SESSION_KEY = "demo_profile"
DEMO_USER_REFERENCE_SESSION_KEY = "demo_user_reference"
DEMO_AFFILIATION_TYPE_SESSION_KEY = "demo_affiliation_type"
DEMO_INSTITUTIONAL_UNIT_SESSION_KEY = "demo_institutional_unit"
DEMO_USER_REFERENCES = {
    DemoProfile.ROOM_USER: "demo-room-user",
    DemoProfile.ROOM_MONITOR: "demo-room-monitor",
    DemoProfile.LIBRARY_SUPERVISOR: "demo-library-supervisor",
    DemoProfile.SYSTEM_ADMIN: "demo-system-admin",
}


def get_demo_profile(request) -> str | None:
    value = request.session.get(DEMO_PROFILE_SESSION_KEY)
    return value if value in DemoProfile.values else None


def get_demo_user_reference(request) -> str | None:
    profile = get_demo_profile(request)
    if profile == DemoProfile.ROOM_USER:
        return request.session.get(DEMO_USER_REFERENCE_SESSION_KEY)
    return DEMO_USER_REFERENCES.get(profile)


def get_demo_affiliation_type(request) -> str | None:
    if get_demo_profile(request) != DemoProfile.ROOM_USER:
        return None
    value = request.session.get(DEMO_AFFILIATION_TYPE_SESSION_KEY)
    return value if value in AffiliationType.values else None


def get_demo_institutional_unit(request) -> str | None:
    if get_demo_profile(request) != DemoProfile.ROOM_USER:
        return None
    return request.session.get(DEMO_INSTITUTIONAL_UNIT_SESSION_KEY)


def select_demo_profile(
    request,
    profile: str,
    *,
    user_reference: str | None = None,
    affiliation_type: str | None = None,
    institutional_unit: str | None = None,
) -> str:
    if profile not in DemoProfile.values:
        raise ValueError("Perfil de demonstração inválido.")
    request.session[DEMO_PROFILE_SESSION_KEY] = profile
    if profile == DemoProfile.ROOM_USER:
        request.session[DEMO_USER_REFERENCE_SESSION_KEY] = user_reference
        request.session[DEMO_AFFILIATION_TYPE_SESSION_KEY] = affiliation_type
        request.session[DEMO_INSTITUTIONAL_UNIT_SESSION_KEY] = institutional_unit
    else:
        request.session.pop(DEMO_USER_REFERENCE_SESSION_KEY, None)
        request.session.pop(DEMO_AFFILIATION_TYPE_SESSION_KEY, None)
        request.session.pop(DEMO_INSTITUTIONAL_UNIT_SESSION_KEY, None)
    request.session.modified = True
    return profile
