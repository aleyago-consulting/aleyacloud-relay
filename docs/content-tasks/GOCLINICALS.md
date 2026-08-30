# Tarea de contenido — GoClinicals

## Objetivo

Subir el material recibido como un borrador de contenido en Relay para la marca
**GoClinicals**. El borrador debe quedar listo para revisión humana.

## Límites de autoridad

Esta tarea puede:

- subir una imagen JPG o PNG de hasta 10 MiB;
- crear un post en estado `DRAFT`;
- informar el identificador y el resultado del borrador.

Esta tarea no puede ni debe:

- aprobar, programar, publicar o cancelar contenido;
- modificar conexiones sociales o credenciales;
- acceder a contenido de AleyaCloud, TavisaSuite u otras marcas;
- solicitar, mostrar o guardar credenciales de Relay.

## Material de entrada

Se debe recibir antes de actuar:

- texto final del post;
- título opcional;
- imagen JPG o PNG adjunta;
- correcciones explícitas si el contenido sustituye a un borrador previo.

Si falta texto o imagen, pedirlo. No inventar datos clínicos, resultados,
precios, disponibilidad, enlaces ni afirmaciones sujetas a verificación.

## Ejecución en Relay

El entorno autorizado entrega `RELAY_API_TOKEN` y `RELAY_BRAND_ID`; no pedirlos
ni escribirlos en mensajes, archivos o resultados. Usarlos sólo durante la
ejecución:

1. Crear la intención en `POST /api/v1/media/upload-intents/` con la imagen,
   `brand_id` y su SHA-256.
2. Subir el archivo mediante `PUT` a la URL firmada recibida.
3. Confirmar el activo con `POST /api/v1/media/{asset_id}/confirm/`.
4. Crear el borrador mediante `POST /api/v1/posts/`, con una
   `Idempotency-Key` nueva, título opcional, texto y el `asset_id`.

No llamar a ningún endpoint de aprobación, publicación o programación.

## Resultado esperado

Crear el contenido para la marca `goclinicals` dentro del Workspace editorial
autorizado. Confirmar al finalizar:

- que el estado es `DRAFT`;
- el título o extracto que identifica el borrador;
- si la imagen quedó asociada correctamente.

No anunciar que algo se ha publicado: un borrador de Relay no es una
publicación en redes sociales.
