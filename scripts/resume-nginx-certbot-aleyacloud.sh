#!/usr/bin/env bash
# Reanuda una instalacion que ya tiene Nginx, Certbot y la configuracion HTTP ACME preparados.
set -Eeuo pipefail
trap 'status=$?; printf "ERROR: fallo en la linea %s (codigo %s).\n" "$LINENO" "$status" >&2' ERR

acme_email="${1:-}"
if [[ ! "$acme_email" =~ ^[^[:space:]@]+@[^[:space:]@]+$ ]]; then
  printf '%s\n' 'Uso: resume-nginx-certbot-aleyacloud.sh correo@ejemplo.com' >&2
  exit 2
fi

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_file="/home/jorge/aleyacloud-nginx-certbot-resume-${stamp}.log"
backup_dir="/root/aleyacloud-nginx-certbot-resume-backups/${stamp}"
verify_marker="/home/jorge/.nginx-certbot-resume-verified-${stamp}"
rollback_script="${backup_dir}/rollback-firewall.sh"

exec > >(tee -a "$log_file") 2>&1
section() { printf '\n== %s ==\n' "$1"; }

section "Autorizacion sudo local"
sudo -v

section "Comprobaciones previas"
for command in nginx certbot at curl; do command -v "$command" >/dev/null || { printf 'ERROR: falta %s.\n' "$command" >&2; exit 2; }; done
for path in /srv/apps/nginx/sites/aleyacloud.conf /srv/data/certbot/webroot /usr/local/sbin/aleyacloud-cloudflare-ufw; do
  sudo test -e "$path" || { printf 'ERROR: falta %s.\n' "$path" >&2; exit 2; }
done
nginx_site_target="$(sudo readlink -f /etc/nginx/sites-enabled/aleyacloud.conf)"
sudo test "$nginx_site_target" = /srv/apps/nginx/sites/aleyacloud.conf
sudo grep -Fq 'well-known/acme-challenge' /srv/apps/nginx/sites/aleyacloud.conf || {
  printf '%s\n' 'ERROR: la configuracion Nginx no es la fase ACME esperada; no se sobrescribe.' >&2
  exit 2
}
getent ahostsv4 production-server.aleyacloud.com | awk '{print $1}' | grep -qx '200.234.228.246' || {
  printf '%s\n' 'ERROR: production-server.aleyacloud.com no resuelve a la IP esperada.' >&2
  exit 2
}
sudo ufw status | grep -qx 'Status: active'

section "Copia de recuperacion y retorno automatico del firewall"
sudo install -d -m 0700 "$backup_dir"
sudo cp -a /etc/ufw "$backup_dir/ufw"
sudo tee "$rollback_script" >/dev/null <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
if test ! -f '$verify_marker'; then
  cp -a '$backup_dir/ufw/.' /etc/ufw/
  ufw --force reload || true
  systemctl stop nginx || true
fi
EOF
sudo chmod 0700 "$rollback_script"
printf 'test -f %q || bash %q\n' "$verify_marker" "$rollback_script" | sudo at now + 15 minutes

section "Nginx HTTP y acceso Cloudflare"
sudo nginx -t
sudo systemctl start nginx
sudo /usr/local/sbin/aleyacloud-cloudflare-ufw

certbot_base=(sudo certbot certonly --webroot -w /srv/data/certbot/webroot \
  --config-dir /srv/data/certbot/conf --work-dir /srv/data/certbot/work --logs-dir /srv/data/certbot/logs \
  --non-interactive --agree-tos --no-eff-email --email "$acme_email")

request_certificates() {
  "${certbot_base[@]}" "$@" --cert-name goclinicals.com -d goclinicals.com -d www.goclinicals.com -d app.goclinicals.com
  "${certbot_base[@]}" "$@" --cert-name aleyasuite.com -d aleyasuite.com -d www.aleyasuite.com -d app.aleyasuite.com
  "${certbot_base[@]}" "$@" --cert-name aleyahomes.com -d aleyahomes.com -d www.aleyahomes.com -d app.aleyahomes.com
  "${certbot_base[@]}" "$@" --cert-name clubtrainers.com -d clubtrainers.com -d www.clubtrainers.com -d app.clubtrainers.com
}

section "Validacion ACME en entorno de pruebas"
request_certificates --dry-run

section "Emision de certificados reales"
request_certificates

section "Configuracion HTTPS final"
sudo tee /srv/apps/nginx/sites/aleyacloud.conf >/dev/null <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    location ^~ /.well-known/acme-challenge/ {
        root /srv/data/certbot/webroot;
        default_type text/plain;
        try_files $uri =404;
    }
    location / { return 444; }
}

server {
    listen 80;
    listen [::]:80;
    server_name goclinicals.com www.goclinicals.com app.goclinicals.com
                aleyasuite.com www.aleyasuite.com app.aleyasuite.com
                aleyahomes.com www.aleyahomes.com app.aleyahomes.com
                clubtrainers.com www.clubtrainers.com app.clubtrainers.com;
    location ^~ /.well-known/acme-challenge/ {
        root /srv/data/certbot/webroot;
        default_type text/plain;
        try_files $uri =404;
    }
    location / { return 308 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name goclinicals.com www.goclinicals.com app.goclinicals.com;
    ssl_certificate /srv/data/certbot/conf/live/goclinicals.com/fullchain.pem;
    ssl_certificate_key /srv/data/certbot/conf/live/goclinicals.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    server_tokens off;
    location / { return 503; }
}
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name aleyasuite.com www.aleyasuite.com app.aleyasuite.com;
    ssl_certificate /srv/data/certbot/conf/live/aleyasuite.com/fullchain.pem;
    ssl_certificate_key /srv/data/certbot/conf/live/aleyasuite.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    server_tokens off;
    location / { return 503; }
}
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name aleyahomes.com www.aleyahomes.com app.aleyahomes.com;
    ssl_certificate /srv/data/certbot/conf/live/aleyahomes.com/fullchain.pem;
    ssl_certificate_key /srv/data/certbot/conf/live/aleyahomes.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    server_tokens off;
    location / { return 503; }
}
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name clubtrainers.com www.clubtrainers.com app.clubtrainers.com;
    ssl_certificate /srv/data/certbot/conf/live/clubtrainers.com/fullchain.pem;
    ssl_certificate_key /srv/data/certbot/conf/live/clubtrainers.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    server_tokens off;
    location / { return 503; }
}
EOF
sudo chmod 0640 /srv/apps/nginx/sites/aleyacloud.conf
sudo nginx -t
sudo systemctl reload nginx

section "Renovacion automatica"
sudo tee /etc/systemd/system/aleyacloud-certbot-renew.service >/dev/null <<'EOF'
[Unit]
Description=Renovar certificados Let's Encrypt de AleyaCloud
After=network-online.target nginx.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet --config-dir /srv/data/certbot/conf --work-dir /srv/data/certbot/work --logs-dir /srv/data/certbot/logs
ExecStartPost=/usr/bin/systemctl reload nginx
EOF
sudo tee /etc/systemd/system/aleyacloud-certbot-renew.timer >/dev/null <<'EOF'
[Unit]
Description=Comprobar dos veces al dia la renovacion de certificados AleyaCloud

[Timer]
OnCalendar=*-*-* 04,16:27:00
RandomizedDelaySec=45m
Persistent=true

[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now aleyacloud-certbot-renew.timer

section "Validacion"
sudo systemctl is-active nginx
sudo systemctl is-enabled nginx aleyacloud-cloudflare-ufw.timer aleyacloud-certbot-renew.timer
sudo certbot certificates --config-dir /srv/data/certbot/conf --work-dir /srv/data/certbot/work --logs-dir /srv/data/certbot/logs
sudo touch "$verify_marker"
printf '%s\n' 'Certificados emitidos. No hay aplicaciones reales: Nginx devolvera 503 hasta configurar backends internos.'
printf 'Registro: %s\n' "$log_file"
