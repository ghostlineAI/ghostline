#!/bin/bash
# Run tests for the infrastructure repository

set -e

cd "$(dirname "$0")"

echo "Running Terraform configuration tests..."

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "Installing pytest..."
    pip install -r requirements.txt
fi

# Run the tests
pytest test_terraform_config.py -v

echo "✅ All infrastructure tests passed!" 