from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.access.forms import IdentifierAuthenticationForm
from apps.access.services import (
    clear_legacy_demo_context,
    get_actor_profile,
    profile_home_url,
)
from apps.configuration.selectors import get_active_room_notices


class AccessLoginView(LoginView):
    template_name = "home.html"
    authentication_form = IdentifierAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        clear_legacy_demo_context(self.request.session)
        return super().form_valid(form)

    def get_success_url(self):
        profile = get_actor_profile(self.request)
        return profile_home_url(profile) if profile else reverse("web:home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_notices"] = get_active_room_notices()
        return context


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "Você saiu da sua conta.")
    return redirect("web:home")
