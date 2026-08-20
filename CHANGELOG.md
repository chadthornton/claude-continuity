# Changelog

## [Unreleased]

### Added
- **`## Ruled out`** in decision files — tested-and-abandoned approaches, one line each (`approach — why it failed`). Recorded by wrap-up/checkpoint when a real dead end occurred; startup replays them in the brief so the next session doesn't re-walk a known dead end. Pruned when the code path that would hit them is gone. Fills the one gap rationale-for-a-decision doesn't cover: the negative space of what was tried and rejected.
- **`/continuity-prune`** command — proposes stale or over-budget decisions, parked features, dead `blocked_by` edges, and untrue gotchas for removal, each with a reason. Human confirms (apply all / pick / cancel); never auto-deletes. Reports that git history is the archive.
- **Top-level `gotchas`** list in feature-status.yml — durable, project-wide facts (env quirks, non-obvious wiring) that stay true across sessions. Hard-capped ~10 lines, pruned when no longer true, surfaced only on cold-return startup to protect the budget. Distinct from session-scoped `blind_spots`.
- **Optional within-file ADR handles** — a short `D1`/`D2` prefix on Decided items so Open/Ruled-out items can reference them ("see D2"). Local to the file; retire when the decision is pruned — not an append-only ADR log.

### Changed
- **Retrospect grades on the necessary-and-sufficient test** — "would the next session have enough to resume, with nothing it could delete and still succeed?" — and routes each note to the right home: tested dead ends to `## Ruled out`, durable facts to `gotchas`, everything else to `blind_spots`. Keeps `blind_spots` from becoming a catch-all.
- **Prune guidance** in wrap-up/checkpoint now states git history is the archive — pruned items are recoverable via `git log`, so there's no need to hoard stale entries "just in case."

## [0.4.0] - 2026-08-19

### Added
- **Retrospect step** in wrap-up and checkpoint — outgoing Claude asks "what might the next Claude miss?" and grades completeness 1-10. Saves to `last_session.blind_spots` in feature-status.yml. Startup surfaces these as "Watch out for:" in the brief.
- **Optional `blocked_by`** — per-feature intra-phase dependency edges in feature-status.yml. Startup marks a feature unworkable while any sibling it lists is still active (not polishing/parked/superseded), shown as "(blocked by {name})". Refines `phase` within same-phase clusters; fully additive — features without `blocked_by` evaluate exactly as before.
- **Decision/task markers** — optional `[decision]`/`[task]` prefixes on Open items in decision files; startup leads with `[decision]` items since they gate building.
- **Fog-of-war section** — optional `## Not yet specified` in decision files for decisions you can see coming but can't phrase yet (distinct from backward-looking `blind_spots`). Low-friction path for side-chat insights; surfaced in cold-return orientation.

### Skill routing
- Added a global `skill-routing` rule (in the user's `~/.claude/CLAUDE.md`, not this repo) that de-conflicts Continuity, Superpowers, and mattpocock-skills: TDD/debugging route to Superpowers, code-review/grilling/prototype/etc. route to Pocock, session boundaries route to Continuity.

## [0.3.0] - 2026-03-16

### Added
- **Phase sequencing** — optional `phase:` field on features for cross-feature ordering. Startup computes a phase frontier so Claudes know what's workable vs blocked.
- **Adaptive startup modes** — startup detects resumed/next/cold sessions and adjusts. Mid-stream resumption shows "step 3 of 7" progress instead of full dashboard.

## [0.2.1] - 2026-03-16

### Added
- **Workflows** — `workflows:` section in feature-status.yml for repeatable operations (incident response, metrics refresh, etc.) with trigger, steps, last_run, artifacts.
- **`next_steps` field** — ordered list replacing lossy one-liner `next:`. Supports plain strings and `{step, done}` objects for cross-session progress tracking.
- **Minimal wrap-up mode** — context-pressure path that updates only next_steps, in_progress, and last_session.

### Fixed
- continuity-recover init flow for projects with `.continuity/` but no features defined.

## [0.2.0] - 2026-02-20

### Added
- **`continuity-recover` command** — reconstructs continuity state from session JSONL transcripts when wrap-up didn't run (crash, context exhaustion).
- SessionStart hook and startup edge cases.

## [0.1.0] - 2026-02-18

### Added
- Initial plugin: feature-status.yml, decisions files, startup/wrap-up skills.
- `continuity-init` command to scaffold `.continuity/` in new projects.
- SessionEnd hook writing `last-activity.txt`.
- pre-compact hook backing up transcript JSONL.
