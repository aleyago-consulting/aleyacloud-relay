# Tarea de contenido — GoClinicals

## Objetivo

Subir el lote recibido a Relay para la marca **GoClinicals** y dejar cada pieza
programada en sus fechas. Relay, no esta tarea, ejecutará la publicación.

## Límites de autoridad

Esta tarea puede:

- subir una imagen JPG o PNG de hasta 10 MiB, o un carrusel de 2 a 10 imágenes;
- crear, aprobar y programar el post en los canales configurados para GoClinicals;
- informar los identificadores y el resultado de cada programación.

Esta tarea no puede ni debe:

- publicar de forma directa, cancelar contenido o elegir conexiones sociales;
- modificar conexiones sociales o credenciales;
- acceder a contenido de AleyaCloud, TavisaSuite u otras marcas;
- solicitar, mostrar o guardar credenciales de Relay.

## Material de entrada

Se debe recibir antes de actuar:

- manifiesto JSON de lote con un `id` estable, texto, título opcional, imágenes
  y fecha/hora ISO 8601 con zona horaria por pieza;
- una imagen para una publicación normal, o de dos a diez para un carrusel;
- correcciones explícitas si el contenido sustituye una pieza previa.

Si falta texto o imagen, pedirlo. No inventar datos clínicos, resultados,
precios, disponibilidad, enlaces ni afirmaciones sujetas a verificación.

## Ejecución en Relay

Usar únicamente el cliente local autorizado con el perfil `goclinicals`. No
pedir, mostrar ni extraer tokens. El cliente cifra el perfil localmente, sube
las imágenes, crea el post, lo aprueba y programa sus canales permitidos.

Ejecutar `C:\Users\Jorge\.codex\tools\relay-task-vault.ps1` con
`-Action SubmitBatch -Profile goclinicals -ManifestPath RUTA_AL_MANIFIESTO`.
El formato exacto está en `docs/CONTENT-INGESTION.md`.

No llamar a la API de Relay directamente ni a Meta. El cliente es el único
medio autorizado; programar no es publicar.

## Resultado esperado

Crear el contenido para la marca `goclinicals` dentro del Workspace editorial
autorizado. Confirmar al finalizar:

- que cada post está `APPROVED`;
- que hay una publicación `SCHEDULED` por canal configurado;
- el título o extracto que identifica cada pieza y si las imágenes quedaron
  asociadas en el orden correcto.

No anunciar que algo se ha publicado: una programación de Relay no es una
publicación en redes sociales.
