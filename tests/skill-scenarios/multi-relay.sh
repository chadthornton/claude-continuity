#!/bin/bash
# Fixture for wrap-up's multi-relay: built on relay-ready.sh (widgets step 2
# just shipped; steps 2-3 concrete, step 4 gated), plus `reports`, which this
# session also advanced: its steps 2-3 are concrete and ungated. Both features
# should get a mandate and their OWN handoff file; relaying both saves once and
# spawns two agents. The fake agent-spawn logs to <dir>/spawn.log.
# Usage: multi-relay.sh <dir>   → checkout at <dir>/work, PATH prefix <dir>/bin
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root="$1"
bash "$here/relay-ready.sh" "$root" >/dev/null
cd "$root/work"
python3 - <<'PY'
p = '.continuity/feature-status.yml'; s = open(p).read()
s = s.replace('''  reports:
    status: planned
    next: "Design report layout"''', '''  reports:
    status: building
    next: "Write reports/weekly.sql"
    next_steps:
      - { step: "Sketch report layout in docs/reports.md", done: true }
      - { step: "Write reports/weekly.sql selecting widget counts per week", done: false }
      - { step: "Add scripts/run-report.sh that runs weekly.sql and writes out/weekly.csv", done: false }
    in_progress: null''')
open(p, 'w').write(s)
PY
mkdir -p docs; printf '# Reports\n\nWeekly: one row per week, widget count.\n' > docs/reports.md
git add -A; git commit -qm "docs: report layout"; git push -q origin HEAD:main
cat > "$root/CONVERSATION.md" <<'MD'
This session did two things:
- widgets: wrote scripts/migrate-widgets.sh with --dry-run (step 2, shipped and pushed).
- reports: sketched the weekly report layout in docs/reports.md (step 1, shipped).
Decided: the weekly report is plain SQL plus a shell runner, because the box has no Python.
The user says: "wrap up". When wrap-up asks whether to continue with new agents, the user picks BOTH widgets and reports.
MD
echo "checkout: $root/work   PATH prefix: $root/bin"
