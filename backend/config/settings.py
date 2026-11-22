import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-not-secret" if DEBUG else None)
if not SECRET_KEY:
    SECRET_KEY = os.urandom(32).hex()  # the API is stateless, a per-process key is fine

ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".vercel.app"] + [
    h for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h
]

INSTALLED_APPS = ["routing"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "OPTIONS": {"MAX_ENTRIES": 5000},
    }
}

USE_TZ = True
TIME_ZONE = "UTC"

VALHALLA_URL = os.environ.get("VALHALLA_URL", "https://valhalla1.openstreetmap.de/route")
OPEN_METEO_URL = os.environ.get("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
PHOTON_URL = os.environ.get("PHOTON_URL", "https://photon.komoot.io/api/")

LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
