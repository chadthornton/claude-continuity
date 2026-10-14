#!/bin/bash
# PostToolUse: tell the main agent, once per climb, that it has used 60% of its
# context window and should hand off. An agent cannot see its own usage, so
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
case "$PCT" in ''|*[!0-9]*) PCT=60 ;; esac

# A subagent runs under its parent's session id with a fresh context of its
# own; its tool calls carry agent_id, the main agent's don't.
IFS=$'\t' read -r SESSION AGENT CWD < <(echo "$INPUT" | jq -r '[.session_id // "", .agent_id // "", .cwd // ""] | map(if . == "" then "-" else . end) | @tsv' 2>/dev/null)
case "$SESSION" in ''|-|*[!A-Za-z0-9_-]*) exit 0 ;; esac
[ "$AGENT" = "-" ] || exit 0
[ -f "$DIR/$SESSION.json" ] || exit 0

read -r USED SIZE < <(jq -r '[.used, .size] | map(tonumber | floor) | select(length == 2) | @tsv' "$DIR/$SESSION.json" 2>/dev/null)
case "$USED$SIZE" in ''|*[!0-9]*) exit 0 ;; esac
[ "$SIZE" -gt 0 ] || exit 0
NOW=$((USED * 100 / SIZE))
if [ "$NOW" -lt "$PCT" ]; then
  # Far enough below to mean a compaction, not turn-to-turn wobble: arm again.
  [ "$NOW" -ge $((PCT / 2)) ] || rm -f "$DIR/$SESSION.told"
  exit 0
fi
[ ! -e "$DIR/$SESSION.told" ] || exit 0

# The notice sends the agent to wrap-up, which needs a board. The session may
# have cd'd below the project root.
board=""
for d in "$CLAUDE_PROJECT_DIR" "$CWD" "$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null)"; do
  [ -n "$d" ] && [ -d "$d/.continuity" ] && board=1 && break
done
[ -n "$board" ] || exit 0

# noclobber makes this the test-and-set: of several hooks run by one turn's
# tool calls, one creates the file and speaks.
( set -C; : > "$DIR/$SESSION.told" ) 2>/dev/null || exit 0
jq -n --arg ctx "CONTEXT HANDOFF: this session has used $NOW% of its context window ($USED of $SIZE tokens). Finish, commit and push the task in hand, then run the wrap-up skill and follow its Context handoff path. Don't start another task in this session." \
  '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}}'
exit 0
