from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.api.urls")),
    path("demo/", include("apps.access.api.urls")),
]
