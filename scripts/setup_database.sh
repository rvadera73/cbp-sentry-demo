#!/bin/bash

#######################################################################
# CBP Sentry - Database Setup and Seeding Script
# Handles database initialization for local, staging, and prod environments
# Usage: ./scripts/setup_database.sh [local|staging|restore] [options]
#######################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
SEED_DATA="$PROJECT_ROOT/services/data/seed_data/manifest_feb_march_2026_with_isf.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}→${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }
log_header() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }

# ====================================================================
# FUNCTION: Backup Current Database
# ====================================================================
backup_database() {
    local env=$1
    local db_file=$2

    log_header "Backing up $env database"

    mkdir -p "$BACKUP_DIR"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/cbp_sentry_${env}_${timestamp}.db"

    if [ "$env" = "local" ]; then
        log_info "Copying from local Docker volume..."
        docker compose cp sentry-data:$db_file "$backup_file"
    else
        log_info "Skipping backup for $env (not implemented)"
        return 0
    fi

    log_success "Database backed up to $backup_file"
    echo "$backup_file"
}

# ====================================================================
# FUNCTION: Seed Database
# ====================================================================
seed_database() {
    local env=$1

    log_header "Seeding $env database"

    if [ ! -f "$SEED_DATA" ]; then
        log_error "Seed data file not found: $SEED_DATA"
        return 1
    fi

    local record_count=$(grep -c '"id":"SHP-' "$SEED_DATA" || echo "0")
    log_info "Seed file contains $record_count records"

    if [ "$env" = "local" ]; then
        log_info "Restarting sentry-data to trigger seeding..."
        docker compose restart sentry-data
        sleep 15

        # Wait for service to be healthy
        local max_wait=60
        local elapsed=0
        while [ $elapsed -lt $max_wait ]; do
            if docker compose exec -T sentry-data curl -sf http://localhost:8005/shipments > /dev/null 2>&1; then
                log_success "Database seeded successfully"
                return 0
            fi
            sleep 2
            elapsed=$((elapsed + 2))
        done

        log_error "Database seeding timed out"
        return 1
    fi

    log_error "Seeding not implemented for $env"
    return 1
}

# ====================================================================
# FUNCTION: Restore Database from Backup
# ====================================================================
restore_database() {
    local backup_file=$1

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi

    log_header "Restoring database from backup"
    log_info "File: $backup_file"
    log_info "Size: $(du -h "$backup_file" | cut -f1)"

    docker compose cp "$backup_file" sentry-data:/app/data/cbp_sentry.db
    docker compose restart sentry-data
    sleep 10

    log_success "Database restored"
}

# ====================================================================
# FUNCTION: Verify Database
# ====================================================================
verify_database() {
    local env=$1

    log_header "Verifying $env database"

    if [ "$env" = "local" ]; then
        local count=$(curl -s http://localhost:8005/shipments 2>/dev/null | grep -c '"id":"SHP-' || echo "0")

        if [ "$count" -gt 0 ]; then
            log_success "Database contains $count shipment records"
            return 0
        else
            log_error "Database is empty"
            return 1
        fi
    fi

    log_error "Verification not implemented for $env"
    return 1
}

# ====================================================================
# MAIN
# ====================================================================
if [ $# -eq 0 ]; then
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  local              Set up and seed local database"
    echo "  staging            Initialize staging database (requires Neon URL)"
    echo "  backup [local]     Create database backup"
    echo "  restore <file>     Restore database from backup file"
    echo "  verify [local]     Verify database contents"
    echo "  export             Export local database to file"
    echo ""
    exit 1
fi

case "$1" in
    local)
        backup_database "local" "/app/data/cbp_sentry.db"
        seed_database "local"
        verify_database "local"
        ;;
    backup)
        if [ -z "$2" ]; then
            ENV="local"
        else
            ENV="$2"
        fi
        backup_database "$ENV" "/app/data/cbp_sentry.db"
        ;;
    restore)
        if [ -z "$2" ]; then
            log_error "Please specify backup file"
            echo "Available backups:"
            ls -lh "$BACKUP_DIR"/*.db 2>/dev/null || echo "No backups found"
            exit 1
        fi
        restore_database "$2"
        ;;
    verify)
        if [ -z "$2" ]; then
            ENV="local"
        else
            ENV="$2"
        fi
        verify_database "$ENV"
        ;;
    export)
        log_header "Exporting local database"
        mkdir -p "$BACKUP_DIR"
        local export_file="$BACKUP_DIR/cbp_sentry_export_$(date +%Y%m%d_%H%M%S).db"
        docker compose cp sentry-data:/app/data/cbp_sentry.db "$export_file"
        log_success "Database exported to: $export_file"
        log_info "File size: $(du -h "$export_file" | cut -f1)"
        log_info "To import into staging, use:"
        log_info "  psql \$DATABASE_URL < dump.sql"
        ;;
    *)
        log_error "Unknown command: $1"
        exit 1
        ;;
esac
