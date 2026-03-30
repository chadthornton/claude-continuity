---
name: checkpoint
description: Save decisions and progress mid-session without ending anything. Quick context save — session continues after. Use when user says "checkpoint", "save progress", "save what we've decided", or "save state" mid-session.
allowed-tools: Agent, Read, Write, Edit, Bash, Glob
---

# Mid-Session Checkpoint

Save what's been decided and where things stand, without ending the session. This is a lighter, faster version of `/wrap-up` — no handoff block, no status changes, no questions. Just capture and continue.

## Prerequisites

The project must have a `.continuity/` directory with `feature-status.yml`. If not, suggest `/continuity-init`.

## Flow

**Run this as a subagent** to protect the main session's context. The subagent does the work and returns a 2-3 line confirmation. This is critical — the same pattern `/startup` uses.

### Step 1: Infer the Active Feature

Determine which feature to checkpoint. Check in order:
1. `in_progress` field in `feature-status.yml` — if set, use that feature
2. `last_session.feature` — if recent (today), use that
3. Conversation context — what has the user been working on?

**Do not ask the user.** Zero questions. If you genuinely can't determine the feature, checkpoint the most recently active one and note it in the confirmation.

### Step 2: Extract from Conversation

Scan the current conversation for:
- **Decisions made** — approaches chosen, alternatives rejected, constraints discovered. Each needs a *why* (one sentence rationale), not just the *what*.
- **Open questions raised** — things that came up but weren't resolved
- **Questions resolved** — open questions from the decisions file that were answered in this session
- **Step progress** — any `next_steps` items that were completed

If there's a recent git commit, read its message for additional decision context. But don't require a commit — the conversation is the primary source.

### Step 3: Update decisions/{feature}.md

Read the current file and:
- **Append** new decisions to the `## Decided` section (with rationale)
- **Append** new open questions to the `## Open` section
- **Remove** resolved open questions (or move to Decided if they became decisions)
- **Prune** if the file exceeds ~30 lines — remove old absorbed decisions that are now obvious from the code

### Step 4: Update feature-status.yml

Update **only these fields** for the active feature:
- `last_session.date` — today
- `last_session.summary` — one sentence about the session so far
- `last_session.feature` — the feature being checkpointed
- `next_steps` — mark completed steps as `done: true`, add new steps at the end
- `next` — update if the next move has changed

**Do NOT change:**
- `status` (exploring/building/etc.) — that's a wrap-up decision
- `in_progress` — session is continuing, don't clear it
- `summary` — the feature's overall summary doesn't change mid-session

### Step 5: Check Context Health

After updating files, check the proxy diagnostics to estimate current context usage. Use the `proxy_diagnostics` MCP tool if available, or check the conversation's approximate size from the context.

Categorize:
- **Low** (under 60k tokens): Plenty of room
- **Medium** (60k-120k tokens): Getting full, clearing soon would help
- **High** (over 120k tokens): Should clear soon to avoid compaction

### Step 6: Confirm With Context Nudge

Return a brief confirmation to the main session. Three lines max:

```
Checkpointed {feature}: {N} decisions saved, {N} questions added.
Next: {updated next field}
Context: ~{N}k tokens. {nudge}
```

The nudge varies by context level:
- **Low:** "Plenty of room — keep going."
- **Medium:** "Getting full. You could `/clear` safely — everything important is saved."
- **High:** "Running hot. Recommend `/clear` now — your progress is checkpointed. Run `/startup` after to resume."

Or if nothing meaningful to capture:

```
Checkpointed {feature}: no new decisions found. Status unchanged.
Context: ~{N}k tokens. {nudge}
```

## Guidelines

- **Zero questions asked.** This must complete without user input.
- **Under 30 seconds.** If it takes longer, you're doing too much.
- **Subagent execution.** Protect the main session's context budget.
- **Decisions need rationale.** "Use X" is not a decision. "Use X — because Y" is.
- **Prune, don't accumulate.** The decisions file is a living doc, not an append-only log.
- **Session continues after.** This is NOT a wrap-up. Don't write handoff blocks or change feature status.
