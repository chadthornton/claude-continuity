# claude-continuity

Help your project survive the leap to a new Claude Code session — a lightweight mix of workstreams, decision logs, and dependencies, more roadmapper than issue tracker. Lighter than a memory bank, sharper than `/compact`, it keeps the *why* both let slip.

## Install

```bash
# Add the marketplace (one-time)
claude plugin marketplace add chadthornton/claude-continuity

# Install the plugin
claude plugin install claude-continuity
```

Restart Claude Code, then run `/continuity-init` in any project to get started.

## Summary

Claude Code forgets everything between sessions. It can re-read your code, but not the reasoning behind it — the approaches you rejected, the constraints nobody wrote down, what you decided last week and why.

Continuity keeps that reasoning in a few small files alongside your project: what's decided (and why), what's still open, where you left off. `/startup` hands the next session a focused brief; `/wrap-up` captures the new state and prunes the stale. The files stay small on purpose — the bet is that 30 curated lines that stay current beat a 500-line memory bank that only grows.

Best for work that compounds across days or weeks — multi-feature apps, architectural build-outs — where session 5 needs what sessions 1–4 decided.

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

Continuity tracks your project as a handful of **features** — the workstreams from the tagline — in a `.continuity/` directory of a few small files:

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

## How it compares

Cross-session memory is a crowded space, and much of it is genuinely good. Continuity is opinionated about one corner of it — *curated, rationale-first, session-bounded* state — and happily points you elsewhere if you want a different trade.

- **Automatic capture.** [claude-mem](https://github.com/thedotmack/claude-mem) and [claude-remember](https://github.com/Digital-Process-Tools/claude-remember) record your session automatically and compress it for recall — great when you want total coverage with zero effort. Continuity asks a human to decide what's worth keeping instead, so the record stays small and every entry has intent behind it.
- **Memory banks.** The [Cline](https://docs.cline.bot/prompting/cline-memory-bank) / [Roo Code](https://github.com/GreatScottyMac/roo-code-memory-bank) memory-bank pattern and ports like [claude-code-memory-bank](https://github.com/hudrazine/claude-code-memory-bank) and [claude-memory-bank](https://github.com/russbeye/claude-memory-bank) keep a rich set of reference files — a strong fit when you want a durable knowledge base. Continuity is the lighter end of that spectrum: a ~500-token brief and a hard line budget rather than a growing library.
- **Handoff docs.** [claude-handoff](https://github.com/willseltzer/claude-handoff), [handoff](https://github.com/thepushkarp/handoff), and [memory-toolkit](https://github.com/IlyaGorsky/memory-toolkit) write a per-session handoff — closest in spirit to this project. Continuity adds a structured feature dashboard, dependency edges, and a rationale rule on top of the handoff.
- **Memory frameworks.** [Mem0](https://github.com/mem0ai/mem0), [Letta](https://github.com/letta-ai/letta), [Zep](https://www.getzep.com/), and [Cognee](https://github.com/topoteretes/cognee) are infrastructure for building memory *into your own product* — vector/graph stores with automatic extraction. Continuity is the opposite scale: no database, no server, just files you can read and `git diff`.
- **Built-ins.** `CLAUDE.md`, `AGENTS.md`, `/compact`, `/rewind`, and the memories features in Cursor, Windsurf, and Copilot all persist real state. They're rules, silent facts, or a replayable transcript, though — none has a dedicated slot for *why a choice was made and what's still open*. Claude Code even ships the `SessionStart`/`SessionEnd`/`PreCompact` hooks to build that on; Continuity is a ritual that uses them.

**In one line:** most tools *accumulate* (logs, memory banks, vector stores) or prescribe *rules*. Continuity treats curation as the feature — decisions that must carry a *why*, pruned to a budget, bound to a startup/wrap-up ritual. If that's not the trade you want, the projects above are excellent at the others.

## Design principles

- **Prune over accumulate.** Decision files stay under ~30 lines. Old items get removed once they're absorbed into the code.
- **Decisions need rationale.** "Use Postgres" isn't a decision. "Use Postgres — need concurrent writes" is.
- **Light ceremonies.** Startup and wrap-up each take under a minute. If they feel heavy, something's wrong.
- **Context budget.** Startup returns a ~500-token brief, not the full continuity state.

## License

MIT
