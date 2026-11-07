#!/bin/bash
# Daily Postgres dump, kept for 14 days. Installed as a cron job by setup.sh.
set -euo pipefail
APP_DIR=/opt/ai-resume-analyzer
BACKUP_DIR=/opt/backups
mkdir -p "$BACKUP_DIR"
cd "$APP_DIR"
set -a; . deploy/.env; set +a
docker compose -f deploy/docker-compose.oracle.yml --env-file deploy/.env \
  exec -T postgres pg_dump -U "${DB_USER:-postgres}" "${DB_NAME:-ai_resume_analyzer}" \
  | gzip > "$BACKUP_DIR/db-$(date +%F).sql.gz"
find "$BACKUP_DIR" -name 'db-*.sql.gz' -mtime +14 -delete
