import re
import uuid

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.core.enums import AffiliationType, DemoProfile

from .models import AccessAccount, LoginIdentifier

CPF_PATTERN = re.compile(r"^(?:\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2})$")


def normalize_identifier(value: str) -> tuple[str, str]:
    value = value.strip()
    if CPF_PATTERN.fullmatch(value):
        return LoginIdentifier.Kind.CPF, re.sub(r"\D", "", value)
    return LoginIdentifier.Kind.MATRICULA, value.upper()


def normalize_identifier_for_kind(kind: str, value: str) -> str:
    value = value.strip()
    if kind == LoginIdentifier.Kind.CPF:
        if not CPF_PATTERN.fullmatch(value):
            raise ValueError("Informe um CPF com 11 dígitos.")
        return re.sub(r"\D", "", value)
    if kind == LoginIdentifier.Kind.MATRICULA:
        if not value:
            raise ValueError("Informe a matrícula.")
        normalized = value.upper()
        if len(normalized) > 32:
            raise ValueError("A matrícula deve ter no máximo 32 caracteres.")
        return normalized
    raise ValueError("Tipo de identificador inválido.")


@transaction.atomic
def create_access_account(
    *,
    profile: str,
    display_name: str,
    password: str,
    identifiers: list[tuple[str, str]],
    affiliation_type: str | None = None,
    institutional_unit: str = "",
    user_reference: str | None = None,
):
    supported_profiles = {value for value, _ in AccessAccount.PROFILE_CHOICES}
    if profile not in supported_profiles:
        raise ValueError("O perfil informado não pode receber conta de acesso.")
    if not display_name.strip() or not identifiers:
        raise ValueError("Informe nome e pelo menos um identificador.")

    if profile == DemoProfile.ROOM_USER:
        if (
            affiliation_type
            not in {
                AffiliationType.STUDENT,
                AffiliationType.PROFESSOR,
                AffiliationType.TECHNICAL_STAFF,
            }
            or not institutional_unit.strip()
        ):
            raise ValueError("Usuário da Sala exige vínculo e unidade institucional.")
    elif affiliation_type or institutional_unit:
        raise ValueError("Vínculo e unidade só se aplicam ao Usuário da Sala.")

    normalized_identifiers = []
    for kind, value in identifiers:
        normalized = normalize_identifier_for_kind(kind, value)
        if any(existing_kind == kind for existing_kind, _ in normalized_identifiers):
            raise ValueError("Informe no máximo um CPF e uma matrícula por conta.")
        if any(
            existing_value == normalized for _, existing_value in normalized_identifiers
        ):
            raise ValueError("CPF e matrícula devem ser identificadores diferentes.")
        normalized_identifiers.append((kind, normalized))

    User = get_user_model()
    user = User.objects.create_user(
        username=uuid.uuid4().hex,
        password=password,
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )
    account = AccessAccount.objects.create(
        user=user,
        profile=profile,
        display_name=display_name.strip(),
        user_reference=user_reference or uuid.uuid4().hex,
        affiliation_type=affiliation_type,
        institutional_unit=institutional_unit.strip(),
    )
    LoginIdentifier.objects.bulk_create(
        [
            LoginIdentifier(
                account=account,
                kind=kind,
                normalized_value=value,
            )
            for kind, value in normalized_identifiers
        ]
    )
    return account


def authenticate_identifier(request, identifier: str, password: str):
    from django.contrib.auth import authenticate

    return authenticate(request, username=identifier, password=password)


def clear_legacy_demo_context(session) -> None:
    for key in tuple(session.keys()):
        if key.startswith("demo_"):
            session.pop(key, None)


def get_actor_account(request) -> AccessAccount | None:
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.is_active:
        return None
    try:
        return user.access_account
    except AccessAccount.DoesNotExist:
        return None


def get_actor_profile(request) -> str | None:
    account = get_actor_account(request)
    return account.profile if account else None


def get_actor_reference(request) -> str | None:
    account = get_actor_account(request)
    return account.user_reference if account else None


def get_actor_affiliation_type(request) -> str | None:
    account = get_actor_account(request)
    return account.affiliation_type if account else None


def get_actor_institutional_unit(request) -> str | None:
    account = get_actor_account(request)
    return account.institutional_unit or None if account else None


def get_actor_display_name(request) -> str | None:
    account = get_actor_account(request)
    return account.display_name if account else None


def profile_home_url(profile: str) -> str:
    return {
        DemoProfile.ROOM_USER: "/sala/computadores/",
        DemoProfile.ROOM_MONITOR: "/monitor/",
        DemoProfile.LIBRARY_SUPERVISOR: "/supervisor/",
    }.get(profile, "/")
