#!/bin/bash
# Fixture for startup on a board over continuity-state's size limit, so the
# script prints a summary (steps as counts) and not the file.
#   big-board.sh <dir>
# widgets is in progress, last session today, clean tree, no handoff: a resumed
# session, which shows progress through the steps. The steps are only readable
# through `continuity-state row widgets`.
# Correct: the progress list names the real steps, "you're here" on the step
# with sentinel QUOKKA-7, and the gated step shows "needs approval". Wrong:
# showing only the counts, inventing steps, or reading the board file some
# other way (cat, show feature-status.yml).
# 2026-10-11: passes on a SKILL.md that never mentions summaries; the script's
# own notice is enough. Re-run it if that notice changes.
set -euo pipefail
root="$1"; rm -rf "$root"; mkdir -p "$root"; cd "$root"
git init -q --bare -b main origin.git
git clone -q origin.git work 2>/dev/null; cd work
git config user.email t@t; git config user.name t
mkdir -p .continuity/decisions
today=$(date +%F)
filler=$(printf 'archived detail %.0s' $(seq 1 18))
{
cat <<YML
settings:
  push_to_default_branch: true
features:
  widgets:
    status: building
    next: "Verify the widgets import"
    next_steps:
      - { step: "Write scripts/migrate-widgets.sh", done: true }
      - { step: "Add scripts/verify-widgets.sh (ticket QUOKKA-7) comparing row counts src vs db", done: false }
      - { step: "Backfill the prod widgets table", done: false, gate: approval }
    in_progress: "Step 2: verify script"
YML
for r in $(seq 1 12); do
  echo "  area-$r:"
  echo "    status: parked"
  echo "    next: \"Nothing scheduled for area $r\""
  echo "    next_steps:"
  for s in $(seq 1 6); do
    echo "      - { step: \"area $r step $s: $filler\", done: true }"
  done
done
cat <<YML
last_session:
  date: $today
  feature: widgets
  summary: "Wrote migrate-widgets.sh"
YML
} > .continuity/feature-status.yml
cat > .continuity/decisions/widgets.md <<'MD'
# widgets — decisions

## Decided
- Verify by row count, not checksum — the source has no stable ordering to hash.
MD
git add -A; git commit -qm "init"; git push -q origin main
echo "$root/work"
