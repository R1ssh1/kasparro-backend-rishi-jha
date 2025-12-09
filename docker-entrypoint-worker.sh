#!/bin/bash
set -e

echo "=== Kasparro ETL Worker Startup ==="

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
until pg_isready -h ${DATABASE_HOST:-db} -p 5432 -U ${DATABASE_USER:-kasparro}; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is up - worker ready to start"
echo "Note: Migrations are run by API service only"
echo "Starting worker: $@"

# Execute the main command (worker scheduler)
exec "$@"
