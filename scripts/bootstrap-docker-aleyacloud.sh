#!/usr/bin/env bash
# Ejecutar únicamente como jorge mediante SSH con TTY. Solicita sudo localmente.
set -Eeuo pipefail

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_file="/home/jorge/aleyacloud-runtime-${stamp}.log"
backup_dir="/root/aleyacloud-runtime-backups/${stamp}"

exec > >(tee -a "$log_file") 2>&1

section() { printf '\n== %s ==\n' "$1"; }

section "Autorizacion sudo local"
sudo -v

section "Comprobaciones previas"
sudo /usr/sbin/sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|port) '
sudo ufw status verbose
if command -v docker >/dev/null 2>&1; then
  printf '%s\n' 'ERROR: Docker ya esta instalado; este guion no migra instalaciones existentes.' >&2
  exit 2
fi

section "Copia de configuraciones existentes"
sudo install -d -m 0700 "$backup_dir"
sudo cp -a /etc/systemd/journald.conf "$backup_dir/journald.conf"
if sudo test -d /etc/docker; then
  sudo cp -a /etc/docker "$backup_dir/docker"
fi

section "Instalacion de Docker Engine y Compose v2"
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends docker.io docker-compose-v2

section "Estructura y permisos"
sudo install -d -o root -g root -m 0750 /srv/apps /srv/data
sudo install -d -o root -g root -m 0711 /srv/docker
# No se anade jorge al grupo docker: dicho grupo equivale practicamente a root.

section "Configuracion del daemon Docker"
sudo install -d -o root -g root -m 0755 /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "data-root": "/srv/docker",
  "storage-driver": "overlay2",
  "live-restore": true,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
sudo chmod 0644 /etc/docker/daemon.json
sudo systemctl enable containerd docker
# El paquete puede iniciar Docker antes de crear daemon.json; reiniciar carga esta configuracion.
sudo systemctl restart docker

section "Red interna base"
if ! sudo docker network inspect aleya-internal >/dev/null 2>&1; then
  sudo docker network create --driver bridge --internal aleya-internal
fi

section "Limites de registros del sistema"
sudo install -d -o root -g root -m 0755 /etc/systemd/journald.conf.d
sudo tee /etc/systemd/journald.conf.d/60-aleyacloud-limits.conf >/dev/null <<'EOF'
[Journal]
SystemMaxUse=100M
RuntimeMaxUse=50M
EOF
sudo systemctl restart systemd-journald

section "Limpieza semanal de imagenes no usadas"
sudo tee /etc/systemd/system/aleya-docker-prune.service >/dev/null <<'EOF'
[Unit]
Description=Eliminar imagenes y cache Docker sin usar durante 14 dias
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/docker image prune -af --filter=until=336h
ExecStart=/usr/bin/docker builder prune -af --filter=until=336h
EOF
sudo tee /etc/systemd/system/aleya-docker-prune.timer >/dev/null <<'EOF'
[Unit]
Description=Programar limpieza semanal y conservadora de Docker

[Timer]
OnCalendar=Sun *-*-* 04:30:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now aleya-docker-prune.timer

section "Validacion"
sudo docker info --format 'Docker {{.ServerVersion}} | driver={{.Driver}} | root={{.DockerRootDir}}'
sudo docker compose version
sudo docker network inspect aleya-internal --format '{{.Name}} internal={{.Internal}}'
sudo docker run --rm hello-world
sudo docker image rm hello-world >/dev/null
sudo systemctl is-active docker containerd
sudo systemctl is-enabled docker aleya-docker-prune.timer
sudo find /srv -maxdepth 1 -printf '%M %u:%g %p\n' | sort
sudo journalctl --disk-usage
df -h /srv

printf '\nConfiguracion aplicada. No cierres esta ventana hasta recibir la validacion final.\n'
printf 'Registro: %s\n' "$log_file"
printf 'Copia de recuperacion: %s\n' "$backup_dir"
