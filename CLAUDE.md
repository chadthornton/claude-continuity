<purpose>
Claude Code plugin for lightweight cross-session continuity. Maintains feature status, decision rationale, and open questions across sessions without heavyweight infrastructure.
</purpose>

<architecture>
## Plugin Structure

- `plugin.json` — manifest with hook registrations
- `lib/continuity-commits.sh` — the shared rules for which commits are continuity state (landed/sync/merge/mixed/pending), the default-branch lookup and the stale count; sourced by continuity-save, continuity-state, away and both hooks. Change the rules here, nowhere else.
- `hooks/session-start.sh` — init hint; flags continuity commits stranded on local branches
- `hooks/session-end.sh` — writes `.continuity/last-activity.txt` on session exit
- `hooks/worktree-remove.sh` — blocks worktree removal that would lose `.continuity/` edits
- `hooks/pre-compact.sh` — backs up transcript JSONL before compaction
- `skills/startup/SKILL.md` — session triage: dashboard + mode/area pick + focused brief
- `skills/startup/continuity-state` — all state startup reads in one allowlistable call; `show <path>` reads a .continuity file from the same source
- `skills/wrap-up/SKILL.md` — session end: update status + decisions + handoff if mid-stream
- `skills/wrap-up/continuity-save` — commits only `.continuity/`; opt-in lands it on origin/<default> without shipping code
- `skills/away/` — `/away`: hand this session's task to a cloud session (`away launch|park|land` script)
- `skills/back/SKILL.md` — `/back`: park the cloud session, fast-forward its commits, brief
- `commands/continuity-init.md` — scaffold `.continuity/` in a new project
- `templates/` — starter files for new projects
- `docs/` — design brief, proposal, and conversation history

## Per-Project Files (in .continuity/)

- `feature-status.yml` — machine-readable dashboard (~20 lines)
- `decisions/{feature}.md` — decided + open items per feature (~30 lines each)
- `last-activity.txt` — auto-written by SessionEnd hook (transient)
- `handoffs/{feature}.md` — one per feature, only while it's mid-stream or relayed (older boards: a single `handoff.md`)
- `away.md` — `/away`'s brief to a cloud session; rides on the feature branch only, never landed

Durability: `.continuity/` is tracked in git and is only shared once it reaches `origin/<default>`. Scenario tests for `continuity-save` and the hooks should build a bare remote + clone + worktree and assert that code never reaches the default branch.
</architecture>

<rules>
<rule name="context-budget">
The startup skill runs as a subagent. The main session should receive a ~500 token brief, not the full continuity state. Only load what's relevant to the chosen work.
</rule>

<rule name="decisions-need-rationale">
Every "Decided" entry must include *why*, not just *what*. One sentence of rationale is enough. "Use WKWebView" is insufficient. "Use WKWebView — NSView subclass, fits existing SplitNode tree" is good.
</rule>

<rule name="prune-over-accumulate">
Decision files should stay under ~30 lines. Old decided items that are absorbed into the codebase get pruned during wrap-up. Append-only logs are an anti-pattern.
</rule>

<rule name="light-ceremonies">
Startup and wrap-up should each take < 1 minute of user time. If either feels heavy, it's doing too much.
</rule>

<rule name="changelog">
When adding or modifying a plugin feature (skills, hooks, commands, templates), add an entry to `CHANGELOG.md` under an `## [Unreleased]` section at the top. Use Keep a Changelog format (Added/Changed/Fixed/Removed). One line per change — describe the *what* and *why*. Version numbers and dates get filled in at release time.
</rule>
</rules>
