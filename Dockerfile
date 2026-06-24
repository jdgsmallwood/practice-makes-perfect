FROM python:3.11-slim-bookworm

# Multi-arch manifest: Docker Hub serves linux/arm64 automatically on Raspberry Pi

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# Pillow system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg-dev \
        zlib1g-dev \
        libpng-dev \
        libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY config    config/
COPY accounts  accounts/
COPY pieces    pieces/
COPY practice  practice/
COPY omr       omr/
COPY scales    scales/
COPY templates templates/
COPY static    static/
COPY manage.py .

RUN pip install --no-cache-dir .

# Bake static files into the image; WhiteNoise serves them at runtime.
# prod.py requires ALLOWED_HOSTS/SECRET_KEY from the environment, but
# collectstatic doesn't actually use them — set placeholders just to satisfy
# the import. The real values come from docker-compose at container start.
RUN mkdir -p data media && \
    SECRET_KEY=build-placeholder \
    ALLOWED_HOSTS=localhost \
    CSRF_TRUSTED_ORIGINS=http://localhost \
    python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "\
  python manage.py migrate --noinput && \
  gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 60 \
    --access-logfile -"]
