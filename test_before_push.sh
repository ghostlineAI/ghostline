#!/bin/bash
# Comprehensive testing before pushing to main

set -e  # Exit on any error

echo "🔍 Running comprehensive tests before push..."

# 1. Backend tests
echo "�� Testing API..."
cd ghostline/api
poetry run pytest -v
poetry run ruff check .
poetry run mypy .

# 2. Frontend tests  
echo "🎨 Testing Web..."
cd ../web
npm test
npm run lint
npm run type-check

# 3. Test API endpoints with curl
echo "🌐 Testing live endpoints..."
# You can add specific endpoint tests here

# 4. Check for common issues
echo "🔎 Checking for common issues..."
# Check for admin credentials in code
if grep -r "YO,_9~5]Vp}vrNGl" . --exclude="*.log" --exclude="test_before_push.sh"; then
    echo "❌ FATAL: Admin password found in code!"
    exit 1
fi

echo "✅ All tests passed! Safe to push to main."
echo ""
echo "To push: git push origin main"
