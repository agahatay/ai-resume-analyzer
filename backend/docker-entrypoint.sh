#!/bin/sh
# Phase 12: run pending Alembic migrations before serving requests, then
# hand off to the container's real command (uvicorn). Never uses
# Base.metadata.create_all() - the existing Alembic migration history is
# the only schema source of truth, in Docker exactly as outside it.
#
# docker-compose's postgres healthcheck (pg_isready) plus
# depends_on: condition: service_healthy already keep this container from
# starting before Postgres accepts connections, but a short retry loop is
# kept here too as defense in depth against the brief window where
# pg_isready succeeds while Postgres is still finishing startup.
set -e

max_attempts=10
attempt=1

until alembic upgrade head; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Alembic migrations failed after $max_attempts attempts" >&2
    exit 1
  fi
  echo "Alembic upgrade failed (attempt $attempt/$max_attempts) - retrying in 3s..." >&2
  attempt=$((attempt + 1))
  sleep 3
done

echo "Migrations applied. Starting application..."
exec "$@"
