#!/bin/bash

# Script to add creation timestamps to markdown filenames in all 5 GhostLine repositories
# Format: original_name_YYYY-MM-DD.md

# Get current date for files without existing timestamps
CURRENT_DATE=$(date "+%Y-%m-%d")

echo "Adding creation timestamps to markdown filenames in GhostLine repositories..."
echo "Date format: YYYY-MM-DD"
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
RENAMED_FILES=0

# Function to add timestamp to filename
add_timestamp_to_filename() {
    local file="$1"
    local dir=$(dirname "$file")
    local basename=$(basename "$file" .md)
    
    # Check if filename already has a date pattern (YYYY-MM-DD)
    if [[ "$basename" =~ [0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo "  [SKIP] $file - already has timestamp"
        ((TOTAL_FILES++))
    else
        # Create new filename with timestamp
        local new_name="${dir}/${basename}_${CURRENT_DATE}.md"
        
        # Check if target file already exists
        if [ -f "$new_name" ]; then
            echo "  [ERROR] Cannot rename $file - $new_name already exists"
            ((TOTAL_FILES++))
        else
            # Rename the file
            mv "$file" "$new_name"
            echo "  [RENAMED] $file -> $new_name"
            ((RENAMED_FILES++))
            ((TOTAL_FILES++))
        fi
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
            add_timestamp_to_filename "$file"
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
echo "  Files renamed: $RENAMED_FILES"
echo "  Date used: $CURRENT_DATE"
echo ""
echo "Note: Files already containing timestamps were skipped."
echo "      You can manually adjust dates for specific files if needed." 