#!/bin/bash
# Fixture: a board review's round is confirmed on the page and the user said "go".
# The page's store has been read into <dir>/w/ (seed.json, overrides.json,
# round.json, audit.json). The round holds: continue `pages`, a starter
# ("Morning-of chooser", think), a chore group, a merge of `discovery` into
# `lists`, and a decision on `lists`, which an agent (lists-4) is already on.
# The user's correction: discovery's size is L. Page notes: discovery's (the review read it, unchanged) and pages'
# (written after the review, beside a size correction M). The page store isn't reachable: each write_db the
# skill would make goes as one JSON line ({op, collection, doc_id, data, if_version}) to <dir>/db.log; every
# override was read at version 1 (<dir>/w/versions.json); tell the agent any read it makes now answers version 2
# (the user is still on the page), so only writes pinned to step 1's versions pass the check. lists-4 matches lists by name only. The user answers yes to every
# board change. A fake agent-spawn in <dir>/bin logs to <dir>/spawn.log.
# A worktree pages-3 ended earlier on `pages`: it is listed, not running.
# --applied: the round was already sent (applied_at set): nothing may start.
# Check the result with review-go-check.sh <dir> [--applied].
# Usage: review-go.sh <dir> [--applied]   → checkout at <dir>/work, PATH prefix <dir>/bin
set -euo pipefail
root="$1"; applied="${2:-}"; rm -rf "$root"; mkdir -p "$root/bin" "$root/w"; cd "$root"
cat > bin/agent-spawn <<'SH'
#!/bin/sh
d="$(dirname "$0")/.."
echo "agent-spawn $*" >> "$d/spawn.log"
echo "✓ Agent '$1' started."
echo "  Open it: Muxy sidebar → work → $1 → right-click → Existing Terminals (⌥⌘T)"
SH
chmod +x bin/agent-spawn
# The audit asks wt:status (through zsh) what is running. This stand-in answers
# for the fixture: lists-4, idle, on branch lists-4-pr-2.
cat > bin/zsh <<'SH'
#!/bin/sh
case "$*" in *wt:status*)
  printf 'repo\tpath\tname\tverdict\tstate\tuncommitted\tunpushed\tbranch\tlock_pid\tactivity\n'
  printf '/r\t/r/.claude/worktrees/lists-4\tlists-4\trunning\trunning\t0\t0\tlists-4-pr-2\t\tidle (replied)\n'
  printf '/r\t/r/.claude/worktrees/pages-3\tpages-3\tsafe\tended\t0\t0\tpages-3\t\tidle (replied)\n' ;;
*) exec /bin/zsh "$@" ;; esac
SH
chmod +x bin/zsh
git init -q --bare -b main origin.git
git clone -q origin.git work 2>/dev/null; cd work
git config user.email t@t; git config user.name t
mkdir -p .continuity/decisions
cat > .continuity/feature-status.yml <<'YML'
settings:
  push_to_default_branch: true
features:
  lists:
    status: building
    size: L
    next: "Ship lists build 3"
    next_steps:
      - { step: "Lists build 3: whole list onto a trip", gate: "decision: one-time copy or living link?", done: false }
  discovery:
    status: parked
    size: M
    inferred: [size]
    next_steps:
      - { step: "Queue screen for suggested places", done: false }
      - { step: "Old Airtable review mode", done: true }
  pages:
    status: building
    size: L
    next: "Trip page loads with one lookup"
    next_steps:
      - { step: "Trip page loads with one lookup", done: false }
YML
printf '# discovery — decisions\n\n## Decided\n\n- Suggestions are kept or dropped in one tap — the queue was the bottleneck.\n' > .continuity/decisions/discovery.md
echo "# app" > README.md; echo "code" > app.js
git add -A; git commit -qm init; git push -q origin HEAD:main

gen="2026-10-19T10:00Z"
cat > "$root/w/seed.json" <<JSON
{"project": "work", "mode": "routine", "since": "2026-10-05", "generated": "$gen", "read": "Lists took the window.",
 "board_source": "local", "lanes": {"live": 1, "back": 3, "quiet": 3},
 "areas": [{"name": "Lists", "what": "Where places come from.", "open_question": "When does a list travel?", "initiatives": 2,
            "starters": [{"title": "Morning-of chooser", "aspiration": "Pick a jaunt in a minute.", "size": "M", "first_session": "think", "brief": "Walk a real trip morning with the user and sketch what the screen must show."}]}],
 "initiatives": [
  {"row": "lists", "area": "Lists", "size": "L", "aspiration": null, "judged": ["line", "recent", "progress", "proposal", "suggest"], "running": "lists-4", "running_idle": true,
   "proposal": {"kind": "decision", "title": "Whole list on the trip", "brief": "Settle one-time copy or living link on a preview.", "comes_back": "Straight away."}, "suggest": {"action": "keep", "reason": "Live."}},
  {"row": "discovery", "area": "Lists", "size": "M", "aspiration": null, "judged": ["size", "line", "recent", "progress", "proposal", "suggest"], "running": null, "running_idle": false,
   "proposal": null, "suggest": {"action": "merge", "into": "lists", "reason": "Lists now turns suggestions into a list."}},
  {"row": "pages", "area": null, "size": "L", "aspiration": null, "judged": ["line", "recent", "progress", "proposal", "suggest"], "running": null, "running_idle": false,
   "proposal": {"kind": "continue", "title": "Trip page loads with one lookup", "brief": "Make a trip page load with one lookup instead of two.", "comes_back": "With a PR to look at."}, "suggest": {"action": "keep", "reason": "Live."}}],
 "chore_groups": [{"title": "Guards on adding places", "code_area": "the add-places handler", "why_together": "Same file.", "items": [{"row": "lists", "title": "Refuse an oversized paste", "step": "Cap paste size at 64 KB"}]}],
 "sessions": [{"name": "lists-4", "branch": "lists-4-pr-2", "verdict": "running", "state": "running", "activity": "idle (replied)", "row": "lists", "match": "name"}],
 "notes_read": {"discovery": "Fold this into lists?"}}
JSON
echo '{"discovery": {"size": "L", "notes": "Fold this into lists?", "at": "2026-10-19T11:00:00Z"}, "pages": {"size": "M", "notes": "Ask about caching first", "at": "2026-10-19T11:02:00Z"}}' > "$root/w/overrides.json"
echo '{"discovery": 1, "pages": 1}' > "$root/w/versions.json"
# The audit at review time; lists-4 is running on lists (no wt:status in the fixture, so a fresh audit sees none).
echo '{"review": {"since": "2026-10-05"}, "rows": [{"name": "lists", "gated": [{"step": "Lists build 3: whole list onto a trip", "gate": "decision: one-time copy or living link?"}]}, {"name": "discovery", "gated": []}, {"name": "pages", "gated": []}], "sessions": {"source": "wt", "items": [{"name": "lists-4", "branch": "lists-4-pr-2", "verdict": "running", "state": "running", "activity": "idle (replied)", "running": true, "row": "lists", "match": "name"}, {"name": "pages-3", "branch": "pages-3", "verdict": "safe", "state": "ended", "activity": "idle (replied)", "running": false, "row": "pages", "match": "name"}]}}' > "$root/w/audit.json"
cat > "$root/w/round.json" <<JSON
{"generated": "$gen", "confirmed_at": "2026-10-19T11:05:00Z",$( [ "$applied" = --applied ] && echo ' "applied_at": "2026-10-19T11:30:00Z",' ) "items": [
  {"key": "p:pages", "kind": "continue", "row": "pages", "title": "Trip page loads with one lookup", "brief": "Make a trip page load with one lookup instead of two.", "comes_back": "With a PR to look at."},
  {"key": "s:0:0", "kind": "think", "title": "Start: Morning-of chooser", "label": "Morning-of chooser", "area": "Lists", "size": "M", "aspiration": "Pick a jaunt in a minute.", "brief": "Walk a real trip morning with the user and sketch what the screen must show."},
  {"key": "c:0", "kind": "chores", "title": "Guards on adding places", "brief": "Refuse an oversized paste.", "area": "the add-places handler", "rows": ["lists"]},
  {"key": "b:discovery", "kind": "board", "row": "discovery", "title": "merge into lists", "brief": "Lists now turns suggestions into a list."},
  {"key": "p:lists", "kind": "decision", "row": "lists", "title": "Whole list on the trip", "brief": "Settle one-time copy or living link on a preview.", "comes_back": "Straight away."}]}
JSON
echo "checkout: $root/work   PATH prefix: $root/bin   page data: $root/w"
