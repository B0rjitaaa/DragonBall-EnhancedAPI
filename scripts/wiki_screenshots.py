"""Capturas de pantalla de la wiki (frontend/wiki/img/).

Abre la web local (docker compose up: http://localhost:5173) con el Chrome del equipo y guarda
cada pantalla. Para las del admin abre una sesión del superusuario local sin contraseña (la crea
con manage.py dentro del contenedor del backend).

Uso (una vez: pip install playwright; usa el Chrome instalado, no descarga navegadores):
    python scripts/wiki_screenshots.py            # todas
    python scripts/wiki_screenshots.py precios    # solo las que contienen «precios» en el nombre
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

# WIKI_BASE=http://<servidor> para sacar alguna captura de otra instalación (p. ej. una con más datos).
BASE = os.environ.get("WIKI_BASE", "http://localhost:5173")
# El admin no pasa por Vite: en local se sirve directamente desde el backend.
ADMIN = "http://localhost:8000"
OUT = Path(__file__).resolve().parent.parent / "frontend" / "wiki" / "img"
DESKTOP = {"width": 1440, "height": 900}
PHONE = {"width": 390, "height": 844}

# Datos de ejemplo de la base local (mazo y ubicación con cartas).
DECK = "9c3a5cc5-00f7-4e51-ab09-1fcb43be1e88"  # Cell Verde
BOX = "0b0b2a75-4026-470c-9f9d-10d562e2c15c"   # Caja 1
FILTERS = '{"color":{"values":["Red"],"match":"any"},"type":{"values":["BATTLE"],"match":"any"}}'
ADVANCED = (
    '{"id":"g","op":"or","children":['
    '{"id":"g1","op":"and","children":['
    '{"id":"c1","field":"type","operator":"eq","value":"LEADER"},'
    '{"id":"c2","field":"color","operator":"has","value":"Red"}]},'
    '{"id":"g2","op":"and","children":['
    '{"id":"c3","field":"keyword_skill","operator":"has","value":"Counter : Play"},'
    '{"id":"c4","field":"energy","operator":"lte","value":2}]}]}'
)


def admin_session() -> str:
    """Clave de una sesión del primer superusuario local (solo en local, sin contraseña)."""
    code = (
        "from django.contrib.auth import get_user_model, BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY;"
        "from importlib import import_module; from django.conf import settings;"
        "u = get_user_model().objects.filter(is_superuser=True).first();"
        "s = import_module(settings.SESSION_ENGINE).SessionStore();"
        "s[SESSION_KEY] = str(u.pk); s[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend';"
        "s[HASH_SESSION_KEY] = u.get_session_auth_hash(); s.create(); print(s.session_key)"
    )
    out = subprocess.run(
        ["docker", "compose", "exec", "-T", "backend", "python", "manage.py", "shell", "-c", code],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip().splitlines()[-1]


def settle(page: Page, ms: int = 1500) -> None:
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(ms)


def go(page: Page, path: str, ms: int = 1500) -> None:
    page.goto(f"{ADMIN if path.startswith('/admin/') else BASE}{path}")
    settle(page, ms)


# (nombre, tamaño, función que deja la pantalla lista). Si la función devuelve un selector, se
# captura solo ese elemento.
def shots():
    def at(path, ms=1500, element=None, full=False):
        def run(page: Page):
            go(page, path, ms)
            return element, full
        return run

    def open_filters(page: Page):
        go(page, f"/?q=goku&filters={FILTERS}")
        return None, False

    def deck_history(page: Page):
        go(page, "/locations")
        return None, True

    return [
        ("buscador.jpg", DESKTOP, at("/")),
        ("buscador-filtros.jpg", DESKTOP, open_filters),
        ("modo-avanzado.jpg", DESKTOP, at(f"/?advanced={ADVANCED}")),
        ("ficha-carta.jpg", DESKTOP, at("/?card=BT20-149", 2500)),
        ("ficha-leader.jpg", DESKTOP, at("/?card=BT10-060", 2500)),
        ("enlace-carta.jpg", DESKTOP, at("/?card=BT20-149", 2500, element=".detail-info")),
        ("precio-ficha.jpg", DESKTOP, at("/?card=BT20-149", 2500, element=".modal")),
        ("novedades.jpg", DESKTOP, at("/news", 2500)),
        ("coleccion.jpg", DESKTOP, at("/collection", 2500)),
        ("coleccion-lista.jpg", DESKTOP, at("/collection?view=list", 2500)),
        ("coleccion-ubicacion.jpg", DESKTOP, at(f"/collection/location/{BOX}", 2500)),
        ("coleccion-ficha.jpg", DESKTOP, at("/collection?card=BT20-149", 2500)),
        ("ubicaciones.jpg", DESKTOP, deck_history),
        ("mazo.jpg", DESKTOP, at(f"/collection/deck/{DECK}", 3000)),
        ("csv.jpg", DESKTOP, at("/collection", 2500)),
        ("escaner.jpg", PHONE, at("/scan", 3000)),
        ("escaner-escritorio.jpg", DESKTOP, at("/scan", 3000)),
        ("precios.jpg", DESKTOP, at("/prices", 3000)),
        ("wiki.jpg", DESKTOP, at("/wiki")),
        ("movil-buscador.jpg", PHONE, at("/", 2500)),
        # Admin de Django (sesión local)
        ("admin.jpg", DESKTOP, at("/admin/")),
        ("admin-precios.jpg", DESKTOP, at("/admin/prices/pricereview/?tab=sin", 2500)),
        ("admin-precios-dudosos.jpg", DESKTOP, at("/admin/prices/pricereview/?tab=raros", 2500)),
        ("admin-errores.jpg", DESKTOP, at("/admin/errorlog/errorgroup/?estado=todos")),
        ("admin-copias.jpg", DESKTOP, at("/admin/backups/backup/")),
        ("admin-sync.jpg", DESKTOP, at("/admin/cards/syncrun/")),
    ]


def main(only: str | None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    session = admin_session() if not only or "admin" in only else ""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for name, size, prepare in shots():
            if only and only not in name:
                continue
            context = browser.new_context(viewport=size, device_scale_factor=2 if size is PHONE else 1, locale="en-GB")
            # Solo en las del admin: con la sesión abierta, la web da error CSRF al buscar.
            if name.startswith("admin"):
                context.add_cookies([{"name": "sessionid", "value": session, "url": ADMIN}])
            page = context.new_page()
            element, full = prepare(page)
            target = OUT / name
            if element:
                page.locator(element).first.screenshot(path=str(target), type="jpeg", quality=85)
            else:
                page.screenshot(path=str(target), full_page=full, type="jpeg", quality=85)
            print("  ✓", name)
            context.close()
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
