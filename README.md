# claude-continuity

Cross-session memory for Claude Code. A few slash commands, a few small files, no infrastructure.

## Install

```bash
# Add the marketplace (one-time)
claude plugin marketplace add chadthornton/claude-continuity

# Install the plugin
claude plugin install claude-continuity
```

Restart Claude Code, then run `/continuity-init` in any project to get started.

## The idea

**The bet:** small, curated, opinionated state beats large, comprehensive, neutral state. A 30-line decisions file that gets pruned every session is more useful than a 500-line memory bank that only grows.

This works best for **iterative product development** — building features across many sessions over days or weeks, where decisions compound and the *why* behind past choices matters as much as the choices themselves. Think multi-feature apps and architectural build-outs: anything where session 5 needs to know what sessions 1–4 decided.

## What's different

There's no shortage of context-management approaches: CLAUDE.md, AGENTS.md, memory banks, handoff docs. This plugin doesn't replace them — it adds a thin layer focused on three things most approaches underserve.

1. **Decisions carry rationale.** Any system can record "we chose Postgres." The difference is recording *why* — "need concurrent writes from multiple workers." Without the why, the next Claude can't judge whether the decision still holds when circumstances change.

2. **The outgoing Claude audits its own handoff.** A mandatory retrospect step asks "what might the next Claude miss?" and grades completeness 1–10. It consistently catches 2–3 things that would otherwise cost a full session to rediscover — implicit constraints, failed approaches, preferences that never made it into code.

3. **Startup adapts to how you're returning.** Instead of loading everything, it detects whether you're mid-stream, next-day, or back after a week, and surfaces only what fits that return. The brief stays around 500 tokens regardless.

## Commands

| Command | When | What it does |
|---------|------|-------------|
| `/startup` | Beginning of session | Reads continuity state, hands the new Claude a focused brief |
| `/wrap-up` | End of session | Captures decisions, flags blind spots, writes handoff if mid-task |
| `/checkpoint` | Whenever | Saves progress mid-session without interrupting work |
| `/continuity-init` | New project | Scaffolds `.continuity/` |
| `/continuity-recover` | After a crash | Reconstructs state from the session transcript |

### Startup adapts to your return

- **Fast resume** — you were just here, left mid-stream. Two-line brief, back to work.
- **Resumed session** — recent work, shows progress ("step 3 of 7").
- **Next session** — clean stop recently. Dashboard with a recommendation.
- **Cold return** — it's been a while. "Since you've been away" orientation first.

### Wrap-up

1. Updates feature status and next steps
2. Captures new decisions (with rationale) and open questions
3. Runs the retrospect — "what might the next Claude miss?", graded 1–10
4. Writes a handoff block if you're stopping mid-task

`/checkpoint` is the zero-question version: it infers the active feature, captures what's changed, and nudges you when context is getting full enough to `/clear`.

## What gets tracked

A `.continuity/` directory with a few small files:

```
.continuity/
  feature-status.yml       # Dashboard: features, status, dependencies, next steps
  decisions/
    {feature}.md           # What's decided, what's open (per feature)
  handoff.md               # Only exists when stopping mid-task
```

The feature-status file is the dashboard:

```yaml
features:
  multi-select:
    status: building        # planned | exploring | building | polishing | parked
    phase: 1
    next_steps:
      - step: "Define selection model"
        done: true
      - step: "Wire up batch actions"
        done: false
  batch-move:
    status: planned
    phase: 1
    blocked_by: [multi-select]   # not workable until multi-select lands

last_session:
  date: 2026-08-19
  summary: Selection model done, starting batch actions
  feature: multi-select
  blind_spots:
    - "Auth middleware expects JWT but the client SDK sends session cookies"
    - "Rate-limit config lives in a separate env var, not in .env.example"
```

Decision files capture the *why*, not just the *what*:

```markdown
## Decided
- Postgres over SQLite — need concurrent writes from multiple workers
- REST over GraphQL — simpler for current scope, team knows it better

## Open
- [decision] Connection pooling — PgBouncer vs built-in pool (gates the data layer)
- [task] Backfill the migration script for existing rows

## Not yet specified
- Rate-limit strategy for batch moves — can't size it until multi-select lands
```

## Dependencies & sequencing

As a project grows past a handful of features, ordering matters. Continuity layers this in without turning into a project planner — every field below is optional and additive:

- **`phase`** — cross-feature ordering. Startup computes a frontier so Claudes know what's workable now vs. what's gated by an earlier phase.
- **`blocked_by`** — intra-phase dependency edges. A feature at the frontier is still held back until every feature it lists is `polishing`, `parked`, or `superseded`. Startup shows it as `(blocked by {name})`. Blocks are recommendations, not gates — you can always override.
- **`[decision]` / `[task]` markers** on Open items — startup leads with `[decision]` items, since an unresolved decision blocks building in a way a task doesn't.
- **`## Not yet specified`** — fog-of-war. Decisions you can see coming but can't phrase yet. Distinct from `blind_spots` (which look backward at what you already learned), this looks forward. Surfaced during cold-return orientation.

Also tracked: **workflows** — repeatable operations (audits, metrics refreshes, incident response) recorded alongside features with their trigger, steps, and last run.

## Works alongside other skills

Continuity owns the **session boundary and the state that crosses it** — where you were, why, and what's next. It's deliberately narrow, so it composes with skill libraries that own the *work inside* a session:

- **[Superpowers](https://github.com/obra/superpowers)** — TDD, systematic debugging, plan execution. Continuity remembers the plan across sessions; Superpowers drives the build within one.
- **[Matt Pocock's skills](https://github.com/mattpocock/skills)** — code review, grilling a plan, domain modeling, ticket flows. Reach for these on the work; let Continuity handle the resume.

**When to graduate off a flat feature list.** Continuity's `phase` + `blocked_by` handle ordering well up to a point. When the work outgrows one context window *and* has real dependency structure a flat list can't express — roughly 15+ interdependent slices — move to a proper ticket tracker (Pocock's `to-tickets` / `wayfinder`, or GitHub issues). Below that threshold, the ticket ceremony costs more than it saves. Continuity is the default; graduate deliberately, not by habit.

## Design principles

- **Prune over accumulate.** Decision files stay under ~30 lines. Old items get removed once they're absorbed into the code.
- **Decisions need rationale.** "Use Postgres" isn't a decision. "Use Postgres — need concurrent writes" is.
- **Light ceremonies.** Startup and wrap-up each take under a minute. If they feel heavy, something's wrong.
- **Context budget.** Startup returns a ~500-token brief, not the full continuity state.

## License

MIT
