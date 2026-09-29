#!/bin/bash
# SessionStart: (a) one-line notice if the project has no .continuity/ directory;
# (b) if the project opted into push_to_default_branch, flag continuity commits
# from the last 14 days that sit on local branches but never reached
# origin/<default> — work that would vanish if its worktree/branch is deleted,
# and that /startup's board (read from this checkout) cannot see.
# Local refs only (worktrees share them) — no fetch, so it fits the timeout.

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')

emit() {
  jq -n --arg ctx "$1" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
}

if [ ! -d "$CWD/.continuity" ]; then
  emit "This project has no .continuity/ directory. Run /continuity-init to enable cross-session continuity tracking (feature status, decisions, open questions)."
  exit 0
fi

cd "$CWD" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
grep -Eq '^[[:space:]]*push_to_default_branch:[[:space:]]*true' .continuity/feature-status.yml 2>/dev/null || exit 0
D_REF=$(git symbolic-ref --short -q refs/remotes/origin/HEAD) || exit 0

EXCL=':(exclude).continuity/last-activity.txt'
AWAYX=':(exclude).continuity/away.md'
landed=$(git log "$D_REF" -n 500 --format='%(trailers:key=Continuity-Source,valueonly)' | grep -v '^$')
lines=""
count=0
for c in $(git rev-list --since=14.days --branches --not "$D_REF" -- .continuity "$EXCL" "$AWAYX"); do
  printf '%s\n' "$landed" | grep -qx "$c" && continue
  # Commits mixing code and .continuity land when their branch merges; only
  # continuity-only commits are the ones continuity-save exists to land.
  files=$(git diff-tree --no-commit-id --name-only -r "$c")
  printf '%s\n' "$files" | grep -qv '^\.continuity/' && continue
  printf '%s\n' "$files" | grep -qx '\.continuity/away\.md' && continue
  count=$((count + 1))
  if [ $count -le 3 ]; then
    br=$(git branch --contains "$c" --format='%(refname:short)' | head -1)
    lines="$lines
  - ${c:0:7} on ${br:-?}: $(git log -1 --format=%s "$c")"
  fi
done

if [ $count -gt 0 ]; then
  emit "CONTINUITY NOT LANDED: $count continuity commit(s) from the last 14 days are on local branches but not on $D_REF, so the /startup board does not include them:$lines
Land them by running the wrap-up skill's continuity-save from that branch's checkout (it re-applies only .continuity/ onto $D_REF). Mention this to the user if they run /startup."
fi
exit 0
