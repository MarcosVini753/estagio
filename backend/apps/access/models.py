import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.enums import AffiliationType, DemoProfile

ACCESS_PROFILE_CHOICES = [
    choice for choice in DemoProfile.choices if choice[0] != DemoProfile.SYSTEM_ADMIN
]


def new_user_reference():
    return uuid.uuid4().hex


class AccessAccount(models.Model):
    PROFILE_CHOICES = ACCESS_PROFILE_CHOICES

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_account",
    )
    profile = models.CharField(max_length=30, choices=PROFILE_CHOICES)
    display_name = models.CharField(max_length=150)
    user_reference = models.CharField(
        max_length=100,
        unique=True,
        default=new_user_reference,
    )
    affiliation_type = models.CharField(
        max_length=30,
        choices=AffiliationType.choices,
        blank=True,
        null=True,
    )
    institutional_unit = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(profile__in=[value for value, _ in ACCESS_PROFILE_CHOICES]),
                name="access_account_supported_profile",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        profile=DemoProfile.ROOM_USER,
                        affiliation_type__in=[
                            AffiliationType.STUDENT,
                            AffiliationType.PROFESSOR,
                            AffiliationType.TECHNICAL_STAFF,
                        ],
                    )
                    & ~Q(institutional_unit="")
                )
                | (
                    ~Q(profile=DemoProfile.ROOM_USER)
                    & Q(affiliation_type__isnull=True)
                    & Q(institutional_unit="")
                ),
                name="access_account_room_identity_consistent",
            ),
        ]


class LoginIdentifier(models.Model):
    class Kind(models.TextChoices):
        CPF = "CPF", "CPF"
        MATRICULA = "MATRICULA", "Matrícula"

    account = models.ForeignKey(
        AccessAccount,
        on_delete=models.CASCADE,
        related_name="identifiers",
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    normalized_value = models.CharField(max_length=32, unique=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account", "kind"],
                name="one_identifier_kind_per_account",
            )
        ]

    def __str__(self):
        return f"{self.kind}: [oculto]"
