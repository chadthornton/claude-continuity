# task-sync — decisions

## Decided

- Don't adopt backloghq/backlog; borrow only its TaskCompleted hook idea — its state lives in ~/.claude/plugins/data, outside git, so it can't ride a branch or reach an /away cloud session, and its 24 MCP tool definitions cost more context per session than startup's whole ~500-token brief.
- The hook never writes feature-status.yml — a hook firing mid-session in one worktree would race wrap-up and parallel agents on the one file everyone edits; it records ticks for wrap-up to apply.
- Starts after closure-pass ships — both touch hooks and wrap-up, and closure-pass-1 is mid-stream on them.

## Open

- [question] How does a built-in task map to a board step: matching text, or wrap-up seeding tasks with step ids?
- [decision] Apply ticks automatically, or list them at wrap-up for a yes?
