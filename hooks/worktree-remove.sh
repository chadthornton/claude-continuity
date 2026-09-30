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

. "$(dirname "$0")/../lib/continuity-commits.sh" || exit 0
SAVE="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}/skills/wrap-up/continuity-save"

dirty=$(git status --porcelain -- .continuity "$CC_EXCL" "$CC_AWAYX")
if [ -n "$dirty" ]; then
  echo "Blocked: $WT has uncommitted .continuity/ changes that would be lost. Run /wrap-up (or $SAVE) there first." >&2
  exit 2
fi

grep -Eq '^[[:space:]]*push_to_default_branch:[[:space:]]*true' .continuity/feature-status.yml 2>/dev/null || exit 0
D_REF=$(cc_default_ref) || exit 0
c=$(cc_pending "$D_REF" "$D_REF..HEAD" | head -1)
if [ -n "$c" ]; then
  echo "Blocked: $WT has continuity commit ${c:0:7} not on $D_REF. Run $SAVE there first (a CONFLICT result needs a hand merge)." >&2
  exit 2
fi
exit 0
