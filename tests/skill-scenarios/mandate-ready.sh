#!/bin/bash
# Fixture for the wrap-up mandate. Built on relay-ready.sh (session just
# finished step 2 of widgets; steps 3-4 concrete; step 5 gated), with variants:
#   mandate-ready.sh <dir>            spawner present (fake agent-spawn in <dir>/bin)
#   mandate-ready.sh <dir> nospawn    no agent-spawn anywhere on the test PATH
#   mandate-ready.sh <dir> vague      steps 3-4 are vague ("polish the UI")
#   mandate-ready.sh <dir> gated      step 3 is gated on a decision
# Test PATH to use: <dir>/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root="$1"; variant="${2:-}"
bash "$here/relay-ready.sh" "$root" >/dev/null
[ "$variant" = nospawn ] && rm -f "$root/bin/agent-spawn"
cd "$root/work"
case "$variant" in
  vague) python3 - <<'PY'
p='.continuity/feature-status.yml'; s=open(p).read()
s=s.replace('"Add scripts/verify-widgets.sh comparing row counts src vs db"','"Polish the importer"')
s=s.replace('"Wire both scripts into ops/run-import.sh"','"Clean things up"')
open(p,'w').write(s)
PY
  ;;
  gated) python3 - <<'PY'
p='.continuity/feature-status.yml'; s=open(p).read()
s=s.replace('"Add scripts/verify-widgets.sh comparing row counts src vs db", done: false }','"Add scripts/verify-widgets.sh comparing row counts src vs db", done: false, gate: "decision: row count or checksum?" }')
open(p,'w').write(s)
PY
  ;;
esac
if [ -n "$(git status --porcelain)" ]; then git commit -qam "fixture: $variant"; git push -q origin HEAD:main; fi
echo "checkout: $root/work"
