"""Páginas de error propias (solo con DEBUG desactivado, como en producción).

- En la API (/api/…): JSON con `detail`, igual que el resto de errores de DRF.
- En lo demás (admin, fotos…): una página (en inglés) con el estilo de la web.
"""
from html import escape

from django.http import HttpResponse, JsonResponse

MESSAGES = {
    400: ("Bad request", "Something in the request could not be understood."),
    403: ("Access denied", "You do not have permission to see this page."),
    404: ("Page not found", "This address does not exist or is no longer available."),
    500: ("Server error", "Something went wrong on the server. Please try again in a moment."),
}

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · DragonBall EnhancedAPI</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: #0f1117;
         color: #e8eaf0; font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ max-width: 30rem; padding: 2rem 1.25rem; text-align: center; }}
  .ball {{ width: 64px; height: 64px; margin: 0 auto 1.25rem; border-radius: 50%; display: grid; place-items: center;
          background: radial-gradient(circle at 35% 30%, #ffd08a, #f59e0b 55%, #c2410c); color: #b91c1c; font-size: 1.6rem; }}
  .code {{ color: #f59e0b; font-weight: 700; letter-spacing: .08em; }}
  h1 {{ margin: .25rem 0 .5rem; font-size: 1.6rem; }}
  p {{ margin: 0 0 1.5rem; color: #9aa1ad; }}
  a {{ display: inline-block; padding: .55rem 1.1rem; border-radius: 8px; background: #f59e0b; color: #1a1205;
       font-weight: 600; text-decoration: none; }}
  a:hover {{ filter: brightness(1.08); }}
</style>
</head>
<body>
<main>
  <div class="ball" aria-hidden="true">★</div>
  <div class="code">ERROR {status}</div>
  <h1>{title}</h1>
  <p>{message}</p>
  <a href="/">Back to the search</a>
</main>
</body>
</html>
"""


def _error(request, status: int) -> HttpResponse:
    title, message = MESSAGES[status]
    if request.path.startswith("/api/"):
        return JsonResponse({"detail": message, "status": status}, status=status)
    return HttpResponse(PAGE.format(status=status, title=escape(title), message=escape(message)), status=status)


def bad_request(request, exception=None):
    return _error(request, 400)


def permission_denied(request, exception=None):
    return _error(request, 403)


def page_not_found(request, exception=None):
    return _error(request, 404)


def server_error(request):
    return _error(request, 500)
