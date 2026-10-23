# Despliegue en Google Cloud (Cloud Run + Cloud SQL)

```
Internet ──HTTPS──> Cloud Run (contenedor: Gunicorn + Django)
                         │ socket /cloudsql/...
                         ▼
                    Cloud SQL (PostgreSQL 16)
Secret Manager ──> SECRET_KEY, DB_PASSWORD, DEMO_PASSWORD
Cloud Run Job  ──> release.sh (migrate + crear_demo), misma imagen
```

- **Cloud Run** ejecuta la imagen del `Dockerfile` (su `CMD` arranca Gunicorn en `$PORT`). Escala a cero cuando no hay tráfico.
- **Cloud SQL** es el PostgreSQL administrado. Cloud Run se conecta por un socket Unix montado en `/cloudsql/<conexión>`; por eso `DB_HOST=/cloudsql/...` (Django/psycopg aceptan una carpeta de socket como host).
- **Secret Manager** guarda las contraseñas; Cloud Run las inyecta como variables de entorno.
- **Cloud Run Job** corre `release.sh` con la misma imagen: aplica migraciones y crea el usuario demo. Se ejecuta en cada versión nueva (equivale al `build.sh` de Render).

> **Costo:** Cloud Run tiene capa gratuita; **Cloud SQL no**: la instancia `db-f1-micro` cobra mientras esté encendida (unos dólares al mes). Las cuentas nuevas reciben crédito de prueba. Ver "Apagar o borrar" al final.

Los comandos son para **PowerShell**, ejecutados en la ra?z del repositorio `ejemplo-prog-web`.

## 0. Preparación (una sola vez)

1. Instala Google Cloud CLI: `winget install Google.CloudSDK` (o el instalador de cloud.google.com/sdk). Abre una terminal nueva.
2. `gcloud auth login`
3. En console.cloud.google.com crea un proyecto y **vincúlale una cuenta de facturación** (Cloud SQL lo exige).
4. Docker Desktop encendido (la imagen se construye en tu PC).

## 1. Variables

```powershell
$PROJECT  = "tu-proyecto-id"          # el ID, no el nombre
$REGION   = "us-central1"
$INSTANCE = "api-tareas-db"
$REPO     = "api-tareas"
$IMAGE    = "$REGION-docker.pkg.dev/$PROJECT/$REPO/api:v1"
$SA       = "api-tareas-run@$PROJECT.iam.gserviceaccount.com"

gcloud config set project $PROJECT
gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com
```

Si cierras la terminal, vuelve a definir estas variables (y `$CONN` del paso 2) antes de seguir.

## 2. Base de datos (Cloud SQL)

```powershell
# Tarda varios minutos
gcloud sql instances create $INSTANCE --database-version=POSTGRES_16 --edition=enterprise --tier=db-f1-micro --region=$REGION

gcloud sql databases create api_tareas --instance=$INSTANCE

$DB_PASSWORD = python -c "import secrets; print(secrets.token_urlsafe(24))"
gcloud sql users create app --instance=$INSTANCE --password=$DB_PASSWORD

# Nombre de conexión: PROYECTO:REGION:INSTANCIA
$CONN = gcloud sql instances describe $INSTANCE --format="value(connectionName)"
$CONN
```

## 3. Secretos

PowerShell agrega un salto de línea al usar `|`, que quedaría dentro de la contraseña. Esta función lo evita escribiendo un archivo temporal:

```powershell
function New-Secret($name, $value) {
  $f = New-TemporaryFile
  [IO.File]::WriteAllText($f, $value)
  gcloud secrets create $name --data-file=$f
  Remove-Item $f
}

New-Secret django-secret-key (python -c "import secrets; print(secrets.token_urlsafe(50))")
New-Secret db-password $DB_PASSWORD
New-Secret demo-password "escribe-aqui-la-contrasena-del-demo"
```

## 4. Cuenta de servicio (permisos mínimos)

La app corre con su propia identidad, que solo puede conectarse a Cloud SQL y leer secretos:

```powershell
gcloud iam service-accounts create api-tareas-run
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$SA" --role="roles/cloudsql.client"
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor"
```

## 5. Imagen (Artifact Registry)

```powershell
gcloud artifacts repositories create $REPO --repository-format=docker --location=$REGION
gcloud auth configure-docker "$REGION-docker.pkg.dev"

docker build -t $IMAGE .
docker push $IMAGE
```

`.dockerignore` evita que tu `.env` entre en la imagen.

## 6. Migraciones (Cloud Run Job)

```powershell
gcloud run jobs create api-tareas-release --image=$IMAGE --region=$REGION `
  --service-account=$SA --set-cloudsql-instances=$CONN `
  --set-env-vars="DB_NAME=api_tareas,DB_USER=app,DB_HOST=/cloudsql/$CONN,DEMO_USER=demo" `
  --set-secrets="SECRET_KEY=django-secret-key:latest,DB_PASSWORD=db-password:latest,DEMO_PASSWORD=demo-password:latest" `
  --command=sh --args=release.sh

gcloud run jobs execute api-tareas-release --region=$REGION --wait
```

## 7. Servicio web (Cloud Run)

```powershell
gcloud run deploy api-tareas --image=$IMAGE --region=$REGION `
  --service-account=$SA --add-cloudsql-instances=$CONN --allow-unauthenticated `
  --set-env-vars="DEBUG=False,DB_NAME=api_tareas,DB_USER=app,DB_HOST=/cloudsql/$CONN" `
  --set-secrets="SECRET_KEY=django-secret-key:latest,DB_PASSWORD=db-password:latest"
```

La URL se conoce hasta después del primer deploy, así que `ALLOWED_HOSTS` se agrega enseguida (mientras tanto Django responde 400):

```powershell
$URL = gcloud run services describe api-tareas --region=$REGION --format="value(status.url)"
$RUN_HOST = $URL -replace "^https://", ""
gcloud run services update api-tareas --region=$REGION --update-env-vars="ALLOWED_HOSTS=$RUN_HOST,CSRF_TRUSTED_ORIGINS=$URL"
$URL
```

Cloud Run también publica una segunda URL alternativa; esa devolverá 400 porque no está en `ALLOWED_HOSTS`. Usa la que imprime `$URL`.

## 8. Probar

```powershell
curl.exe "$URL/api/tasks/"
python clientes/cliente.py $URL
```

Y abre `$URL` en el navegador (frontend) e inicia sesión con `demo` y la contraseña de `demo-password`.

## Publicar una versión nueva

```powershell
$IMAGE = "$REGION-docker.pkg.dev/$PROJECT/$REPO/api:v2"   # sube el número
docker build -t $IMAGE .
docker push $IMAGE
gcloud run jobs update api-tareas-release --image=$IMAGE --region=$REGION
gcloud run jobs execute api-tareas-release --region=$REGION --wait   # migraciones primero
gcloud run deploy api-tareas --image=$IMAGE --region=$REGION         # conserva variables y secretos
```

## Problemas comunes

- **Ver errores:** consola de Google Cloud → Cloud Run → servicio o job → pestaña *Logs*, o `gcloud run services logs read api-tareas --region=$REGION`.
- **400 Bad Request:** el host no está en `ALLOWED_HOSTS` (paso 7).
- **`connection ... /cloudsql/... failed`:** falta `--add-cloudsql-instances` / `--set-cloudsql-instances`, el `$CONN` está mal o la cuenta de servicio no tiene `roles/cloudsql.client`.
- **`Permission denied on secret`:** falta `roles/secretmanager.secretAccessor`.
- **`Define la variable de entorno SECRET_KEY`:** con `DEBUG=False` es obligatoria; revisa `--set-secrets`.

## Apagar o borrar

```powershell
# Apagar Cloud SQL (deja de cobrar CPU/RAM; el disco sigue cobrando)
gcloud sql instances patch $INSTANCE --activation-policy=NEVER
# Encender de nuevo
gcloud sql instances patch $INSTANCE --activation-policy=ALWAYS

# Borrar todo
gcloud run services delete api-tareas --region=$REGION
gcloud run jobs delete api-tareas-release --region=$REGION
gcloud sql instances delete $INSTANCE
```

O borra el proyecto completo desde la consola.
