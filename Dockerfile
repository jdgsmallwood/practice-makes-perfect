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
COPY pieces    pieces/
COPY practice  practice/
COPY omr       omr/
COPY templates templates/
COPY static    static/
COPY manage.py .

RUN pip install --no-cache-dir .

# Bake static files into the image; WhiteNoise serves them at runtime.
# The manifest (staticfiles.json) enables aggressive browser caching with
# fingerprinted filenames.
RUN mkdir -p data media && python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "\
  python manage.py migrate --noinput && \
  gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 60 \
    --access-logfile -"]
