from rest_framework.permissions import BasePermission

from .services import get_actor_account, get_actor_profile


class HasAccessRole(BasePermission):
    message = "Entre com uma conta autorizada para esta operação."

    def has_permission(self, request, view):
        allowed_profiles = getattr(view, "allowed_profiles", None)
        account = get_actor_account(request)
        if account is None:
            return False
        return not allowed_profiles or get_actor_profile(request) in set(
            allowed_profiles
        )


class HasAccessAccount(BasePermission):
    message = "Entre com uma conta válida para acessar este recurso."

    def has_permission(self, request, view):
        return get_actor_account(request) is not None
