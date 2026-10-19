#!/bin/bash
# Fixture: the session hit a problem an existing gotcha already warned about.
#   relearned-gotcha.sh <dir>     checkout at <dir>/work
# Story to give the agent: "you wrote scripts/migrate.sh with a bash array; it
# failed on the box (busybox sh has no arrays); you rewrote it with a plain loop
# and it works. Step one of `importer` is done; clean stop."
# Correct: the busybox gotcha ends with "(re-learned <today>)" and the gotchas
# list does not grow. Wrong: a second busybox gotcha, or only a blind spot.
set -euo pipefail
root="$1"; rm -rf "$root"; mkdir -p "$root"; cd "$root"
git init -q --bare -b main origin.git
git clone -q origin.git work 2>/dev/null; cd work
git config user.email t@t; git config user.name t
mkdir -p .continuity/decisions scripts
cat > .continuity/feature-status.yml <<'YML'
settings:
  push_to_default_branch: true
features:
  importer:
    status: building
    next: "Write scripts/migrate.sh"
    next_steps:
      - { step: "Write scripts/migrate.sh", done: false }
      - { step: "Verify row counts", done: false }
last_session:
  date: 2026-10-10
  feature: importer
  summary: "Planned the importer"
gotchas:
  - "scripts/*.sh run on the box under busybox sh: no bash arrays, no [[ ]]."
  - "The docs site builds with Hugo 0.121 exactly."
YML
printf '#!/bin/sh\nfor t in a b; do echo "$t"; done\n' > scripts/migrate.sh
git add -A; git commit -qm init; git push -q origin HEAD:main
echo "checkout: $root/work"
