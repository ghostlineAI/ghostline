#!/bin/bash

# Script to add ACTUAL Git creation timestamps to markdown filenames
# Uses git log to find when each file was first added to the repository

echo "Adding Git-based creation timestamps to markdown filenames..."
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
ERRORS=0

# Function to get file's first commit date from Git
get_git_creation_date() {
    local file="$1"
    local repo_dir="$2"
    
    # Get relative path within the repository
    local rel_path="${file#$repo_dir/}"
    
    # Use git log to find when file was first added
    local creation_date=$(cd "$repo_dir" && git log --format="%ad" --date=short --diff-filter=A --follow -- "$rel_path" 2>/dev/null | tail -1)
    
    if [ -z "$creation_date" ]; then
        # If no git history, use file modification date as fallback
        if [[ "$OSTYPE" == "darwin"* ]]; then
            local timestamp=$(stat -f "%m" "$file")
            date -r "$timestamp" "+%Y-%m-%d"
        else
            date -r "$file" "+%Y-%m-%d"
        fi
    else
        echo "$creation_date"
    fi
}

# Function to add timestamp to filename
add_timestamp_to_filename() {
    local file="$1"
    local repo_dir="$2"
    local dir=$(dirname "$file")
    local basename=$(basename "$file" .md)
    
    # Check if filename already has a date pattern (YYYY-MM-DD)
    if [[ "$basename" =~ [0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo "  [SKIP] $file - already has timestamp"
        ((TOTAL_FILES++))
    else
        # Get the Git creation date
        local creation_date=$(get_git_creation_date "$file" "$repo_dir")
        
        if [ -z "$creation_date" ]; then
            echo "  [ERROR] Could not determine date for $file"
            ((ERRORS++))
            ((TOTAL_FILES++))
        else
            # Create new filename with timestamp
            local new_name="${dir}/${basename}_${creation_date}.md"
            
            # Check if target file already exists
            if [ -f "$new_name" ]; then
                echo "  [ERROR] Cannot rename $file - $new_name already exists"
                ((ERRORS++))
                ((TOTAL_FILES++))
            else
                # Rename the file
                mv "$file" "$new_name"
                echo "  [RENAMED] $file -> $new_name (Git date: $creation_date)"
                ((RENAMED_FILES++))
                ((TOTAL_FILES++))
            fi
        fi
    fi
}

# First, let's revert any existing timestamps to get clean filenames
echo "First, reverting any existing timestamps..."
echo "------------------------"
for repo in "${REPOS[@]}"; do
    if [ -d "$repo" ]; then
        while IFS= read -r -d '' file; do
            filename=$(basename "$file")
            if [[ "$filename" =~ ^(.+)_[0-9]{4}-[0-9]{2}-[0-9]{2}\.md$ ]]; then
                dir=$(dirname "$file")
                original_name="${BASH_REMATCH[1]}.md"
                new_path="${dir}/${original_name}"
                if [ ! -f "$new_path" ]; then
                    mv "$file" "$new_path"
                    echo "  [REVERTED] $file -> $new_path"
                fi
            fi
        done < <(find "$repo" -name "*.md" -type f -print0)
    fi
done

echo ""
echo "Now adding Git-based timestamps..."
echo "================================"

# Process each repository
for repo in "${REPOS[@]}"; do
    if [ -d "$repo" ]; then
        echo ""
        echo "Processing repository: $repo"
        echo "------------------------"
        
        # Find all markdown files in the repository
        while IFS= read -r -d '' file; do
            add_timestamp_to_filename "$file" "$repo"
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
echo "  Errors: $ERRORS"
echo ""
echo "Note: Dates are based on actual Git history (when files were first added)."
echo "      Files without Git history use modification date as fallback." 