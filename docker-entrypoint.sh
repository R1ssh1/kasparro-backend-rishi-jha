#!/bin/bash
set -e

echo "=== Kasparro ETL Pipeline Startup ==="

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
until pg_isready -h ${DATABASE_HOST:-db} -p 5432 -U ${DATABASE_USER}; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is up - checking connection..."

# Test database connection with retry
max_retries=30
counter=0
until PGPASSWORD=${DATABASE_PASSWORD} psql -h ${DATABASE_HOST:-db} -U ${DATABASE_USER} -d ${DATABASE_NAME} -c '\q' 2>/dev/null; do
  counter=$((counter + 1))
  if [ $counter -gt $max_retries ]; then
    echo "Failed to connect to database after $max_retries attempts"
    exit 1
  fi
  echo "Database not ready yet (attempt $counter/$max_retries)..."
  sleep 2
done

echo "Database connection successful!"

# Run migrations (only API service uses this entrypoint)
echo "Running database migrations..."
if alembic upgrade head; then
  echo "Migrations complete!"
else
  echo "Migration failed!"
  exit 1
fi

# Ensure master_entities tables exist (in case alembic is out of sync)
echo "Verifying master_entities tables..."
python create_master_entities.py || echo "Warning: Failed to verify master_entities tables"

echo "Starting application: $@"

# Execute the main command
exec "$@"
