from functools import wraps

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.access.services import get_demo_profile


def is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def service_error_message(error) -> str:
    detail = error.detail
    if isinstance(detail, dict):
        detail = detail.get("detail", detail)
    if isinstance(detail, (list, tuple)):
        return " ".join(str(item) for item in detail)
    return str(detail)


def require_profiles(*, allowed_profiles, message):
    """Protect an HTML view using the profile stored in the demo session."""

    allowed_profiles = frozenset(allowed_profiles)

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if get_demo_profile(request) not in allowed_profiles:
                messages.warning(request, message)
                return redirect("web:home")
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


def render_room_screen(request, *, content_template, context, status=200):
    context = {**context, "content_template": content_template}
    if request.headers.get("HX-Target") == "screen-content":
        template = "room_user/partials/screen.html"
    elif is_htmx(request):
        template = "room_user/partials/app.html"
    else:
        template = "room_user/page.html"
    return render(request, template, context, status=status)


def render_staff_screen(request, *, content_template, context, status=200):
    context = {**context, "content_template": content_template}
    if request.headers.get("HX-Target") == "staff-content":
        template = "staff/partials/content.html"
    elif is_htmx(request):
        template = "staff/partials/app.html"
    else:
        template = "staff/page.html"
    return render(request, template, context, status=status)


def redirect_response(request, url_name: str, **kwargs):
    url = reverse(url_name, kwargs=kwargs or None)
    if is_htmx(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url_name, **kwargs)


def redirect_url_response(request, url: str):
    if is_htmx(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url)
