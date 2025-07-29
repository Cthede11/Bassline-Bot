#!/bin/bash
set -e

# Docker entrypoint script for BasslineBot

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Trap signals for graceful shutdown
cleanup() {
    log "Received shutdown signal, cleaning up..."
    
    if [ ! -z "$HEALTH_CHECK_PID" ]; then
        kill $HEALTH_CHECK_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$MAIN_PID" ]; then
        kill -TERM $MAIN_PID 2>/dev/null || true
        wait $MAIN_PID 2>/dev/null || true
    fi
    
    success "Cleanup completed"
    exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT

# Wait for a service to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=${4:-30}
    local attempt=1
    
    log "Waiting for $service_name at $host:$port..."
    
    while [ $attempt -le $max_attempts ]; do
        if timeout 1 bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
            success "$service_name is ready!"
            return 0
        fi
        
        log "Attempt $attempt/$max_attempts: $service_name not ready, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    error "$service_name failed to become ready after $max_attempts attempts"
    return 1
}

# Validate environment variables
validate_environment() {
    log "Validating environment configuration..."
    
    local required_vars=("DISCORD_TOKEN" "DATABASE_URL")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        error "Missing required environment variables:"
        printf '%s\n' "${missing_vars[@]}" | sed 's/^/  - /'
        return 1
    fi
    
    # Basic Discord token validation
    if [[ ! $DISCORD_TOKEN =~ ^[A-Za-z0-9._-]{50,}$ ]]; then
        error "DISCORD_TOKEN appears to be invalid"
        return 1
    fi
    
    # Database URL validation
    if [[ ! $DATABASE_URL =~ ^(postgresql|sqlite|mysql):// ]]; then
        error "DATABASE_URL must start with postgresql://, sqlite://, or mysql://"
        return 1
    fi
    
    success "Environment validation passed"
    return 0
}

# Wait for database to be ready
wait_for_database() {
    log "Checking database connectivity..."
    
    if [[ $DATABASE_URL =~ ^postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+)$ ]]; then
        local db_host="${BASH_REMATCH[3]}"
        local db_port="${BASH_REMATCH[4]}"
        
        wait_for_service "$db_host" "$db_port" "PostgreSQL database" 60
        
        log "Testing database connection..."
        python -c "
import os, sys
from sqlalchemy import create_engine, text
try:
    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}', file=sys.stderr)
    sys.exit(1)
        " || return 1
        
    elif [[ $DATABASE_URL =~ ^sqlite:// ]]; then
        log "Using SQLite database, ensuring directory exists..."
        
        local db_path="${DATABASE_URL#sqlite:///}"
        local db_dir=$(dirname "$db_path")
        
        if [ "$db_dir" != "." ] && [ ! -d "$db_dir" ]; then
            mkdir -p "$db_dir"
            log "Created database directory: $db_dir"
        fi
    fi
    
    success "Database connectivity verified"
}

# Wait for Redis if configured
wait_for_redis() {
    if [ ! -z "$REDIS_URL" ]; then
        log "Checking Redis connectivity..."
        
        if [[ $REDIS_URL =~ ^redis://([^:]+):([0-9]+) ]]; then
            local redis_host="${BASH_REMATCH[1]}"
            local redis_port="${BASH_REMATCH[2]}"
            
            wait_for_service "$redis_host" "$redis_port" "Redis cache" 30
            
            python -c "
import redis, os, sys
try:
    r = redis.from_url(os.environ['REDIS_URL'])
    r.ping()
    print('Redis connection successful')
except Exception as e:
    print(f'Redis connection failed: {e}', file=sys.stderr)
    sys.exit(1)
            " || return 1
        fi
        
        success "Redis connectivity verified"
    else
        log "Redis not configured, skipping..."
    fi
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    if python scripts/migrate.py; then
        success "Database migrations completed"
    else
        error "Database migrations failed"
        return 1
    fi
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    local dirs=("logs" "data" "downloads" "static")
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log "Created directory: $dir"
        fi
    done
    
    chmod 755 logs data downloads static
    success "Directory setup completed"
}

# Start health check monitor
start_health_monitor() {
    if [ "${HEALTH_CHECK_ENABLED:-true}" = "true" ]; then
        log "Starting health check monitor..."
        
        (
            sleep 60
            
            while true; do
                if ! curl -f http://localhost:${DASHBOARD_PORT:-8080}/health >/dev/null 2>&1; then
                    warn "Health check failed - bot may be unhealthy"
                fi
                sleep 30
            done
        ) &
        
        HEALTH_CHECK_PID=$!
        log "Health check monitor started (PID: $HEALTH_CHECK_PID)"
    fi
}

# Show startup banner
show_banner() {
    echo ""
    echo -e "${BLUE}==============================${NC}"
    echo -e "${BLUE}    BasslineBot Starting      ${NC}"
    echo -e "${BLUE}==============================${NC}"
    echo -e "${GREEN}Version: ${BOT_VERSION:-1.0.0}${NC}"
    echo -e "${GREEN}Environment: ${ENVIRONMENT:-production}${NC}"
    echo -e "${GREEN}Python: $(python --version)${NC}"
    echo -e "${GREEN}Dashboard: http://localhost:${DASHBOARD_PORT:-8080}${NC}"
    echo -e "${BLUE}==============================${NC}"
    echo ""
}

# Main execution
main() {
    show_banner
    
    validate_environment || exit 1
    create_directories
    wait_for_database || exit 1
    wait_for_redis || exit 1
    
    if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
        run_migrations || exit 1
    fi
    
    start_health_monitor
    
    success "Initialization completed successfully"
    log "Starting BasslineBot with command: $*"
    
    exec "$@" &
    MAIN_PID=$!
    
    wait $MAIN_PID
}

# Handle special commands
case "$1" in
    "bash"|"sh")
        exec "$@"
        ;;
    "test")
        log "Running tests..."
        exec python -m pytest tests/ -v
        ;;
    "migrate")
        log "Running migrations only..."
        validate_environment || exit 1
        wait_for_database || exit 1
        run_migrations || exit 1
        success "Migrations completed"
        exit 0
        ;;
    "health")
        log "Running health check..."
        if curl -f http://localhost:${DASHBOARD_PORT:-8080}/health >/dev/null 2>&1; then
            success "Bot is healthy"
            exit 0
        else
            error "Bot is unhealthy"
            exit 1
        fi
        ;;
    *)
        main "$@"
        ;;
esac: $HEALTH_CHECK_PID)"
    fi
}

# Function to display startup banner
show_banner() {
    echo ""
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}    🎵 Bassline-Bot Starting    ${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo -e "${GREEN}Version: ${BOT_VERSION:-1.0.0}${NC}"
    echo -e "${GREEN}Environment: ${ENVIRONMENT:-production}${NC}"
    echo -e "${GREEN}Python: $(python --version)${NC}"
    echo -e "${GREEN}Dashboard: http://localhost:${DASHBOARD_PORT:-8080}${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo ""
}

# Main execution
main() {
    show_banner
    
    # Validate environment
    if ! validate_environment; then
        error "Environment validation failed"
        exit 1
    fi
    
    # Create directories
    create_directories
    
    # Wait for external services
    wait_for_database || exit 1
    wait_for_redis || exit 1
    
    # Run migrations
    if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
        run_migrations || exit 1
    fi
    
    # Validate configuration
    validate_config || exit 1
    
    # Start health monitor
    start_health_monitor
    
    success "Initialization completed successfully"
    log "Starting Bassline-Bot with command: $*"
    
    # Execute the main command
    exec "$@" &
    MAIN_PID=$!
    
    # Wait for the main process
    wait $MAIN_PID
}

# Handle special commands
case "$1" in
    "bash"|"sh")
        # Interactive shell
        exec "$@"
        ;;
    "test")
        # Run tests
        log "Running tests..."
        exec python -m pytest tests/ -v
        ;;
    "migrate")
        # Run migrations only
        log "Running migrations only..."
        validate_environment || exit 1
        wait_for_database || exit 1
        run_migrations || exit 1
        success "Migrations completed"
        exit 0
        ;;
    "validate")
        # Validate configuration only
        log "Validating configuration only..."
        validate_environment || exit 1
        validate_config || exit 1
        success "Validation completed"
        exit 0
        ;;
    "health")
        # Health check
        log "Running health check..."
        if curl -f http://localhost:${DASHBOARD_PORT:-8080}/health >/dev/null 2>&1; then
            success "Bot is healthy"
            exit 0
        else
            error "Bot is unhealthy"
            exit 1
        fi
        ;;
    *)
        # Normal startup
        main "$@"
        ;;
esac