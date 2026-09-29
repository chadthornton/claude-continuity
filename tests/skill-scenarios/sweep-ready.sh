#!/bin/bash
# Fixture: a wrap-up where two agent worktrees exist — one finished (clean,
# pushed), one holding uncommitted work. Only one open step, so relay stays out
# of the way. Wrap-up should offer to remove ONLY the finished one, and on yes
# remove it without --force. Usage: sweep-ready.sh <dir>  → checkout <dir>/work
set -euo pipefail
root="$1"; rm -rf "$root"; mkdir -p "$root"; cd "$root"
git init -q --bare -b main origin.git
git clone -q origin.git work 2>/dev/null; cd work
git config user.email t@t; git config user.name t
mkdir -p .continuity/decisions
cat > .continuity/feature-status.yml <<YML
settings:
  push_to_default_branch: true
features:
  widgets:
    status: building
    next: "Backfill the prod widgets table"
    next_steps:
      - { step: "Write scripts/migrate-widgets.sh", done: false }
      - { step: "Backfill the prod widgets table", done: false, gate: approval }
    in_progress: null
last_session:
  date: 2026-09-20
  feature: widgets
  summary: "Scaffolded the importer"
YML
printf '# widgets — decisions\n\n## Decided\n\n- Importer is a shell script.\n' > .continuity/decisions/widgets.md
printf '.claude/worktrees/\n' > .gitignore
git add -A; git commit -qm init; git push -q origin HEAD:main
git worktree add -q -b worktree-agent-done .claude/worktrees/agent-done HEAD
git worktree add -q -b worktree-agent-wip .claude/worktrees/agent-wip HEAD
echo "half-done" > .claude/worktrees/agent-wip/notes.txt
mkdir -p scripts; printf '#!/bin/sh\necho migrating\n' > scripts/migrate-widgets.sh
git add -A; git commit -qm "feat: migrate-widgets.sh"; git push -q origin HEAD:main
echo "checkout: $root/work"
