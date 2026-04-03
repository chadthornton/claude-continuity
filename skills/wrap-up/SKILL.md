---
name: wrap-up
description: Use at the end of a session to update continuity state. Updates feature status, decision files, and writes a handoff block if mid-stream. Also use when user says "wrap up", "end session", "save state", "update status", or "write handoff".
---

# Session Wrap-Up

Update the project's continuity state so the next session can pick up smoothly. This should feel like updating a few lines in two files, not writing a report.

## Prerequisites

The project must have a `.continuity/` directory with `feature-status.yml`. If it doesn't exist, suggest running `/continuity-init`.

## Flow

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
- **next_steps** — ordered list of specific, actionable steps for the next session. These should be concrete enough that a fresh Claude can act on them without re-reading the conversation. Include file paths where relevant. Aim for 3-7 items. This is the primary handoff mechanism — don't compress a multi-step plan into the `next` one-liner.
  - **Step completion tracking:** When steps use the `{step, done}` object format, mark completed steps as `done: true` rather than removing them. Add new steps discovered during the session at the end with `done: false`. This preserves the progress trail so the next startup can show "step 3 of 7" instead of a context-free list.
  - If all steps are done and the work is at a clean stop, replace with a fresh list for the next phase of work.
  - If steps are plain strings, it's fine to rewrite the list as usual — or upgrade to `{step, done}` format if the work is clearly multi-session.
- **summary** — one-line current state
- **in_progress** — set to a task description if mid-stream, `null` if at a clean stop

**If the session ran a workflow**, update:

- **last_run** — today's date
- **steps** — if the workflow steps evolved or need updating based on what was learned, update them. Workflows improve over time.
- **summary** — if the workflow's description needs clarifying, update it
- Don't set `in_progress` for workflows — they're either done or they aren't. If interrupted mid-workflow, set it on the top-level `in_progress` field.

**Minimal wrap-up (context pressure):** If the user mentions token pressure, or the session is being cut short, do a minimal wrap-up: update only `next_steps` (mark done/not-done), `in_progress`, and `last_session`. Skip decisions file updates — preserving where-you-are matters more than capturing rationale when tokens are scarce.

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

**Add new open questions** to the "Open" section:
- Describe the question and any known constraints.
- Example: "File browser refresh strategy: poll with timer vs FSEvents. FSEvents is more efficient but adds complexity."

**Resolve open questions** that were answered during the session:
- Move them to "Decided" with the resolution, or simply remove if no longer relevant.

**Prune stale items:**
- Decided items that are old and fully absorbed into the codebase can be removed. They live in MEMORY.md or the code itself at that point.
- Aim to keep the file under ~30 lines.

### Step 4: Retrospect

Before finishing, pause and ask yourself: **"What might the next Claude miss?"**

Think about things you learned during this session that aren't obvious from the code, git history, or the decisions file. These are the implicit assumptions, gotchas, failed approaches, or context that would cost the next instance time to rediscover.

Write 2-5 bullet points and a completeness grade (1-10) reflecting how well the continuity state captures what matters from this session.

Examples of good retrospect items:
- "The SwiftUI preview crashes if you don't set the environment object — not obvious from the error message"
- "We tried FSEvents first but it doesn't work in sandboxed apps — don't re-explore that path"
- "The user wants the sidebar to feel like Finder, not like a typical IDE file tree"
- "There's a circular dependency between Canvas and Renderer that isn't in the decisions file yet"

Save these to `last_session.blind_spots` in `feature-status.yml` as a list. They get naturally replaced on the next wrap-up. If the grade is below 7, take another look at the decisions file and next_steps — something important is probably missing.

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

Write this to `.continuity/handoff.md`. Keep it minimal — just enough for the next Claude to continue without re-reading the whole conversation.

If the session ended at a clean stopping point, delete `.continuity/handoff.md` if it exists — it's stale.

### Step 6: Confirm

Print a brief summary of what was updated:

```
Updated .continuity/:
  feature-status.yml — Canvas Types: exploring → building
  decisions/canvas-types.md — +1 decided, +2 open, -1 resolved
  handoff.md — removed (clean stop)

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
