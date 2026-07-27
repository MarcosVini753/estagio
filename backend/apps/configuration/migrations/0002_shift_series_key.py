import uuid

from django.db import migrations, models


def populate_series_keys(apps, schema_editor):
    Shift = apps.get_model("configuration", "Shift")
    series = {}
    for shift in Shift.objects.order_by("id"):
        key = (shift.name, shift.display_order)
        series_key = series.setdefault(key, uuid.uuid4())
        Shift.objects.filter(pk=shift.pk).update(series_key=series_key)


class Migration(migrations.Migration):
    dependencies = [
        ("configuration", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="shift",
            name="series_key",
            field=models.UUIDField(db_index=True, editable=False, null=True),
        ),
        migrations.RunPython(populate_series_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="shift",
            name="series_key",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
            ),
        ),
    ]
