<purpose>
Claude Code plugin for lightweight cross-session continuity. Maintains feature status, decision rationale, and open questions across sessions without heavyweight infrastructure.
</purpose>

<architecture>
## Plugin Structure

- `plugin.json` — manifest with hook registrations
- `hooks/session-end.sh` — writes `.continuity/last-activity.txt` on session exit
- `hooks/pre-compact.sh` — backs up transcript JSONL before compaction
- `skills/startup/SKILL.md` — session triage: dashboard + mode/area pick + focused brief
- `skills/wrap-up/SKILL.md` — session end: update status + decisions + handoff if mid-stream
- `commands/continuity-init.md` — scaffold `.continuity/` in a new project
- `templates/` — starter files for new projects
- `docs/` — design brief, proposal, and conversation history

## Per-Project Files (in .continuity/)

- `feature-status.yml` — machine-readable dashboard (~20 lines)
- `decisions/{feature}.md` — decided + open items per feature (~30 lines each)
- `last-activity.txt` — auto-written by SessionEnd hook (transient)
- `handoff.md` — only exists when mid-stream on a task
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
</rules>
