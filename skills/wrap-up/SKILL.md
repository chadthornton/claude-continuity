---
name: wrap-up
description: Use at the end of a session to update continuity state. Updates feature status, decision files, and writes a handoff block if mid-stream. Also use when user says "wrap up", "end session", "save state", "update status", or "write handoff".
---

# Session Wrap-Up

Update the project's continuity state so the next session can pick up smoothly. This should feel like updating a few lines in two files, not writing a report.

## Prerequisites

The project must have a `.continuity/` directory with `feature-status.yml`. If it doesn't exist, suggest running `/continuity-init`.

## Flow

### Step 0: Edit the Newest Board

In a git repo with an `origin` remote, other sessions (other worktrees, other machines) may have landed continuity updates since this checkout was cut. Editing a stale copy is how conflicts are born. Before touching any file:

1. `git fetch -q origin <default>` (default = `git symbolic-ref --short refs/remotes/origin/HEAD`, minus `origin/`).
2. If `git log --oneline HEAD..origin/<default> -- .continuity` is non-empty **and** `.continuity/` has no local changes (`git status --porcelain -- .continuity` empty, ignoring `last-activity.txt`) **and** this branch has no continuity commits missing from origin, run `git restore --source=origin/<default> --staged --worktree -- .continuity ':(exclude).continuity/last-activity.txt'`. `restore` (unlike `checkout`) also removes files origin deleted, such as a stale `handoff.md`.
3. Otherwise edit in place — Step 6 merges three-way and reports a conflict rather than overwriting.

Skip this step if there is no remote or `.continuity/` is gitignored.

### Step 1: Identify What Changed

Review the current session's work:

- What feature area or workflow was the focus?
- Were any decisions made? (New approaches chosen, alternatives rejected, constraints discovered)
- Were any open questions resolved? Any new ones discovered?
- Is the work at a clean stopping point, or mid-stream?

If it's not obvious from conversation context, ask the user briefly.

### Step 2: Update feature-status.yml

Read the current `.continuity/feature-status.yml` and update the relevant section.

**If the session worked on a feature**, update:

- **status** for the worked-on feature (exploring → building, etc., if it changed)
- **next** — short label for the next move (shown in dashboard table)
- **blocked_by** (optional) — if this feature can't start until a sibling feature lands, set `blocked_by: [sibling-name]`. Only add it where a real dependency exists; most features need none. Remove the entry once the blocker is `polishing`/`parked`/`superseded`.
- **next_steps** — ordered list of specific, actionable steps for the next session. These should be concrete enough that a fresh Claude can act on them without re-reading the conversation. Include file paths where relevant. Aim for 3-7 items. This is the primary handoff mechanism — don't compress a multi-step plan into the `next` one-liner.
  - **Step completion tracking:** When steps use the `{step, done}` object format, mark completed steps as `done: true` rather than removing them. Add new steps discovered during the session at the end with `done: false`. This preserves the progress trail so the next startup can show "step 3 of 7" instead of a context-free list.
  - If all steps are done and the work is at a clean stop, replace with a fresh list for the next phase of work.
  - If steps are plain strings, it's fine to rewrite the list as usual — or upgrade to `{step, done}` format if the work is clearly multi-session.
  - **Gates (optional):** add `gate: approval` to a step that needs the user's explicit go-ahead (prod deploy, data migration, spend), or `gate: "decision: <question>"` to a step blocked on an unmade choice. Startup and relay stop at gated steps.
- **summary** — one-line current state
- **in_progress** — set to a task description if mid-stream, `null` if at a clean stop
- **owner** — set by a relay (Step 6b) or by a session that takes a mandate (startup). If this checkout is the owner and its chain is finished, or the user said "take over {feature}", set `owner` to this checkout's name (`basename "$(git rev-parse --show-toplevel)"`) or remove it when the work is at a clean stop.

**If the session ran a workflow**, update:

- **last_run** — today's date
- **steps** — if the workflow steps evolved or need updating based on what was learned, update them. Workflows improve over time.
- **summary** — if the workflow's description needs clarifying, update it
- Don't set `in_progress` for workflows — they're either done or they aren't. If interrupted mid-workflow, set it on the top-level `in_progress` field.

**Minimal wrap-up (context pressure):** If the user mentions token pressure, or the session is being cut short, do a minimal wrap-up: update only `next_steps` (mark done/not-done), `in_progress`, and `last_session`. Skip decisions file updates — preserving where-you-are matters more than capturing rationale when tokens are scarce. **Never skip Step 6 (Make It Durable)** — it is one command, and a minimal update that isn't saved is no update.

**Always update:**

- **last_session.date** — today's date
- **last_session.summary** — one sentence about what happened
- **last_session.feature** — which area or workflow was worked on

Keep the YAML concise. Don't add commentary.

### Step 3: Update decisions/{feature}.md

Read the current decisions file for the worked-on feature. If it doesn't exist, create it.

**Add new decisions** to the "Decided" section:
- Include the *why*, not just the *what*. One sentence of rationale.
- Example: "NSOutlineView for file browser, not SwiftUI OutlineGroup. OutlineGroup has known bugs with dynamic content updates."
- *Optional stable handle:* if an Open item or Ruled out entry needs to point back at a decision, prefix it with a short within-file handle (`D1`, `D2`, …) and reference it as "(see D2)". Handles are local to this file and retire when the decision is pruned — don't build a permanent numbered log.

**Record ruled-out approaches (optional).** If the session tried an approach and abandoned it, add one line to a `## Ruled out` section: `approach — why it failed`. This is the negative of a decision — it stops the next session from re-walking a dead end. Only record real, tested dead ends; don't speculate. Prune an entry once the code path that would have hit it no longer exists.

**Add new open questions** to the "Open" section:
- Describe the question and any known constraints.
- Example: "File browser refresh strategy: poll with timer vs FSEvents. FSEvents is more efficient but adds complexity."

**Resolve open questions** that were answered during the session:
- Move them to "Decided" with the resolution, or simply remove if no longer relevant.

**Optionally mark open items by kind.** If it clarifies triage, prefix an open item with `[decision]` (answer is a choice, resolve before building) or `[task]` (queued work, nothing to decide). Unmarked items are fine — don't force markers.

**Capture fog (optional).** If a decision is clearly coming but you can't phrase it sharply yet, add one line to a `## Not yet specified` section in the decisions file. Don't invent fog — only record a real, not-yet-specifiable decision. This is the low-friction path for side-chat insights: a brainstorm that shifts direction leaves its trace here instead of evaporating.

**Prune stale items:**
- Decided items that are old and fully absorbed into the codebase can be removed. They live in MEMORY.md or the code itself at that point.
- Aim to keep the file under ~30 lines.
- Prune without fear: git history is the archive. Anything you remove is recoverable via `git log`/`git blame` on the decisions file, so there's no need for an "archive" section or keeping stale items "just in case."

### Step 4: Retrospect

Before finishing, pause and ask yourself: **"What might the next Claude miss?"**

Think about things you learned during this session that aren't obvious from the code, git history, or the decisions file — implicit assumptions, gotchas, or context that would cost the next instance time to rediscover.

Write 2-5 bullet points, then grade the handoff on the **necessary-and-sufficient test**: *would the next session have enough to resume, with nothing it could delete and still succeed?* Score 1-10. Below 7 means something important is missing (look again at decisions and next_steps) or there's noise to prune.

Examples of good retrospect items:
- "The SwiftUI preview crashes if you don't set the environment object — not obvious from the error message"
- "The user wants the sidebar to feel like Finder, not like a typical IDE file tree"
- "There's a circular dependency between Canvas and Renderer that isn't in the decisions file yet"

**Route each item to the right home** — blind_spots is not a catch-all:
- **Tested dead end** ("we tried FSEvents, it fails in sandboxed apps") → a `## Ruled out` line in the decisions file, not a blind spot. It's about that feature and should be pruned with it.
- **Durable project-wide fact** ("the test harness needs `CI=1` set") → the top-level `gotchas` list (see below). It stays true across many sessions, so it shouldn't evaporate on the next wrap-up.
- **Everything else** (this-session assumptions, preferences, easy-to-miss context) → `last_session.blind_spots`, a list in `feature-status.yml`. These are session-scoped and naturally replaced on the next wrap-up.

**Promote to `gotchas` sparingly.** Only a fact that will still bite three sessions from now belongs there. Keep the list under ~10 lines and prune any entry that's no longer true — it loads on cold return and competes for the startup budget. When in doubt, it's a blind spot, not a gotcha.

### Step 5: Write Handoff Block (if mid-stream)

Only if `in_progress` is set — the user is stopping mid-task and needs the next Claude to pick up exactly where they left off.

Write a `<handoff>` block following this format:

```xml
<handoff>
<!--
  Claude: Read ONLY this block first.
  Start with <first-action>, expand context only if stuck.
-->

<task>Single atomic deliverable</task>
<status>in-progress</status>

<first-action>
What to do next — specific file path and 3-5 bullets.
</first-action>

<verify>
How to confirm it works.
</verify>
</handoff>
```

Write this to `.continuity/handoffs/{feature}.md`, one file per feature, so parallel agents never overwrite each other's handoff. Keep it minimal — just enough for the next Claude to continue without re-reading the whole conversation.

If the session ended at a clean stopping point, delete that feature's handoff if it exists — it's stale. Delete a legacy `.continuity/handoff.md` only if its `<task>` names this feature.

### Step 6: Make It Durable

Edited files are not saved state. `.continuity/` lives in git, so an uncommitted edit dies with its worktree, and a commit on a feature branch is invisible to every other checkout's `/startup` until that branch merges. Run the bundled script from this skill's base directory:

```
<skill base directory>/continuity-save -m "continuity: <one-line summary>"
```

Invoke it by its absolute path (it is executable) — not via `bash <script>`, which some worktree guards refuse. It:

- commits **only** `.continuity/` (never `last-activity.txt`, never code, and leaves anything else the user staged untouched);
- if the project opted in with `settings: { push_to_default_branch: true }` in `feature-status.yml`, lands those commits on `origin/<default>` — re-applying just the `.continuity/` diff with a three-way `git merge-tree`, so code on the current branch is never shipped. It fast-forwards only, never forces, and stamps each landed commit with a `Continuity-Source:` trailer;
- after landing from a feature branch, adds one `continuity: sync` commit so the branch's `.continuity/` matches `origin/<default>`. The branch's PR then can't conflict on continuity files unless the board moves again before it merges, and the next save re-syncs it. The sync commit carries a `Continuity-Sync:` trailer and is never landed again;
- without the setting, commits on the current branch and says whether that is on the default branch.

Invoking wrap-up is consent to commit (and, when opted in, push) `.continuity/` — nothing else.

**Report its first line verbatim in the Step 7 summary.** Don't soften a failure:

- `SAVED …` — done.
- `SAVED ON BRANCH ONLY` / `SAVED LOCALLY` — tell the user continuity is not on the default branch yet and why.
- `CONFLICT` (exit 2) — another session changed the same lines. Nothing was pushed; the commit is safe on this branch. Resolve: `git restore --source=origin/<default> -- .continuity`, re-apply this session's edits, then run `continuity-save --resolve`, which lands this checkout's `.continuity/` as-is and marks the earlier commits landed.

A `WorktreeRemove` hook refuses to delete a worktree with uncommitted or unlanded `.continuity/` changes, and `SessionStart` flags unlanded continuity commits on any local branch — so a skipped Step 6 surfaces instead of vanishing.

### Step 6b: Leave a Mandate (and offer a relay)

When the next steps are clear enough to hand over cold, write them down as a **mandate**: a commission for whichever session picks the work up next, now or days later. Check each feature this session worked on. Write one without asking when **all** of these hold for it:

- it has **2 or more** not-done steps;
- the first not-done step has no `gate:`;
- each step in the chain is concrete enough to act on cold: it names the file, command, or artifact to produce. "Polish the UI" or "clean things up" is not concrete, so the feature gets no mandate;
- its `owner` is absent or is this checkout.

The **chain** is the run of not-done steps from the first one up to, but not including, the first gated step. If the conditions don't hold, skip this step without mentioning it.

Writing the mandate:

1. On the feature, set `mandate: {today}` and `in_progress: "Steps {first}–{last} per handoffs/{feature}.md"`. Leave `owner` unset: the session that takes the mandate claims it.
2. Write `.continuity/handoffs/{feature}.md` in the relay shape:

```xml
<handoff>
<task>{feature}: steps {first} → {last}, one commit per step.</task>
<status>Done so far: {not-yet-pruned done steps, one line}.</status>
<first-action>
1. `git fetch -q origin && git switch -c {feature}-step-{first} origin/{default}` — this checkout may be stale.
2. Step {first}: {its text, with file paths}.
</first-action>
<stops>
- {each gated step in or right after the chain, with its gate}
- Anything these steps don't cover, a permission denial, or a check failing for an unclear reason: stop and ask. Don't route around it.
</stops>
<environment>
{Only the `gotchas` and `last_session.blind_spots` entries that touch the chain's files or tools; omit the rest. Add any peer session known to share a resource with this chain.}
</environment>
<verify>
{Per step: how to confirm it works.} After each step ships: mark it `done: true` and run continuity-save. After the last step: clear `mandate`, `owner` and `in_progress`, then run wrap-up.
</verify>
</handoff>
```

3. Once every qualifying feature has its mandate, run continuity-save once (`-m "continuity: mandate {features}"`).
4. Add a line per feature to the Step 7 summary: `MANDATE: {feature} steps {first}–{last} left for the next session (say "drop the {feature} mandate" to remove)`.

**Offering a relay.** If `command -v agent-spawn` succeeds, ask once with AskUserQuestion. With one mandate: **"Continue {feature} steps {first}–{last} with a new agent now, or leave it for the next session?"** Options: **Continue with a new agent** / **Leave it for the next session**. With several: **"Which of these should new agents continue now?"** with `multiSelect: true` and one option per mandated feature (`{feature}: steps {first}–{last}`); selecting none leaves them all for the next session. The question holds four options at most: with more mandates, offer the four features this session worked on most, and name the rest in the summary as left for the next session. With no spawner, don't ask.

For the features chosen, relay them all in one save, then spawn one agent per feature:

1. Pick a name per feature: `{feature}-{N}` with the lowest N ≥ 1 for which `.claude/worktrees/{feature}-{N}` does not exist.
2. Set `owner: {name}` on each feature, and in its handoff's first action use the branch `{name}-step-{first}`.
3. Run continuity-save once (`-m "continuity: relay {features} to {names}"`). If it reports `CONFLICT`, stop and resolve before spawning: the new agents would read a board without their handoffs.
4. Per feature, run `agent-spawn {name} --prompt "/startup"` from the repo root, name first: an older agent-spawn reads only its first argument and ignores the rest. The new session opens already running `/startup`, finds the feature whose `owner` is its checkout name, and resumes from `handoffs/{feature}.md`. Don't message it afterwards: a cross-session message can sit waiting for approval, and the handoff already carries everything.
5. Judge each spawn by its exit status. agent-spawn exits 0 only once it has seen the agent running; on any other exit nothing is left running (it closes whatever it opened). Every path prints an `Open it: …` line: where the agent is, or the command that starts it by hand.
   - **Exit 0:** in place of that feature's MANDATE line, report `RELAY: {name} spawned — owns {feature} steps {first}–{last}`, and under it that spawn's own `Open it: …` line, copied exactly. Each agent gets its own, because each one opens somewhere different.
   - **Any other exit:** the feature must not stay owned by an agent that isn't running. Undo step 2 for it: remove its `owner`, and put the handoff's branch back to `{feature}-step-{first}`; keep the mandate and handoff. Report its MANDATE line with ` — {name} didn't start`, and under it the spawn's `Open it: …` line (starting the agent that way asks the user to take the mandate, since nothing owns it now).
   - **No `Open it:` line** (an older agent-spawn): copy its last instruction line as-is in its place.

   If any spawn failed, run continuity-save once after the last one (`-m "continuity: {names} didn't start; mandates kept"`); on `CONFLICT`, stop and resolve as in step 3. If any agent started, end with one line: `Check on them: agent-spawn status`.

**Dropping a mandate.** When the user asks to drop one, remove `mandate` and `in_progress` from the feature, delete `.continuity/handoffs/{feature}.md` (or a legacy `handoff.md`), and run continuity-save.

### Step 6c: Clear Finished Worktrees

Agent worktrees (subagents, relays, spawned sessions) each hold a full checkout, often with its own `node_modules`, and nothing removes them once their work has landed. Run the bundled script from the repo:

```
<skill base directory>/worktree-sweep
```

It prints one `<path>\t<reason>` line per worktree under `.claude/worktrees/` that is finished: no uncommitted changes, every commit on a remote, no live session working in it, and not held by another running session's lock. Worktrees locked by this session (its own subagents) and locks whose process has died count as finished.

- **Prints nothing** → skip this step without mentioning it.
- **Prints lines** → ask once with AskUserQuestion: **"Remove {N} finished worktree(s): {names}? Their folders are deleted; branches and commits stay."** Options: **Remove them** / **Keep them**.

On yes, run `worktree-sweep --remove` and report its `REMOVED` / `KEPT` lines in Step 7. Remove only what the script listed, and leave any worktree it didn't list for the user to decide.

### Step 7: Confirm

Print a brief summary of what was updated:

```
Updated .continuity/:
  feature-status.yml — Canvas Types: exploring → building
  decisions/canvas-types.md — +1 decided, +2 open, -1 resolved
  handoffs/canvas-types.md — removed (clean stop)
  SAVED: 5ee1f0c landed on origin/master (from feature-x)
  MANDATE: canvas-types steps 3–5 left for the next session (say "drop the canvas-types mandate" to remove)
  RELAY: sidebar-1 spawned — owns sidebar steps 2–3
    Open it: Muxy sidebar → app → sidebar-1 → right-click → Existing Terminals (⌥⌘T)
  Check on them: agent-spawn status
  WORKTREES: removed 2 finished (agent-a1b2, agent-c3d4)

Blind spots (7/10):
  • The WebKit content sizing workaround only applies to the split view — full-screen mode uses a different layout path
  • User prefers Finder-style navigation feel, not IDE-style
```

**Phase gate note:** If the worked-on feature has a `phase` field and higher-phase features exist in the YAML, append a phase status line:

- If the feature's status is now `building` or `exploring` → `"Phase N is underway. Phase N+1 unblocks when it completes."`
- If the feature's status is now `polishing` or `parked` → `"Phase N complete. Phase N+1 is now unblocked."`

This is informational — it helps the user (and the next startup) understand where the project stands in its phase sequence.

## Guidelines

- **Speed over completeness.** This should take < 1 minute. If it feels heavy, you're doing too much.
- **Don't rewrite everything.** Only touch the fields/entries that changed this session.
- **Don't update MEMORY.md.** That's the auto-memory system's job for stable facts.
- **Don't write a session summary.** The decisions file captures what matters. The git log captures what changed in code.
- **Decisions need rationale.** "Use WKWebView" is not enough. "Use WKWebView — NSView subclass, fits existing SplitNode tree, no SwiftUI bridging needed" is.
- **Open questions need context.** "Handle keyboard focus" is not enough. "WKWebView captures keyboard input aggressively — Cmd+D/T/W may not fire when web pane is focused" is.
- **When in doubt, prune.** A 15-line decisions file that's all signal is better than a 50-line file with noise.
