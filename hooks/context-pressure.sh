#!/bin/bash
# PostToolUse: tell the main agent, once per session, that it has used 60% of
# its context window and should hand off. An agent cannot see its own usage, so
# without this it either guesses ("this session has run long") or runs on until
# compaction.
#
# A hook is not given context figures; only a status line command is. So the
# status line writes {"used": <tokens>, "size": <window>} to
# $CONTINUITY_CONTEXT_DIR/<session_id>.json and this hook reads it. With no
# file, or no window size, it stays silent rather than assume a window.

INPUT=$(cat)
DIR="${CONTINUITY_CONTEXT_DIR:-$HOME/.claude/state/continuity-context}"
PCT="${CONTINUITY_HANDOFF_PCT:-60}"

SESSION=$(echo "$INPUT" | jq -r '.session_id // empty')
case "$SESSION" in ''|*[!A-Za-z0-9_-]*) exit 0 ;; esac
# A subagent runs under its parent's session id with a fresh context of its own.
[ -z "$(echo "$INPUT" | jq -r '.agent_id // empty')" ] || exit 0
[ -f "$DIR/$SESSION.json" ] || exit 0
[ ! -e "$DIR/$SESSION.told" ] || exit 0
# The notice sends the agent to wrap-up, which needs a board.
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')
[ -d "$CWD/.continuity" ] || exit 0

read -r USED SIZE < <(jq -r '[.used, .size] | map(numbers | floor) | select(length == 2) | @tsv' "$DIR/$SESSION.json" 2>/dev/null)
case "$USED$SIZE" in ''|*[!0-9]*) exit 0 ;; esac
[ "$SIZE" -gt 0 ] || exit 0
NOW=$((USED * 100 / SIZE))
[ "$NOW" -ge "$PCT" ] || exit 0

: > "$DIR/$SESSION.told"
jq -n --arg ctx "CONTEXT HANDOFF: this session has used $NOW% of its context window ($USED of $SIZE tokens). Finish and commit the task in hand, then run the wrap-up skill: it relays the remaining ungated steps to a new agent. Don't start another task in this session." \
  '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}}'
exit 0
