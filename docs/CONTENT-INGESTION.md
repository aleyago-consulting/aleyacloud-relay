# Ingestión de contenido por tareas

Relay puede recibir borradores desde tareas internas sin conectarse a otros
productos, sin acceder a sus bases de datos y sin conceder capacidad de
publicación. Cada tarea usa una credencial temporal, asociada a **un único
Workspace y Brand** y con sólo estos scopes:

- `media:write`
- `posts:write`

No incluye permisos para aprobar, solicitar aprobación, programar, publicar,
consultar conexiones sociales ni cambiar de marca.

## Preparación de las marcas editoriales

En el servidor, como `root`, ejecutar una vez tras desplegar esta versión:

```bash
cd /srv/apps/relay
docker compose -f docker-compose.production.yml exec web python manage.py \
  provision_content_workspace \
  --workspace-slug alya-content \
  --workspace-name "Alya Content" \
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

## Bóveda local de tareas (Windows)

Para que una tarea no reciba el token en el chat, Relay incluye el cliente
local [`tools/relay-task-vault.ps1`](../tools/relay-task-vault.ps1). Instalarlo
en `C:\Users\Jorge\.codex\tools\relay-task-vault.ps1` para que sea accesible
desde cualquier workspace. Guarda cada perfil cifrado con DPAPI de Windows y
con una ACL privada para el usuario de Windows actual. El token no se imprime
al usar el perfil.

Después de emitir un token en el servidor, copiarlo directamente desde el
terminal y guardarlo localmente; nunca pegarlo aquí. Se necesita el UUID de la
marca que mostró `provision_content_workspace`.

```powershell
# En el equipo Windows, una vez por perfil. El script solicita el token de
# forma oculta y lo cifra en %LOCALAPPDATA%\AleyaCloud\Relay\TaskSecrets.
& 'C:\Users\Jorge\.codex\tools\relay-task-vault.ps1' `
  -Action Set -Profile tavisasuite -BrandId 'UUID-DE-TAVISASUITE'

& 'C:\Users\Jorge\.codex\tools\relay-task-vault.ps1' `
  -Action Set -Profile goclinicals -BrandId 'UUID-DE-GOCLINICALS'

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

La tarea debe recibir texto, título opcional y una imagen JPG o PNG de hasta
10 MiB. No debe llamar a endpoints de aprobación o publicación.

1. Usa el cliente de bóveda con el perfil asignado; éste crea la intención de
   subida, realiza el `PUT` firmado, confirma el activo y crea el post.
2. El cliente llama únicamente a los endpoints de multimedia y borradores con
   una `Idempotency-Key` nueva.

El último paso crea siempre un `DRAFT`. Relay registra el actor técnico en su
auditoría y el borrador queda listo para revisión humana en el panel.
