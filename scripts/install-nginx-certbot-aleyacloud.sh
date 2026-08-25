#!/usr/bin/env bash
# Ejecutar únicamente como jorge mediante SSH con TTY. Solicita sudo localmente.
# Instala Nginx y Certbot en el host. Las aplicaciones futuras permanecen en Docker.
set -Eeuo pipefail

acme_email="${1:-}"
if [[ ! "$acme_email" =~ ^[^[:space:]@]+@[^[:space:]@]+$ ]]; then
  printf '%s\n' 'Uso: install-nginx-certbot-aleyacloud.sh correo@ejemplo.com' >&2
  exit 2
fi

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_file="/home/jorge/aleyacloud-nginx-certbot-${stamp}.log"
backup_dir="/root/aleyacloud-nginx-certbot-backups/${stamp}"
verify_marker="/home/jorge/.nginx-certbot-verified-${stamp}"
rollback_script="${backup_dir}/rollback-firewall.sh"

exec > >(tee -a "$log_file") 2>&1

section() { printf '\n== %s ==\n' "$1"; }

section "Autorizacion sudo local"
sudo -v

section "Comprobaciones previas"
for path in /srv/apps/nginx /srv/apps/nginx/sites /srv/data/certbot/conf /srv/data/certbot/webroot; do
  sudo test -d "$path" || {
    printf 'ERROR: falta %s; ejecuta primero la preparacion de estructura.\n' "$path" >&2
    exit 2
  }
done
sudo systemctl is-active --quiet docker
sudo docker network inspect aleya-internal --format '{{.Internal}}' | grep -qx true
sudo ufw status | grep -qx 'Status: active'
command -v at >/dev/null || {
  printf '%s\n' 'ERROR: falta el planificador at; no se modifican servicios ni firewall.' >&2
  exit 2
}
if command -v nginx >/dev/null; then
  printf '%s\n' 'ERROR: Nginx ya existe; este guion no migra una instalacion previa.' >&2
  exit 2
fi
for path in /srv/apps/nginx/sites/aleyacloud.conf /etc/nginx/sites-enabled/aleyacloud.conf; do
  if sudo test -e "$path"; then
    printf 'ERROR: ya existe %s; no se sobrescribe.\n' "$path" >&2
    exit 2
  fi
done

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
printf 'Marcador de verificacion: %s\n' "$verify_marker"

section "Instalacion de Nginx ligero y Certbot"
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nginx-light certbot curl acl

section "Sincronizador de rangos Cloudflare"
sudo install -o root -g root -m 0700 \
  /home/jorge/update-cloudflare-ufw-aleyacloud.sh \
  /usr/local/sbin/aleyacloud-cloudflare-ufw
sudo tee /etc/systemd/system/aleyacloud-cloudflare-ufw.service >/dev/null <<'EOF'
[Unit]
Description=Sincronizar UFW HTTP/HTTPS con las redes de Cloudflare
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/aleyacloud-cloudflare-ufw
EOF
sudo tee /etc/systemd/system/aleyacloud-cloudflare-ufw.timer >/dev/null <<'EOF'
[Unit]
Description=Actualizar diariamente las redes Cloudflare de UFW

[Timer]
OnCalendar=*-*-* 03:23:00
RandomizedDelaySec=45m
Persistent=true

[Install]
WantedBy=timers.target
EOF

section "Configuracion inicial HTTP para ACME"
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

    location / {
        return 404;
    }
}
EOF
sudo chmod 0640 /srv/apps/nginx/sites/aleyacloud.conf
# Los trabajadores no privilegiados de Nginx solo pueden atravesar hasta el webroot ACME.
sudo setfacl -m u:www-data:--x /srv /srv/data /srv/data/certbot
sudo setfacl -m u:www-data:rx /srv/data/certbot/webroot
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /srv/apps/nginx/sites/aleyacloud.conf /etc/nginx/sites-enabled/aleyacloud.conf
sudo nginx -t
sudo systemctl enable --now nginx

section "Firewall HTTP/HTTPS solo desde Cloudflare"
sudo /usr/local/sbin/aleyacloud-cloudflare-ufw
sudo systemctl daemon-reload
sudo systemctl enable --now aleyacloud-cloudflare-ufw.timer

section "Emision de certificados exactos"
certbot_base=(sudo certbot certonly --webroot -w /srv/data/certbot/webroot \
  --config-dir /srv/data/certbot/conf --work-dir /srv/data/certbot/work --logs-dir /srv/data/certbot/logs \
  --non-interactive --agree-tos --no-eff-email --email "$acme_email")
"${certbot_base[@]}" --cert-name goclinicals.com \
  -d goclinicals.com -d www.goclinicals.com -d app.goclinicals.com
"${certbot_base[@]}" --cert-name aleyasuite.com \
  -d aleyasuite.com -d www.aleyasuite.com -d app.aleyasuite.com
"${certbot_base[@]}" --cert-name aleyahomes.com \
  -d aleyahomes.com -d www.aleyahomes.com -d app.aleyahomes.com
"${certbot_base[@]}" --cert-name clubtrainers.com \
  -d clubtrainers.com -d www.clubtrainers.com -d app.clubtrainers.com

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
sudo ufw status numbered
sudo touch "$verify_marker"
printf '%s\n' 'Nginx y Certbot configurados. No se ha desplegado ninguna aplicacion real; los dominios devuelven 503 hasta definir sus backends.'
printf 'Registro: %s\n' "$log_file"
printf 'Copia de recuperacion UFW: %s\n' "$backup_dir"
