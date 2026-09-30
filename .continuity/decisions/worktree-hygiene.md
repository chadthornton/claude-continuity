# worktree-hygiene — decisions

## Decided

- worktree-sweep only lists clean, fully-pushed worktrees not held by another live session's lock — removal deletes uncommitted work; branches and commits survive.
- wt:status --tsv column order is a contract — mac-diskspace's launchd check.sh reads by position; append only.
- Deleting merged branches is tidiness, not disk — trip-planner's whole .git is 7.7 MB; the cost is per-worktree node_modules.

## Open

- [decision] Switch trip-planner to a hard-linking package manager (pnpm/bun) so worktrees share node_modules? trip-planner's call; passed to mac-diskspace.
