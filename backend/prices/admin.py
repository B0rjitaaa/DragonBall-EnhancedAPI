from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib import admin, messages
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from cards.models import Card
from cards.thumbs import thumb_url

from . import review
from .models import (
    CardmarketExpansion, CardmarketLink, CardmarketProduct, CardPrice, ExchangeRate, PricePoint, PriceReview, TcgLink,
    TcgProduct,
)
from .services import PRODUCT_URL

PAGE_SIZE = 25


@admin.register(CardmarketExpansion)
class CardmarketExpansionAdmin(admin.ModelAdmin):
    list_display = ["id", "card_set", "score", "manual", "fusion_world"]
    list_filter = ["fusion_world", "manual"]
    search_fields = ["card_set"]


@admin.register(CardmarketProduct)
class CardmarketProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "expansion", "price", "trend", "avg30", "low", "fetched_at"]
    list_filter = ["expansion__fusion_world"]
    search_fields = ["name"]
    raw_id_fields = ["expansion"]


@admin.register(CardmarketLink)
class CardmarketLinkAdmin(admin.ModelAdmin):
    list_display = ["card", "product", "method", "manual_price"]
    list_filter = ["method"]
    search_fields = ["card__card_number", "card__name", "product__name"]
    raw_id_fields = ["card", "product"]


@admin.register(TcgProduct)
class TcgProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "number", "rarity", "variant", "group_name", "market_usd", "low_usd", "sub_type"]
    search_fields = ["name", "number"]


@admin.register(TcgLink)
class TcgLinkAdmin(admin.ModelAdmin):
    list_display = ["card", "product"]
    search_fields = ["card__card_number", "card__name", "product__name"]
    raw_id_fields = ["card", "product"]


@admin.register(CardPrice)
class CardPriceAdmin(admin.ModelAdmin):
    list_display = ["card", "eur", "source", "counts", "cardmarket_eur", "tcgplayer_eur", "updated_at"]
    list_filter = ["source", "counts"]
    search_fields = ["card__card_number", "card__name"]
    raw_id_fields = ["card"]


@admin.register(PricePoint)
class PricePointAdmin(admin.ModelAdmin):
    list_display = ["card", "date", "eur"]
    date_hierarchy = "date"
    search_fields = ["card__card_number", "card__name"]
    raw_id_fields = ["card"]


admin.site.register(ExchangeRate)


@admin.register(PriceReview)
class PriceReviewAdmin(admin.ModelAdmin):
    """Página propia: tus cartas sin emparejar y los emparejamientos dudosos (ver review.py)."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        view = self.admin_site.admin_view
        return [
            path("choose/", view(self.choose_view), name="prices_pricereview_choose"),
            path("group/", view(self.group_view), name="prices_pricereview_group"),
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        tab = request.GET.get("tab", "sin")
        page = max(1, int(request.GET.get("page", "1") or 1))
        offset = (page - 1) * PAGE_SIZE
        unmatched_total, unmatched_pending = review.unmatched(PAGE_SIZE if tab == "sin" else 0, offset)
        suspect_total, suspect_pending = review.suspects(PAGE_SIZE if tab == "raros" else 0, offset)
        listing_total, listing_pending = review.listing_only(PAGE_SIZE if tab == "sinventas" else 0, offset)
        total, pending = {"raros": (suspect_total, suspect_pending),
                          "sinventas": (listing_total, listing_pending)}.get(tab, (unmatched_total, unmatched_pending))
        groups = review.doubtful()
        rows = [{
            "card": p.card,
            "thumb": thumb_url(p.card.id, p.card.image_url) if p.card.image_url else "",
            "current": getattr(getattr(p.card, "cardmarket", None), "product_id", None) if tab != "sin" else None,
            "candidates": [{"product": c.product, "same_set": c.same_set, "url": PRODUCT_URL.format(id=c.product.id)}
                           for c in p.candidates],
            # «Tengo otra edición»: las demás impresiones de la carta, con su foto y su precio.
            "prints": [{
                "card": other,
                "thumb": thumb_url(other.id, other.image_url) if other.image_url else "",
                "price": getattr(other, "price", None) if hasattr(other, "price") else None,
            } for other in review.other_prints(p.card)] if tab == "sinventas" else [],
        } for p in pending] if tab in ("sin", "raros", "sinventas") else []
        context = {
            **self.admin_site.each_context(request),
            "title": "Revisar emparejamientos con Cardmarket",
            "opts": self.model._meta,
            "tab": tab,
            "page": page,
            "pages": max(1, -(-total // PAGE_SIZE)),
            "total": total,
            "rows": rows,
            "doubtful_count": len(groups),
            "unmatched_count": unmatched_total,
            "suspect_count": suspect_total,
            "listing_count": listing_total,
            "groups": [{
                "links": [{"link": link, "thumb": thumb_url(link.card.id, link.card.image_url) if link.card.image_url else "",
                           "url": PRODUCT_URL.format(id=link.product_id)} for link in group],
                "products": sorted({link.product for link in group}, key=lambda p: p.id),
            } for group in groups] if tab == "dudosos" else [],
        }
        return TemplateResponse(request, "admin/prices/review.html", context)

    def _back(self, request):
        query = {k: request.POST[k] for k in ("tab", "page") if request.POST.get(k)}
        return redirect(f"{reverse('admin:prices_pricereview_changelist')}?{urlencode(query)}")

    def choose_view(self, request):
        """Guarda de una vez lo elegido en las cartas de la página: por carta, `choice_<id>` es un
        producto, «none» (no está en Cardmarket), «price» (con `price_<id>`) o «fake» (tus copias son
        falsas). Las demás no cambian."""
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        cards = Card.objects.in_bulk([int(k.split("_", 1)[1]) for k in request.POST if k.startswith("choice_")])
        saved, wrong, fakes = [], [], []
        for card_id, card in sorted(cards.items(), key=lambda kv: (kv[1].card_number, kv[0])):
            choice = request.POST[f"choice_{card_id}"]
            label = f"{card.card_number} {card.rarity_code}"
            if choice == "price":
                try:
                    price = Decimal(request.POST.get(f"price_{card_id}", "").replace(",", ".").strip()).quantize(Decimal("0.01"))
                except InvalidOperation:
                    price = None
                if price is None or price < 0:
                    wrong.append(label)
                    continue
                review.set_price(card, price)
            elif choice == "fake":
                n = review.mark_fake(card)
                fakes.append(f"{label} ({n} {'copia' if n == 1 else 'copias'})")
                continue
            elif choice.startswith("print:"):
                target = Card.objects.filter(pk=choice.split(":", 1)[1]).first()
                if target is None:
                    wrong.append(label)
                    continue
                n = review.change_print(card, target)
                saved.append(f"{label} → {target.card_number} {target.rarity_code} ({n} {'copia' if n == 1 else 'copias'})")
                continue
            elif choice == "none":
                review.choose(card, None)
            else:
                product = CardmarketProduct.objects.filter(pk=choice).first()
                if product is None:
                    wrong.append(label)
                    continue
                review.choose(card, product)
            saved.append(label)
        if saved:
            self.message_user(request, f"Guardadas {len(saved)} cartas (y sus reimpresiones idénticas): {', '.join(saved)}.")
        if fakes:
            self.message_user(request, f"Marcadas como falsas (ya no cuentan en el valor): {', '.join(fakes)}.")
        if wrong:
            self.message_user(request, f"Sin guardar, con un precio no válido: {', '.join(wrong)}. Escribe p. ej. 3,50.",
                              messages.WARNING)
        if not saved and not wrong and not fakes:
            self.message_user(request, "No había ninguna carta marcada.", messages.WARNING)
        return self._back(request)

    def group_view(self, request):
        """Un grupo dudoso: confirmarlo tal cual o guardar el producto elegido para cada impresión."""
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        card_ids = [int(i) for i in request.POST.getlist("cards")]
        if request.POST.get("action") == "confirm":
            review.confirm(card_ids)
            self.message_user(request, "Emparejamientos confirmados.")
            return self._back(request)
        for card in Card.objects.filter(id__in=card_ids):
            product_id = request.POST.get(f"product_{card.id}")
            if product_id:
                review.choose(card, get_object_or_404(CardmarketProduct, pk=product_id))
        self.message_user(request, "Emparejamientos corregidos.")
        return self._back(request)
