#!/bin/bash
# Writes last-activity.txt on session end.
# Automatic safety net — captures minimal state even if wrap-up skill wasn't run.

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')
CONTINUITY_DIR="$CWD/.continuity"

# Only write if this project has a .continuity directory
if [ ! -d "$CONTINUITY_DIR" ]; then
  exit 0
fi

# Get recent git state
UNCOMMITTED=$(cd "$CWD" && git diff --name-only 2>/dev/null | head -10)
STAGED=$(cd "$CWD" && git diff --cached --name-only 2>/dev/null | head -10)
HAS_CHANGES="false"
if [ -n "$UNCOMMITTED" ] || [ -n "$STAGED" ]; then
  HAS_CHANGES="true"
fi

cat > "$CONTINUITY_DIR/last-activity.txt" << EOF
session_end: $(date -u +%Y-%m-%dT%H:%M:%S)
uncommitted_changes: $HAS_CHANGES
files_touched:
$UNCOMMITTED
$STAGED
EOF
