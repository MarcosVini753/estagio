from django.urls import path

from .views import AuthContextAPIView, LoginAPIView, LogoutAPIView

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("me/", AuthContextAPIView.as_view(), name="me"),
]
