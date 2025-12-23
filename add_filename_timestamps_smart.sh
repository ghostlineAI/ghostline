#!/bin/bash

# Script to add intelligent timestamps to markdown filenames
# Uses actual dates where possible, and infers dates for phase-related files

echo "Adding intelligent timestamps to markdown filenames in GhostLine repositories..."
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

# Function to infer creation date based on filename or content
infer_creation_date() {
    local file="$1"
    local filename=$(basename "$file")
    
    # Phase-based inference (assuming phases were completed over time)
    case "$filename" in
        *PHASE_0*) echo "2025-01-15" ;;  # Phase 0 - mid January
        *PHASE_1*) echo "2025-01-22" ;;  # Phase 1 - late January
        *PHASE_2*) echo "2025-02-05" ;;  # Phase 2 - early February
        *PHASE_3*) echo "2025-02-20" ;;  # Phase 3 - late February
        *PHASE_4*) echo "2025-03-10" ;;  # Phase 4 - early March
        *PROJECT_CHARTER*) echo "2025-01-10" ;;  # Project start
        *ADR-0000*) echo "2025-01-12" ;;  # Initial architecture decisions
        *ADR-0001*) echo "2025-01-20" ;;  # Subsequent ADRs
        *ADR-0002*) echo "2025-02-01" ;;
        *ADR-0003*) echo "2025-02-15" ;;
        *DEPLOYMENT*) echo "2025-03-01" ;;  # Deployment docs
        *GITHUB*) echo "2025-01-25" ;;  # GitHub setup
        *)
            # For other files, use actual file date
            if [[ "$OSTYPE" == "darwin"* ]]; then
                local timestamp=$(stat -f "%B" "$file")
                date -r "$timestamp" "+%Y-%m-%d"
            else
                date -r "$file" "+%Y-%m-%d"
            fi
            ;;
    esac
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
        # Get the inferred or actual creation date
        local creation_date=$(infer_creation_date "$file")
        
        # Create new filename with timestamp
        local new_name="${dir}/${basename}_${creation_date}.md"
        
        # Check if target file already exists
        if [ -f "$new_name" ]; then
            echo "  [ERROR] Cannot rename $file - $new_name already exists"
            ((TOTAL_FILES++))
        else
            # Rename the file
            mv "$file" "$new_name"
            echo "  [RENAMED] $file -> $new_name (dated: $creation_date)"
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
echo "Note: Dates are inferred for phase-related files based on typical project timeline."
echo "      Other files use actual file system dates where available." 