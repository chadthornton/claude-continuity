#!/bin/bash
# Saves the full transcript before compaction.
# Insurance — if compaction ever triggers accidentally, the full conversation is recoverable.

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')
BACKUP_DIR="$HOME/.claude/transcript-backups"

if [ -z "$TRANSCRIPT" ] || [ "$TRANSCRIPT" = "null" ] || [ ! -f "$TRANSCRIPT" ]; then
  exit 0
fi

mkdir -p "$BACKUP_DIR"
cp "$TRANSCRIPT" "$BACKUP_DIR/$(date +%Y%m%d-%H%M%S).jsonl"

# Keep only last 20 backups to avoid unbounded growth
ls -t "$BACKUP_DIR"/*.jsonl 2>/dev/null | tail -n +21 | xargs rm -f 2>/dev/null

exit 0
