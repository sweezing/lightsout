#build context is the repository root (see docker-compose.yml),
#so the seed data in /seed ships inside the image.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SEED_DIR=/app/seed

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY backend/ /app/
COPY seed/ /app/seed/

RUN chmod +x /app/entrypoint.sh \
    && DJANGO_SECRET_KEY=build python manage.py collectstatic --noinput

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
