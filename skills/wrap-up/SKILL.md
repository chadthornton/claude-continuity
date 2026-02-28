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

- What feature area was the focus?
- Were any decisions made? (New approaches chosen, alternatives rejected, constraints discovered)
- Were any open questions resolved? Any new ones discovered?
- Is the work at a clean stopping point, or mid-stream?

If it's not obvious from conversation context, ask the user briefly.

### Step 2: Update feature-status.yml

Read the current `.continuity/feature-status.yml` and update:

- **status** for the worked-on feature (exploring → building, etc., if it changed)
- **next** — short label for the next move (shown in dashboard table)
- **next_steps** — ordered list of specific, actionable steps for the next session. These should be concrete enough that a fresh Claude can act on them without re-reading the conversation. Include file paths where relevant. Aim for 3-7 items. This is the primary handoff mechanism — don't compress a multi-step plan into the `next` one-liner.
- **summary** — one-line current state
- **in_progress** — set to a task description if mid-stream, `null` if at a clean stop
- **last_session.date** — today's date
- **last_session.summary** — one sentence about what happened
- **last_session.feature** — which area was worked on

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

### Step 4: Write Handoff Block (if mid-stream)

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

### Step 5: Confirm

Print a brief summary of what was updated:

```
Updated .continuity/:
  feature-status.yml — Canvas Types: exploring → building
  decisions/canvas-types.md — +1 decided, +2 open, -1 resolved
  handoff.md — removed (clean stop)
```

## Guidelines

- **Speed over completeness.** This should take < 1 minute. If it feels heavy, you're doing too much.
- **Don't rewrite everything.** Only touch the fields/entries that changed this session.
- **Don't update MEMORY.md.** That's the auto-memory system's job for stable facts.
- **Don't write a session summary.** The decisions file captures what matters. The git log captures what changed in code.
- **Decisions need rationale.** "Use WKWebView" is not enough. "Use WKWebView — NSView subclass, fits existing SplitNode tree, no SwiftUI bridging needed" is.
- **Open questions need context.** "Handle keyboard focus" is not enough. "WKWebView captures keyboard input aggressively — Cmd+D/T/W may not fire when web pane is focused" is.
- **When in doubt, prune.** A 15-line decisions file that's all signal is better than a 50-line file with noise.
