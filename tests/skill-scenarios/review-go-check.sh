#!/bin/bash
# Checks what an agent did with the review-go.sh fixture. Usage: review-go-check.sh <dir>
# Prints PASS/FAIL per expectation; exit 1 when any fails.
set -u
root="$1"; B="$root/work/.continuity/feature-status.yml"; log="$root/spawn.log"; fails=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fails=$((fails + 1)); fi; }
row() { awk -v r="$1" '/^  [a-z0-9-]+:/{on = ($0 == "  " r ":")} on' "$B"; }
today=$(date +%F)
check "last review date set" "grep -q 'last_review: $today' '$B'"
check "your correction applied: discovery or its merge target carries no inferred size for discovery" "! row discovery | grep -q 'inferred: \\[size\\]'"
check "starter added as an exploring initiative" "row morning-of-chooser | grep -q 'status: exploring'"
check "pages owned by a new agent" "row pages | grep -q 'owner: pages-1'"
check "starter owned by a new agent" "row morning-of-chooser | grep -q 'owner: morning-of-chooser-1'"
check "pages handoff written" "test -s '$root/work/.continuity/handoffs/pages.md'"
check "starter handoff says build nothing yet" "grep -qi 'nothing' '$root/work/.continuity/handoffs/morning-of-chooser.md'"
check "pages agent started with /startup" "grep -q 'agent-spawn pages-1.*/startup' '$log'"
check "starter agent started" "grep -q 'agent-spawn morning-of-chooser-1' '$log'"
check "one chore agent started with its brief" "grep -q 'agent-spawn chores-1 --prompt' '$log'"
check "no second agent on lists (lists-4 is on it)" "! grep -q 'agent-spawn lists' '$log'"
check "lists-4 got the decision brief" "grep -qi 'lists-4' '$root/messages.log'"
check "lists now owned by the agent on it" "row lists | grep -q 'owner: lists-4'"
check "discovery merged: row gone" "! grep -q '^  discovery:' '$B'"
check "discovery's open step moved to lists" "row lists | grep -q 'Queue screen for suggested places'"
check "board landed on origin/main" "git -C '$root/work' fetch -q origin && git -C '$root/work' show origin/main:.continuity/feature-status.yml | grep -q 'owner: pages-1'"
check "no code reached origin/main" "test -z \"\$(git -C '$root/work' diff --name-only \$(git -C '$root/work' rev-list --max-parents=0 origin/main) origin/main -- . ':(exclude).continuity')\""
echo; [ "$fails" -eq 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
