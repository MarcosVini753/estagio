from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("perfil-indisponivel/", views.profile_unavailable, name="profile-unavailable"),
    path("sala/computadores/", views.computers, name="computers"),
    path(
        "sala/computadores/<int:pk>/",
        views.computer_detail,
        name="computer-detail",
    ),
    path("sala/reservas/", views.create_booking, name="booking-create"),
    path(
        "sala/reservas/<int:pk>/cancelar/",
        views.cancel_booking,
        name="booking-cancel",
    ),
    path(
        "sala/reservas/<int:pk>/entrada/",
        views.check_in_booking,
        name="booking-check-in",
    ),
    path("sala/agenda/", views.agenda, name="agenda"),
    path("sala/sessao/", views.session, name="session"),
    path("sala/sessao/iniciar/", views.start_session, name="session-start"),
    path(
        "sala/sessao/<int:pk>/trocar/",
        views.switch_session_computer,
        name="session-switch",
    ),
    path(
        "sala/sessao/<int:pk>/encerrar/",
        views.finish_session,
        name="session-finish",
    ),
    path("sala/problemas/", views.problems, name="problems"),
]
