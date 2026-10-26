from django.http import HttpResponse
from django.test import Client, SimpleTestCase, override_settings
from django.urls import include, path


def boom(request):
    raise RuntimeError("fallo de prueba")


def ok(request):
    return HttpResponse("ok")


urlpatterns = [
    path("api/boom/", boom),
    path("boom/", boom),
    path("ok/", ok),
    path("", include("config.urls")),
]
# Los mismos que config/urls.py (Django los busca en el urlconf raíz).
from config.urls import handler400, handler403, handler404, handler500  # noqa: E402,F401


@override_settings(ROOT_URLCONF=__name__, DEBUG=False)
class ErrorPagesTests(SimpleTestCase):
    """Con DEBUG desactivado: JSON en la API y página propia en lo demás, sin detalles internos."""

    def setUp(self):
        self.client = Client(raise_request_exception=False)

    def test_api_404_is_json(self):
        r = self.client.get("/api/no-existe/")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["status"], 404)
        self.assertIn("no existe", r.json()["detail"])

    def test_page_404_is_friendly_html(self):
        r = self.client.get("/admin-no-existe/")
        self.assertEqual(r.status_code, 404)
        html = r.content.decode()
        self.assertIn("Página no encontrada", html)
        self.assertIn("Volver al buscador", html)
        self.assertNotIn("URLconf", html)  # nada de la página de depuración

    def test_500_hides_the_error(self):
        api = self.client.get("/api/boom/")
        self.assertEqual(api.status_code, 500)
        self.assertEqual(api.json()["status"], 500)
        page = self.client.get("/boom/")
        self.assertEqual(page.status_code, 500)
        self.assertNotIn("fallo de prueba", page.content.decode())
        self.assertIn("Error del servidor", page.content.decode())
