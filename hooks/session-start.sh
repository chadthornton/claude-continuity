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
. "$(dirname "$0")/../lib/continuity-commits.sh" || exit 0
D_REF=$(cc_default_ref) || exit 0
lines=""
count=0
# Only pending (continuity-only, unlanded) commits are what continuity-save
# exists to land; mixed ones land when their branch merges.
for c in $(cc_pending "$D_REF" --since=14.days --branches --not "$D_REF"); do
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
