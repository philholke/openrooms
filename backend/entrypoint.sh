#!/bin/sh
set -e

# Run Alembic migrations before starting the application server.
# Uses DATABASE_URL_SYNC (psycopg2) which Alembic is configured to read.
echo "Running database migrations..."
alembic upgrade head

echo "Starting application server..."
exec "$@"
