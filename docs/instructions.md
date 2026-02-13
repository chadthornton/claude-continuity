# Installation & Usage

## Installation

### Register the local marketplace and install

Inside a Claude Code session:

```
/plugin marketplace add ~/Projects/claude-continuity
/plugin install claude-continuity@claude-continuity-local
```

Then restart Claude Code to load the plugin.

After making changes to the plugin source, refresh the cached copy:

```
/plugin marketplace update
```

### Alternative: load per-session (for development)

```bash
claude --plugin-dir ~/Projects/claude-continuity
```

This loads the plugin for one session without caching. Useful when iterating on the skills or hooks.

## Setting up a project

Run `/continuity-init` in any project to scaffold a `.continuity/` directory. This creates `feature-status.yml` and `decisions/` stubs based on your project's feature areas.

For xterm-woes, this has already been done — see `.continuity/` in that project.

## How discovery works

**You do NOT need to remind Claude about this plugin.** Once installed:

- **Skills** (`startup`, `wrap-up`) appear in Claude's available skills list automatically. Claude sees the trigger phrases and will use them when you say things like "what should I work on" or "wrap up."

- **Hooks** (`SessionEnd`, `PreCompact`) fire automatically on every session exit and before any compaction. No invocation needed. No Claude awareness needed. They're shell scripts that run independently.

- **The `/continuity-init` command** appears in the slash command list when the plugin is loaded.

## Daily workflow

### Starting a session

Say any of these:
- `/startup`
- "what should I work on"
- "start session"
- "show me the board"
- "triage"

The startup skill will:

1. **Check for mid-stream work** — uncommitted changes, in-progress tasks, stale state from an abrupt exit. If found, it offers to pick up where you left off.

2. **Render a dashboard** — a table showing all feature areas with their status and next move.

3. **Ask your work mode** — Build feature, Polish/UX, Harden, Architecture, or Brainstorm. These are about your energy and intent, not strict categories.

4. **Ask which feature area** (if the mode involves one).

5. **Load the relevant decisions file** and compose a ~500 token brief for the main session. This includes key past decisions (so Claude works within them), open questions (so Claude is aware), and any contextual flags the agent judges worth surfacing.

The main session starts with a focused brief, not a document dump.

### During a session

Work normally. The continuity system is not in the way.

### Ending a session

Say any of these:
- `/wrap-up`
- "wrap up"
- "end session"
- "save state"
- "update status"

The wrap-up skill will:

1. **Update `feature-status.yml`** — status, next move, last session info for the feature that was worked on.

2. **Update the relevant `decisions/{feature}.md`** — add new decisions with rationale, add new open questions, resolve answered questions, prune stale items.

3. **Write a handoff block** to `.continuity/handoff.md` if mid-stream on a task. Delete it if at a clean stopping point.

This should take less than a minute. If it feels heavy, it's doing too much.

### If you forget to wrap up

The **SessionEnd hook** fires automatically when Claude Code exits — even if you just close the terminal. It writes `.continuity/last-activity.txt` with:
- Timestamp
- Whether there are uncommitted changes
- Which files were touched

The next startup triage reads this and can detect that a wrap-up didn't happen. It won't have the semantic richness of a proper wrap-up (no decision updates), but it prevents total state loss.

### If compaction triggers accidentally

The **PreCompact hook** copies the full conversation transcript (JSONL) to `~/.claude/transcript-backups/` with a timestamp. Keeps the last 20 backups. Pure insurance.

### Brainstorm / side-chat sessions

The startup and wrap-up skills work in any session, but side-chat Claudes may not think to update continuity files unprompted. Add this to your project's CLAUDE.md:

```
If this session produced decisions or insights about a feature area,
update .continuity/feature-status.yml and the relevant
.continuity/decisions/{feature}.md before ending.
```

This is the one piece that relies on a norm rather than automation. Side-chat Claudes need to know the files exist and are worth updating.

## What fires when

| Event | What happens | Automatic? |
|-------|-------------|------------|
| You start any session | One-line nudge if no `.continuity/` exists | Yes — SessionStart hook |
| You start a session and say "startup" | Dashboard + triage + focused brief | No — you invoke it |
| You say "wrap up" | Status + decisions updated | No — you invoke it |
| You exit Claude Code (any way) | `last-activity.txt` written with git state | Yes — SessionEnd hook |
| Compaction triggers | Full transcript JSONL backed up | Yes — PreCompact hook |

## File locations

### Plugin files (in `~/Projects/claude-continuity/`)

| File | Purpose |
|------|---------|
| `.claude-plugin/plugin.json` | Plugin manifest |
| `.claude-plugin/marketplace.json` | Local marketplace registration |
| `hooks/hooks.json` | Hook configuration (SessionStart + SessionEnd + PreCompact) |
| `hooks/session-start.sh` | Nudges to run /continuity-init if no .continuity/ exists |
| `hooks/session-end.sh` | Writes last-activity.txt on exit |
| `hooks/pre-compact.sh` | Backs up transcript before compaction |
| `skills/startup/SKILL.md` | Startup triage skill |
| `skills/wrap-up/SKILL.md` | Session wrap-up skill |
| `commands/continuity-init.md` | Scaffold command for new projects |
| `templates/` | Starter files for new projects |

### Per-project files (in `{project}/.continuity/`)

| File | Purpose | Updated by |
|------|---------|-----------|
| `feature-status.yml` | Dashboard data — status, next move per feature | Wrap-up skill |
| `decisions/{feature}.md` | Decided + open items per feature | Wrap-up skill, brainstorm sessions |
| `last-activity.txt` | Git state at session exit | SessionEnd hook (automatic) |
| `handoff.md` | Atomic next task (only when mid-stream) | Wrap-up skill |

### Backup files

| File | Purpose |
|------|---------|
| `~/.claude/transcript-backups/*.jsonl` | Full conversation transcripts saved before compaction |
