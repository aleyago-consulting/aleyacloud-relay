# Ingestión de contenido por tareas

Relay puede recibir borradores desde tareas internas sin conectarse a otros
productos, sin acceder a sus bases de datos y sin conceder capacidad de
publicación. Cada tarea usa una credencial temporal, asociada a **un único
Workspace y Brand** y con sólo estos scopes:

- `media:write`
- `posts:write`

No incluye permisos para aprobar, solicitar aprobación, programar, publicar,
consultar conexiones sociales ni cambiar de marca.

## Preparación de TavisaSuite y GoClinicals

En el servidor, como `root`, ejecutar una vez tras desplegar esta versión:

```bash
cd /srv/apps/relay
docker compose -f docker-compose.production.yml exec web python manage.py \
  provision_content_workspace \
  --workspace-slug alya-content \
  --workspace-name "Alya Content" \
  --brand tavisasuite:TavisaSuite \
  --brand goclinicals:GoClinicals \
  --owner-username jorge.llavata
```

Esto crea dos marcas distintas dentro del Workspace editorial. No conecta Meta,
no importa datos desde esos productos y no crea publicaciones.

## Credenciales de las tareas

Emitir una credencial por tarea y marca. Nunca pegar el resultado en un chat,
un commit, una variable de CI visible ni un archivo del repositorio. Guardarlo
en el almacén de secretos del entorno que ejecuta la tarea.

```bash
# TavisaSuite: devuelve únicamente el token por stdout.
docker compose -f docker-compose.production.yml exec -T web python manage.py \
  issue_draft_ingest_token \
  --workspace-slug alya-content \
  --brand-slug tavisasuite \
  --subject task:content-ingest-tavisasuite \
  --days 14

# GoClinicals: una credencial distinta, aislada de TavisaSuite.
docker compose -f docker-compose.production.yml exec -T web python manage.py \
  issue_draft_ingest_token \
  --workspace-slug alya-content \
  --brand-slug goclinicals \
  --subject task:content-ingest-goclinicals \
  --days 14
```

Las credenciales expiran como máximo a los 30 días. Para revocarlas antes de
tiempo, cambiar `RELAY_SERVICE_JWT_SECRET` revoca todos los JWT de servicio;
por ello debe tratarse como operación de emergencia y reemitirse las
credenciales activas. La siguiente evolución, cuando haga falta revocación
individual, será un registro de credenciales con identificador y digest.

## Contrato de una tarea de contenido

La tarea debe recibir texto, título opcional y una imagen JPG o PNG de hasta
10 MiB. No debe llamar a endpoints de aprobación o publicación.

1. `POST /api/v1/media/upload-intents/` con `brand_id`, nombre, tipo, tamaño y
   SHA-256; autenticado con `Authorization: Bearer <token>`.
2. Realiza `PUT` de la imagen en la URL firmada que devuelve Relay.
3. `POST /api/v1/media/{asset_id}/confirm/`.
4. `POST /api/v1/posts/` con `brand_id`, `title`, `body`, `media_asset_ids` y
   una cabecera `Idempotency-Key` única.

El último paso crea siempre un `DRAFT`. Relay registra el actor técnico en su
auditoría y el borrador queda listo para revisión humana en el panel.
