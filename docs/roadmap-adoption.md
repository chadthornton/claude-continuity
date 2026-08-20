# Adoption roadmap — best practices from the landscape

Distilled from a survey of the cross-session memory/continuity landscape (Claude Code plugins, first-party agent memory, and general agent-memory frameworks), filtered against continuity's five hard design rules:

1. **Prune over accumulate** — decision files stay ~30 lines; append-only logs are an anti-pattern.
2. **Decisions need rationale** — reject a decision without a *why*.
3. **Light ceremonies** — startup and wrap-up each under a minute.
4. **Context budget** — startup returns a ~500-token brief, not full state.
5. **No infrastructure** — plain git-diffable files; no DB, server, or MCP requirement.

The rejections matter as much as the adoptions: they're where continuity's identity lives. A feature that violates the constitution is off the table no matter how popular it is elsewhere.

## Adopt

### 1. `## Ruled out` — failed-approaches capture
**Source:** willseltzer/claude-handoff (mandatory "failed approaches" section), a recurring pattern across handoff tools.

Continuity records what was *decided* and *what's next*, but not what was *tried and abandoned*. The most expensive cross-session failure is re-walking a known dead end — and decision rationale doesn't capture the negative space ("we tried X, it broke on Y"). `blind_spots` is adjacent but covers *unknowns*, not *tested-and-rejected* paths.

**Adaptation that keeps it philosophy-native:** an optional `## Ruled out` block in the decision-file template — each line `approach — why it failed`. Wrap-up's retrospect prompts for it *only* when a real dead end occurred; it's pruned when the surrounding decision is absorbed. This is the existing "decisions need a why" rule applied to the negative case.

**Effort:** Low (template + one retrospect prompt). **This is the single highest-leverage addition.**

### 2. "Necessary and sufficient" retrospect rubric
**Source:** thepushkarp/handoff ("necessary and sufficient context").

The retrospect step already grades handoff completeness 1–10 but without a concrete rubric. Name the criterion: *"Would the next session have enough to resume, with nothing it could delete and still succeed?"* This is the constitution restated as a test the grader can apply.

**Effort:** Trivial (wording change in the wrap-up ceremony).

### 3. `/continuity-prune` — an explicit pruning pass
**Source:** russbeye/claude-memory-bank (`/stale-check`, `/cleanup-context`), centminmod setup.

Prune-over-accumulate is currently enforced only as a *hope* during wrap-up. Under time pressure, wrap-up skips pruning and files drift past the 30-line budget. A named, on-demand pass makes the most-violated rule actionable.

**Guardrail:** it *proposes*, never auto-deletes — scans decision files over ~30 lines and `feature-status.yml` for parked/absorbed items, lists specific prune candidates with reasons, human confirms. Preserves the human-curates bet.

**Effort:** Low–Medium (one command).

## Adapt

### 4. Git is the archive
**Source:** rejecting claude-remember's now/today/recent/archive rotation.

The real need behind archive tiers — "what if I prune something I later want?" — is met by git history. Rotation is a softer append-only log; building it would betray rule 1. Instead, wrap-up should simply *state* that pruned decisions live in git history, recoverable via `git log`/blame. The reassurance is the entire benefit, at zero cost.

**Effort:** Trivial (one line of reassurance in wrap-up).

### 5. Within-file ADR reference handles
**Source:** centminmod's ADR numbering (ADR-017…), russbeye.

Cross-referencing and supersession ("this replaces the earlier auth decision") are currently impossible — decisions are anonymous lines. Steal *only* the stable ID (`D3:` prefix on Decided lines) so `Open` items and `blocked_by` can reference a decision. **Not** the permanent numbered log — IDs are within-file handles that retire when their decision is pruned.

**Effort:** Low. Adopt only as reference handles; reject the moment it implies a permanent ledger.

### 6. `gotchas` via extended `workflows`
**Source:** russbeye's patterns/ + troubleshooting/, Cline's systemPatterns.

Durable cross-feature knowledge ("the test harness needs env var X", "auth always routes through Y") has no home and gets re-learned every session. Don't add a memory-bank file — that's the heavy pattern continuity avoids. Instead extend the existing `workflows` concept in `feature-status.yml` with a bounded `gotchas` list, hard-capped (~10 lines), pruned like everything else, and loaded *only* in cold-return startup mode to protect the budget.

**Effort:** Medium.

## Reject

| Candidate | Source | Why it's out |
|-----------|--------|--------------|
| Auto-extraction / file-watchers | claude-mem, memory-toolkit `WATCH:` | Inverts the human-curates bet + needs an always-on worker (rules 1, 5). Auto-extraction trades intent for coverage — continuity makes the opposite trade on purpose. |
| Vector/SQLite/graph DB + MCP query | claude-mem, Mem0, Letta, Zep, Graphiti, Cognee | Rule 5. Solves a token/recall problem continuity designed itself out of (its state is already ~500 tokens). None model phase/dependencies/what-next — continuity's actual differentiator. |
| Cross-agent shared session log | session-handoff, Obsidian-vault handoffs | A log shared across agents can't stay curated or under budget, and pulls state outside git-diffable files. Out of scope, not a violation to revisit later. |
| Hierarchical 6-file dependency chain | Cline/Roo Memory Bank | Rules 3, 4 — a read-order file graph is exactly the ceremony weight continuity avoids, and reading the chain blows the startup budget. Its one good idea (durable patterns) is captured by #6. |

## Value-to-effort summary

| Rank | Candidate | Verdict | Effort |
|------|-----------|---------|--------|
| 1 | `## Ruled out` (failed approaches) | Adopt | Low |
| 2 | "Necessary and sufficient" rubric | Adopt | Trivial |
| 3 | `/continuity-prune` | Adopt | Low–Med |
| 4 | Git-is-the-archive reassurance | Adapt | Trivial |
| 5 | Within-file ADR handles | Adapt | Low |
| 6 | `gotchas` via `workflows` | Adapt | Medium |
