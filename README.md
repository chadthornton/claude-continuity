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

## About

If you're using Claude Code to build something over multiple sessions, you've probably noticed the main limitation: every session starts from zero. The previous Claude made decisions, rejected approaches, discovered constraints -- and the next Claude has no idea. You end up re-explaining context, re-litigating settled questions, and watching Claude cheerfully re-explore the dead end you already mapped.

This plugin adds a lightweight continuity layer. A small `.continuity/` directory in your project tracks what's been decided (and why), what's still open, and where things left off. Three slash commands manage the lifecycle:

- **`/startup`** reads the state and gives the new Claude a focused brief
- **`/wrap-up`** captures what happened and flags what the next Claude might miss
- **`/checkpoint`** saves progress mid-session without ending anything

That's the core loop. Everything else -- adaptive startup modes, phase sequencing, step tracking, crash recovery -- grew out of using it daily on real projects.

### A note on opinions

There is no shortage of approaches to LLM context management. CLAUDE.md files, AGENTS.md, handoff documents, memory banks, custom system prompts, elaborate scaffolding -- people have strong feelings and everyone's workflow is different.

This plugin doesn't try to be the universal answer. It's opinionated toward a specific style of work: **iterative product development where you're building features across many sessions over days or weeks.** The kind of work where you need to remember *why* you chose Postgres over SQLite three sessions ago, not just *that* you did.

If you're doing one-off scripts, greenfield prototypes you'll finish in a sitting, or work where the code itself is the complete context -- you probably don't need this. If you keep finding yourself saying "we already decided that" to a Claude that wasn't there, it might help.

## How it works

### The session lifecycle

**Starting a session** -- run `/startup`. It detects how you're returning:

- **Fast resume** -- you were just here, left mid-stream. Skips the dashboard, gets you back to work.
- **Resumed session** -- recent work, shows progress ("step 3 of 7").
- **Next session** -- clean stop recently. Shows the board, recommends what to tackle.
- **Cold return** -- it's been a while. Orients you before showing the board.

**During a session** -- run `/checkpoint` to save decisions and progress. Zero questions asked.

**Ending a session** -- run `/wrap-up` to:
1. Update feature status and next steps
2. Capture decisions (with rationale) and open questions
3. Run a retrospect -- "what might the next Claude miss?" -- graded 1-10
4. Write a handoff if you're stopping mid-task

**After a crash** -- run `/continuity-recover` with a session ID. It reconstructs what `/wrap-up` would have produced from the transcript.

### What gets tracked

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
- **Retrospect** -- the outgoing Claude flags blind spots for the incoming one. Surprisingly effective at catching the 2-3 things that would otherwise cost a session to rediscover.

## Design principles

- **Prune over accumulate.** Decision files stay under ~30 lines. Old items get removed once they're absorbed into the code.
- **Decisions need rationale.** "Use Postgres" is not a decision. "Use Postgres -- need concurrent writes" is.
- **Light ceremonies.** Startup and wrap-up each take under a minute. If they feel heavy, something's wrong.
- **Context budget.** Startup returns a ~500 token brief, not the full continuity state.

## License

MIT
