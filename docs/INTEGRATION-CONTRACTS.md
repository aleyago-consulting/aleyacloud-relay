# Relay — contratos de integración

## Contrato de la landing

- La landing es una web estática independiente.
- No llama a la API de Relay ni incorpora SDKs de redes sociales.
- Puede enlazar de forma controlada a /app/ cuando el panel esté desplegado.
- El blog futuro sólo publica información de producto verificada y enlaces
  públicos; nunca documentación de operaciones, secretos o rutas administrativas.

## Contrato de productos clientes

TavisaSuite, goClinicals, ClubTrainers y futuros productos son clientes de una
API versionada. No importan código Relay, no comparten su base de datos y no
pueden seleccionar arbitrariamente un workspace o marca. Las credenciales de
servicio llevan los scopes y el contexto autorizado.

Una solicitud de aprobación se crea desde la API autenticada para un borrador
autorizado. Relay devuelve el enlace en texto plano sólo en esa respuesta y
guarda únicamente su digest; el cliente lo entrega al aprobador por su canal
habitual. El enlace permite consultar ese contenido y decidir aprobar o pedir
cambios, sin conceder acceso al Workspace, a otras marcas ni a la API general.

## Contrato de atribución

Un sistema de captación externo puede reportar un evento agregado a Relay con:

- workspace y brand autorizados por su credencial;
- publicación/campaña o parámetros UTM de Relay;
- tipo de evento: visita, formulario iniciado, lead o venta;
- fecha, valor opcional y referencia externa opcional.

El contrato no transmite nombre, correo, teléfono, contenido de formularios ni
otra información personal por defecto. La captura de datos personales requiere
una evaluación específica de consentimiento, retención y relación contractual.

## Contrato futuro de conversión

Sin activarlo en el MVP social, la API reserva eventos de captación y conversión
con origen, Brand, campaña/publicación/UTM, estado, referencia externa y marca
temporal. Cuando incluya contacto, conversación, cita o seguimiento, exigirá
consentimiento, finalidad, retención y permisos por Brand. Los canales de email
o WhatsApp nunca se activan sólo por recibir un lead; requieren consentimiento
verificable y reglas de aprobación humana para mensajes sensibles.
