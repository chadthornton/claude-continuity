#!/bin/bash
# Fixture for /away: a session is midway through feature `importer` step 2 with an
# uncommitted edit. A fake `claude` in <dir>/bin prints the real launch lines and
# logs its args to <dir>/claude.log. CONVERSATION.md is the session's transcript
# summary the scenario agent treats as "the conversation so far".
# Usage: away-midtask.sh <dir>   → checkout at <dir>/work, PATH prefix <dir>/bin
#   Run /away with AWAY_CLAUDE=<dir>/bin/claude AWAY_ALLOW_ANY_ORIGIN=1.
set -euo pipefail
root="$1"; rm -rf "$root"; mkdir -p "$root/bin"; cd "$root"
cat > bin/claude <<'SH'
#!/bin/bash
printf '%s\n' "$*" >> "$(dirname "$0")/../claude.log"
printf 'Created cloud session: Importer\nView: https://claude.ai/code/session_01SCENARIO?from=cli&m=0\nResume with: claude --teleport session_01SCENARIO\n'
SH
chmod +x bin/claude
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
    next: Parse the CSV header row
    next_steps:
      - { step: "Add scripts/import.py reading data/widgets.csv", done: true }
      - { step: "Parse the header row and map columns to Widget fields", done: false }
      - { step: "Write rows to db/widgets.sqlite in one transaction", done: false }
in_progress: "importer step 2: header mapping"
YML
printf '# importer\n\n## Decided\n\n## Open\n' > .continuity/decisions/importer.md
printf 'import csv\n\ndef load(path):\n    with open(path) as f:\n        return list(csv.reader(f))\n' > scripts/import.py
git add -A; git commit -qm "importer step 1"; git push -q origin HEAD:main
git remote set-head origin main >/dev/null
git switch -q -c importer
printf 'import csv\n\nCOLUMNS = {"id": "widget_id", "name": "title"}  # half-done: price column pending\n\ndef load(path):\n    with open(path) as f:\n        return list(csv.reader(f))\n' > scripts/import.py
cat > "$root/CONVERSATION.md" <<'MD'
User and Claude are mid-way through step 2 of `importer`.
- Decided: map columns with a dict in scripts/import.py (COLUMNS), because the CSV header order changes between exports.
- Decided: `price` arrives as a string like "$4.50"; parse it with Decimal, not float, to avoid rounding in totals.
- In flight: Claude just added COLUMNS with id and name; `price` is next, then `qty`.
- Not yet run: `python3 scripts/import.py data/widgets.csv` (data/widgets.csv is not in git; it lives on the user's laptop).
The user says: "I need to close my laptop, send this to the cloud."
MD
echo "checkout: $root/work"
