#!/bin/bash
# Local deployment script for CBP Sentry with selective rebuild options

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
  echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
  echo -e "${RED}✗ $1${NC}"
}

print_info() {
  echo -e "${YELLOW}→ $1${NC}"
}

OBS_DIR="/home/rahulvadera/cbp-observability"

show_usage() {
  cat << 'EOF'
Usage: ./scripts/deploy-local.sh [OPTION]

Local deployment options:

  full          Full clean build (wipes all containers, volumes, images, cache)
  ui            Rebuild UI only (fastest for frontend changes)
  api           Rebuild sentry-api only
  data          Rebuild sentry-data only
  cord          Rebuild sentry-cord-integration only
  quick         Quick restart (no rebuild, just docker compose up)
  status        Show container status (sentry + observability)
  logs          Show container logs
  down          Stop all containers (sentry + observability)
  obs           Start/stop observability stack only (obs up|obs down|obs status)
  clean         Full system cleanup (docker system prune -a)
  help          Show this help message

Examples:
  ./scripts/deploy-local.sh full          # Fresh build from scratch
  ./scripts/deploy-local.sh ui            # Rebuild only UI after changes
  ./scripts/deploy-local.sh quick         # Fast restart (containers already built)
  ./scripts/deploy-local.sh status        # Check health
  ./scripts/deploy-local.sh obs up        # Start observability stack
  ./scripts/deploy-local.sh obs down      # Stop observability stack
EOF
}

# Wait for sentry-db to be healthy (PostgreSQL)
wait_for_db() {
  print_info "Waiting for sentry-db (PostgreSQL) to be ready..."
  for i in $(seq 1 30); do
    if docker compose exec -T sentry-db pg_isready -U sentry -d sentry > /dev/null 2>&1; then
      print_success "sentry-db is healthy (schemas initialised by init.sql)"
      return 0
    fi
    echo -e "  ${YELLOW}→${NC} Attempt $i/30: sentry-db not ready yet, waiting 3s..."
    sleep 3
  done
  print_error "sentry-db did not become healthy in time — check: docker compose logs sentry-db"
  return 1
}

# Observability stack helpers
obs_up() {
  if [ -d "$OBS_DIR" ]; then
    print_info "Starting observability stack..."
    docker compose -f "$OBS_DIR/docker-compose.yml" up -d
    print_success "Observability stack running → Grafana: http://localhost:3002"
  else
    print_error "cbp-observability not found at $OBS_DIR — skipping obs stack"
  fi
}

obs_down() {
  if [ -d "$OBS_DIR" ]; then
    print_info "Stopping observability stack..."
    docker compose -f "$OBS_DIR/docker-compose.yml" down
    print_success "Observability stack stopped"
  fi
}

obs_status() {
  if [ -d "$OBS_DIR" ]; then
    echo ""
    print_header "OBSERVABILITY STACK"
    docker compose -f "$OBS_DIR/docker-compose.yml" ps 2>/dev/null || print_error "Obs stack not running"
  fi
}

# Main deployment functions
deploy_full_clean() {
  print_header "FULL CLEAN BUILD DEPLOYMENT"

  print_info "Stopping all containers and removing volumes..."
  cd "$PROJECT_DIR"
  docker compose down -v 2>/dev/null || true
  obs_down

  print_info "Removing all Docker images and build cache..."
  docker system prune -f --all 2>/dev/null || true

  print_info "Cleaning build artifacts..."
  rm -rf ui/dist ui/.tsbuildinfo 2>/dev/null || true

  print_info "Building UI..."
  npm run build --prefix=ui > /dev/null 2>&1
  print_success "UI built"

  print_info "Building Docker images (no cache)..."
  docker compose build --no-cache > /dev/null 2>&1
  print_success "Docker images built"

  print_info "Starting sentry-db (PostgreSQL) and all containers..."
  docker compose up -d
  wait_for_db

  print_info "Starting observability stack..."
  obs_up

  print_info "Waiting for application containers to be healthy..."
  sleep 6

  print_header "DEPLOYMENT COMPLETE"
  docker compose ps

  print_info "Testing API connectivity..."
  if curl -s http://localhost:3001/api/shipments?limit=1 > /dev/null 2>&1; then
    print_success "API responding on localhost:3001"
  else
    print_error "API not responding yet, waiting..."
    sleep 3
    if curl -s http://localhost:3001/api/shipments?limit=1 > /dev/null 2>&1; then
      print_success "API responding on localhost:3001"
    else
      print_error "API not responding - check logs with: ./scripts/deploy-local.sh logs"
    fi
  fi

  echo ""
  print_success "Ready! Open http://localhost:3001 in your browser"
  echo -e "${YELLOW}→ Grafana (observability): http://localhost:3002${NC}"
  echo -e "${YELLOW}→ Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)${NC}"
  echo -e "${YELLOW}→ Clear browser cache in DevTools → Application → Clear site data${NC}"
}

deploy_ui_only() {
  print_header "UI-ONLY REBUILD"

  cd "$PROJECT_DIR"

  print_info "Building UI..."
  npm run build --prefix=ui > /dev/null 2>&1
  print_success "UI built"

  print_info "Rebuilding sentry-ui Docker image..."
  docker compose build sentry-ui > /dev/null 2>&1
  print_success "Docker image built"

  print_info "Restarting sentry-ui container..."
  docker compose up -d sentry-ui

  sleep 3

  print_header "DEPLOYMENT COMPLETE"
  docker compose ps | grep sentry-ui

  print_success "UI redeployed! Hard refresh your browser: Ctrl+Shift+R"
}

deploy_service() {
  local service=$1
  print_header "REBUILDING $service"

  cd "$PROJECT_DIR"

  print_info "Rebuilding $service Docker image..."
  docker compose build "$service" > /dev/null 2>&1
  print_success "Docker image built"

  print_info "Restarting $service container..."
  docker compose up -d "$service"

  sleep 3

  print_header "DEPLOYMENT COMPLETE"
  docker compose ps | grep "$service"

  print_success "$service redeployed!"
}

deploy_quick() {
  print_header "QUICK RESTART (no rebuild)"

  cd "$PROJECT_DIR"

  print_info "Starting sentry-db (PostgreSQL) and containers..."
  docker compose up -d
  wait_for_db
  obs_up

  sleep 4

  print_header "STATUS"
  docker compose ps

  print_info "Testing API..."
  if curl -s http://localhost:3001/api/shipments?limit=1 > /dev/null 2>&1; then
    print_success "API responding"
  else
    print_error "API not responding"
  fi
}

show_status() {
  print_header "CONTAINER STATUS"
  cd "$PROJECT_DIR"
  docker compose ps

  echo ""
  print_info "PostgreSQL (sentry-db)..."
  if docker compose exec -T sentry-db pg_isready -U sentry -d sentry > /dev/null 2>&1; then
    print_success "sentry-db healthy (cbp_sentry schema)"
  else
    print_error "sentry-db not ready"
  fi

  echo ""
  print_info "Testing API connectivity..."
  if curl -s http://localhost:3001/api/shipments?limit=1 > /dev/null 2>&1; then
    print_success "API responding on localhost:3001"
  else
    print_error "API not responding - check logs"
  fi

  obs_status
}

show_logs() {
  print_header "CONTAINER LOGS (last 50 lines, press Ctrl+C to exit)"
  cd "$PROJECT_DIR"
  docker compose logs -f --tail=50
}

stop_containers() {
  print_header "STOPPING CONTAINERS"
  cd "$PROJECT_DIR"
  docker compose down
  obs_down
  print_success "All containers stopped"
}

cleanup_system() {
  print_header "FULL SYSTEM CLEANUP"
  print_error "This will remove:"
  echo "  - All stopped containers"
  echo "  - All dangling images"
  echo "  - All dangling build cache"
  echo ""
  read -p "Continue? (y/N) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker system prune -af
    print_success "System cleaned"
  else
    print_info "Cleanup cancelled"
  fi
}

# Main script logic
if [ $# -eq 0 ]; then
  print_error "No option specified"
  echo ""
  show_usage
  exit 1
fi

case "$1" in
  full)
    deploy_full_clean
    ;;
  ui)
    deploy_ui_only
    ;;
  api)
    deploy_service "sentry-api"
    ;;
  data)
    deploy_service "sentry-data"
    ;;
  cord)
    deploy_service "sentry-cord-integration"
    ;;
  quick)
    deploy_quick
    ;;
  status)
    show_status
    ;;
  logs)
    show_logs
    ;;
  down)
    stop_containers
    ;;
  obs)
    case "${2:-up}" in
      up)   cd "$PROJECT_DIR" && obs_up ;;
      down) obs_down ;;
      status) obs_status ;;
      *) print_error "Unknown obs sub-command: $2 (use: up, down, status)" ;;
    esac
    ;;
  clean)
    cleanup_system
    ;;
  help)
    show_usage
    ;;
  *)
    print_error "Unknown option: $1"
    echo ""
    show_usage
    exit 1
    ;;
esac
