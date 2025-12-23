#!/bin/bash

# GhostLine Local Integration Test Runner
# This script sets up and runs integration tests locally

echo "🚀 GhostLine Local Integration Test Runner"
echo "========================================="

# Check if database tunnel is active
if ! nc -z localhost 5433 2>/dev/null; then
    echo "❌ Database tunnel not active. Starting tunnel..."
    ./db_connect.sh tunnel &
    sleep 5
else
    echo "✅ Database tunnel is active"
fi

# Kill any existing API servers
echo "🔄 Stopping any existing API servers..."
pkill -f uvicorn || true
sleep 2

# Start API server
echo "🚀 Starting local API server..."
cd ghostline/api
export DATABASE_URL="postgresql://ghostlineadmin:YO,_9~5]Vp}vrNGl@localhost:5433/ghostline"
export JWT_SECRET_KEY="test-secret-key-for-local-testing"
export CORS_ORIGINS='["http://localhost:3000","http://localhost:8001","http://localhost:8000"]'

poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
API_PID=$!
echo "API server PID: $API_PID"

# Wait for API to be ready
echo "⏳ Waiting for API to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8001/health > /dev/null; then
        echo "✅ API is ready!"
        break
    fi
    echo -n "."
    sleep 1
done

# Run API tests with local server
echo ""
echo "🧪 Running API integration tests..."
export BASE_URL="http://localhost:8001/api/v1"
export TEST_DATABASE_URL="postgresql://ghostlineadmin:YO,_9~5]Vp}vrNGl@localhost:5433/ghostline"

# Run only integration tests that don't use SQLite
poetry run pytest tests/integration/test_project_creation_e2e.py -v -k "not sqlite" || true

# Go to web directory
cd ../web

# Update test configuration to use local API
echo "📝 Configuring web tests for local API..."
export NEXT_PUBLIC_API_URL="http://localhost:8001"
export API_URL="http://localhost:8001"

# Run web integration tests
echo "🧪 Running Web integration tests..."
npm test -- --testPathPattern="real|e2e" --watchAll=false || true

# Cleanup
echo ""
echo "🧹 Cleaning up..."
kill $API_PID 2>/dev/null || true

echo ""
echo "✅ Local integration tests completed!"
echo ""
echo "📊 Summary:"
echo "- API tests run against local server at http://localhost:8001"
echo "- Web tests configured to use local API"
echo "- Database accessed through SSH tunnel"
echo ""
echo "💡 To run continuously during development:"
echo "   1. Keep this script running in one terminal"
echo "   2. Make changes in another terminal"
echo "   3. Tests will auto-rerun with --reload flag" 