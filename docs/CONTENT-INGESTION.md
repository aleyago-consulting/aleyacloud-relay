# Ingestión de contenido por tareas

Relay puede recibir lotes desde tareas internas sin conectarse a otros
productos ni acceder a sus bases de datos. Cada tarea usa una credencial
temporal asociada a **un único Workspace y Brand**. Hay dos niveles:

- `draft`: sube imágenes y crea borradores (`media:write`, `posts:write`).
- `schedule`: además aprueba y programa sólo el contenido que crea
  (`posts:approve`, `publications:write`).

Ninguno concede publicar directamente, consultar conexiones sociales ni cambiar
de marca. Cuando llega la hora, el worker de Relay publica y deja el resultado,
el error o el reintento en la auditoría.

## Preparación de las marcas editoriales

En el servidor, como `root`, ejecutar una vez tras desplegar esta versión:

```bash
cd /srv/apps/relay
docker compose -f docker-compose.production.yml exec web python manage.py \
  provision_content_workspace \
  --workspace-slug alya-content \
  --workspace-name "AleyaCloud" \
  --brand aleyacloud:AleyaCloud \
  --brand tavisasuite:TavisaSuite \
  --brand goclinicals:GoClinicals \
  --owner-username jorge.llavata
```

Esto crea tres marcas distintas dentro del Workspace editorial. No conecta Meta,
no importa datos desde esos productos y no crea publicaciones.

## Credenciales de las tareas

Emitir una credencial por tarea y marca. Nunca pegar el resultado en un chat,
un commit, una variable de CI visible ni un archivo del repositorio. Guardarlo
en el almacén de secretos del entorno que ejecuta la tarea.

```bash
# TavisaSuite: programa el lote de su propia marca, sin publicar directamente.
docker compose -f docker-compose.production.yml exec -T web python manage.py \
  issue_draft_ingest_token \
  --workspace-slug alya-content \
  --brand-slug tavisasuite \
  --subject task:content-ingest-tavisasuite \
  --purpose schedule \
  --days 14

# GoClinicals: una credencial distinta, aislada de TavisaSuite.
docker compose -f docker-compose.production.yml exec -T web python manage.py \
  issue_draft_ingest_token \
  --workspace-slug alya-content \
  --brand-slug goclinicals \
  --subject task:content-ingest-goclinicals \
  --purpose schedule \
  --days 14
```

Las credenciales expiran como máximo a los 30 días. Para revocarlas antes de
tiempo, cambiar `RELAY_SERVICE_JWT_SECRET` revoca todos los JWT de servicio;
por ello debe tratarse como operación de emergencia y reemitirse las
credenciales activas. La siguiente evolución, cuando haga falta revocación
individual, será un registro de credenciales con identificador y digest.

## Bóveda local de tareas (Windows)

Para que una tarea no reciba el token en el chat, Relay incluye el cliente
local [`tools/relay-task-vault.ps1`](../tools/relay-task-vault.ps1). Instalarlo
en `C:\Users\Jorge\.codex\tools\relay-task-vault.ps1` para que sea accesible
desde cualquier workspace. Guarda cada perfil cifrado con DPAPI de Windows y
con una ACL privada para el usuario de Windows actual. El token no se imprime
al usar el perfil.

Después de emitir un token en el servidor, copiarlo directamente desde el
terminal y guardarlo localmente; nunca pegarlo aquí. Se necesita el UUID de la
marca que mostró `provision_content_workspace`. Para un perfil que programa,
el administrador obtiene también los UUID de los canales de esa marca (estos
identificadores no son credenciales):

```bash
docker compose -f docker-compose.production.yml exec -T web python manage.py \
  list_brand_connections \
  --workspace-slug alya-content \
  --brand-slug tavisasuite
```

```powershell
# En el equipo Windows, una vez por perfil. El script solicita el token de
# forma oculta y lo cifra en %LOCALAPPDATA%\AleyaCloud\Relay\TaskSecrets.
& 'C:\Users\Jorge\.codex\tools\relay-task-vault.ps1' `
  -Action Set -Profile tavisasuite -BrandId 'UUID-DE-TAVISASUITE' `
  -ConnectionId 'UUID-FACEBOOK-TAVISA', 'UUID-INSTAGRAM-TAVISA'

& 'C:\Users\Jorge\.codex\tools\relay-task-vault.ps1' `
  -Action Set -Profile goclinicals -BrandId 'UUID-DE-GOCLINICALS' `
  -ConnectionId 'UUID-FACEBOOK-GOCLINICALS', 'UUID-INSTAGRAM-GOCLINICALS'

& 'C:\Users\Jorge\.codex\tools\relay-task-vault.ps1' `
  -Action Set -Profile aleyacloud -BrandId 'UUID-DE-ALEYACLOUD'
```

Comprobar un perfil sin revelar el token:

```powershell
& 'C:\Users\Jorge\.codex\tools\relay-task-vault.ps1' `
  -Action Status -Profile tavisasuite
```

La cuenta de Windows es el límite de la bóveda: todas las tareas locales de
esa misma cuenta podrían invocar el cliente. La separación efectiva se logra
con un token diferente y limitado a una sola marca por perfil. No ejecutar
dos tareas de perfiles diferentes en paralelo hasta disponer de una bóveda con
identidad de tarea gestionada externamente.

## Contrato de una tarea de contenido

Las guías que se entregan a las tareas están separadas de esta documentación
administrativa:

- [AleyaCloud](content-tasks/ALEYA-CLOUD.md)
- [TavisaSuite](content-tasks/TAVISASUITE.md)
- [GoClinicals](content-tasks/GOCLINICALS.md)

Se entrega a cada tarea solamente su guía de marca, junto con el texto y la
imagen. Este documento y las credenciales quedan en administración.

Un contenido normal lleva una imagen JPG o PNG de hasta 10 MiB. Un carrusel
lleva entre dos y diez imágenes, en el orden en que deban aparecer. La tarea
de lote recibe además la fecha/hora ISO 8601 con zona horaria y un identificador
estable por contenido.

1. Usa el cliente de bóveda con el perfil asignado; éste crea la intención de
   subida, realiza el `PUT` firmado, confirma cada activo y crea el post.
2. Para un lote, usa una clave de idempotencia estable por item: reintentar el
   mismo manifiesto no duplica publicaciones.
3. Un perfil `schedule` aprueba y programa los canales que el administrador
   configuró en ese perfil. No puede ejecutar una publicación inmediata.

## Manifiesto de un lote programado

La tarea de TavisaSuite debe entregar un JSON junto a la carpeta de imágenes.
Las rutas de imagen relativas se resuelven respecto a ese JSON. Cada `id` debe
mantenerse si se reintenta el mismo lote.

```json
{
  "items": [
    {
      "id": "tavisa-2026-09-01-pantallas-01",
      "title": "Pantallas informativas",
      "body": "Texto final del post",
      "image_paths": ["images/pantallas-01.png"],
      "scheduled_for": "2026-09-01T10:30:00+02:00"
    },
    {
      "id": "tavisa-2026-09-03-carrusel-01",
      "title": "Cinco ideas para recepción",
      "body": "Texto final del carrusel",
      "image_paths": ["images/01.jpg", "images/02.jpg", "images/03.jpg"],
      "scheduled_for": "2026-09-03T10:30:00+02:00"
    }
  ]
}
```

Ejecución:

```powershell
& 'C:\Users\Jorge\.codex\tools\relay-task-vault.ps1' `
  -Action SubmitBatch -Profile tavisasuite `
  -ManifestPath 'C:\ruta\del\lote\relay-manifest.json'
```

Relay registra el actor técnico y deja cada post `APPROVED` con una publicación
`SCHEDULED` por canal autorizado. Si el perfil es `draft`, el mismo cliente
puede usar `Submit` para dejar un contenido como `DRAFT`.
