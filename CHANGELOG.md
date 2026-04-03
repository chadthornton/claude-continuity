# Changelog

## [Unreleased]

### Added
- **Retrospect step** in wrap-up and checkpoint — outgoing Claude asks "what might the next Claude miss?" and grades completeness 1-10. Saves to `last_session.blind_spots` in feature-status.yml. Startup surfaces these as "Watch out for:" in the brief.

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
