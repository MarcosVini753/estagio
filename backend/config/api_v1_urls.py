from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.api.urls")),
    path("demo/", include("apps.access.api.urls")),
    path("computers/", include("apps.computers.api.urls")),
    path("", include("apps.configuration.api.urls")),
]
