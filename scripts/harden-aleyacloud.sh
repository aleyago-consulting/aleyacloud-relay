#!/usr/bin/env bash
# Ejecutar únicamente como jorge a través de una sesión SSH con TTY.
set -Eeuo pipefail

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="/root/aleyacloud-hardening-backups/${stamp}"
verify_marker="/home/jorge/.ufw-verified-${stamp}"
log_file="/home/jorge/aleyacloud-hardening-${stamp}.log"

exec > >(tee -a "$log_file") 2>&1

section() { printf '\n== %s ==\n' "$1"; }

section "Autorización sudo local"
sudo -v

section "Línea base privilegiada y copia de recuperación"
sudo install -d -m 0700 "$backup_dir"
sudo cp -a /etc/ufw "$backup_dir/ufw"
sudo cp -a /etc/ssh "$backup_dir/ssh"
sudo ufw status verbose || true
sudo /usr/sbin/sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|port) '

section "Actualizaciones esenciales"
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

section "Actualizaciones automáticas de seguridad"
if ! apt-cache show unattended-upgrades >/dev/null 2>&1; then
  printf '%s\n' 'ERROR: unattended-upgrades no está disponible tras apt-get update; UFW no se ha modificado.' >&2
  exit 2
fi
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y unattended-upgrades
sudo tee /etc/apt/apt.conf.d/20auto-upgrades >/dev/null <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
sudo tee /etc/apt/apt.conf.d/52aleya-security-updates >/dev/null <<'EOF'
// Mantener el reinicio bajo control administrativo.
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Dependencies "false";
EOF
sudo systemctl enable --now apt-daily.timer apt-daily-upgrade.timer
sudo unattended-upgrade --dry-run --debug

section "Ruta de recuperación del firewall"
rollback_cmd="test -f '$verify_marker' || /usr/sbin/ufw --force disable"
printf '%s\n' "$rollback_cmd" | sudo at now + 5 minutes
printf '%s\n' "Marcador de verificación: $verify_marker"

section "Firewall mínimo y limitación SSH"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw limit 22/tcp comment 'SSH rate limited'
sudo ufw --force enable
sudo ufw status numbered

section "Validación posterior"
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|port) '
printf '%s\n' "Configuración aplicada. Espera la prueba de una segunda conexión SSH antes de cerrar esta ventana."
printf '%s\n' "Registro: $log_file"
