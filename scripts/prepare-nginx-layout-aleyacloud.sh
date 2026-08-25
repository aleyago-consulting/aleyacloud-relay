#!/usr/bin/env bash
# Ejecutar únicamente como jorge mediante SSH con TTY. Solicita sudo localmente.
# Esta fase solo prepara directorios; no instala ni ejecuta servicios.
set -Eeuo pipefail

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_file="/home/jorge/aleyacloud-nginx-layout-${stamp}.log"

exec > >(tee -a "$log_file") 2>&1

section() { printf '\n== %s ==\n' "$1"; }

section "Autorizacion sudo local"
sudo -v

section "Comprobaciones previas"
for path in /srv/apps /srv/data; do
  if ! sudo test -d "$path"; then
    printf 'ERROR: falta el directorio base %s; ejecuta primero la fase Docker.\n' "$path" >&2
    exit 2
  fi
done

for path in /srv/apps/nginx /srv/data/certbot; do
  if sudo test -e "$path" && ! sudo test -d "$path"; then
    printf 'ERROR: %s existe y no es un directorio; no se modifica.\n' "$path" >&2
    exit 2
  fi
done

section "Estructura de configuracion de Nginx"
sudo install -d -o root -g root -m 0750 \
  /srv/apps/nginx \
  /srv/apps/nginx/sites

section "Almacenamiento persistente de Certbot"
sudo install -d -o root -g root -m 0700 \
  /srv/data/certbot \
  /srv/data/certbot/conf
sudo install -d -o root -g root -m 0750 \
  /srv/data/certbot/webroot

section "Validacion"
sudo find /srv/apps/nginx /srv/data/certbot -maxdepth 1 -printf '%M %u:%g %p\n' | sort
printf '%s\n' 'Estructura preparada. No se han instalado paquetes, creado contenedores, modificado UFW ni emitido certificados.'
printf 'Registro: %s\n' "$log_file"
