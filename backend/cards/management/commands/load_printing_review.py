"""Carga la comparación con DeckPlanet (report.json) para revisarla en Tools → Printings review.

Volver a cargarla actualiza las versiones y conserva las marcas ya hechas."""
import json

from django.core.management.base import BaseCommand

from cards.models import ExternalPrinting

IMG = "https://multi-deckplanet.us-southeast-1.linodeobjects.com/dbs_masters/{}.webp"


class Command(BaseCommand):
    help = "Load the DeckPlanet comparison (report.json) into the printings review"

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, path, **opts):
        report = json.load(open(path))
        # Fuera los marcadores de energía y los tokens: no son cartas.
        skip = lambda g: (g.get("series") or "").lower() in ("energy markers", "token") or g["number"] == "T" or "-EM" in g["number"]  # noqa: E731
        groups = [("absent", g) for g in report["absent"] if not skip(g)]
        groups += [("fewer", g) for g in report["missing"] if not skip(g)]
        seen = set()
        position = 0
        for kind, g in groups:
            ours = g.get("ours") or []
            number = ours[0]["number"] if ours else g["dp"][0]["number"].split("_")[0]
            for v in g["dp"]:
                position += 1
                code = v["number"]
                if code in seen:  # DeckPlanet repite alguna (p. ej. dos «P-763»)
                    code = f"{code}#{position}"
                seen.add(code)
                ExternalPrinting.objects.update_or_create(
                    source="deckplanet", code=code,
                    defaults={"card_number": number, "name": g["name"], "series": g.get("series") or "",
                              "image_url": IMG.format(v.get("img") or v["number"]), "kind": kind,
                              "their_versions": len(g["dp"]), "our_versions": len(ours), "position": position},
                )
        gone = ExternalPrinting.objects.filter(source="deckplanet").exclude(code__in=seen)
        removed = gone.count()
        gone.delete()
        self.stdout.write(f"{len(seen)} versions in {len(groups)} cards ({removed} removed)")
