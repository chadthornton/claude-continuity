---
name: startup
description: Use when starting a new session on a project with a .continuity/ directory. Renders a feature dashboard, asks what mode and area to work on, loads relevant decisions, and hands off a focused brief. Also use when user says "what should I work on", "start session", "show me the board", or "triage".
---

# Startup Triage

Render a project dashboard and guide the user into a focused work session. Runs as a subagent to protect the main session's context budget.

## Prerequisites

The project must have a `.continuity/` directory. Check for `.continuity/feature-status.yml` in the current working directory. If it doesn't exist, suggest running `/continuity-init` to set one up.

## Flow

### Step 1: Gather State

Read these files (all are small — do this in parallel):

1. `.continuity/feature-status.yml` — feature areas, statuses, next moves
2. `.continuity/last-activity.txt` — if it exists, check for stale/unfinished state
3. Run `git log --oneline -5` — recent commits
4. Run `git diff --name-only` — uncommitted changes

### Step 2: Check for Mid-Stream Work

Look for signals that work was interrupted:

- `in_progress` is set in `feature-status.yml`
- Uncommitted changes exist
- `last-activity.txt` is newer than `feature-status.yml` (wrap-up didn't happen)

If mid-stream work is detected, present it immediately:

> "Looks like you were mid-stream on [task]. There are uncommitted changes in [files]. Pick up where you left off?"

Use AskUserQuestion:
- **Yes, continue** — load the relevant `decisions/{feature}.md`, compose a brief, done.
- **No, show me the board** — proceed to Step 3.

### Step 3: Render Dashboard

Print the feature status as a formatted table:

```
  MacTerminal — Session Start

  FEATURE AREAS
  ┌────────────────┬───────────┬────────────────────┐
  │ Area           │ Status    │ Next move          │
  ├────────────────┼───────────┼────────────────────┤
  │ Canvas Types   │ exploring │ WebKit prototype   │
  │ Sidebar        │ exploring │ File browser       │
  │ Tab/Splits     │ parked    │ Keyboard nav       │
  │ Browsing UX    │ planned   │ Scrollbar markers  │
  └────────────────┴───────────┴────────────────────┘
```

Read the feature names, statuses, and next moves from `feature-status.yml`. Adapt the table to whatever features exist — don't hardcode MacTerminal's features.

### Step 4: Ask Work Mode

Use AskUserQuestion:

> What mode feels right today?

Options:
- **Build feature** — Pick up or start building a feature
- **Polish / UX** — Details, refinement on existing features
- **Harden** — Tests, edge cases, stability
- **Architecture** — Framework, process, planning
- **Brainstorm** — Explore ideas, no commitment

### Step 5: Ask Feature Area (if applicable)

If the chosen mode involves a specific feature area (Build, Polish, Harden), ask which area using AskUserQuestion. List the features from `feature-status.yml`.

For Architecture and Brainstorm, the user may or may not want a specific area — ask with an "Open / cross-cutting" option.

### Step 6: Load Decisions and Compose Brief

Read `.continuity/decisions/{chosen-feature}.md` if a feature was selected.

Compose a focused brief (~500 tokens max) containing:

1. **What the user chose** — mode and area
2. **Current status** — from the YAML
3. **Key decisions** — from the "Decided" section, so the main Claude works within established choices
4. **Open questions** — from the "Open" section, so the main Claude is aware of unresolved issues
5. **Contextual flags** — use your judgment. If an open question is directly relevant to the chosen work, flag it. If a past decision might need revisiting given the chosen mode, mention it. If nothing needs flagging, say nothing. Be a thoughtful project manager, not a checklist.
6. **Relevant file paths** — if you can infer them from the decisions or YAML

### Step 7: Return Brief

Output the brief as your final response. The main session will receive this as context to begin working.

## Guidelines

- Keep the dashboard clean and scannable. No prose in the table.
- Keep the brief concise. The main session doesn't need the full decision history — just what's relevant to the chosen work.
- The contextual flags should be 0-2 sentences. If you're writing more, you're over-thinking it.
- If `feature-status.yml` is empty or missing features, that's fine — just show what's there and suggest the user add features during wrap-up.
- The work modes are about *energy and intent*, not strict categories. Don't gatekeep — if someone picks "Build" but the conversation drifts into brainstorming, that's fine.
