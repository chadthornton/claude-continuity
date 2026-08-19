# Pocock Skills Integration + Continuity Enhancements — Design

**Date:** 2026-08-19
**Status:** Approved-pending-review
**Scope:** Global skill routing (CLAUDE.md) + Continuity `/startup` wiring + two additive Continuity enhancements

## Problem

Three skill systems now coexist and overlap: **Superpowers** (mandatory `using-superpowers` gate, process skills), **mattpocock-skills** (v1.2.3, official plugin), and **Continuity** (this repo, session-boundary + roadmap). The goal is to make the right skill fire day-to-day without the user remembering to invoke it — while resolving the collisions between the three, and enhancing Continuity with the best ideas from Pocock's tracker flow rather than adopting that flow wholesale.

Two direct collisions exist: Superpowers and Pocock both ship TDD (`test-driven-development` vs `tdd`) and debugging (`systematic-debugging` vs `diagnosing-bugs`) skills, each model-invocable on its own description.

## Non-Goals

- **Not** un-gating any Pocock skill. Every `disable-model-invocation` gate is either a user-invoked interview (already available as a slash command) or a setup-dependent tracker skill (dormant by design) or unfinished. Un-gating auto-invocation on interview skills (`grill-me`, `loop-me`) would drop the user into interrogations mid-task. Leave all gates as-is.
- **Not** adopting Pocock's issue-tracker workflow (`setup-matt-pocock-skills`, `to-tickets`, `triage`, `wayfinder`, `to-spec`) globally. It competes with Continuity's roadmap for the same job. Keep it gated-but-available for the rare too-big-for-one-session build, invoked explicitly per-repo.
- **Not** adding `blocked_by` fine-grained dependency edges to `feature-status.yml`. See "Rejected: blocked_by" below.

## Overlap Analysis (verified against source)

| Concern | Superpowers | Pocock | Verdict |
|---|---|---|---|
| TDD | `test-driven-development` | `tdd` | Route to **Superpowers** (in the enforced `using-superpowers` path) |
| Debugging | `systematic-debugging` | `diagnosing-bugs` | Route to **Superpowers** (one canonical "broken" trigger) |
| Code review | `requesting-/receiving-code-review` (etiquette) | `code-review` (two-axis engine) | **Stack** — Superpowers for workflow discipline, Pocock as the review engine |
| Grilling | — | `grilling` | Pocock-unique; keep |
| Planning | `writing-plans`, `executing-plans` | `to-spec`, `wayfinder` (tracker-bound, gated) | Route to **Superpowers + Continuity**; don't route to Pocock's |

Continuity vs Pocock tracker flow: **different jobs.** Continuity answers "where were we, and why?" (feature status + rationale, cheap, direction-current). The tracker flow answers "what's the dependency-ordered path through a build too big for one context?" (tickets with blocking edges, visual frontier, parallel-agent grabbable). What pure-Continuity loses: dependency ordering + parallel-agent frontier — real, but only felt on 15+-slice builds, exactly where `/wayfinder` is the right tool.

## Deliverable 1 — Global routing block (`~/.claude/CLAUDE.md`)

A `<rules><rule name="skill-routing">` block. Format: **two-column table, plain-language triggers, exact skill IDs.** No pseudo-code (semantic match runs on natural language; code framing adds noise and implies false precision).

**Critical constraint:** a routing table *biases* skill choice; it does **not** gate a competing skill. `tdd` and `diagnosing-bugs` carry no `disable-model-invocation`, so they stay model-invocable on their own descriptions regardless of the table. De-confliction rows must be written as explicit *preference statements* ("prefer X over Y — one canonical trigger for Z"), not as if the loser goes silent. Real enforcement, if ever wanted, is a hook — deferred.

Skill IDs are copied **verbatim** from the session skill listing. Verified this session: `mattpocock-skills:code-review` resolves (the prefix is `mattpocock-skills:`, not `mattpocock:`).

Draft table (final wording set at implementation):

```
| Trigger (what you say / what's happening)          | Skill                                 |
|----------------------------------------------------|---------------------------------------|
| bug, throwing, failing test, slow, regression      | superpowers:systematic-debugging      |  ← prefer over mattpocock-skills:diagnosing-bugs
| new feature / bugfix, build it test-first          | superpowers:test-driven-development   |  ← prefer over mattpocock-skills:tdd
| review a branch/PR/diff before merge               | mattpocock-skills:code-review         |
| stress-test my plan / decision / idea              | mattpocock-skills:grilling            |
| sanity-check a state model or UI feel              | mattpocock-skills:prototype           |
| research a question against primary sources        | mattpocock-skills:research            |
| pin down domain terms / record an ADR              | mattpocock-skills:domain-modeling     |
| design or deepen a module's interface              | mattpocock-skills:codebase-design     |
| walk a human through steps only they can do        | mattpocock-skills:wizard              |
| resolve an in-progress merge/rebase conflict       | mattpocock-skills:resolving-merge-conflicts |
| start/end a session, "what should I work on"       | claude-continuity:startup / wrap-up   |
```

The block must respect the user's `claude-md-format` rule (XML scaffolding, named rule). It sits alongside — not inside — the existing `using-superpowers` machinery, which already forces a pre-action skill check; this block resolves *which* skill that check lands on.

## Deliverable 2 — `/startup` skill wiring

Add a **work-mode → suggested-skill** hint to `startup/SKILL.md` Step 5 ("Load Context For Chosen Work"). When the user picks a feature and a mode (Build / Polish / Harden), surface the matching Pocock/Superpowers skill in the composed brief:

- Build (greenfield) → suggest `superpowers:test-driven-development`
- Harden (something's broken/flaky) → suggest `superpowers:systematic-debugging`
- Polish / pre-merge → suggest `mattpocock-skills:code-review`

This is a **suggestion in the brief**, not an auto-invocation — Continuity's `light-ceremonies` rule (startup < 1 min) and its "don't gatekeep modes" guideline both hold. One or two lines, no new AskUserQuestion.

## Deliverable 3 — Continuity enhancements (2, not 3)

### 3a. Decision-vs-task marking in `decisions/{feature}.md` "Open" section

Borrowed from wayfinder's sharpest idea: separate *questions whose answer is a decision* from *work to execute*. Continuity's "Open" section currently blurs both. Add an optional convention — prefix open items with `[decision]` or `[task]` — so `/startup` triage can distinguish "you need to decide X before building" from "X is just work queued up."

**Additive & optional.** Unmarked open items render exactly as today. `wrap-up` gains one line encouraging the marker; `startup` Step 6 gains one line using it when present. Template `decisions/_template.md` gets a comment documenting the convention.

### 3b. `## Not yet specified` (fog-of-war) section in `decisions/{feature}.md`

Borrowed from wayfinder's fog-of-war: a place to park decisions you can *see coming* but can't phrase precisely yet. Directly addresses Continuity's design-brief pain points S3 (direction drift) and S5 (side-chat insights have no path back).

**Distinct from the existing `blind_spots`** (added to source since the cache): `blind_spots` = backward-looking gotchas the next Claude will trip on; fog = forward-looking decisions not yet sharp enough to be an Open question. The spec positions them so they don't blur — `blind_spots` lives in `feature-status.yml last_session`, fog lives in the per-feature decisions file.

**Additive & optional.** A decisions file without the section behaves exactly as today. `wrap-up` Step 3 gains a sub-step: "if a coming-but-unphrasable decision surfaced, add it to `## Not yet specified`." `startup` optionally surfaces it in cold-return orientation.

### Rejected: `blocked_by` fine-grained edges

Continuity's own anti-goal A3 ("don't track at a granularity that creates maintenance burden without proportional value") and its "human is a product designer, low-maintenance" constraint rule this out. Integer `phase` already expresses ordering over the ~4–6 feature areas a project has, and `startup` already computes the frontier from it. Explicit edges only pay off at 15+ interdependent slices — the `/wayfinder` case. Two overlapping ordering models is worse than one. Dropped.

## Rollout Constraint (critical)

**~25 projects already have populated `.continuity/` directories.** Template edits reach only *newly initialized* projects. Therefore every enhancement (decision/task markers, `## Not yet specified`) **must be optional** — `startup` and `wrap-up` must behave identically when the marker/section is absent. This is already baked into 3a and 3b as "additive & optional," but it is a hard acceptance criterion: **no existing project's startup may change behavior after this ships.**

## Source-of-Truth Constraint (critical)

All edits target the **source repo** `~/Projects/claude-continuity` (git: `github.com/chadthornton/claude-continuity`), **not** the plugin cache at `~/.claude/plugins/cache/claude-continuity-local/...`. The cache is a stale build artifact (its `startup`/`wrap-up`/`feature-status.yml` already differ from source). Cache edits are clobbered on reload. After source edits, the plugin must be rebuilt/reinstalled for changes to take effect (plugin hooks/skills load at session start).

## Files Touched

**Global (outside this repo):**
- `~/.claude/CLAUDE.md` — add `skill-routing` rule block

**This repo (`~/Projects/claude-continuity`):**
- `skills/startup/SKILL.md` — Step 5 mode→skill hint; Step 6 use decision/task marker if present; optional fog surfacing in cold return
- `skills/wrap-up/SKILL.md` — Step 3 encourage decision/task marker + fog sub-step
- `templates/decisions/_template.md` — document `[decision]`/`[task]` convention + `## Not yet specified` section
- `CHANGELOG.md` — version bump entry
- `.claude-plugin/plugin.json` — version bump 0.3.0 → 0.4.0

## Acceptance Criteria

1. Routing block present in `~/.claude/CLAUDE.md`, every skill ID verified to resolve, de-confliction rows phrased as preferences.
2. `/startup` on a project **without** the new markers/sections produces byte-identical behavior to pre-change (verify against one existing `.continuity/` project).
3. `/startup` on a project **with** a decision/task marker distinguishes decisions from tasks in the brief.
4. `wrap-up` writes fog items only when a coming-but-unphrasable decision actually surfaced (no forced ceremony).
5. All edits in the source repo; plugin rebuilt; version bumped to 0.4.0.

## Testing Approach

- **Regression (AC2):** run `/startup` mentally against an unchanged existing project's `.continuity/` (e.g. `~/Projects/INSTALLATION-GARAGE/.continuity`) — confirm no new prompts or format changes.
- **New-feature (AC3, AC4):** run `/startup` and `/wrap-up` against a decisions file carrying the new markers + fog section (use this repo's own `.continuity/` or a scratch copy).
- **Routing (AC1):** spot-invoke two IDs from the table (one Superpowers, one Pocock) to confirm resolution.
