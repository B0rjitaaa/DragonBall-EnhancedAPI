from django.db import migrations

FIELDS = ["characters", "special_traits", "eras", "color_cost", "color_cost_colors"]


def renormalize(apps, schema_editor):
    """Unifica comillas tipográficas ("Frieza’s Army" -> "Frieza's Army") y corrige las erratas
    de Bandai (Bule, Napapa, (Duplicate) Vegeta…) en las cartas ya importadas."""
    from cards.parsing import parse_card

    Card = apps.get_model("cards", "Card")
    batch = []
    for card in Card.objects.only("id", "raw", *FIELDS).iterator(chunk_size=500):
        if not card.raw:
            continue
        parsed = parse_card(card.raw)
        if all(getattr(card, f) == parsed[f] for f in FIELDS):
            continue
        for f in FIELDS:
            setattr(card, f, parsed[f])
        batch.append(card)
        if len(batch) >= 500:
            Card.objects.bulk_update(batch, FIELDS)
            batch.clear()
    if batch:
        Card.objects.bulk_update(batch, FIELDS)

    # Las facetas cacheadas llevan los valores viejos.
    try:
        from cards.importer import invalidate_facets

        invalidate_facets()
    except Exception:  # noqa: BLE001 - sin caché (p. ej. en tests) no pasa nada
        pass


class Migration(migrations.Migration):

    dependencies = [
        ("cards", "0008_load_errata_rulings"),
    ]

    operations = [
        migrations.RunPython(renormalize, migrations.RunPython.noop),
    ]
