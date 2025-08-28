"""
Django settings for konservativt project.
"""

from pathlib import Path
import os

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- .env (valgfritt, anbefalt i prod) ---
try:
    from dotenv import load_dotenv  # pip install python-dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

# --- Security / Debug ---
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-me"  # bytt i .env i prod
)
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = ["q1.no", "www.q1.no", "127.0.0.1", "localhost"]
CSRF_TRUSTED_ORIGINS = ["https://q1.no", "https://www.q1.no"]


STATICFILES_DIRS = [
    BASE_DIR / "konservativt" / "static",
]


# --- Apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Dine apper
    "docs",
    "access",
    "geo", 
    "members",
    "audit",
    "portal",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
     'audit.middleware.PageViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# --- URLs / WSGI ---
ROOT_URLCONF = "konservativt.urls"
WSGI_APPLICATION = "konservativt.wsgi.application"

# --- Templates ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # dine templates
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

# --- Database (MySQL) ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "konservativt"),
        "USER": os.getenv("DB_USER", "konservativt"),
        "PASSWORD": os.getenv("DB_PASSWORD", "Tula-2012"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
    }
}

# --- Auth / Redirects ---
LOGIN_URL = "/accounts/login/"
# Bruk namespace fordi docs/urls.py har app_name="docs"
LOGIN_REDIRECT_URL = "docs:docs-list"

# --- I18N / TZ ---
LANGUAGE_CODE = "nb"
TIME_ZONE = "Europe/Oslo"
USE_I18N = True
USE_TZ = True

# --- Kjører under URL-prefiks /konservativt ---
# Nginx STRIPPER prefiks (proxy_pass ...9071/;), men vi vil at reverserte lenker skal ha /konservativt
FORCE_SCRIPT_NAME = "/konservativt"

# --- Static / Media ---
STATIC_URL = "/konservativt/static/"
MEDIA_URL = "/konservativt/media/"
STATIC_ROOT = "/srv/konservativt/static/"
MEDIA_ROOT = BASE_DIR / "media"

# --- Proxy / sikkerhet ---
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [
    "https://q1.no",
    "https://www.q1.no",
]

# --- Unngå cookie-kollisjon med annen app på samme domene ---
SESSION_COOKIE_NAME = "konservativt_sessionid"
CSRF_COOKIE_NAME = "konservativt_csrftoken"
SESSION_COOKIE_PATH = "/konservativt"
CSRF_COOKIE_PATH = "/konservativt"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# --- Default PK ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- safety patch: ensure 'audit' (not 'membersaudit') ---
INSTALLED_APPS = [a for a in INSTALLED_APPS if a != "membersaudit"]
if "audit" not in INSTALLED_APPS:
    INSTALLED_APPS.append("audit")
