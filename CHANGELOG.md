# Changelog

## [Unreleased]

### Changed
- **One handoff per feature** — handoffs live at `.continuity/handoffs/{feature}.md` (a legacy `handoff.md` is still read). Wrap-up can relay several mandated features at once (one question, one save, one agent each), and a relayed agent's `/startup` resumes the feature whose `owner` is its checkout. Why: parallel relays in trip-planner had to improvise per-feature files because a second relay's `handoff.md` would overwrite the first's. Scenario: two features relayed in one save with separate handoffs; the `widgets-1` checkout resumed widgets from its own file and ignored `reports`.

### Fixed
- **Relayed agents no longer stall on their first command** — startup gathers state with one bundled script, `continuity-state` (identity, board from origin when stale, handoffs, last activity, log, uncommitted; `show <path>` reads any `.continuity/` file from the same source), instead of shell the agent composes. Why: in trip-planner all three relayed agents sat on a "cannot be statically analyzed" permission prompt from startup's compound state-gathering command.

## [0.11.0] - 2026-09-29

### Added
- **`/away` and `/back`** — hand a mid-stream task to a Claude Code cloud session and take it back. `/away` writes `.continuity/away.md` from the conversation, commits and pushes the branch (never the default branch), starts `claude --cloud` under a pseudo-terminal, and marks the feature `away:`; `/back` parks the session, finds its `claude/*` branch by ancestry, fast-forwards, and briefs. Why: leaving the laptop mid-task used to stop the work; a spike showed cloud sessions can only push `claude/*` branches and can't be started with `-p`, which shaped the script.

### Changed
- **`continuity-save` and hooks ignore `.continuity/away.md`** — it rides on the feature branch only, and a commit touching it is never landed on the default branch. Why: the cloud rewrites the brief as it works; landing it would create merge conflicts on the default branch for a file that's deleted on return.
- **Startup shows features that are away** — a feature with `away:` opens the output as `☁ … in the cloud` and isn't resumed locally. Why: a new local session would otherwise start the same work the cloud is doing.

## [0.10.0] - 2026-09-29

### Changed
- **`/checkpoint` saves with `continuity-save`** — it now ends by committing `.continuity/` and, with `push_to_default_branch`, landing it on `origin/<default>`, then reports the script's first line. Still zero questions, and a conflict is reported rather than resolved. Why: a feature-branch session checkpointed for a day while the default branch's board stayed stale, so a relay spawned from it would have redone shipped work.
- **Relay starts the new agent on `/startup`** (wrap-up Step 6b) — it calls `agent-spawn {name} --prompt "/startup"` (name first, so an older agent-spawn ignores the flag) and drops the follow-up cross-session message. Why: spawned sessions sat idle at a bare prompt, and the nudge message could be held for approval.
- **Relay summary gives the switch command** — when agent-spawn prints `Find it: <command>`, wrap-up's summary copies it as `Switch to it: …` (now `muxy switch-project <main> && muxy switch-worktree <path>`, by path because Muxy labels worktrees by branch). Why: that hint only reached the calling agent, so a user on another project had no way to the new tab. (agent-spawn now opens the tab in the user's current view of the project rather than the new worktree's own view.)

## [0.9.0] - 2026-09-29

### Added
- **Mandates** — when a feature's next steps form a clear chain (2+ not-done, ungated head, each step concrete enough to act on cold, no other owner), wrap-up writes the relay-shaped handoff and `mandate: <date>` automatically, with no owner, and reports `MANDATE: … (say "drop the {feature} mandate" to remove)`. Why: sessions often end with an obvious bundle of work that the next session should pick up as a commission, whether or not an agent is spawned now.
- **Startup offers a waiting mandate first** (Step 1c) — an unclaimed mandate leads the output whatever its age, with first action, stops and environment, a "check recent commits" note past 3 days, and **Take it / Not now / Drop it**. Taking it claims `owner` and saves before any work starts, so other checkouts see it as owned; the brief says so when the claim only reached this checkout.

### Changed
- **Relay folds into the mandate** — wrap-up's relay question is now "continue with a new agent now, or leave it for the next session?", asked only when `agent-spawn` exists; the mandate is written either way. Scenario runs: baseline wrap-up wrote no mandate without a spawner and baseline startup treated a 5-day-old mandate as the user's own in-progress work; with the change, wrap-up wrote mandates only for concrete, ungated chains (none for vague or gated steps), and startup led with the commission, claimed it on origin on "Take it", and removed it on "Drop it".

## [0.8.0] - 2026-09-29

### Added
- **Clear finished worktrees (wrap-up Step 6c)** + bundled **`worktree-sweep`** — lists worktrees under `.claude/worktrees/` that are clean, fully on a remote, not in use by a live session, and not held by another session's lock (this session's own subagent locks and dead-pid locks count as finished); wrap-up asks once and removes them without `--force`. Why: each agent worktree carries a full checkout and `node_modules` (~356 MB each in trip-planner, 4.3 GB total) and nothing removed them after their work landed; baseline wrap-up only noted them as a blind spot.

## [0.7.0] - 2026-09-28

### Added
- **Chain ownership (`owner:` on a feature)** — startup compares a feature's `owner` with this checkout's worktree name; another agent's chain is shown as `(owned by …)` and never fast-resumed. Why: in scenario tests, 3/3 baseline startups told a non-owner session "Resuming widgets", which invites duplicate work on a relayed chain.
- **Gated steps (`gate:` on a next_step)** — `approval` or `"decision: <question>"`; startup renders `⛔` and says "stop and ask" when the next step is gated. Why: stops lived only in handoff prose, invisible to anything that reads the board.
- **Relay (wrap-up Step 6b)** — after saving, when the worked-on feature has 2+ not-done steps, an ungated head, and `agent-spawn` exists, wrap-up asks once whether to hand the chain to a new agent. On yes it sets `owner`, writes a relay handoff (`<stops>`, and an `<environment>` filtered from gotchas/blind_spots to the chain's files), saves again, and spawns. Why: sessions often end with obvious next work; waiting for someone to run `/startup` is pure latency. Baseline wrap-up offered it 0/2 times; with the step, 4/4 offered or relayed, and a gated head skipped it.
- **Skill scenario fixtures** in `tests/skill-scenarios/` — build a bare origin + clones for running skills against in subagents (stale handoff + ownership; relay-ready).

## [0.6.0] - 2026-09-26

### Added
- **`continuity-save`** (wrap-up skill script) — the new "Make It Durable" step. Commits only `.continuity/` (never code or `last-activity.txt`), and with the opt-in `settings: { push_to_default_branch: true }` lands it on `origin/<default>` by re-applying just the `.continuity/` diff via three-way `git merge-tree` — so a worktree branch's unmerged code is never shipped. Fast-forward only, never forces; each landed commit carries a `Continuity-Source:` trailer. `--resolve` lands a hand-merged `.continuity/` after a conflict. Why: continuity lived in git but nothing committed or pushed it, so edits died with deleted worktrees and other checkouts' boards went stale.
- **Wrap-up Step 0: edit the newest board** — fetch, and if `.continuity/` is behind origin and untouched locally, `git restore` origin's copy before editing, shrinking the conflict window from a session to a minute.
- **`WorktreeRemove` hook** — refuses to delete a worktree with uncommitted `.continuity/` changes, or (when opted in) continuity commits not on `origin/<default>`.
- **Unlanded-continuity notice** in the `SessionStart` hook — flags continuity-only commits from the last 14 days sitting on local branches but not on `origin/<default>` (local refs only, no fetch).
- **Startup freshness check** — fetches and, if this checkout is behind on `.continuity/`, reads the board from `origin/<default>` and says so.

### Fixed
- **`session-start.sh` emitted top-level `additionalContext`**, which Claude Code doesn't read for SessionStart — the `/continuity-init` hint likely never reached the model. Now `hookSpecificOutput.additionalContext`.

### Changed
- **Minimal wrap-up never skips the save step**, and `/checkpoint` documents that it stays local until wrap-up.

## [0.5.0] - 2026-08-20

### Added
- **`## Ruled out`** in decision files — tested-and-abandoned approaches, one line each (`approach — why it failed`). Recorded by wrap-up, checkpoint, and continuity-recover when a real dead end occurred; startup replays them in every brief (fast-resume, resumed, next, cold) so the next session doesn't re-walk a known dead end. Pruned when the code path that would hit them is gone. Fills the one gap rationale-for-a-decision doesn't cover: the negative space of what was tried and rejected.
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
