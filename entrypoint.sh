#!/usr/bin/env sh
set -eu

if [ -n "${POSTGRES_HOST:-}" ]; then
  echo "Aguardando Postgres em ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."
  until nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
    sleep 1
  done
fi

python manage.py migrate --noinput
exec "$@"
