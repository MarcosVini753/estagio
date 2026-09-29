import uuid

from apps.access.models import AccessAccount, LoginIdentifier
from apps.access.services import create_access_account
from apps.core.enums import AffiliationType, DemoProfile


def login_test_account(
    client,
    profile: str,
    *,
    user_reference: str | None = None,
    affiliation_type: str | None = None,
    institutional_unit: str | None = None,
):
    reference = user_reference or f"test-{profile.lower()}-{uuid.uuid4().hex}"
    account = AccessAccount.objects.filter(user_reference=reference).first()
    if account is None:
        if profile == DemoProfile.ROOM_USER:
            affiliation_type = affiliation_type or AffiliationType.STUDENT
            institutional_unit = institutional_unit or "Sistemas de Informação"
        identifier = f"T{uuid.uuid4().hex[:20]}"
        account = create_access_account(
            profile=profile,
            display_name=f"Conta de teste {profile}",
            password="TestPassword123!",
            identifiers=[(LoginIdentifier.Kind.MATRICULA, identifier)],
            affiliation_type=affiliation_type,
            institutional_unit=institutional_unit or "",
            user_reference=reference,
        )
    client.force_login(account.user)
    return account
