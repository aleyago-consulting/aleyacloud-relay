#!/usr/bin/env bash
# Sincroniza las reglas HTTP/HTTPS de UFW con los rangos publicados por Cloudflare.
set -Eeuo pipefail

state_dir="/etc/aleyacloud-cloudflare"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

require_active_ufw() {
  ufw status | grep -q '^Status: active$' || {
    printf '%s\n' 'ERROR: UFW no esta activo; no se modifican reglas.' >&2
    exit 2
  }
}

fetch_ranges() {
  curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
    https://www.cloudflare.com/ips-v4 -o "$tmp_dir/ips-v4"
  curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
    https://www.cloudflare.com/ips-v6 -o "$tmp_dir/ips-v6"

  for family in v4 v6; do
    sed -i 's/\r$//' "$tmp_dir/ips-$family"
    if test ! -s "$tmp_dir/ips-$family" || grep -Evq '^[0-9A-Fa-f:.]+/[0-9]{1,3}$' "$tmp_dir/ips-$family"; then
      printf 'ERROR: la lista IPv%s de Cloudflare no tiene un formato esperado.\n' "$family" >&2
      exit 2
    fi
  done
}

remove_rules() {
  local file="$1"
  test -f "$file" || return 0
  while IFS= read -r cidr; do
    test -n "$cidr" || continue
    for port in 80 443; do
      ufw --force delete allow from "$cidr" to any port "$port" proto tcp >/dev/null 2>&1 || true
    done
  done < "$file"
}

add_rules() {
  local file="$1"
  while IFS= read -r cidr; do
    test -n "$cidr" || continue
    for port in 80 443; do
      ufw allow from "$cidr" to any port "$port" proto tcp comment 'Aleya Cloudflare' >/dev/null
    done
  done < "$file"
}

require_active_ufw
fetch_ranges
install -d -o root -g root -m 0700 "$state_dir"

# Solo eliminamos reglas correspondientes a los rangos que este script gestionó antes.
remove_rules "$state_dir/ips-v4"
remove_rules "$state_dir/ips-v6"
add_rules "$tmp_dir/ips-v4"
add_rules "$tmp_dir/ips-v6"
install -o root -g root -m 0600 "$tmp_dir/ips-v4" "$state_dir/ips-v4"
install -o root -g root -m 0600 "$tmp_dir/ips-v6" "$state_dir/ips-v6"
ufw --force reload >/dev/null

printf 'Rangos Cloudflare aplicados: IPv4=%s, IPv6=%s.\n' \
  "$(wc -l < "$state_dir/ips-v4")" "$(wc -l < "$state_dir/ips-v6")"
