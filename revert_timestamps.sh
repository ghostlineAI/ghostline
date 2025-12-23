#!/bin/bash

# Script to revert timestamp additions from markdown filenames
# This removes the _YYYY-MM-DD suffix that was incorrectly added

echo "Reverting timestamp additions from markdown filenames..."
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
REVERTED_FILES=0

# Function to remove timestamp from filename
remove_timestamp_from_filename() {
    local file="$1"
    local dir=$(dirname "$file")
    local filename=$(basename "$file")
    
    # Check if filename has the pattern _YYYY-MM-DD.md at the end
    if [[ "$filename" =~ ^(.+)_[0-9]{4}-[0-9]{2}-[0-9]{2}\.md$ ]]; then
        local original_name="${BASH_REMATCH[1]}.md"
        local new_path="${dir}/${original_name}"
        
        # Check if target file already exists
        if [ -f "$new_path" ]; then
            echo "  [ERROR] Cannot revert $file - $new_path already exists"
            ((TOTAL_FILES++))
        else
            # Rename the file back
            mv "$file" "$new_path"
            echo "  [REVERTED] $file -> $new_path"
            ((REVERTED_FILES++))
            ((TOTAL_FILES++))
        fi
    else
        echo "  [SKIP] $file - no timestamp pattern found"
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
            remove_timestamp_from_filename "$file"
        done < <(find "$repo" -name "*.md" -type f -print0)
    else
        echo ""
        echo "[WARNING] Repository not found: $repo"
    fi
done

echo ""
echo "================================"
echo "Summary:"
echo "  Total files processed: $TOTAL_FILES"
echo "  Files reverted: $REVERTED_FILES" 