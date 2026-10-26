"""Carga las copias incluidas de erratas y Card Q&A y marca las cartas ya importadas."""
import json
from collections import Counter
from pathlib import Path

from django.db import migrations

DATA = Path(__file__).resolve().parent.parent / "data"


def load_snapshots(apps, schema_editor):
    CardErrata = apps.get_model("cards", "CardErrata")
    CardRuling = apps.get_model("cards", "CardRuling")
    Card = apps.get_model("cards", "Card")

    errata = json.loads((DATA / "errata_snapshot.json").read_text(encoding="utf-8"))
    CardErrata.objects.bulk_create([
        CardErrata(list_updated=errata.get("updated", ""), source="snapshot", **e) for e in errata["entries"]
    ])
    errata_numbers = [e["card_number"] for e in errata["entries"]]
    Card.objects.filter(card_number__in=errata_numbers).update(has_errata=True)

    rulings = json.loads((DATA / "rulings_snapshot.json").read_text(encoding="utf-8"))
    CardRuling.objects.bulk_create(
        [CardRuling(list_updated=rulings.get("updated", ""), source="snapshot", **e) for e in rulings["entries"]],
        batch_size=1000,
    )
    for number, count in Counter(e["card_number"] for e in rulings["entries"]).items():
        Card.objects.filter(card_number=number).update(rulings_count=count)


class Migration(migrations.Migration):

    dependencies = [
        ("cards", "0007_carderrata_card_has_errata_card_rulings_count_and_more"),
    ]

    operations = [
        migrations.RunPython(load_snapshots, migrations.RunPython.noop),
    ]
