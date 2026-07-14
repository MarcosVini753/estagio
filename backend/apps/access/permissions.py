from rest_framework.permissions import BasePermission

from .services import get_demo_profile


class HasDemoProfile(BasePermission):
    message = "Selecione um perfil de demonstração compatível com esta operação."

    def has_permission(self, request, view):
        allowed_profiles = getattr(view, "allowed_demo_profiles", None)
        if not allowed_profiles:
            return True
        return get_demo_profile(request) in set(allowed_profiles)
