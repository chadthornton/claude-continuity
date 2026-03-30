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

### Step 2: Detect Re-entry Mode

Determine which of three modes applies. This shapes the entire flow.

**Compute the mode from signals (check in this order):**

1. If `in_progress` is set AND `last_session.date` is today or yesterday AND (`handoff.md` exists OR uncommitted changes) → **fast resume**
2. If `in_progress` is set, OR (uncommitted changes exist AND last session < 3 days ago) → **resumed session**
3. If `last_session.date` is null or ≥ 3 days ago → **cold return**
4. Otherwise (recent session, clean stop) → **next session**

Then jump to the matching flow below.

---

### Fast Resume Flow

**Triggers when ALL of these are true:**
- `in_progress` is set in feature-status.yml
- `last_session.date` is today or yesterday
- A `handoff.md` file exists OR there are uncommitted changes (`git diff`)

The user was just here and left mid-stream. Don't show a dashboard. Don't ask questions. Get them back to work immediately.

1. Read `.continuity/handoff.md` if it exists (the `<first-action>` block has the next step)
2. Read `decisions/{feature}.md` for the in-progress feature
3. Read the `next_steps` list from feature-status.yml for the in-progress feature
4. Compose a single brief:

> Resuming **{feature}**. Last: {last_session.summary}. Next: {first action from handoff, or first not-done next_step}.
>
> Key decisions: {1-2 most recent from decisions file}
>
> Say "board" if you want the full dashboard instead.

That's it. No AskUserQuestion. No mode selection. The "board" escape hatch is a plain text instruction, not a prompt — the user types it if they want it, otherwise work begins immediately.

**If Fast Resume conditions are NOT all met**, fall through to the Resumed Session Flow below.

---

### Resumed Session Flow

The user was recently here but conditions for Fast Resume aren't fully met (e.g., clean stop with `in_progress` set but no handoff or uncommitted changes). Still minimize friction.

**Skip the dashboard entirely.** Show the in-progress feature, its status, and progress through `next_steps`.

If `next_steps` contains objects with `done` fields, show a progress display:

> Picking up **standalone-app** (step 3 of 7). Steps 1–2 are done:
> ~~1. Create AppKit app target~~
> ~~2. Wire up WKWebView~~
> **3. Add dual-render toggle** ← you're here
> 4. Test with sample markdown
> 5. Hook up menu bar controls
> ...

If `next_steps` contains plain strings (no `done` field), show the full list as-is — progress tracking isn't available, but the list still provides direction. Present the first item as "Top priority" and the rest as a numbered list.

Use AskUserQuestion:
- **Continue here** — load the relevant `decisions/{feature}.md`, compose a brief with remaining steps only. Done.
- **No, show me the board** — proceed to the Next Session Flow (Step 3 onward).

---

### Next Session Flow

Recent work, clean stop. Light triage — show the board, make a recommendation, get going.

#### Step 3: Render Dashboard

Print the feature status as a formatted table.

**If any feature has a `phase` field**, sort features by phase ascending (features without a phase sort after phased features) and include a `#` column:

```
  Project Name — Session Start

  FEATURE AREAS
  ┌───┬────────────────────┬───────────┬──────────────────────────┐
  │ # │ Area               │ Status    │ Next move                │
  ├───┼────────────────────┼───────────┼──────────────────────────┤
  │ 1 │ standalone-app     │ building  │ Dual-render toggle       │
  │ 2 │ settled-detection  │ planned   │ Auto-detect settled      │
  │ 3 │ chat-layout        │ planned   │ Chat timeline + input    │
  │ 4 │ pattern-polish     │ planned   │ Permissions, collapsing  │
  └───┴────────────────────┴───────────┴──────────────────────────┘
```

**If no features have `phase`**, render without the `#` column (today's format):

```
  Project Name — Session Start

  FEATURE AREAS
  ┌────────────────┬───────────┬────────────────────┐
  │ Area           │ Status    │ Next move          │
  ├────────────────┼───────────┼────────────────────┤
  │ Canvas Types   │ exploring │ WebKit prototype   │
  │ Sidebar        │ exploring │ File browser       │
  │ Tab/Splits     │ parked    │ Keyboard nav       │
  └────────────────┴───────────┴────────────────────┘
```

Read the feature names, statuses, and next moves from `feature-status.yml`. Adapt the table to whatever features exist — don't hardcode any project's features.

If there is a `workflows` section in the YAML, render a second table:

```
  WORKFLOWS
  ┌────────────────────┬─────────────┬────────────────────────┐
  │ Workflow           │ Last run    │ Trigger                │
  ├────────────────────┼─────────────┼────────────────────────┤
  │ Permission Audit   │ 3d ago      │ Weekly or after drift  │
  │ Tool Usage Review  │ never       │ 500+ new log entries   │
  └────────────────────┴─────────────┴────────────────────────┘
```

Workflows differ from features: they don't have a build lifecycle (exploring → building → polishing). They are repeatable operations. When a user picks a workflow, load its `steps` list as the work guide and its `artifacts` as relevant file paths.

#### Step 4: Ask What To Work On

**Phase frontier logic (when phases exist):**

Compute the "frontier" — the lowest phase number where the feature's status is NOT `polishing` or `parked` (i.e., the phase still has active work to do). Features at the frontier are **workable**. Features above the frontier are **blocked**.

- If exactly one feature is at the frontier and all other phased features are above it, **auto-recommend** instead of asking:
  > "Phase 1 (standalone-app) is the active frontier. Phases 2–4 are blocked until it progresses. Start there?"
  >
  > Use AskUserQuestion: **Yes, start there** / **No, show me all options**
  >
  > If "No," fall through to the full list below.

- If multiple features share the frontier phase, present them normally — they're parallel work.

**Full options list (no phases, or user asked for all options):**

Present a single unified list of all workable items — features and workflows together. Use AskUserQuestion.

Build the options list dynamically from `feature-status.yml`:
- Each feature becomes an option: **"{name}"** with description "{status} — {next}"
- If phases exist and a feature is above the frontier, append `(blocked by phase {N})` to the description
- Each workflow becomes an option: **"{name}"** with description "Workflow — {summary}" (append "last run: {last_run}" or "never run" if available)
- Add **"Brainstorm / explore"** as a final catch-all option

The user can always pick a blocked feature — phases are recommendations, not gates.

#### Step 5: Load Context For Chosen Work

Once the user picks, determine whether it's a feature or a workflow:

**If feature:** Ask what mode feels right (Build / Polish / Harden). Then load `decisions/{feature}.md` and compose the brief.

**If workflow:** Skip the mode question — workflows have their own steps. Load the workflow's `steps` list as a numbered action plan, and `artifacts` as relevant file paths. Load `decisions/{workflow-name}.md` if it exists.

#### Step 6: Load Decisions and Compose Brief

Read `.continuity/decisions/{chosen-feature}.md` if a feature was selected.

Compose a focused brief (~500 tokens max) containing:

1. **What the user chose** — mode and area
2. **Current status** — from the YAML
3. **Next steps** — if the feature has `next_steps` in the YAML, display them as a numbered list. If steps have `done` fields, show only the remaining (not-done) steps. If no `next_steps` exist, fall back to the `next` field.
4. **Key decisions** — from the "Decided" section, so the main Claude works within established choices
5. **Open questions** — from the "Open" section, so the main Claude is aware of unresolved issues
6. **Contextual flags** — use your judgment. If an open question is directly relevant to the chosen work, flag it. If a past decision might need revisiting given the chosen mode, mention it. If nothing needs flagging, say nothing. Be a thoughtful project manager, not a checklist.
7. **Relevant file paths** — if you can infer them from the decisions or YAML

#### Step 7: Return Brief

Output the brief as your final response. The main session will receive this as context to begin working.

---

### Cold Return Flow

It's been a while. The user needs orientation, not just a menu.

#### Step 3c: Render Dashboard

Same as Next Session Flow Step 3 (phase-aware table). But before asking what to work on, add a "Since you've been away" block:

> **Since you've been away** (last session: Mar 10)
> - Last session worked on **standalone-app**: "Got WKWebView rendering, dual-mode toggle wired up"
> - Recent commits: `a1b2c3d Add dual render toggle`, `e4f5g6h Fix WebKit content sizing`
> - Open questions still hanging: "How to handle keyboard focus when WebView is active"

Pull this from:
- `last_session.summary` and `last_session.feature` in the YAML
- `git log --oneline -5`
- The "Open" section of `decisions/{last_session.feature}.md` if it exists

#### Step 4c: Ask What To Work On

Use AskUserQuestion with options:
- **Pick an area** — proceeds to the normal Step 4 options list (phase-aware)
- **Refresher on {last_session.feature}** — loads that feature's decisions file, summarizes decided + open items, then proceeds to normal pick flow
- If another feature is at the frontier and differs from last session's feature, offer: **Refresher on {frontier feature}**

After the refresher (if chosen), proceed to Step 4's normal options list.

Then continue with Steps 5–7 as in the Next Session Flow.

---

## Edge Cases

### No .continuity/ directory
The project hasn't been initialized. Tell the user:
> "This project doesn't have continuity tracking set up yet. Run `/continuity-init` to create a `.continuity/` directory with your feature areas. It takes about a minute."

Don't proceed with the triage flow — there's nothing to show.

### Fresh init — all features are "planned" with empty decisions
This is normal for a new project. Show the dashboard (even if everything says "planned"), skip the contextual flags (there's no history to reference). If phases exist and there's a clear phase 1, auto-recommend it. Otherwise narrate briefly:
> "Fresh project — no history yet. Everything is in the planning stage. What feels right to start with?"

### feature-status.yml exists but has no features
The file was created but never populated. Suggest:
> "Your `.continuity/feature-status.yml` exists but has no feature areas defined. Want to add some now, or run `/continuity-init` to set them up interactively?"

### Decisions file missing for chosen feature
The user picks a feature area but `decisions/{feature}.md` doesn't exist yet. That's fine — create it during wrap-up. For now, compose the brief without decision context and note:
> "No decision history for this area yet — starting fresh."

### last-activity.txt is stale but no uncommitted changes
The wrap-up didn't run last time, but the user committed their work or it was a brainstorm session with no code changes. Don't alarm — just note it lightly:
> "Last session didn't run wrap-up, but no uncommitted changes detected. Decisions from that session may not be captured."

### Multiple signals of mid-stream work
`in_progress` is set AND there are uncommitted changes AND last-activity.txt shows recent file touches. Present all the signals together rather than asking about each one:
> "Looks like you were mid-stream on [task]. There are uncommitted changes in [files], and last session touched [other files]. Pick up where you left off?"

### User invokes startup but clearly just wants to ask a quick question
If the user's message includes a specific question alongside "startup" or "what should I work on," use judgment. They might want the triage, or they might want to skip it and just ask their question. When in doubt, offer:
> "Want to run the full triage, or just dive in?"

### Mixed phase and non-phase features
Some features have `phase`, others don't. Sort phased features first (by phase number), then non-phased features after. Non-phased features are always workable — they're outside the phase sequence.

## Guidelines

- Keep the dashboard clean and scannable. No prose in the table.
- Keep the brief concise. The main session doesn't need the full decision history — just what's relevant to the chosen work.
- The contextual flags should be 0-2 sentences. If you're writing more, you're over-thinking it.
- If `feature-status.yml` is empty or missing features, that's fine — just show what's there and suggest the user add features during wrap-up.
- The work modes are about *energy and intent*, not strict categories. Don't gatekeep — if someone picks "Build" but the conversation drifts into brainstorming, that's fine.
- The three re-entry modes should feel natural, not mechanical. Don't announce "Detected: cold return mode." Just adapt the flow.
