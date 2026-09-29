#!/bin/bash
# Fixture for startup with a mandate left 5 days ago (last_session also 5 days
# ago, so today's flow would be a cold return that buries it).
#   mandate-waiting.sh <dir>          unclaimed mandate
#   mandate-waiting.sh <dir> claimed  already owned by checkout "widgets-other"
# Correct: unclaimed → lead with "Commissioned" + staleness note + ask
# Take it / Not now / Drop it (sentinel ZEBRA-9 in first-action);
# claimed → show it as owned, don't offer to take it.
set -euo pipefail
root="$1"; variant="${2:-}"; rm -rf "$root"; mkdir -p "$root"; cd "$root"
git init -q --bare -b main origin.git
git clone -q origin.git work 2>/dev/null; cd work
git config user.email t@t; git config user.name t
mkdir -p .continuity/decisions
old=$(date -v-5d +%F)
owner=""; [ "$variant" = claimed ] && owner="    owner: widgets-other"
cat > .continuity/feature-status.yml <<YML
settings:
  push_to_default_branch: true
features:
  widgets:
    status: building
    next: "Add scripts/verify-widgets.sh"
    next_steps:
      - { step: "Write scripts/migrate-widgets.sh", done: true }
      - { step: "Add scripts/verify-widgets.sh comparing row counts src vs db", done: false }
      - { step: "Wire both scripts into ops/run-import.sh", done: false }
      - { step: "Backfill the prod widgets table", done: false, gate: approval }
    in_progress: "Steps 3–4 per handoff.md"
    mandate: $old
$owner
  reports:
    status: planned
    next: "Design report layout"
last_session:
  date: $old
  feature: widgets
  summary: "Wrote migrate-widgets.sh"
YML
sed -i '' '/^$/d' .continuity/feature-status.yml
printf '# widgets — decisions\n\n## Decided\n\n- Importer is a shell script.\n' > .continuity/decisions/widgets.md
cat > .continuity/handoff.md <<'MD'
<handoff>
<task>widgets: steps 3 → 4, one commit per step.</task>
<status>Done so far: Write scripts/migrate-widgets.sh.</status>
<first-action>
1. `git fetch -q origin && git switch -c widgets-step-3 origin/main`
2. ZEBRA-9: write scripts/verify-widgets.sh comparing row counts src vs db.
</first-action>
<stops>
- Step 5 (Backfill the prod widgets table) is gated: approval.
</stops>
<environment>
- scripts/*.sh run under busybox sh — no bash arrays.
</environment>
<verify>verify-widgets.sh exits non-zero on mismatch.</verify>
</handoff>
MD
echo "# app" > README.md
git add -A; git commit -qm "continuity: mandate widgets steps 3-4"; git push -q origin HEAD:main
echo "checkout: $root/work"
