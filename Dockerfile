FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Estáticos para WhiteNoise. La SECRET_KEY es de relleno: solo se usa en este paso.
RUN SECRET_KEY=solo-para-build python manage.py collectstatic --no-input

# Arranque con Gunicorn en $PORT (8080 si no se define).
# docker-compose.yml reemplaza este comando por runserver para desarrollo.
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 0"]
