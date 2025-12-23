#!/bin/bash

# Script to add ACTUAL creation timestamps to markdown filenames in all 5 GhostLine repositories
# This version uses the file's actual creation date, not today's date

echo "Adding ACTUAL creation timestamps to markdown filenames in GhostLine repositories..."
echo "Using file system creation dates..."
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

# Function to get file creation date
get_file_creation_date() {
    local file="$1"
    
    # On macOS, use GetFileInfo or stat -f "%B"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # Use stat to get birth time (creation time) on macOS
        local timestamp=$(stat -f "%B" "$file")
        # Convert timestamp to YYYY-MM-DD format
        date -r "$timestamp" "+%Y-%m-%d"
    else
        # On Linux, use stat --format=%W (birth time) if available
        # Note: Not all filesystems support birth time on Linux
        local timestamp=$(stat --format=%W "$file" 2>/dev/null)
        if [ "$timestamp" != "-" ] && [ "$timestamp" != "0" ]; then
            date -d "@$timestamp" "+%Y-%m-%d"
        else
            # Fallback to modification time if birth time not available
            date -r "$file" "+%Y-%m-%d"
        fi
    fi
}

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
        # Get the actual creation date of the file
        local creation_date=$(get_file_creation_date "$file")
        
        # Create new filename with actual creation timestamp
        local new_name="${dir}/${basename}_${creation_date}.md"
        
        # Check if target file already exists
        if [ -f "$new_name" ]; then
            echo "  [ERROR] Cannot rename $file - $new_name already exists"
            ((TOTAL_FILES++))
        else
            # Rename the file
            mv "$file" "$new_name"
            echo "  [RENAMED] $file -> $new_name (created: $creation_date)"
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
echo ""
echo "Note: Files now show their ACTUAL creation dates."
echo "      On some systems, creation date may fall back to modification date." 