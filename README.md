# Ejemplo Prog Web ? API de tareas

Práctica educativa: API de tareas con JWT, un frontend HTML/JS y un cliente Python, lista para ejecutarse en localhost y desplegarse en Render.

```
config/          configuración del proyecto (settings, urls)
tasks/           app: modelo, serializer, vista, tests, frontend (templates/index.html)
clientes/        cliente.py (requests)
build.sh         build de Render
Dockerfile       imagen de producción (Gunicorn); docker-compose.yml para desarrollo
release.sh       migraciones + usuario demo (Cloud Run Job)
DEPLOY_GCP.md    guía de despliegue en Google Cloud Run + Cloud SQL
render.yaml      blueprint de Render
```

## 1. Ejecutar en localhost

### Con Docker Compose (recomendado)

Requiere Docker Desktop. Levanta PostgreSQL 16 y la API; aplica migraciones y crea el usuario demo.

```bash
cd "ejemplo-prog-web"
copy .env.example .env            # Linux/macOS: cp .env.example .env
# edita .env: DEMO_PASSWORD y DB_PASSWORD
docker compose up --build
```

- Pruebas: `docker compose exec web python manage.py test`
- Consola SQL: `docker compose exec db psql -U postgres -d api_tareas`
- Detener: `docker compose down` (los datos quedan en el volumen `pgdata`; `down -v` los borra)

### Sin Docker

Requiere Python 3.11+ y PostgreSQL corriendo con los valores `DB_*` de `.env` (con el compose, `docker compose up db` basta).

```bash
cd "ejemplo-prog-web"
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env            # Linux/macOS: cp .env.example .env
# edita .env: pon un DEMO_PASSWORD (y deja DEBUG=True)

python manage.py migrate
python manage.py crear_demo       # crea el usuario con DEMO_USER / DEMO_PASSWORD
python manage.py runserver
```

Abre http://127.0.0.1:8000 (frontend). La API está en http://127.0.0.1:8000/api/tasks/.
Pruebas automáticas: `python manage.py test`.

## 2. Endpoints

| Método | Endpoint | Auth | Éxito | Errores |
|---|---|---|---|---|
| GET | `/api/tasks/` | No | 200 | |
| GET | `/api/tasks/{id}/` | No | 200 | 404 |
| POST | `/api/tasks/` | JWT | 201 | 400, 401 |
| PATCH | `/api/tasks/{id}/` | JWT | 200 | 400, 401, 404 |
| DELETE | `/api/tasks/{id}/` | JWT | 204 | 401, 404 |
| POST | `/api/token/` | No | 200 | 400, 401 |

Un 401 indica token ausente, inválido o expirado (dura 5 minutos). No hay roles, por lo que 403 solo aparecería ante un permiso denegado; no se usa en esta práctica.

## 3. Ejemplos de solicitudes HTTP

```bash
# Obtener token
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"TU_PASSWORD"}'
# -> {"refresh":"...","access":"<TOKEN>"}

# Listar (sin autenticación)
curl http://127.0.0.1:8000/api/tasks/

# Crear
curl -X POST http://127.0.0.1:8000/api/tasks/ \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"title":"Estudiar","description":"Unidad 2"}'

# Marcar como completada
curl -X PATCH http://127.0.0.1:8000/api/tasks/1/ \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"completed":true}'

# Eliminar
curl -X DELETE http://127.0.0.1:8000/api/tasks/1/ -H "Authorization: Bearer <TOKEN>"

# Sin token -> 401
curl -i -X POST http://127.0.0.1:8000/api/tasks/ -H "Content-Type: application/json" -d '{"title":"x"}'
```

## 4. Tres clientes, una API

1. **Postman**: crea `POST /api/token/` (Body → raw → JSON), copia `access`; en las demás solicitudes usa Authorization → Bearer Token. Usa una variable `{{base}}` = `http://127.0.0.1:8000` (o la URL de Render) para cambiar de entorno.
2. **Navegador (fetch)**: abre `/`. Lista las tareas sin sesión; inicia sesión para crear, completar y eliminar. Los errores se muestran con su código HTTP.
3. **Python (requests)**: `python clientes/cliente.py [URL_BASE]`.

Los tres reciben JSON (`Content-Type: application/json`).

**CORS**: el frontend incluido se sirve desde el mismo origen, así que no lo necesita. Si alojas la página en otro dominio, agrega ese origen a `CORS_ALLOWED_ORIGINS` (separados por comas) y cambia la constante `API` en `index.html` por la URL de la API.

## 5. Localhost vs. nube

Mismo código; solo cambian las variables de entorno:

| | Localhost | Render |
|---|---|---|
| Servidor | `runserver` | Gunicorn |
| `DEBUG` | True | False |
| Base de datos | PostgreSQL (Docker, variables `DB_*`) | PostgreSQL de Render (`DATABASE_URL`) |
| HTTPS | No (http) | Lo provee Render; Django redirige a HTTPS |
| Acceso | 127.0.0.1 | URL pública `*.onrender.com` |

> **Nota:** `render.yaml` crea también la base PostgreSQL gratuita (`api-tareas-db`) y pasa su `DATABASE_URL` al servicio web. La base gratuita de Render expira a los 30 días.

## 6. Despliegue en Render

1. Sube el repositorio a GitHub.
2. En Render: **New → Blueprint** (usa `render.yaml`) o **New → Web Service** con:
   - Root Directory: dejar vac?o (el proyecto est? en la ra?z del repositorio)
   - Build Command: `./build.sh`
   - Start Command: `gunicorn config.wsgi:application`
3. Variables de entorno: `DEBUG=False`, `SECRET_KEY` (generada), `DEMO_USER`, `DEMO_PASSWORD` (escríbela en el panel), y opcionalmente `DATABASE_URL`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`. `RENDER_EXTERNAL_HOSTNAME` lo define Render y se agrega solo a `ALLOWED_HOSTS`.
4. Cuando termine el deploy, prueba con la URL pública: `python clientes/cliente.py https://TU-APP.onrender.com`.

Estado: la configuración está preparada pero **el despliegue en Render no se ha probado**; el proyecto se verificó únicamente en localhost (tests y solicitudes reales). Gunicorn no corre en Windows, por lo que tampoco se probó localmente.

## 7. Despliegue en Google Cloud

Cloud Run + Cloud SQL (PostgreSQL). Pasos completos en [DEPLOY_GCP.md](DEPLOY_GCP.md). La imagen de producción se probó localmente (Gunicorn, migraciones, HTTPS, estáticos); el despliegue en Google Cloud no se ha probado.
