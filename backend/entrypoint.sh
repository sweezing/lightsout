#!/bin/sh
set -e

python manage.py wait_for_db

if [ "$RUN_MIGRATIONS" = "1" ]; then
    python manage.py migrate --noinput

    if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
        python manage.py createsuperuser --noinput >/dev/null 2>&1 || true
    fi

    if [ "$LOAD_SEED" = "1" ]; then
        python manage.py seed --if-empty
    fi
fi

exec "$@"
