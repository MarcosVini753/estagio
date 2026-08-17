import datetime

from django.db import migrations

SCHEDULE_NAME = "Horário regular da Sala de Informática"
BASE_VALID_FROM = datetime.date(2025, 1, 1)


def seed_regular_schedule(apps, schema_editor):
    OperatingSchedule = apps.get_model("configuration", "OperatingSchedule")
    OperatingScheduleDay = apps.get_model("configuration", "OperatingScheduleDay")
    OperatingWindow = apps.get_model("configuration", "OperatingWindow")

    schedule = OperatingSchedule.objects.create(
        name=SCHEDULE_NAME,
        schedule_type="REGULAR",
        valid_from=BASE_VALID_FROM,
        created_by_profile="SYSTEM_ADMIN",
    )
    for weekday in range(7):
        is_open = weekday != 6
        day = OperatingScheduleDay.objects.create(
            schedule=schedule,
            weekday=weekday,
            is_open=is_open,
        )
        if is_open:
            OperatingWindow.objects.create(
                schedule_day=day,
                opens_at=datetime.time(7, 15),
                closes_at=datetime.time(13 if weekday == 5 else 21),
            )


def remove_seeded_regular_schedule(apps, schema_editor):
    OperatingSchedule = apps.get_model("configuration", "OperatingSchedule")
    OperatingSchedule.objects.filter(
        name=SCHEDULE_NAME,
        schedule_type="REGULAR",
        valid_from=BASE_VALID_FROM,
        created_by_profile="SYSTEM_ADMIN",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0003_operating_schedule_models"),
    ]

    operations = [
        migrations.RunPython(
            seed_regular_schedule,
            remove_seeded_regular_schedule,
        )
    ]
