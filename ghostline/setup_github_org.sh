#!/bin/bash

# GhostLine GitHub Organization Setup Script
# This script helps initialize and push the repositories to GitHub

echo "=== GhostLine GitHub Organization Setup ==="
echo ""
echo "Prerequisites:"
echo "1. Create a private GitHub organization named 'ghostline'"
echo "2. Have GitHub CLI (gh) installed and authenticated"
echo "3. Run this script from the ghostline directory"
echo ""
read -p "Have you completed the prerequisites? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please complete the prerequisites first."
    exit 1
fi

# Function to create and push repository
create_and_push_repo() {
    local repo_name=$1
    local repo_desc=$2
    
    echo ""
    echo "Setting up repository: $repo_name"
    echo "Description: $repo_desc"
    
    cd $repo_name
    
    # Create GitHub repository
    gh repo create ghostline/$repo_name --private --description "$repo_desc" --confirm
    
    # Add remote and push
    git remote add origin git@github.com:ghostline/$repo_name.git
    git add .
    git commit -m "Initial commit: Phase 0 bootstrap"
    git branch -M main
    git push -u origin main
    
    # Enable branch protection
    gh api repos/ghostline/$repo_name/branches/main/protection \
        --method PUT \
        --field required_status_checks='{"strict":true,"contexts":["markdown-lint"]}' \
        --field enforce_admins=false \
        --field required_pull_request_reviews='{"required_approving_review_count":1}' \
        --field restrictions=null
    
    cd ..
}

# Create repositories
create_and_push_repo "web" "GhostLine web frontend application"
create_and_push_repo "api" "GhostLine backend API service"
create_and_push_repo "agents" "GhostLine AI agent system"
create_and_push_repo "infra" "GhostLine infrastructure as code"
create_and_push_repo "docs" "GhostLine documentation"

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Visit https://github.com/ghostline to verify repositories"
echo "2. Invite team members to the organization"
echo "3. Configure organization settings (2FA, permissions, etc.)"
echo "4. Begin Phase 1: Open-Source Capability Scan" 