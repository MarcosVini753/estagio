from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


def is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def service_error_message(error) -> str:
    detail = error.detail
    if isinstance(detail, dict):
        detail = detail.get("detail", detail)
    if isinstance(detail, (list, tuple)):
        return " ".join(str(item) for item in detail)
    return str(detail)


def redirect_response(request, url_name: str, **kwargs):
    url = reverse(url_name, kwargs=kwargs or None)
    if is_htmx(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url_name, **kwargs)
