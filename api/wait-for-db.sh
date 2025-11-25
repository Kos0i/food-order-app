#!/bin/bash
# Ожидание готовности базы данных

set -e

host="$1"
shift
cmd="$@"

until PGPASSWORD=password psql -h "$host" -U "user" -d "food_orders" -c '\q'; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 5
done

>&2 echo "PostgreSQL is up - executing command"
exec $cmd