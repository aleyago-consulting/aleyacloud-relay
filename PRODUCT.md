# Relay — producto y MVP

## Propósito

Relay es una plataforma de gestión de redes sociales para agencias y negocios
locales. Su promesa de producto es:

> Planifica, crea, aprueba y publica contenido; demuestra qué publicaciones
> generan clientes.

No es un CRM, un gestor de anuncios, un constructor de automatizaciones ni un
clon genérico de Buffer. La medición comercial debe ayudar a una agencia o marca
a explicar resultados, sin convertir Relay en el sistema de relación con el
cliente.

## Usuarios y espacios

Un Workspace representa una agencia o negocio. Dentro de él, una Brand
representa cada cliente o marca gestionada; una agencia puede administrar varias
marcas sin mezclar datos, activos ni aprobadores.

Roles iniciales:

| Rol | Capacidades MVP |
| --- | --- |
| Workspace owner | Gestiona el espacio, miembros, marcas, conexiones y facturación futura. |
| Agency manager | Gestiona marcas, calendario, conexiones y aprobaciones. |
| Content creator | Crea borradores y programa contenido autorizado. |
| Client approver | Accede sólo a las solicitudes de aprobación de su marca. |
| Viewer | Consulta calendario, resultados y auditoría de su marca. |

El rol de cliente no ve otras marcas ni requiere una cuenta completa para el
primer MVP: se le entrega un enlace firmado, con caducidad y revocación, para
una solicitud concreta.

## Recorrido MVP

1. La agencia crea una marca, sus guías de voz y un calendario editorial.
2. Un creador prepara un borrador, con una variante por canal y, cuando esté
   habilitado, ayuda de IA basada únicamente en la guía de esa marca.
3. El contenido se envía a aprobación de cliente o queda aprobado por el
   equipo autorizado.
4. Tras la aprobación, Relay publica de forma programada en Facebook Pages e
   Instagram Professional Accounts conectadas por OAuth.
5. Relay conserva el resultado de publicación, añade UTM cuando corresponda y
   presenta métricas de publicación y conversiones atribuidas disponibles.

El MVP admite texto y una imagen. Carruseles, vídeo, Reels, anuncios, inbox,
leads, Google Business, LinkedIn y TikTok no forman parte de esta primera
entrega.

## IA asistida, no automática

La IA es un asistente de redacción, no un actor con capacidad de publicar.
Recibe una guía de marca, objetivo, campaña y contexto que el usuario decide
enviar; genera propuestas editables y variantes por canal. Todo resultado
permanece en borrador hasta una aprobación humana. La elección del proveedor,
política de retención y límites de uso se resuelven antes de habilitarlo.

## Medición comercial del MVP, sin CRM

Relay crea enlaces con UTM consistentes por marca, canal y publicación. La
atribución inicial usa un contrato de eventos firmado para que la web o sistema
de captación del cliente reporte una visita o conversión agregada, con un
identificador externo opcional y sin datos personales por defecto. Relay
almacena la trazabilidad de campaña/publicación y totales; el CRM o formulario
de origen conserva el contacto y su consentimiento.

## Fase posterior: conversión comercial mínima

Una vez validado el MVP social, Relay podrá incorporar captura unificada de
leads, oportunidad mínima, conversación, cita y resultado para relacionar
publicación/campaña/UTM con venta. No será un CRM completo: no sustituirá la
ficha de cliente, contabilidad ni la automatización comercial generalista.

El modelo se diseña ahora para admitir origen, contacto mínimo, consentimiento,
estado, responsable, cita, resultado y eventos de seguimiento. La respuesta
con IA, mensajes sensibles, WhatsApp/email, recordatorios y recuperación de
no-shows exigen consentimiento y aprobación humana donde corresponda. Ninguna
de estas capacidades se implementa antes de que el MVP social sea usable.

## Límites de comunicación pública

La landing pública sólo puede presentar funcionalidades ya desplegadas o
describirlas expresamente como futuras. No integra SDK de Meta, cookies de
producto, tokens, rutas de API ni datos operativos. El panel futuro vive bajo
/app/ y la API bajo /api/v1/; ambos permanecen fuera de la web de marketing.
