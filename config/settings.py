import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-local-development-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "rest_framework",
    "relay.api",
    "relay.tenancy",
    "relay.social",
    "relay.content",
    "relay.approvals",
    "relay.publications",
    "relay.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "relay"),
        "USER": os.environ.get("POSTGRES_USER", "relay"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "relay-local-only"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

if os.environ.get("RELAY_TEST_DATABASE") == "sqlite":
    DATABASES["default"] = {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60
CELERY_BEAT_SCHEDULE = {
    "dispatch-due-publications": {
        "task": "relay.publications.tasks.dispatch_due_publications",
        "schedule": timedelta(minutes=1),
    }
}

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "relay.api.authentication.RelayPanelSessionAuthentication",
        "relay.api.authentication.RelayServiceJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

RELAY_SERVICE_JWT_SECRET = os.environ.get(
    "RELAY_SERVICE_JWT_SECRET", "unsafe-local-development-jwt-secret"
)
RELAY_SERVICE_JWT_ISSUER = os.environ.get("RELAY_SERVICE_JWT_ISSUER", "relay.aleyacloud.com")
RELAY_SERVICE_JWT_AUDIENCE = os.environ.get("RELAY_SERVICE_JWT_AUDIENCE", "relay-api")
TOKEN_ENCRYPTION_KEY = os.environ.get("TOKEN_ENCRYPTION_KEY", "")
META_APP_ID = os.environ.get("META_APP_ID", "")
META_APP_SECRET = os.environ.get("META_APP_SECRET", "")
META_REDIRECT_URI = os.environ.get("META_REDIRECT_URI", "")
META_GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "")
RELAY_PUBLIC_API_URL = os.environ.get("RELAY_PUBLIC_API_URL", "https://relay.aleyacloud.com/api/v1")
RELAY_MEDIA_PUBLIC_BASE_URL = os.environ.get("RELAY_MEDIA_PUBLIC_BASE_URL", "")
RELAY_MEDIA_URL_TTL_SECONDS = int(os.environ.get("RELAY_MEDIA_URL_TTL_SECONDS", "900"))
B2_ENDPOINT_URL = os.environ.get("B2_ENDPOINT_URL", "")
B2_REGION = os.environ.get("B2_REGION", "")
B2_BUCKET = os.environ.get("B2_BUCKET", "")
B2_APPLICATION_KEY_ID = os.environ.get("B2_APPLICATION_KEY_ID", "")
B2_APPLICATION_KEY = os.environ.get("B2_APPLICATION_KEY", "")
RELAY_PUBLICATION_MAX_ATTEMPTS = int(os.environ.get("RELAY_PUBLICATION_MAX_ATTEMPTS", "3"))
