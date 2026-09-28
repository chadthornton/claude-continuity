# Closure-pass calibration — trip-planner, 2026-09-28

**Status:** observing. PR #18 was merged 2026-09-28 as merge commit `3fbf213`.
Before building the plugin changes below, check the next 3–5 trip-planner
sessions for the rollback signal: an agent digging through git, or re-learning a
fact the pass moved or deleted. If that happens, adjust the destinations table
first.

Input for the next plugin change. Hand-run on trip-planner's
`migration-execution` feature (trip-planner PR #18, baseline tag
`continuity-baseline-2026-09-28`).

## Problem

trip-planner had the largest `.continuity/` of 28 projects: 2,721 lines / ~57k
tokens, with `feature-status.yml` at 572 lines (~18k tokens, read every
startup) against a ~20-line target. The budgets exist but nothing enforces them.
The leaks:

- 116 `done: true` steps (~45% of the YAML)
- `next:` fields averaging 399 characters
- runbooks and phase logs sitting in decisions files
- finished features left on the board

## Why finished steps can't simply be deleted

83 of the 116 finished steps cite no commit. They hold what git doesn't:

- rationale ("Chad's call: …")
- negative results
- actions taken outside the repo (dashboards, env vars)
- measurements
- roadmap progress

"Git is the archive" holds only for content that is purely a record of what
changed.

## Destinations (the sorting rule)

| Content | Goes to |
|---|---|
| Live decision + why | stays in `decisions/{feature}.md` |
| Built into the code, costly to reverse, not obvious from the code | `docs/adr/` (proposed; the human confirms) |
| Built into the code and cheap or obvious | delete |
| Tested dead end | `## Ruled out` |
| Fact about the outside environment that bites repeatedly | repo ops doc / CLAUDE.md, else `gotchas` |
| Runbook, phase log, measurements | `docs/` or `ops/`, with a pointer |
| "Built X (commit abc)" | delete |
| Finished phase | one `shipped` line with a commit range |

The boundary with `docs/roadmap-adoption.md` §5 holds: continuity keeps no
ledger. The permanent log is the repo's ADRs.

## What the pass taught

1. **A finished feature whose status never changed is the root cause.** Phase 4
   ran 2026-09-11, yet the feature stayed `polishing`, so 595 lines stayed live.
   → A closing pass triggers when a feature's last step finishes.
2. **Live work hides in DONE blocks.** One confirmed live bug (the inverted
   `listUnenriched` selector) and a dead column were buried in finished phases.
   → Pull open work out before deleting.
3. **Expired warnings.** Test whether the *hazard* is gone, not just its time
   window.
4. **Destinations may not exist.** Directus had no home in the repo; the pass
   created `ops/box/directus/README.md`.
5. **Check the code before promoting to an ADR.** 2 of 3 ADR candidates were
   already recorded in the `db/schema.sql` header. Yield: 1 ADR from 595 lines.
6. **Search for references before deleting.** README.md and CLAUDE.md named the
   file as "infra of record". Six references were repointed.
7. **Too heavy for wrap-up.** It needed code checks. Make it a separate command;
   wrap-up only suggests it.

Result: total `.continuity/` −25%, but startup YAML only −12%. The board's
finished steps across the other features are the real startup cost, so the pass
needs to run board-wide.

## Plugin changes to make

1. Wrap-up sorts content out of a finished step before removing it; a closing
   phase collapses to a `shipped` line.
2. A closing pass (`/continuity-prune`, or a new `/continuity-close`), with
   rules 1–7 above.
3. `next:` capped at ~120 characters; `done` features come off the board.
4. The SessionStart hook checks size (YAML > ~150 lines, decisions file > ~60)
   and suggests the pass.
5. Record the ledger boundary in `roadmap-adoption.md`, and update the
   CHANGELOG.

## Relay proposal (from a trip-planner peer session) — SHIPPED in 0.7.0

Shipped: relay (wrap-up Step 6b, runs after the save), `owner:`, `gate:`. Dropped: the startup freshness fix, because 3/3 baseline runs already read handoff.md from origin. Scenario fixtures: `tests/skill-scenarios/`. The original proposal follows for reference.

Optional end-of-wrap-up step. It fires when the worked-on feature has ≥2 open
steps and no unmet gate at the head. It:

1. writes `handoff.md`
2. sets `in_progress` to name the owner agent and worktree
3. runs `continuity-save`
4. runs `agent-spawn`, then sends a nudge message

With no spawner, it degrades to "handoff.md written + in_progress set", and the
next `/startup` resumes from that.

Worked example: `git -C ~/Projects/trip-planner show
02620cb:.continuity/handoff.md`. Beyond the standard block, it has `<stops>`,
`<environment>`, and a `<task>` covering a chain of steps.

Folded-in asks:

- **Startup freshness bug.** When the board is stale, also read `handoff.md`
  and the loaded decisions file from origin.
- **Optional `gate:` field on a step.** Values: `approval` or
  `decision:<text>`. Startup and relay stop at a gate.
- **`handoff.md` is the source of truth.** The message is only a nudge.
- **`in_progress` names the owner.** Make it a wrap-up convention.
- **Generate `<environment>`** by filtering `gotchas` + `blind_spots` to the
  chain's files, plus active peers sharing a resource.
- **Outside the plugin:** agent-spawn should give each session a distinct name,
  which is Chad's tooling.
