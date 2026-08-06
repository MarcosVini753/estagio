from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0005_room_notice"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="bookingpolicy",
            name="slot_duration_minutes",
        ),
        migrations.RemoveField(
            model_name="bookingpolicy",
            name="check_in_tolerance_minutes",
        ),
    ]
