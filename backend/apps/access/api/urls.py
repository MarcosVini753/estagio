from django.urls import path

from .views import DemoContextAPIView, DemoSelectProfileAPIView

urlpatterns = [
    path("context/", DemoContextAPIView.as_view(), name="demo-context"),
    path(
        "select-profile/",
        DemoSelectProfileAPIView.as_view(),
        name="demo-select-profile",
    ),
]
