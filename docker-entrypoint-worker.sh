#!/bin/bash
set -e

echo "=== Kasparro ETL Worker Startup ==="

# Wait for database to be ready
echo "Waiting for PostgreSQL..."

# First check if pg_isready works
until pg_isready -h ${DATABASE_HOST:-db} -p 5432 -U ${DATABASE_USER:-kasparro} 2>&1; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 5
done

echo "PostgreSQL port is open, testing connection..."

# Then test actual connection
MAX_RETRIES=30
RETRY_COUNT=0
until PGPASSWORD=${DATABASE_PASSWORD} psql -h ${DATABASE_HOST} -U ${DATABASE_USER} -d ${DATABASE_NAME:-kasparro} -c '\q' 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "Failed to connect to database after $MAX_RETRIES attempts"
    exit 1
  fi
  echo "Database connection test failed (attempt $RETRY_COUNT/$MAX_RETRIES) - retrying..."
  sleep 2
done

echo "PostgreSQL is up - worker ready to start"
echo "Note: Migrations are run by API service only"
echo "Starting worker: $@"

# Execute the main command (worker scheduler)
exec "$@"
