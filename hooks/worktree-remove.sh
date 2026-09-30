#!/bin/bash
# WorktreeRemove: refuse to delete a worktree whose .continuity/ edits would be
# lost — uncommitted changes, or (when the project opted into
# push_to_default_branch) continuity-only commits that never reached
# origin/<default>. Any nonzero exit blocks the removal; stderr says why.

INPUT=$(cat)
WT=$(echo "$INPUT" | jq -r '.worktree_path // .cwd')
[ -n "$WT" ] && [ -d "$WT/.continuity" ] || exit 0
cd "$WT" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

SAVE="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}/skills/wrap-up/continuity-save"

# Needs nothing but git, so it runs even if the shared lib can't load.
dirty=$(git status --porcelain -- .continuity ':(exclude).continuity/last-activity.txt' ':(exclude).continuity/away.md')
if [ -n "$dirty" ]; then
  echo "Blocked: $WT has uncommitted .continuity/ changes that would be lost. Run /wrap-up (or $SAVE) there first." >&2
  exit 2
fi

. "$(dirname "$0")/../lib/continuity-commits.sh" || exit 0

grep -Eq '^[[:space:]]*push_to_default_branch:[[:space:]]*true' .continuity/feature-status.yml 2>/dev/null || exit 0
D_REF=$(cc_default_ref) || exit 0
pending=$(cc_pending "$D_REF" "$D_REF..HEAD")
if [ -n "$pending" ]; then
  n=$(printf '%s\n' "$pending" | wc -l | tr -d ' '); c=$(printf '%s\n' "$pending" | tail -1)
  echo "Blocked: $WT has $n continuity commit(s) not on $D_REF (newest ${c:0:7}). Run $SAVE there first (a CONFLICT result needs a hand merge)." >&2
  exit 2
fi
exit 0
