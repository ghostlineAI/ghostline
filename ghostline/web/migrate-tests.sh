#!/bin/bash

echo "🔄 Test Migration Helper"
echo "========================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if API is running
check_api() {
    echo -n "Checking if API is running at localhost:8000... "
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API is running${NC}"
        return 0
    else
        echo -e "${RED}✗ API is not running${NC}"
        echo ""
        echo "To run the API locally:"
        echo "  cd ../api"
        echo "  docker-compose up"
        echo ""
        return 1
    fi
}

# Function to run real tests
run_real_tests() {
    echo ""
    echo "Running real integration tests..."
    echo "================================="
    npm test -- --testNamePattern="Real" --verbose
}

# Function to compare mocked vs real test results
compare_tests() {
    echo ""
    echo "Comparing mocked vs real test results..."
    echo "========================================"
    
    # Run mocked tests
    echo -e "${YELLOW}Running mocked tests...${NC}"
    npm test -- --testPathPattern="api-client.test" --json > mocked-results.json 2>&1
    
    # Run real tests  
    echo -e "${YELLOW}Running real tests...${NC}"
    npm test -- --testPathPattern="real" --json > real-results.json 2>&1
    
    echo ""
    echo "Results comparison:"
    echo -e "${GREEN}Mocked tests:${NC} $(grep -c '"status":"passed"' mocked-results.json || echo 0) passed"
    echo -e "${GREEN}Real tests:${NC} $(grep -c '"status":"passed"' real-results.json || echo 0) passed"
    
    # Clean up
    rm -f mocked-results.json real-results.json
}

# Function to create test database
setup_test_db() {
    echo ""
    echo "Setting up test database..."
    echo "==========================="
    
    # This would normally create a test database
    # For now, we'll just check if we can connect
    if command -v psql &> /dev/null; then
        echo "PostgreSQL client found"
    else
        echo -e "${YELLOW}Warning: psql not found. Install PostgreSQL client for database tests.${NC}"
    fi
}

# Main menu
show_menu() {
    echo ""
    echo "What would you like to do?"
    echo "1) Check API status"
    echo "2) Run real integration tests"
    echo "3) Compare mocked vs real tests"
    echo "4) Setup test database"
    echo "5) Migrate a specific test file"
    echo "6) Exit"
    echo ""
    read -p "Enter choice [1-6]: " choice
    
    case $choice in
        1) check_api ;;
        2) 
            if check_api; then
                run_real_tests
            fi
            ;;
        3) compare_tests ;;
        4) setup_test_db ;;
        5) 
            echo "Enter the test file to migrate (e.g., api-client.test.ts):"
            read filename
            echo "Creating real version of $filename..."
            # Would implement migration logic here
            echo "TODO: Implement migration for $filename"
            ;;
        6) exit 0 ;;
        *) echo -e "${RED}Invalid choice${NC}" ;;
    esac
    
    show_menu
}

# Start
echo "This script helps migrate mocked tests to real integration tests."
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}Error: Must run from ghostline/web directory${NC}"
    exit 1
fi

show_menu 