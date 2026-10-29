from django.contrib.auth.models import User
from django.test import Client, TestCase


class SessionCsrfTests(TestCase):
    """Con la sesión del admin iniciada, la API exige el token CSRF (la web lo manda en X-CSRFToken).
    El 28/10/2026 la web no lo mandaba y, tras entrar en /admin, el buscador daba 403."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def search(self, **headers):
        return self.client.post("/api/cards/search/", "{}", content_type="application/json", **headers)

    def test_anonymous_needs_no_token(self):
        self.assertEqual(self.search().status_code, 200)

    def test_with_admin_session_the_token_is_required(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@a.es", "x"))
        self.client.get("/admin/")  # deja la cookie csrftoken, como en el navegador
        self.assertEqual(self.search().status_code, 403)
        token = self.client.cookies["csrftoken"].value
        self.assertEqual(self.search(HTTP_X_CSRFTOKEN=token).status_code, 200)
