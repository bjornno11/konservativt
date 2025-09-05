# konservativt/settings.py
FORCE_SCRIPT_NAME = "/konservativt"
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
