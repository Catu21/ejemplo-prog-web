FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Estáticos para WhiteNoise. La SECRET_KEY es de relleno: solo se usa en este paso.
RUN SECRET_KEY=solo-para-build python manage.py collectstatic --no-input

# Migraciones + Gunicorn en $PORT (Render lo define). docker-compose.yml lo reemplaza por runserver.
CMD ["sh", "start.sh"]
