#!/bin/bash

# GhostLine Push to GitHub Script
# This script pushes all repositories to the ghostlineAI organization

echo "=== Pushing GhostLine Repositories to GitHub ==="
echo ""
echo "Organization: ghostlineAI"
echo "Visibility: Private"
echo ""
echo "You'll need to:"
echo "1. Create each repository manually on GitHub (as private)"
echo "2. Have your GitHub personal access token ready"
echo ""
read -p "Have you created all 5 repositories on GitHub? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Please create these repositories on https://github.com/ghostlineAI:"
    echo "  - web (private)"
    echo "  - api (private)"
    echo "  - agents (private)"
    echo "  - infra (private)"
    echo "  - docs (private)"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Function to push repository
push_repo() {
    local repo_name=$1
    
    echo ""
    echo "=== Pushing $repo_name repository ==="
    
    cd $repo_name
    
    # Add remote
    git remote add origin https://github.com/ghostlineAI/$repo_name.git
    
    # Check if remote was already added
    if [ $? -ne 0 ]; then
        echo "Remote already exists, updating URL..."
        git remote set-url origin https://github.com/ghostlineAI/$repo_name.git
    fi
    
    # Add all files and commit
    git add .
    git commit -m "Initial commit: Phase 0 bootstrap" || echo "Already committed"
    
    # Set main branch
    git branch -M main
    
    # Push to GitHub
    echo "Pushing to GitHub (you may be prompted for credentials)..."
    git push -u origin main
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully pushed $repo_name"
    else
        echo "❌ Failed to push $repo_name"
        echo "   Make sure the repository exists on GitHub and you have the correct credentials"
    fi
    
    cd ..
}

# Push all repositories
push_repo "web"
push_repo "api"
push_repo "agents"
push_repo "infra"
push_repo "docs"

echo ""
echo "=== Push Complete! ==="
echo ""
echo "Next steps:"
echo "1. Visit https://github.com/ghostlineAI to verify all repositories"
echo "2. Configure branch protection rules"
echo "3. Invite team members to the organization"
echo "4. Begin Phase 1: Open-Source Capability Scan"
echo ""
echo "To set up branch protection, you can use these settings for each repo:"
echo "  - Require pull request reviews before merging"
echo "  - Require status checks to pass (markdown-lint)"
echo "  - Include administrators" 