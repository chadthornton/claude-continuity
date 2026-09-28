#!/bin/bash
# Fixture: a session just finished step 2 of 5 on `widgets`; steps 3-4 are clear,
# step 5 is gated. Wrap-up should offer a relay; on yes it writes a relay
# handoff, sets owner + in_progress, saves, and spawns. A fake agent-spawn in
# <dir>/bin logs its args to <dir>/spawn.log instead of opening a session.
# gotchas: one touches the chain's files (scripts/), one doesn't (docs site).
# Usage: relay-ready.sh <dir>   → checkout at <dir>/work, PATH prefix <dir>/bin
set -euo pipefail
root="$1"; rm -rf "$root"; mkdir -p "$root/bin"; cd "$root"
cat > bin/agent-spawn <<'SH'
#!/bin/sh
echo "agent-spawn $*" >> "$(dirname "$0")/../spawn.log"; echo "✓ spawned agent '$1' (fake)"
SH
chmod +x bin/agent-spawn
git init -q --bare -b main origin.git
git clone -q origin.git work 2>/dev/null; cd work
git config user.email t@t; git config user.name t
mkdir -p .continuity/decisions scripts
today=$(date +%F)
cat > .continuity/feature-status.yml <<YML
settings:
  push_to_default_branch: true
features:
  widgets:
    status: building
    next: "Write migrate-widgets.sh"
    next_steps:
      - { step: "Scaffold importer", done: true }
      - { step: "Write scripts/migrate-widgets.sh (reads WIDGETS_SRC, --dry-run flag)", done: false }
      - { step: "Add scripts/verify-widgets.sh comparing row counts src vs db", done: false }
      - { step: "Wire both scripts into ops/run-import.sh", done: false }
      - { step: "Backfill the prod widgets table", done: false, gate: approval }
    in_progress: null
  reports:
    status: planned
    next: "Design report layout"
last_session:
  date: 2026-09-20
  feature: widgets
  summary: "Scaffolded the importer"
gotchas:
  - "scripts/*.sh run on the box under busybox sh — no bash arrays, no [[ ]]."
  - "The docs site builds with Hugo 0.121 exactly; newer versions break the theme."
YML
printf '# widgets — decisions\n\n## Decided\n\n- Importer is a shell script — no runtime deps on the box.\n' > .continuity/decisions/widgets.md
echo "# app" > README.md
git add -A; git commit -qm init; git push -q origin HEAD:main
printf '#!/bin/sh\n# migrate widgets from $WIDGETS_SRC\n[ "$1" = "--dry-run" ] && echo dry && exit 0\necho migrating\n' > scripts/migrate-widgets.sh
git add -A; git commit -qm "feat: migrate-widgets.sh with --dry-run"; git push -q origin HEAD:main
echo "checkout: $root/work   PATH prefix: $root/bin"
