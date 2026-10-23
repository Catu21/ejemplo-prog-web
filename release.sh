#!/bin/sh
# Tareas de despliegue (Cloud Run Job): migraciones y usuario demo.
set -e
python manage.py migrate --no-input
python manage.py crear_demo
