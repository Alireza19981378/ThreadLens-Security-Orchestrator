INSTALLED_APPS = [
    # ...
    "corsheaders",
    "rest_framework",
    "scanner_engine",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    # ...
]

# CORS for Next.js/React
# Prefer environment variable split by comma
import os
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

# Optional:
# CORS_ALLOW_CREDENTIALS = True

# Celery/Redis
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
