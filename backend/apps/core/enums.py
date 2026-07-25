from django.db import models


class DemoProfile(models.TextChoices):
    ROOM_USER = "ROOM_USER", "Usuário da Sala"
    INTERN = "INTERN", "Monitor da Sala"
    LIBRARY_SUPERVISOR = "LIBRARY_SUPERVISOR", "Supervisor da Biblioteca"
    SYSTEM_ADMIN = "SYSTEM_ADMIN", "Administrador do Sistema"
