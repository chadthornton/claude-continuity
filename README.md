# claude-continuity

Cross-session memory for Claude Code. Three slash commands, a few small files, no infrastructure.

## Install

```bash
# Add the marketplace (one-time)
claude plugin marketplace add chadthornton/claude-continuity

# Install the plugin
claude plugin install claude-continuity
```

Restart Claude Code, then run `/continuity-init` in any project to get started.

## The idea

**The underlying bet:** small, curated, opinionated state beats large, comprehensive, neutral state. A 30-line decisions file that gets pruned every session is more useful than a 500-line memory bank that only grows.

This works best for **iterative product development** -- building features across many sessions over days or weeks, where decisions compound and the *why* behind past choices matters as much as the choices themselves. Think: multi-feature apps, architectural build-outs, anything where session 5 needs to know what sessions 1-4 decided.

It's probably not worth the overhead for one-off scripts, quick prototypes, or work where each session is self-contained.

### What's different

There's no shortage of approaches to LLM context management -- CLAUDE.md files, AGENTS.md, memory banks, handoff docs, elaborate scaffolding. This plugin doesn't try to replace any of that. It adds a thin layer on top, focused on three things most approaches underserve:

1. **Decisions carry rationale.** Every system can record "we chose Postgres." The difference is recording *why* -- "need concurrent writes from multiple workers." Without the why, the next Claude can't judge whether the decision still holds when circumstances change.

2. **The outgoing Claude audits its own handoff.** A mandatory retrospect step asks "what might the next Claude miss?" and grades completeness 1-10. In practice it consistently catches 2-3 things that would cost a full session to rediscover -- implicit constraints, failed approaches, user preferences not in the code.

3. **Startup adapts to how you're returning.** Instead of loading everything, it detects whether you're mid-stream, next-day, or back after a week, and adjusts what it surfaces. The context budget stays around 500 tokens regardless.

## Usage

Three commands cover the whole lifecycle:

| Command | When | What it does |
|---------|------|-------------|
| `/startup` | Beginning of session | Reads continuity state, gives the new Claude a focused brief |
| `/wrap-up` | End of session | Captures decisions, flags blind spots, writes handoff if mid-task |
| `/checkpoint` | Whenever | Saves progress mid-session without interrupting work |

Plus `/continuity-init` to set up a new project and `/continuity-recover` to reconstruct state after a crash.

### Startup

`/startup` detects how you're returning and adjusts:

- **Fast resume** -- you were just here, left mid-stream. Two-line brief, back to work.
- **Resumed session** -- recent work, shows progress ("step 3 of 7").
- **Next session** -- clean stop recently. Dashboard with a recommendation.
- **Cold return** -- it's been a while. "Since you've been away" orientation first.

### Wrap-up

`/wrap-up` at the end of a session:
1. Updates feature status and next steps
2. Captures new decisions (with rationale) and open questions
3. Runs the retrospect -- "what might the next Claude miss?" graded 1-10
4. Writes a handoff block if you're stopping mid-task

### Checkpoint

`/checkpoint` mid-session. Zero questions asked -- infers the active feature and captures what's changed. Includes a context health nudge so you know when to `/clear`.

## What gets tracked

A `.continuity/` directory with a few small files:

```
.continuity/
  feature-status.yml      # Dashboard: features, status, next steps
  decisions/
    {feature}.md           # What's decided, what's open (per feature)
  handoff.md               # Only exists when stopping mid-task
```

The feature status file is the dashboard:

```yaml
features:
  my-feature:
    status: building        # planned | exploring | building | polishing | parked
    next: Wire up the API
    next_steps:
      - step: "Define API routes"
        done: true
      - step: "Wire up database layer"
        done: false

last_session:
  date: 2026-04-03
  summary: Got API routes defined, starting database layer
  feature: my-feature
  blind_spots:
    - "Auth middleware expects JWT but the client SDK sends session cookies"
    - "Rate limiting config lives in a separate env var not in .env.example"
```

Decision files capture the *why*, not just the *what*:

```markdown
## Decided
- Use Postgres over SQLite -- need concurrent writes from multiple workers
- REST over GraphQL -- simpler for current scope, team knows it better

## Open
- Connection pooling strategy -- PgBouncer vs built-in pool
```

### Other features

- **Phase sequencing** -- optional `phase` field for cross-feature ordering (phase 1 before phase 2)
- **Workflows** -- repeatable operations (audits, reviews) tracked alongside features

## Design principles

- **Prune over accumulate.** Decision files stay under ~30 lines. Old items get removed once they're absorbed into the code.
- **Decisions need rationale.** "Use Postgres" is not a decision. "Use Postgres -- need concurrent writes" is.
- **Light ceremonies.** Startup and wrap-up each take under a minute. If they feel heavy, something's wrong.
- **Context budget.** Startup returns a ~500 token brief, not the full continuity state.

## License

MIT
