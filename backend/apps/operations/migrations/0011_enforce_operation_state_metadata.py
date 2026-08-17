from django.db import migrations, models
from django.db.models import Q


def validate_operation_state_metadata(apps, schema_editor):
    reservation = apps.get_model("operations", "Reservation")
    use_session = apps.get_model("operations", "UseSession")
    allocation = apps.get_model("operations", "ComputerAllocation")

    invalid = {
        "Reservation": reservation.objects.filter(
            Q(status="CANCELLED")
            & (Q(cancelled_at__isnull=True) | Q(cancelled_by_profile=""))
            | ~Q(status="CANCELLED")
            & (
                Q(cancelled_at__isnull=False)
                | ~Q(cancelled_by_profile="")
                | ~Q(cancellation_reason="")
            )
        ),
        "UseSession": use_session.objects.filter(
            Q(status="ACTIVE")
            & (Q(ended_at__isnull=False) | ~Q(exit_recorded_by_profile=""))
            | ~Q(status="ACTIVE")
            & (Q(ended_at__isnull=True) | Q(exit_recorded_by_profile=""))
        ),
        "ComputerAllocation": allocation.objects.filter(
            Q(ended_at__isnull=True) & ~Q(end_reason="")
            | Q(ended_at__isnull=False) & Q(end_reason="")
        ),
    }
    failures = []
    for model_name, queryset in invalid.items():
        ids = list(queryset.order_by("pk").values_list("pk", flat=True)[:25])
        if ids:
            failures.append(f"{model_name}: IDs {ids}")
    if failures:
        details = "; ".join(failures)
        raise RuntimeError(
            "Metadados operacionais inconsistentes impedem a migration 0011. "
            f"Corrija explicitamente os registros antes do deploy: {details}."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0010_allow_early_reservation_check_in"),
    ]

    operations = [
        migrations.RunPython(
            validate_operation_state_metadata,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="reservation",
            constraint=models.CheckConstraint(
                condition=(
                    Q(status="CANCELLED", cancelled_at__isnull=False)
                    & ~Q(cancelled_by_profile="")
                    | ~Q(status="CANCELLED")
                    & Q(
                        cancelled_at__isnull=True,
                        cancelled_by_profile="",
                        cancellation_reason="",
                    )
                ),
                name="reservation_cancellation_metadata_matches_status",
            ),
        ),
        migrations.AddConstraint(
            model_name="usesession",
            constraint=models.CheckConstraint(
                condition=(
                    Q(
                        status="ACTIVE",
                        ended_at__isnull=True,
                        exit_recorded_by_profile="",
                    )
                    | ~Q(status="ACTIVE")
                    & Q(ended_at__isnull=False)
                    & ~Q(exit_recorded_by_profile="")
                ),
                name="session_exit_metadata_matches_status",
            ),
        ),
        migrations.AddConstraint(
            model_name="computerallocation",
            constraint=models.CheckConstraint(
                condition=(
                    Q(ended_at__isnull=True, end_reason="")
                    | Q(ended_at__isnull=False) & ~Q(end_reason="")
                ),
                name="allocation_end_reason_matches_end",
            ),
        ),
    ]
