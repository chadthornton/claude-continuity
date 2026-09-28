#!/bin/bash
# Fixture: a checkout cut BEFORE another session landed in_progress + handoff.md
# on origin. Correct startup behavior: fast-resume from origin's handoff and
# surface its <first-action> (sentinel ZEBRA-7) ONLY when this checkout is the
# owner (named widgets-2); any other checkout must not resume the chain.
# Usage: stale-handoff.sh <dir> [checkout-name]   (default: stale)
set -euo pipefail
root="$1"; name="${2:-stale}"; rm -rf "$root"; mkdir -p "$root"; cd "$root"
git init -q --bare -b main origin.git
git clone -q origin.git author 2>/dev/null; cd author
git config user.email t@t; git config user.name t
mkdir -p .continuity/decisions
today=$(date +%F)
cat > .continuity/feature-status.yml <<YML
features:
  widgets:
    status: building
    next: "Build the widget importer"
    next_steps:
      - { step: "Scaffold importer", done: true }
      - { step: "Write migrate-widgets.sh", done: false }
      - { step: "Backfill widgets table", done: false, gate: approval }
    in_progress: null
  reports:
    status: planned
    next: "Design report layout"
last_session:
  date: $today
  feature: widgets
  summary: "Scaffolded the importer"
YML
printf '# widgets — decisions\n\n## Decided\n\n- Importer is a shell script — no runtime deps on the box.\n' > .continuity/decisions/widgets.md
echo "# app" > README.md
git add -A; git commit -qm init; git push -q origin HEAD:main
cd ..; git clone -q origin.git "$name" 2>/dev/null   # the stale checkout is cut here
cd author
python3 - <<'PY'
p='.continuity/feature-status.yml'; s=open(p).read()
s=s.replace('    in_progress: null\n  reports','    in_progress: "Steps 2-3 per handoff.md"\n    owner: widgets-2\n  reports',1)
open(p,'w').write(s)
PY
cat > .continuity/handoff.md <<'MD'
<task>Widgets steps 2 -> 3, one commit per step.</task>
<first-action>ZEBRA-7: write scripts/migrate-widgets.sh reading WIDGETS_SRC; dry-run first.</first-action>
<stops>- Backfill touches prod data: needs Chad's ship-it.</stops>
MD
git add -A; git commit -qm "continuity: relay widgets to Agent B"; git push -q origin HEAD:main
echo "checkout: $root/$name"
