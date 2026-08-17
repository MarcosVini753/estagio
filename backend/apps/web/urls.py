from django.urls import path

from . import monitor_views, supervisor_views, views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("perfil-indisponivel/", views.profile_unavailable, name="profile-unavailable"),
    path("monitor/", monitor_views.dashboard, name="monitor-dashboard"),
    path(
        "monitor/computadores/",
        monitor_views.computers,
        name="monitor-computers",
    ),
    path(
        "monitor/computadores/<int:pk>/estado/",
        monitor_views.change_computer_state,
        name="monitor-computer-state",
    ),
    path(
        "monitor/ocorrencias/",
        monitor_views.occurrences,
        name="monitor-occurrences",
    ),
    path(
        "monitor/ocorrencias/<int:pk>/transicao/",
        monitor_views.transition_occurrence_view,
        name="monitor-occurrence-transition",
    ),
    path("monitor/historico/", monitor_views.history, name="monitor-history"),
    path(
        "monitor/historico/<int:pk>/",
        monitor_views.history_detail,
        name="monitor-history-detail",
    ),
    path(
        "monitor/historico/<int:pk>/corrigir/",
        monitor_views.correct_history,
        name="monitor-history-correct",
    ),
    path(
        "supervisor/",
        supervisor_views.dashboard,
        name="supervisor-dashboard",
    ),
    path(
        "supervisor/computadores/",
        supervisor_views.computers,
        name="supervisor-computers",
    ),
    path(
        "supervisor/computadores/<int:pk>/editar/",
        supervisor_views.update_computer,
        name="supervisor-computer-update",
    ),
    path(
        "supervisor/funcionamento/",
        supervisor_views.configuration,
        name="supervisor-configuration",
    ),
    path(
        "supervisor/turnos/",
        supervisor_views.shifts,
        name="supervisor-shifts",
    ),
    path(
        "supervisor/turnos/<int:pk>/editar/",
        supervisor_views.update_shift,
        name="supervisor-shift-update",
    ),
    path(
        "supervisor/turnos/<int:pk>/substituir/",
        supervisor_views.replace_shift_view,
        name="supervisor-shift-replace",
    ),
    path(
        "supervisor/calendarios/novo/",
        supervisor_views.create_schedule,
        name="supervisor-schedule-create",
    ),
    path(
        "supervisor/calendarios/<int:pk>/substituir/",
        supervisor_views.replace_schedule,
        name="supervisor-schedule-replace",
    ),
    path(
        "supervisor/excecoes/",
        supervisor_views.exceptions,
        name="supervisor-exceptions",
    ),
    path(
        "supervisor/avisos/",
        supervisor_views.notices,
        name="supervisor-notices",
    ),
    path(
        "supervisor/avisos/<int:pk>/estado/",
        supervisor_views.update_notice_state,
        name="supervisor-notice-state",
    ),
    path(
        "supervisor/configuracoes/",
        supervisor_views.configurations,
        name="supervisor-configurations",
    ),
    path(
        "supervisor/relatorios/",
        supervisor_views.reports,
        name="supervisor-reports",
    ),
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
