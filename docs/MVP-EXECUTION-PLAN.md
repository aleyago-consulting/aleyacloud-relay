# Relay — plan de ejecución del MVP

Este plan sustituye el roadmap centrado sólo en publicación. Cada fase termina
con pruebas, observabilidad y una revisión de seguridad; ninguna se anuncia en
la landing como disponible antes de desplegarse.

## Fase A — Producto, identidad y aislamiento

- Añadir Workspace, Brand, Membership y roles de agencia/cliente.
- Elegir autenticación del panel y MFA antes de exponer /app/.
- Aplicar autorización por workspace y marca a cada consulta, comando y media.
- Migrar la base técnica actual de Tenant/Post hacia este modelo sin compartir
  datos ni código con otros productos Alya Cloud.

**Salida:** una agencia puede operar varias marcas aisladas con auditoría.

## Fase B — Conexión Meta segura

- Registrar la Meta App y definir sus responsables, activos y permisos mínimos.
- Implementar OAuth con state de un solo uso, selección explícita de Pages e
  Instagram Professional Accounts y cifrado de tokens.
- Implementar renovación, desconexión, errores de credencial y auditoría.
- Validar límites y requisitos vigentes de Graph API antes de solicitar revisión
  o activar producción.

**Salida:** una marca puede conectar exclusivamente sus activos Meta autorizados.

## Fase C — Calendario, contenidos y voz de marca

- Calendario por marca, campañas, borradores y variantes de canal.
- Guía de voz/brief de marca versionada.
- Primer asistente de IA con trazabilidad de entrada/salida, límites y revisión
  humana obligatoria.
- Media de una imagen con almacenamiento privado y validación.

**Salida:** el equipo puede preparar contenido coherente y revisable.

## Fase D — Aprobación y publicación fiable

- Solicitudes de aprobación por enlace firmado, caducable y revocable.
- Aprobar, pedir cambios y comentar; conservar el historial.
- Programación UTC, bloqueo de concurrencia, idempotencia, intentos, reintentos
  limitados y alertas de fallo.
- Publicación inicial en Facebook Pages e Instagram Professional Accounts.

**Salida:** una marca puede aprobar y publicar contenido programado con evidencia
operativa de su resultado.

**Implementado parcialmente:** el trabajador reclama una publicación debida,
crea un intento, registra resultado/error/reintento y contiene el adaptador de
Meta para una imagen. Falta configurar la entrega privada de media, las
credenciales Meta y el proceso Celery de despliegue antes de activarlo.

## Fase E — Panel de contenido, UTM y métricas

- Plantillas UTM por marca/campaña y enlaces de publicación trazables.
- Panel de contenido con publicaciones, alcance, interacción, clics UTM,
  fallos y métricas normalizadas por proveedor.
- Contrato de evento firmado para visitas/conversiones agregadas procedentes de
  la web o sistema de captación del cliente.
- Panel de resultado por publicación/campaña, sin fichas de contacto ni CRM.

**Salida:** la agencia puede relacionar publicaciones con actividad comercial
medible cuando el cliente integra el contrato de eventos.

## Fase F — Endurecimiento y lanzamiento controlado

- Pruebas de aislamiento, permisos, revocación de enlaces, errores Meta y
  publicación duplicada.
- Retención, consentimiento, exportación/borrado y revisión de privacidad.
- Copias de seguridad, alertas, límites de coste y runbooks.
- Piloto con una agencia y pocas marcas antes de apertura general.

## Fase 2 posterior — Conversión comercial mínima

Esta fase no se implementa ni bloquea el MVP social. Se prepara ahora mediante
entidades, permisos y eventos compatibles:

- Captura de leads desde formularios, Meta Lead Ads, Instagram, email y Google
  Business, con origen y consentimiento explícitos.
- Oportunidad mínima: contacto, conversación, estado, responsable, cita y
  resultado; no un CRM completo.
- Respuesta/cualificación asistida por IA con revisión humana para mensajes
  sensibles.
- Reserva, recordatorios, recuperación de no-shows y seguimiento por email o
  WhatsApp sólo con consentimiento comprobable.
- Atribución completa publicación/campaña/UTM a visita, lead, cita y venta.
- Alertas de leads no atendidos y fallos de automatización.
- Un vertical inicial decidido antes de construir plantillas; candidatos:
  inmobiliaria, fitness/bienestar o uno único aprobado por Dirección.

## Después de Fase 2

1. Google Business.
2. LinkedIn.
3. TikTok.
4. Carruseles, vídeo y Reels.
5. Flujos de aprobación de equipo más avanzados y analítica ampliada.

No se inicia un proveedor nuevo hasta que el flujo Meta sea estable y medible.
