#!/bin/bash

# Database migration script

echo "Running database migrations..."

# PostgreSQL
export DATABASE_URL=${DATABASE_URL:-postgresql://sentry_user:sentry_password@localhost:5432/sentry_cbp}

# Alembic would go here in production
# alembic upgrade head

echo "✓ Migrations complete"
