from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

from .models import LoginIdentifier
from .services import normalize_identifier


class IdentifierBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("identifier")
        if not identifier or password is None:
            return None

        _, normalized_value = normalize_identifier(identifier)
        login_identifier = (
            LoginIdentifier.objects.select_related("account__user")
            .filter(normalized_value=normalized_value)
            .first()
        )
        if login_identifier is None:
            get_user_model()().set_password(password)
            return None

        user = login_identifier.account.user
        if not user.check_password(password) or not user.is_active:
            return None
        return user

    def get_user(self, user_id):
        return (
            get_user_model()
            .objects.filter(
                pk=user_id,
                is_active=True,
                access_account__isnull=False,
            )
            .first()
        )
