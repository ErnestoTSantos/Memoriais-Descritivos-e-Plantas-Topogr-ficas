#!/usr/bin/env sh
set -eu

DB_HOST="${POSTGRES_HOST:-${PGHOST:-}}"
DB_PORT="${POSTGRES_PORT:-${PGPORT:-5432}}"

if [ -n "$DB_HOST" ]; then
  echo "Aguardando Postgres em ${DB_HOST}:${DB_PORT}..."
  until nc -z "$DB_HOST" "$DB_PORT"; do
    sleep 1
  done
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec "$@"
