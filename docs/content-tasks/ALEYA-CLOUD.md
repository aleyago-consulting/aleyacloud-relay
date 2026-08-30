# Tarea de contenido — AleyaCloud

## Objetivo

Subir el material recibido como un borrador de contenido en Relay para la marca
**AleyaCloud**. El borrador debe quedar listo para revisión humana.

## Límites de autoridad

Esta tarea puede:

- subir una imagen JPG o PNG de hasta 10 MiB;
- crear un post en estado `DRAFT`;
- informar el identificador y el resultado del borrador.

Esta tarea no puede ni debe:

- aprobar, programar, publicar o cancelar contenido;
- modificar conexiones sociales o credenciales;
- acceder a contenido de otras marcas;
- solicitar, mostrar o guardar credenciales de Relay.

## Material de entrada

Se debe recibir antes de actuar:

- texto final del post;
- título opcional;
- imagen JPG o PNG adjunta;
- correcciones explícitas si el contenido sustituye a un borrador previo.

Si falta texto o imagen, pedirlo. No inventar datos comerciales, enlaces,
promociones, precios, fechas ni afirmaciones verificables.

## Ejecución en Relay

Usar únicamente el cliente local autorizado con el perfil `aleyacloud`. No
pedir, mostrar ni extraer tokens. El cliente cifra el perfil localmente y
realiza la subida de imagen y creación del borrador.

Ejecutar `tools/relay-task-vault.ps1` con `-Action Submit -Profile aleyacloud`,
el archivo de imagen y el texto recibido (preferiblemente mediante `-BodyFile`
para conservar saltos de línea).

No llamar a ningún endpoint de aprobación, publicación o programación.

## Resultado esperado

Crear el contenido para la marca `aleyacloud` dentro del Workspace editorial
autorizado. Confirmar al finalizar:

- que el estado es `DRAFT`;
- el título o extracto que identifica el borrador;
- si la imagen quedó asociada correctamente.

No anunciar que algo se ha publicado: un borrador de Relay no es una
publicación en redes sociales.
