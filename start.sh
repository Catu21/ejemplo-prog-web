#!/bin/sh
# Arranque del contenedor en producción (Render con Docker).
set -e
python manage.py migrate --no-input      # crea/actualiza las tablas en PostgreSQL
python manage.py crear_demo || echo "Aviso: usuario demo no creado (define DEMO_PASSWORD)"
# --access-logfile - : muestra cada petición en los logs de Render
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8080} \
    --workers 1 --threads 8 --timeout 0 --access-logfile -
