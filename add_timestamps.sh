#!/bin/bash

# Script to add timestamps to all markdown files in the 5 GhostLine repositories
# Last Updated: 2025-01-28 09:30:00 PDT

# Get current timestamp
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S PDT")

echo "Adding timestamps to all markdown files in GhostLine repositories..."
echo "Timestamp: $TIMESTAMP"
echo "================================"

# Define the 5 repositories
REPOS=(
    "ghostline/web"
    "ghostline/api"
    "ghostline/agents"
    "ghostline/infra"
    "ghostline/docs"
)

# Counter for processed files
TOTAL_FILES=0

# Function to add timestamp to a markdown file
add_timestamp_to_file() {
    local file="$1"
    local repo="$2"
    
    # Check if file already has a timestamp header
    if head -n 5 "$file" | grep -q "Last Updated:"; then
        echo "  [SKIP] $file - already has timestamp"
    else
        # Create temp file with timestamp header
        temp_file=$(mktemp)
        echo "---" > "$temp_file"
        echo "Last Updated: $TIMESTAMP" >> "$temp_file"
        echo "---" >> "$temp_file"
        echo "" >> "$temp_file"
        cat "$file" >> "$temp_file"
        
        # Replace original file
        mv "$temp_file" "$file"
        echo "  [DONE] $file"
        ((TOTAL_FILES++))
    fi
}

# Process each repository
for repo in "${REPOS[@]}"; do
    if [ -d "$repo" ]; then
        echo ""
        echo "Processing repository: $repo"
        echo "------------------------"
        
        # Find all markdown files in the repository
        while IFS= read -r -d '' file; do
            add_timestamp_to_file "$file" "$repo"
        done < <(find "$repo" -name "*.md" -type f -print0)
    else
        echo ""
        echo "[WARNING] Repository not found: $repo"
    fi
done

echo ""
echo "================================"
echo "Summary: Added timestamps to $TOTAL_FILES markdown files"
echo "Timestamp used: $TIMESTAMP" 