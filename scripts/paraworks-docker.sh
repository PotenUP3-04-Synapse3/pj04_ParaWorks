#!/bin/bash

# ParaWorks Docker Startup Script for macOS/Linux
# This script mimics the behavior of paraworks-docker.ps1

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$REPO_ROOT/.tmp"
mkdir -p "$TMP_DIR"

# Default Ports
BACKEND_PORT=8000
FRONTEND_PORT=3000
POSTGRES_PORT=5432
REDIS_PORT=6379
HOST_ADDRESS="127.0.0.1"

# Flags
STOP_MODE=false
DOWN_MODE=false
FORCE_MODE=false

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --stop) STOP_MODE=true ;;
        --down) DOWN_MODE=true ;;
        --force) FORCE_MODE=true ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

function write_step() {
    echo -e "\033[1;34m[ParaWorks]\033[0m $1"
}

function kill_port() {
    local port=$1
    local pids=$(lsof -ti:"$port")
    if [ -n "$pids" ]; then
        write_step "Killing processes on port $port (PIDs: $pids)"
        echo "$pids" | xargs kill -9
    fi
}

function stop_all() {
    write_step "Stopping ParaWorks..."
    
    # Kill backend and frontend if they are running on these ports
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    
    cd "$REPO_ROOT"
    if [ "$DOWN_MODE" = true ]; then
        docker compose down
    else
        docker compose stop postgres redis minio
    fi
    write_step "Stopped."
}

# 0. Handle Stop/Down mode
if [ "$STOP_MODE" = true ] || [ "$DOWN_MODE" = true ]; then
    stop_all
    exit 0
fi

# 1. Ensure Docker is running
if ! docker info >/dev/null 2>&1; then
    write_step "Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

# 2. Check for port conflicts
if [ "$FORCE_MODE" = true ]; then
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
else
    if lsof -i :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null; then
        write_step "Backend port $BACKEND_PORT is already in use. Use --force to kill it."
        exit 1
    fi
    if lsof -i :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null; then
        write_step "Frontend port $FRONTEND_PORT is already in use. Use --force to kill it."
        exit 1
    fi
fi

# 3. Start Docker services
write_step "Starting production-like Docker dev mode"
export PARAWORKS_POSTGRES_PORT=$POSTGRES_PORT
export PARAWORKS_REDIS_PORT=$REDIS_PORT

cd "$REPO_ROOT"
docker compose up -d postgres redis minio

# 4. Wait for Postgres to be ready
write_step "Waiting for Postgres to be ready..."
until docker exec paraworks-postgres pg_isready -U paraworks -d paraworks >/dev/null 2>&1; do
  sleep 1
done

# 5. Database Initialization
DATABASE_URL="postgresql+psycopg://paraworks:paraworks@127.0.0.1:$POSTGRES_PORT/paraworks"
export DATABASE_URL=$DATABASE_URL
export PARAWORKS_DATABASE_URL=$DATABASE_URL
export REDIS_URL="redis://127.0.0.1:$REDIS_PORT/0"
export PARAWORKS_DEMO_MODE="false"

write_step "Checking pgvector schema"
uv run python scripts/check_pgvector_dev.py --database-url "$DATABASE_URL" --ensure-vector-schema

write_step "Applying database migrations"
uv run alembic upgrade head

write_step "Seeding local application data"
uv run python -m backend.app.db.init_db

# 6. Start Backend and Frontend
write_step "Starting backend and frontend..."

# Backend in background
export AGENT_LLM_ENABLED="true"
uv run uvicorn backend.app.main:app --host $HOST_ADDRESS --port $BACKEND_PORT > "$TMP_DIR/paraworks-backend.out.log" 2> "$TMP_DIR/paraworks-backend.err.log" &
BACKEND_PID=$!

# Frontend in background
cd "$REPO_ROOT/frontend"
export NEXT_PUBLIC_API_BASE_URL="http://$HOST_ADDRESS:$BACKEND_PORT"
npm run dev -- --hostname 127.0.0.1 --port $FRONTEND_PORT > "$TMP_DIR/paraworks-frontend.out.log" 2> "$TMP_DIR/paraworks-frontend.err.log" &
FRONTEND_PID=$!

write_step "Ready!"
echo "Backend:  http://$HOST_ADDRESS:$BACKEND_PORT/health"
echo "Frontend: http://127.0.0.1:$FRONTEND_PORT/login"
echo ""
echo "PIDs: Backend($BACKEND_PID), Frontend($FRONTEND_PID)"
echo "Logs are in $TMP_DIR"
echo "To stop:  ./scripts/paraworks-docker.sh --stop"

# Keep script running to allow easy stopping via Ctrl+C
trap stop_all EXIT

# Wait for processes
wait
