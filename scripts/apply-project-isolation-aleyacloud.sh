#!/usr/bin/env bash
# Fase de aislamiento: no instala aplicaciones, no crea bases de datos y no
# modifica Nginx. Ejecutar como jorge con una TTY; sudo se solicita localmente.
set -Eeuo pipefail

readonly projects=(goclinicals aleyahomes clubtrainers aleyasuite)
readonly ports=(18081 18082 18083 18084)
readonly uids=(12001 12002 12003 12004)
readonly marker_name='.aleyacloud-isolation-v1'

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_file="/home/jorge/aleyacloud-project-isolation-${stamp}.log"

exec > >(tee -a "$log_file") 2>&1

section() { printf '\n== %s ==\n' "$1"; }
fail() { printf 'ERROR: %s\n' "$1" >&2; exit 2; }

project_user() { printf 'svc-%s' "$1"; }
project_marker() { printf 'version=1 project=%s\n' "$1"; }

require_managed_directory() {
  local path="$1" project="$2"
  if sudo test -e "$path" && ! sudo test -d "$path"; then
    fail "$path existe y no es un directorio."
  fi
  if sudo test -d "$path" && ! sudo test -f "/srv/apps/${project}/${marker_name}"; then
    fail "$path ya existe, pero no pertenece a esta fase de aislamiento; no se modifica."
  fi
}

check_network() {
  local project="$1" purpose="$2" internal="$3" name="aleya-${1}-${2}"
  if sudo docker network inspect "$name" >/dev/null 2>&1; then
    test "$(sudo docker network inspect -f '{{ index .Labels "com.aleyacloud.managed" }}' "$name")" = true || \
      fail "la red existente $name no esta marcada como gestionada por AleyaCloud."
    test "$(sudo docker network inspect -f '{{ index .Labels "com.aleyacloud.project" }}' "$name")" = "$project" || \
      fail "la red existente $name pertenece a otro proyecto."
    test "$(sudo docker network inspect -f '{{.Internal}}' "$name")" = "$internal" || \
      fail "la red existente $name no tiene el aislamiento esperado."
  fi
}

section "Autorizacion sudo local"
id -un | grep -qx jorge || fail 'este guion solo debe ejecutarse como jorge.'
sudo -v

section "Prerequisitos y capacidad"
for command in docker ss setfacl getent; do
  command -v "$command" >/dev/null || fail "falta el comando $command."
done
sudo systemctl is-active --quiet docker || fail 'Docker no esta activo.'
sudo systemctl is-active --quiet nginx || fail 'Nginx no esta activo.'
sudo docker compose version >/dev/null || fail 'Docker Compose v2 no esta disponible.'
sudo docker info --format '{{.DockerRootDir}}' | grep -qx /srv/docker || \
  fail 'Docker no usa /srv/docker como data-root.'
sudo docker network inspect aleya-internal --format '{{.Internal}}' | grep -qx true || \
  fail 'falta la red interna base aleya-internal o no es interna.'
for path in /srv/apps /srv/data; do
  sudo test -d "$path" || fail "falta el directorio base $path."
done
available_kib="$(df -Pk /srv | awk 'NR == 2 { print $4 }')"
test "$available_kib" -ge 8388608 || fail 'se requieren al menos 8 GiB libres en /srv.'
mem_total_kib="$(awk '/MemTotal:/ { print $2 }' /proc/meminfo)"
test "$mem_total_kib" -ge 1835008 || fail 'se requieren al menos 1.75 GiB de RAM.'

for index in "${!projects[@]}"; do
  project="${projects[$index]}"
  user="$(project_user "$project")"
  uid="${uids[$index]}"
  port="${ports[$index]}"

  require_managed_directory "/srv/apps/${project}" "$project"
  require_managed_directory "/srv/data/${project}" "$project"
  require_managed_directory "/srv/secrets/${project}" "$project"

  if getent passwd "$user" >/dev/null; then
    test "$(getent passwd "$user" | cut -d: -f3)" = "$uid" || \
      fail "$user ya existe con un UID diferente."
  elif getent passwd "$uid" >/dev/null; then
    fail "el UID reservado $uid ya esta en uso."
  fi
  ss -ltnH | awk '{print $4}' | grep -Eq "(^|:)${port}$" && \
    fail "el puerto local ${port} ya esta ocupado."
  check_network "$project" private true
  check_network "$project" egress false
done

section "Cuentas, directorios y permisos"
sudo install -d -o root -g root -m 0700 /srv/secrets

for index in "${!projects[@]}"; do
  project="${projects[$index]}"
  user="$(project_user "$project")"
  uid="${uids[$index]}"
  port="${ports[$index]}"

  if ! getent passwd "$user" >/dev/null; then
    sudo useradd --system --uid "$uid" --user-group --no-create-home \
      --shell /usr/sbin/nologin "$user"
  fi

  sudo install -d -o root -g root -m 0750 "/srv/apps/${project}"
  sudo install -d -o "$user" -g "$user" -m 0750 \
    "/srv/data/${project}" \
    "/srv/data/${project}/production" \
    "/srv/data/${project}/production/app" \
    "/srv/data/${project}/production/uploads" \
    "/srv/data/${project}/production/runtime"
  sudo install -d -o root -g root -m 0700 \
    "/srv/secrets/${project}" \
    "/srv/secrets/${project}/production"
  sudo setfacl -m "u:${user}:--x" /srv/data

  project_marker "$project" | sudo tee "/srv/apps/${project}/${marker_name}" >/dev/null
  sudo chmod 0640 "/srv/apps/${project}/${marker_name}"

  sudo tee "/srv/apps/${project}/compose.yaml" >/dev/null <<EOF
name: aleya-${project}

# Limite y endurecimiento que toda aplicacion futura de este proyecto debe heredar.
# Este archivo no define servicios: aplicar esta fase no inicia contenedores.
x-aleya-runtime: &aleya-runtime
  user: "${uid}:${uid}"
  init: true
  read_only: true
  tmpfs:
    - /tmp:rw,noexec,nosuid,size=32m
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  pids_limit: 64
  mem_limit: 192m
  mem_reservation: 96m
  cpus: "0.15"
  restart: unless-stopped

services: {}

networks:
  private:
    name: aleya-${project}-private
    external: true
  egress:
    name: aleya-${project}-egress
    external: true
EOF
  sudo tee "/srv/apps/${project}/deployment.env" >/dev/null <<EOF
# Configuracion no secreta. No anadir contrasenas, tokens ni claves a este archivo.
PROJECT_SLUG=${project}
APP_UID=${uid}
HOST_HTTP_PORT=${port}
CONTAINER_HTTP_PORT=8080
EOF
  sudo tee "/srv/secrets/${project}/production/README" >/dev/null <<EOF
Directorio reservado para secretos de produccion de ${project}.
Los secretos se crean como archivos individuales, propiedad de root y modo 0400,
y se montan en /run/secrets/<nombre>. No usar variables de entorno para secretos.
EOF
  sudo chmod 0640 "/srv/apps/${project}/compose.yaml" "/srv/apps/${project}/deployment.env"
  sudo chmod 0400 "/srv/secrets/${project}/production/README"
done

section "Redes Docker aisladas"
for project in "${projects[@]}"; do
  if ! sudo docker network inspect "aleya-${project}-private" >/dev/null 2>&1; then
    sudo docker network create --driver bridge --internal \
      --label com.aleyacloud.managed=true \
      --label com.aleyacloud.project="$project" \
      --label com.aleyacloud.purpose=private \
      "aleya-${project}-private" >/dev/null
  fi
  if ! sudo docker network inspect "aleya-${project}-egress" >/dev/null 2>&1; then
    sudo docker network create --driver bridge \
      --opt com.docker.network.bridge.enable_icc=false \
      --label com.aleyacloud.managed=true \
      --label com.aleyacloud.project="$project" \
      --label com.aleyacloud.purpose=egress \
      "aleya-${project}-egress" >/dev/null
  fi
done

section "Validacion final"
for index in "${!projects[@]}"; do
  project="${projects[$index]}"
  user="$(project_user "$project")"
  uid="${uids[$index]}"
  port="${ports[$index]}"
  test "$(getent passwd "$user" | cut -d: -f3)" = "$uid"
  sudo test -d "/srv/data/${project}/production/uploads"
  test "$(sudo stat -c '%U:%G' "/srv/data/${project}")" = "${user}:${user}"
  test "$(sudo stat -c '%a' "/srv/secrets/${project}/production")" = 700
  sudo docker network inspect "aleya-${project}-private" --format '{{.Internal}}' | grep -qx true
  sudo docker network inspect "aleya-${project}-egress" --format '{{.Internal}}' | grep -qx false
  sudo docker ps --format '{{.Names}}' | grep -Eq "^aleya-${project}" && \
    fail "se ha detectado un contenedor de aplicacion no esperado para ${project}."
  printf '%s: uid=%s puerto=127.0.0.1:%s redes=privada+egress\n' "$project" "$uid" "$port"
done
sudo find /srv/apps /srv/data /srv/secrets -maxdepth 2 -type d -printf '%M %u:%g %p\n' | sort
printf '%s\n' 'Aislamiento preparado. No se han iniciado contenedores, desplegado aplicaciones, creado bases de datos ni modificado Nginx.'
printf 'Registro: %s\n' "$log_file"
