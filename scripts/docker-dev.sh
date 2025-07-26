#!/bin/bash

# Docker Development Helper Script for ProScrape
# This script provides convenient commands for Docker-based development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
PROJECT_NAME="proscrape"
COMPOSE_FILE="docker-compose.dev.yml"
ENV_FILE=".env.docker"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Check if docker-compose is available
check_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        log_error "docker-compose is not installed. Please install it and try again."
        exit 1
    fi
}

# Check if environment file exists
check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        log_warning "Environment file $ENV_FILE not found."
        if [ -f "${ENV_FILE}.example" ]; then
            log_info "Copying from ${ENV_FILE}.example..."
            cp "${ENV_FILE}.example" "$ENV_FILE"
            log_success "Created $ENV_FILE from example file."
            log_warning "Please review and customize the environment variables in $ENV_FILE"
        else
            log_error "No environment file found. Please create $ENV_FILE"
            exit 1
        fi
    fi
}

# Show help
show_help() {
    echo "ProScrape Docker Development Helper"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  setup           - Initial setup (create env file, pull images)"
    echo "  start           - Start all services"
    echo "  stop            - Stop all services"
    echo "  restart         - Restart all services"
    echo "  status          - Show status of all services"
    echo "  logs [service]  - Show logs (optionally for specific service)"
    echo "  shell [service] - Open shell in service container"
    echo "  build           - Build all Docker images"
    echo "  rebuild         - Force rebuild all images"
    echo "  clean           - Clean up containers and volumes"
    echo "  reset           - Full reset (clean + rebuild + start)"
    echo "  health          - Check health of all services"
    echo "  backup          - Backup database data"
    echo "  restore [file]  - Restore database from backup"
    echo "  update          - Update all images and restart"
    echo ""
    echo "Services:"
    echo "  api       - FastAPI application"
    echo "  worker    - Celery worker"
    echo "  beat      - Celery beat scheduler"
    echo "  flower    - Celery monitoring"
    echo "  frontend  - Svelte frontend"
    echo "  mongodb   - MongoDB database"
    echo "  redis     - Redis cache/queue"
    echo "  postgres  - PostgreSQL metadata database"
    echo "  nginx     - Nginx reverse proxy"
    echo ""
    echo "Examples:"
    echo "  $0 setup                    # Initial setup"
    echo "  $0 start                    # Start all services"
    echo "  $0 logs api                 # Show API logs"
    echo "  $0 shell worker             # Open shell in worker container"
    echo "  $0 restart api worker       # Restart specific services"
}

# Setup command
setup() {
    log_info "Setting up ProScrape development environment..."
    
    check_docker
    check_compose
    check_env_file
    
    log_info "Pulling Docker images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
    
    log_info "Creating Docker volumes..."
    docker volume create proscrape_mongodb_data
    docker volume create proscrape_postgres_data
    docker volume create proscrape_redis_data
    
    log_success "Setup completed!"
    log_info "Run '$0 start' to start the development environment."
}

# Start services
start_services() {
    log_info "Starting ProScrape services..."
    
    check_docker
    check_compose
    check_env_file
    
    if [ $# -eq 0 ]; then
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
        log_success "All services started!"
    else
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d "$@"
        log_success "Services started: $*"
    fi
    
    log_info "Waiting for services to be ready..."
    sleep 5
    
    show_status
}

# Stop services
stop_services() {
    log_info "Stopping ProScrape services..."
    
    if [ $# -eq 0 ]; then
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop
        log_success "All services stopped!"
    else
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop "$@"
        log_success "Services stopped: $*"
    fi
}

# Restart services
restart_services() {
    log_info "Restarting ProScrape services..."
    
    if [ $# -eq 0 ]; then
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart
        log_success "All services restarted!"
    else
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart "$@"
        log_success "Services restarted: $*"
    fi
    
    show_status
}

# Show status
show_status() {
    log_info "ProScrape service status:"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
    
    log_info "Service URLs:"
    echo "  API:           http://localhost:8000"
    echo "  Frontend:      http://localhost:3000"
    echo "  Flower:        http://localhost:5555"
    echo "  API Docs:      http://localhost:8000/docs"
    echo "  MongoDB:       mongodb://localhost:27017"
    echo "  Redis:         redis://localhost:6379"
    echo "  PostgreSQL:    postgresql://localhost:5432"
}

# Show logs
show_logs() {
    if [ $# -eq 0 ]; then
        log_info "Showing logs for all services..."
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f --tail=100
    else
        log_info "Showing logs for: $*"
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f --tail=100 "$@"
    fi
}

# Open shell
open_shell() {
    if [ $# -eq 0 ]; then
        log_error "Please specify a service name"
        echo "Available services: api, worker, beat, flower, frontend, mongodb, redis, postgres"
        exit 1
    fi
    
    service=$1
    log_info "Opening shell in $service container..."
    
    case $service in
        api|worker|beat|flower)
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec "$service" /bin/bash
            ;;
        frontend)
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec "$service" /bin/sh
            ;;
        mongodb)
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec "$service" mongosh
            ;;
        redis)
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec "$service" redis-cli
            ;;
        postgres)
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec "$service" psql -U proscrape_user -d proscrape_db
            ;;
        *)
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec "$service" /bin/bash
            ;;
    esac
}

# Build images
build_images() {
    log_info "Building Docker images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build "$@"
    log_success "Images built successfully!"
}

# Rebuild images
rebuild_images() {
    log_info "Force rebuilding Docker images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build --no-cache "$@"
    log_success "Images rebuilt successfully!"
}

# Clean up
clean_up() {
    log_warning "This will remove all containers, networks, and volumes!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleaning up..."
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down -v --remove-orphans
        docker system prune -f
        log_success "Cleanup completed!"
    else
        log_info "Cleanup cancelled."
    fi
}

# Full reset
full_reset() {
    log_warning "This will perform a full reset: clean + rebuild + start"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        clean_up
        rebuild_images
        start_services
        log_success "Full reset completed!"
    else
        log_info "Reset cancelled."
    fi
}

# Health check
health_check() {
    log_info "Checking service health..."
    
    # API health
    if curl -s http://localhost:8000/health > /dev/null; then
        log_success "API is healthy"
    else
        log_error "API is not responding"
    fi
    
    # Frontend health
    if curl -s http://localhost:3000 > /dev/null; then
        log_success "Frontend is healthy"
    else
        log_error "Frontend is not responding"
    fi
    
    # Flower health
    if curl -s http://localhost:5555 > /dev/null; then
        log_success "Flower is healthy"
    else
        log_error "Flower is not responding"
    fi
    
    # Database connections
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        log_success "MongoDB is healthy"
    else
        log_error "MongoDB is not responding"
    fi
    
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis is healthy"
    else
        log_error "Redis is not responding"
    fi
    
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres pg_isready -U proscrape_user > /dev/null 2>&1; then
        log_success "PostgreSQL is healthy"
    else
        log_error "PostgreSQL is not responding"
    fi
}

# Backup database
backup_db() {
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_dir="./backups"
    mkdir -p "$backup_dir"
    
    log_info "Creating database backup..."
    
    # MongoDB backup
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T mongodb mongodump --db proscrape --archive > "${backup_dir}/mongodb_backup_${timestamp}.archive"
    log_success "MongoDB backup created: ${backup_dir}/mongodb_backup_${timestamp}.archive"
    
    # PostgreSQL backup
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres pg_dump -U proscrape_user -d proscrape_db > "${backup_dir}/postgres_backup_${timestamp}.sql"
    log_success "PostgreSQL backup created: ${backup_dir}/postgres_backup_${timestamp}.sql"
}

# Restore database
restore_db() {
    if [ $# -eq 0 ]; then
        log_error "Please specify backup file"
        exit 1
    fi
    
    backup_file=$1
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log_warning "This will overwrite existing database data!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restoring database from $backup_file..."
        
        if [[ $backup_file == *.archive ]]; then
            # MongoDB restore
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T mongodb mongorestore --db proscrape --archive < "$backup_file"
            log_success "MongoDB restored successfully!"
        elif [[ $backup_file == *.sql ]]; then
            # PostgreSQL restore
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres psql -U proscrape_user -d proscrape_db < "$backup_file"
            log_success "PostgreSQL restored successfully!"
        else
            log_error "Unknown backup file format. Expected .archive (MongoDB) or .sql (PostgreSQL)"
        fi
    else
        log_info "Restore cancelled."
    fi
}

# Update images
update_images() {
    log_info "Updating Docker images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
    restart_services
    log_success "Images updated and services restarted!"
}

# Main script logic
case "$1" in
    setup)
        setup
        ;;
    start)
        shift
        start_services "$@"
        ;;
    stop)
        shift
        stop_services "$@"
        ;;
    restart)
        shift
        restart_services "$@"
        ;;
    status)
        show_status
        ;;
    logs)
        shift
        show_logs "$@"
        ;;
    shell)
        shift
        open_shell "$@"
        ;;
    build)
        shift
        build_images "$@"
        ;;
    rebuild)
        shift
        rebuild_images "$@"
        ;;
    clean)
        clean_up
        ;;
    reset)
        full_reset
        ;;
    health)
        health_check
        ;;
    backup)
        backup_db
        ;;
    restore)
        shift
        restore_db "$@"
        ;;
    update)
        update_images
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac