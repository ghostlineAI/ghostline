#!/bin/bash
# GhostLine Local Development Setup Script
# This script starts all services needed for local development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 GhostLine Local Development Setup"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# Start PostgreSQL and Redis via docker-compose
echo ""
echo "📦 Starting PostgreSQL and Redis..."
cd "$PROJECT_ROOT"
docker-compose up -d

# Wait for PostgreSQL to be ready
echo ""
echo "⏳ Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U ghostline -d ghostline > /dev/null 2>&1; do
    sleep 1
done
echo -e "${GREEN}✓ PostgreSQL is ready${NC}"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    sleep 1
done
echo -e "${GREEN}✓ Redis is ready${NC}"

# Setup API environment
echo ""
echo "🔧 Setting up API..."
cd "$PROJECT_ROOT/ghostline/api"

# Copy env.example to .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from env.example..."
    cp env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
else
    echo -e "${YELLOW}ℹ .env already exists, skipping${NC}"
fi

# Create uploads directory
mkdir -p uploads
echo -e "${GREEN}✓ Created uploads directory${NC}"

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}❌ Poetry is not installed. Please install it first:${NC}"
    echo "   curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Install Python dependencies
echo ""
echo "📚 Installing Python dependencies..."
poetry install

# Run database migrations
echo ""
echo "🗄️ Running database migrations..."
poetry run alembic upgrade head

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "To start the API server, run:"
echo -e "  ${YELLOW}cd ghostline/api && poetry run uvicorn app.main:app --reload${NC}"
echo ""
echo "To start the frontend, run:"
echo -e "  ${YELLOW}cd ghostline/web && npm install && npm run dev${NC}"
echo ""
echo "Services:"
echo "  - API:        http://localhost:8000"
echo "  - Frontend:   http://localhost:3000"
echo "  - PostgreSQL: localhost:5432 (user: ghostline, pass: ghostline)"
echo "  - Redis:      localhost:6379"
echo ""
echo "Auth is DISABLED - no login required for local development!"


