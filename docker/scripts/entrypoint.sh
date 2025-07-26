#!/bin/bash
# Entrypoint script for ProScrape containers
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Wait for service to be available
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local timeout=${4:-30}
    
    log "Waiting for $service_name at $host:$port..."
    
    for i in $(seq 1 $timeout); do
        if nc -z "$host" "$port" 2>/dev/null; then
            log "$service_name is available!"
            return 0
        fi
        sleep 1
    done
    
    error "$service_name is not available after ${timeout}s"
    return 1
}

# Check required environment variables
check_env_vars() {
    local required_vars=("$@")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing required environment variables: ${missing_vars[*]}"
        return 1
    fi
    
    log "All required environment variables are set"
    return 0
}

# Initialize database connections
init_database() {
    log "Initializing database connections..."
    
    # MongoDB health check
    if [[ -n "$MONGODB_URL" ]]; then
        log "Testing MongoDB connection..."
        python -c "
import pymongo
import sys
try:
    client = pymongo.MongoClient('$MONGODB_URL', serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print('MongoDB connection successful')
except Exception as e:
    print(f'MongoDB connection failed: {e}')
    sys.exit(1)
" || return 1
    fi
    
    # Redis health check
    if [[ -n "$REDIS_URL" ]]; then
        log "Testing Redis connection..."
        python -c "
import redis
import sys
try:
    r = redis.from_url('$REDIS_URL')
    r.ping()
    print('Redis connection successful')
except Exception as e:
    print(f'Redis connection failed: {e}')
    sys.exit(1)
" || return 1
    fi
    
    log "Database connections initialized successfully"
}

# Run database migrations (if needed)
run_migrations() {
    log "Running database migrations..."
    # Add migration commands here if needed
    # python manage.py migrate
    log "Migrations completed"
}

# Main entrypoint logic
main() {
    log "Starting ProScrape container entrypoint..."
    
    # Parse service type from first argument
    SERVICE_TYPE=${1:-api}
    
    case $SERVICE_TYPE in
        api)
            log "Starting API service..."
            check_env_vars "MONGODB_URL" "REDIS_URL" || exit 1
            
            # Wait for dependencies
            if [[ "$REDIS_URL" == *"redis:"* ]]; then
                wait_for_service "redis" "6379" "Redis" || exit 1
            fi
            
            init_database || exit 1
            run_migrations || exit 1
            
            # Start API
            exec uvicorn api.main:app --host 0.0.0.0 --port ${API_PORT:-8000} "${@:2}"
            ;;
            
        worker)
            log "Starting Celery worker..."
            check_env_vars "MONGODB_URL" "REDIS_URL" || exit 1
            
            # Wait for dependencies
            if [[ "$REDIS_URL" == *"redis:"* ]]; then
                wait_for_service "redis" "6379" "Redis" || exit 1
            fi
            
            init_database || exit 1
            
            # Start Celery worker
            exec celery -A tasks.celery_app worker --loglevel=info "${@:2}"
            ;;
            
        beat)
            log "Starting Celery beat scheduler..."
            check_env_vars "MONGODB_URL" "REDIS_URL" || exit 1
            
            # Wait for dependencies
            if [[ "$REDIS_URL" == *"redis:"* ]]; then
                wait_for_service "redis" "6379" "Redis" || exit 1
            fi
            
            init_database || exit 1
            
            # Start Celery beat
            exec celery -A tasks.celery_app beat --loglevel=info "${@:2}"
            ;;
            
        flower)
            log "Starting Flower monitoring..."
            check_env_vars "REDIS_URL" || exit 1
            
            # Wait for Redis
            if [[ "$REDIS_URL" == *"redis:"* ]]; then
                wait_for_service "redis" "6379" "Redis" || exit 1
            fi
            
            # Start Flower
            exec celery -A tasks.celery_app flower "${@:2}"
            ;;
            
        *)
            log "Running custom command: $*"
            exec "$@"
            ;;
    esac
}

# Trap signals for graceful shutdown
trap 'log "Received SIGTERM, shutting down gracefully..."; exit 0' TERM
trap 'log "Received SIGINT, shutting down gracefully..."; exit 0' INT

# Run main function
main "$@"