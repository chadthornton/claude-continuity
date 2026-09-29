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

EXCL=':(exclude).continuity/last-activity.txt'
AWAYX=':(exclude).continuity/away.md'
SAVE="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}/skills/wrap-up/continuity-save"

dirty=$(git status --porcelain -- .continuity "$EXCL" "$AWAYX")
if [ -n "$dirty" ]; then
  echo "Blocked: $WT has uncommitted .continuity/ changes that would be lost. Run /wrap-up (or $SAVE) there first." >&2
  exit 2
fi

grep -Eq '^[[:space:]]*push_to_default_branch:[[:space:]]*true' .continuity/feature-status.yml 2>/dev/null || exit 0
D_REF=$(git symbolic-ref --short -q refs/remotes/origin/HEAD) || exit 0
landed=$(git log "$D_REF" -n 500 --format='%(trailers:key=Continuity-Source,valueonly)' | grep -v '^$')
for c in $(git rev-list "$D_REF..HEAD" -- .continuity "$EXCL" "$AWAYX"); do
  printf '%s\n' "$landed" | grep -qx "$c" && continue
  files=$(git diff-tree --no-commit-id --name-only -r "$c")
  printf '%s\n' "$files" | grep -qv '^\.continuity/' && continue
  printf '%s\n' "$files" | grep -qx '\.continuity/away\.md' && continue
  echo "Blocked: $WT has continuity commit ${c:0:7} not on $D_REF. Run $SAVE there first (a CONFLICT result needs a hand merge)." >&2
  exit 2
done
exit 0
