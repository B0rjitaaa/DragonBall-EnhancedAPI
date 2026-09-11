"""Settings de DragonBall-EnhancedAPI. Toda la configuración sensible llega por variables de entorno."""
import os
from pathlib import Path

from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    return env(name, str(default)).lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [x.strip() for x in env(name, default).split(",") if x.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "corsheaders",
    "django_celery_beat",
    "drf_spectacular",
    "cards",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "dbs"),
        "USER": env("POSTGRES_USER", "dbs"),
        "PASSWORD": env("POSTGRES_PASSWORD", "dbs"),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

REDIS_URL = env("REDIS_URL", "redis://localhost:6379")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"{REDIS_URL}/1",
        "TIMEOUT": 60 * 60,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- DRF -------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "cards.pagination.CardPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]
    + (["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": env("API_ANON_RATE", "1000/min")},
}

SPECTACULAR_SETTINGS = {
    "TITLE": "DragonBall-EnhancedAPI",
    "DESCRIPTION": "Buscador avanzado de cartas de Dragon Ball Super Card Game",
    "VERSION": "0.1.0",
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

# --- Celery ----------------------------------------------------------------
CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/0"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 60 * 3  # un sync completo puede tardar
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# Se registran en la BD al arrancar beat y se pueden editar desde /admin
CELERY_BEAT_SCHEDULE = {
    "sync-new-cards-daily": {
        "task": "cards.tasks.sync_cards",
        "schedule": crontab(hour=4, minute=0),
        "kwargs": {"full": False},
    },
    "sync-banlist-daily": {
        "task": "cards.tasks.sync_banlist",
        "schedule": crontab(hour=3, minute=30),
    },
    "sync-keyword-skills-weekly": {
        "task": "cards.tasks.sync_keyword_skills",
        "schedule": crontab(hour=3, minute=45, day_of_week="mon"),
    },
    "sync-all-cards-weekly": {
        "task": "cards.tasks.sync_cards",
        "schedule": crontab(hour=5, minute=0, day_of_week="sun"),
        "kwargs": {"full": True},
    },
}

# --- Bandai TCG+ -------------------------------------------------------------
BANDAI_API_URL = env("BANDAI_API_URL", "https://api.bandai-tcg-plus.com/api/user")
BANDAI_GAME_TITLE_ID = int(env("BANDAI_GAME_TITLE_ID", "1"))
BANDAI_REQUEST_DELAY = float(env("BANDAI_REQUEST_DELAY", "0.25"))
BANDAI_WORKERS = int(env("BANDAI_WORKERS", "4"))
KEYWORD_SKILLS_URL = env("KEYWORD_SKILLS_URL", "https://www.dbs-cardgame.com/us-en/rule/keyword-skills.php")
BANLIST_URL = env("BANLIST_URL", "https://www.dbs-cardgame.com/us-en/rule/banned-limited-cards.php")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
