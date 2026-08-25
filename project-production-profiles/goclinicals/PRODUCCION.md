# Ficha de producción — goClinicals

## Identidad y publicación

| Campo | Valor |
| --- | --- |
| Identificador de infraestructura | `goclinicals` |
| Dominio principal | Pendiente |
| Dominios y subdominios adicionales | Pendiente |
| DNS y proxy Cloudflare | Pendiente |
| Puerto local asignado | `127.0.0.1:18081` |
| Responsable de producción | Pendiente |

## Código y entrega

| Campo | Valor |
| --- | --- |
| Repositorio u origen | Pendiente |
| Rama, tag o commit de producción | Pendiente |
| Método de entrega | Pendiente: pull en VPS / CI por SSH / imagen de registry |
| Archivo de orquestación | Pendiente |
| Comando de construcción | Pendiente |
| Imagen y versión inmutable | Pendiente |
| Endpoint de salud | Pendiente |

## Ejecución y dependencias

| Campo | Valor |
| --- | --- |
| Puerto HTTP dentro del contenedor | Pendiente |
| Base de datos | Pendiente |
| Redis, colas u otros servicios | Pendiente |
| Correo transaccional | Pendiente |
| Almacenamiento de archivos | Pendiente |
| Directorios persistentes necesarios | Pendiente |
| RAM, CPU y espacio estimados | Pendiente |

## Configuración sensible

Variables no sensibles: Pendiente.

Secretos requeridos —solo nombre y finalidad, sin valores—: Pendiente.

Ruta de carga prevista: `/srv/secrets/goclinicals/production/`.

## Validación y reversión

| Campo | Valor |
| --- | --- |
| Comprobación previa | `docker compose config --quiet` + Pendiente |
| Comprobación posterior | Pendiente |
| Ventana de observación | Pendiente |
| Versión anterior que se conserva | Pendiente |
| Criterio y procedimiento de rollback | Pendiente |
