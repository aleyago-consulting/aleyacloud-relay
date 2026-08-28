# Activación de Meta para Relay

Este documento permite poner en marcha el primer canal real de Relay:
Facebook Pages e Instagram Professional (Business o Creator). No incluye
anuncios, mensajes, grupos ni cuentas personales.

## Qué está preparado en Relay

- OAuth con `state` aleatorio, de un solo uso y con caducidad de diez minutos.
- Descubrimiento de las Pages autorizadas y de las cuentas de Instagram
  Professional vinculadas a cada Page.
- Tokens cifrados en la base de datos de Relay; no se devuelven por API ni se
  escriben en logs.
- Carga directa de JPEG/PNG de hasta 10 MB a B2 mediante una URL firmada,
  seguida de una comprobación de tamaño y tipo antes de aceptar el archivo.
- Publicación programada de texto e imagen, con un intento inmutable por llamada,
  reintentos acotados y registro de resultado.

Relay usa el flujo de Facebook Login para descubrir conjuntamente Pages y sus
cuentas de Instagram Professional vinculadas. Una cuenta de Instagram que no
esté vinculada a una Page no aparecerá en este primer flujo.

## Crear y configurar la Meta App

1. Con una cuenta de empresa de Meta que vaya a conservarse, crear una App de
   tipo **Business** en Meta for Developers. Relay debe tener al menos dos
   administradores de la App; no usar una cuenta personal como propietario
   único.
2. Añadir el producto de inicio de sesión de Facebook y el caso de uso/API de
   Pages e Instagram que ofrezca el panel. Configurar exactamente esta URL de
   redirección OAuth:

   `https://relay.aleyacloud.com/api/v1/oauth/meta/callback/`

3. Registrar `relay.aleyacloud.com` como dominio de la App y completar los
   campos de política de privacidad, eliminación de datos y contacto de soporte
   con URLs reales de Relay antes de solicitar acceso para terceros.
4. Durante pruebas, añadir al equipo de la App las personas que vayan a
   conectar activos de prueba. Deben tener acceso administrativo a la Facebook
   Page y a la cuenta de Instagram Professional vinculada.
5. Solicitar únicamente los permisos que necesita el código actual:

   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`,
   `instagram_basic` e `instagram_content_publish`.

   Meta puede mostrar nombres o requisitos distintos según el producto/caso de
   uso elegido. Antes de enviar App Review, confirmar en su panel que esos son
   los permisos concedidos al flujo de Facebook Login de Relay. No añadir
   permisos de anuncios, mensajes, grupos o datos de perfil que Relay no usa.
6. Mantener la App en modo desarrollo hasta que una cuenta de prueba complete
   el recorrido entero. Para conectar marcas ajenas al equipo de la App, pasar
   a producción y completar la revisión que Meta requiera.

Las guías de Meta exigen que la imagen sea accesible para sus servidores cuando
se publica. Relay satisface ese requisito con una URL firmada de B2 de vida
corta: el bucket continúa siendo privado. [Referencia de la colección oficial
de Meta](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-ab559ffb-8e2c-4b0a-b43a-5737b6d2f672)

## Secretos de producción

Añadir estos valores a `/srv/secrets/relay/production.env`, sin compartirlos por
chat, Git ni capturas:

```dotenv
META_APP_ID=valor-del-panel-meta
META_APP_SECRET=secreto-del-panel-meta
META_REDIRECT_URI=https://relay.aleyacloud.com/api/v1/oauth/meta/callback/
META_GRAPH_VERSION=version-estable-elegida-en-el-panel-meta
```

Usar una versión explícita de Graph API y revisarla periódicamente en Meta for
Developers; no dejar que Relay adopte una versión nueva de forma implícita.
Después de modificar los secretos, reiniciar `web`, `worker` y `beat` para que
reciban el entorno actualizado.

## Prueba controlada

1. Confirmar que B2 está configurado y que el bucket es privado.
2. Crear una marca de prueba y emitir una credencial de servicio de Relay con
   `connections:write`, `connections:read`, `media:write`, `posts:write`,
   `posts:approve`, `publications:write` y `publications:read`.
3. Llamar `POST /api/v1/oauth/meta/start/` con el `brand_id`; abrir la URL
   recibida y autorizar sólo los activos de prueba.
4. Comprobar `GET /api/v1/connections/?brand_id=...`. La respuesta contiene
   IDs, nombres, scopes y caducidad, nunca el token.
5. Crear una intención de carga, subir el archivo al `upload_url` con el
   encabezado `Content-Type` y, si Relay lo devuelve, `x-amz-meta-sha256`; luego
   confirmar el activo. Sólo un activo
   `READY` puede adjuntarse a un borrador de la marca.
6. Crear, aprobar y programar una publicación a unos minutos vista. Verificar
   el resultado y `PublicationAttempt` antes de probar otra cuenta.

No activar publicaciones de clientes reales hasta que una Page y una cuenta de
Instagram Professional de prueba hayan publicado correctamente y la revisión
de Meta esté concedida.
