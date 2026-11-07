#!/bin/bash
# One-shot server setup for a fresh Ubuntu 24.04 ARM VM on Oracle Cloud.
# Called by deploy/cloud-init.sh at first boot (as root), with DOMAIN set.
# Safe to re-run: secrets are generated only once and never printed.
set -euo pipefail
: "${DOMAIN:?DOMAIN must be set, e.g. DOMAIN=myapp.duckdns.org}"
APP_DIR=/opt/ai-resume-analyzer
cd "$APP_DIR"

echo "==> Packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io docker-compose-v2 git openssl iptables-persistent
systemctl enable --now docker
usermod -aG docker ubuntu || true

echo "==> Swap (2 GB, helps the torch install during the image build)"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> Host firewall: Oracle's Ubuntu images reject everything but SSH"
for port in 80 443; do
  iptables -C INPUT -p tcp --dport "$port" -m conntrack --ctstate NEW -j ACCEPT 2>/dev/null \
    || iptables -I INPUT 1 -p tcp --dport "$port" -m conntrack --ctstate NEW -j ACCEPT
done
netfilter-persistent save

echo "==> Secrets (generated on the server, never leave it)"
if [ ! -f deploy/.env ]; then
  umask 077
  cat > deploy/.env <<ENV
DOMAIN=$DOMAIN
DB_NAME=ai_resume_analyzer
DB_USER=postgres
DB_PASSWORD=$(openssl rand -hex 24)
JWT_SECRET_KEY=$(openssl rand -hex 32)
ENV
fi

echo "==> Build and start (first build takes 10-20 minutes on 2 ARM cores)"
docker compose -f deploy/docker-compose.oracle.yml --env-file deploy/.env up -d --build

echo "==> Daily backup at 03:30"
chmod +x deploy/backup.sh
echo "30 3 * * * root $APP_DIR/deploy/backup.sh >> /var/log/ai-resume-backup.log 2>&1" > /etc/cron.d/ai-resume-backup

echo "==> Done: https://$DOMAIN"
