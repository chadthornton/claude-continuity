# claude-continuity

A Claude Code plugin for lightweight cross-session continuity. Maintains feature status, decision rationale, and open questions across sessions without heavyweight infrastructure.

## The problem

Claude Code sessions are stateless. Each new session starts from scratch -- no memory of what was decided, what was tried, or what's in progress. For multi-session projects, this means:

- Re-explaining context every session
- Accidentally revisiting rejected approaches
- Losing track of open questions and decisions
- No structured way to hand off mid-stream work

## What this plugin does

It maintains a small `.continuity/` directory in your project with two key files:

- **`feature-status.yml`** -- a machine-readable dashboard of feature areas, their status, and next steps
- **`decisions/{feature}.md`** -- decided items (with rationale) and open questions per feature

Three skills manage the lifecycle:

| Command | When | What it does |
|---------|------|-------------|
| `/startup` | Session start | Renders a dashboard, detects re-entry mode (fast resume / resumed / next / cold return), loads relevant context into a focused brief |
| `/wrap-up` | Session end | Updates feature status, decisions, writes handoff if mid-stream, runs a retrospect to flag blind spots |
| `/checkpoint` | Mid-session | Quick save of decisions and progress without ending the session |

Plus two recovery commands:

| Command | When | What it does |
|---------|------|-------------|
| `/continuity-init` | New project | Scaffolds `.continuity/` with your feature areas |
| `/continuity-recover` | After crash/context exhaustion | Reconstructs continuity state from a session transcript |

## Key features

- **Adaptive startup** -- detects whether you're resuming mid-stream work, starting a new session, or returning after time away, and adjusts the flow accordingly
- **Phase sequencing** -- optional `phase` field on features for cross-feature ordering (phase 1 must progress before phase 2 unblocks)
- **Step tracking** -- `next_steps` with `{step, done}` objects show "step 3 of 7" progress across sessions
- **Retrospect** -- wrap-up and checkpoint include a "what might the next Claude miss?" step that surfaces blind spots the next session should watch for
- **Workflows** -- repeatable operations (audits, reviews) tracked alongside features
- **Minimal ceremony** -- startup and wrap-up each take under a minute

## Install

```bash
# Add the marketplace (one-time)
claude plugin marketplace add chadthornton/claude-continuity

# Install the plugin
claude plugin install claude-continuity
```

Restart Claude Code, then run `/continuity-init` in any project to set up `.continuity/`.

## Usage

### Starting a session

Run `/startup` (or just start working -- the plugin detects `.continuity/` and offers to triage).

The startup skill detects your re-entry mode automatically:

- **Fast resume** -- you were just here and left mid-stream. Skips the dashboard, gets you back to work immediately.
- **Resumed session** -- recent work, shows progress through next_steps ("step 3 of 7").
- **Next session** -- clean stop from a recent session. Shows the dashboard and recommends what to work on.
- **Cold return** -- it's been a while. Shows a "since you've been away" summary before the dashboard.

### During a session

Run `/checkpoint` any time to save decisions and progress without interrupting your work. Zero questions asked -- it infers the active feature and captures what's changed.

### Ending a session

Run `/wrap-up` to:
1. Update feature status and next steps
2. Capture new decisions (with rationale) and open questions
3. Run a retrospect -- "what might the next Claude miss?" with a 1-10 completeness grade
4. Write a handoff block if you're stopping mid-task

### Recovering from crashes

If a session ended without wrap-up (context exhaustion, crash, forgot), run `/continuity-recover` with the session ID or transcript path. It reconstructs what `/wrap-up` would have produced.

## File structure

```
.continuity/
  feature-status.yml      # Dashboard: features, status, next steps, last session
  decisions/
    {feature}.md           # Decided items + open questions per feature
  handoff.md               # Only exists when mid-stream (deleted on clean stop)
  last-activity.txt        # Auto-written by SessionEnd hook (add to .gitignore)
```

### feature-status.yml

```yaml
features:
  my-feature:
    status: building        # planned | exploring | building | polishing | parked
    phase: 1                # Optional. Lower phases first.
    next: Wire up the API
    summary: REST API for widget management
    next_steps:
      - step: "Define API routes"
        done: true
      - step: "Wire up database layer"
        done: false
      - step: "Add auth middleware"
        done: false

in_progress: null           # Task description if mid-stream, null if clean

last_session:
  date: 2026-04-03
  summary: Got API routes defined, starting database layer
  feature: my-feature
  blind_spots:
    - "The auth middleware expects JWT tokens but the client SDK sends session cookies"
    - "Rate limiting config is in a separate env var not mentioned in .env.example"
```

### decisions/{feature}.md

```markdown
# My Feature

## Decided
- Use Postgres over SQLite -- need concurrent writes from multiple workers
- REST over GraphQL -- simpler for the current use case, team has more REST experience

## Open
- Connection pooling strategy -- PgBouncer vs built-in pool. PgBouncer adds ops complexity but handles connection storms better
```

## Design principles

- **Prune over accumulate.** Decision files stay under ~30 lines. Old items absorbed into the codebase get removed.
- **Decisions need rationale.** "Use Postgres" is insufficient. "Use Postgres -- need concurrent writes from multiple workers" is good.
- **Light ceremonies.** Startup and wrap-up each take under a minute. If they feel heavy, they're doing too much.
- **Context budget.** Startup runs as a subagent and returns a ~500 token brief, not the full continuity state.

## License

MIT
