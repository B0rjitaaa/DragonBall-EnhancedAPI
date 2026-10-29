from django.db import migrations

OLD, NEW = "Sin ubicar", "Unsorted"


def rename(apps, schema_editor, old=OLD, new=NEW):
    """La ubicación por defecto pasa a llamarse en inglés (si nadie ha usado ya ese nombre)."""
    Location = apps.get_model("collection", "Location")
    if not Location.objects.filter(name=new).exists():
        Location.objects.filter(is_default=True, name=old).update(name=new)


def rename_back(apps, schema_editor):
    rename(apps, schema_editor, old=NEW, new=OLD)


class Migration(migrations.Migration):
    dependencies = [("collection", "0004_english_labels")]

    operations = [migrations.RunPython(rename, rename_back)]
