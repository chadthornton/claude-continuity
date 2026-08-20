---
name: continuity-prune
description: Propose prunes for continuity state that has gone stale or over-budget. Lists candidates with reasons; you confirm before anything is removed. Use when decision files have grown past ~30 lines, when features are parked/absorbed, or when the board feels cluttered.
allowed-tools: Read, Write, Edit, Bash, Glob, AskUserQuestion
---

# Continuity Prune

Keep continuity state small and true. This command finds decisions, features, and notes that have likely outlived their usefulness and **proposes** removing them. It never deletes on its own — you confirm first. Git history is the archive, so anything removed stays recoverable via `git log`.

## Prerequisites

The project must have a `.continuity/` directory with `feature-status.yml`. If not, suggest `/continuity-init`.

## Flow

### Step 1: Scan for Prune Candidates

Read `.continuity/feature-status.yml` and every file in `.continuity/decisions/`. Flag candidates in these categories — each candidate needs a one-line *reason*, not just a flag:

**Over-budget decision files** (the primary target):
- Any `decisions/{feature}.md` over ~30 lines. Within it, flag specific `## Decided` items that are old and fully absorbed into the codebase (the code now *is* the decision — the rationale no longer needs restating).
- `## Ruled out` entries whose dead-end code path no longer exists.
- Resolved-looking `## Open` items that were never cleared.

**Stale feature-status entries:**
- Features `parked` or `superseded` for a long time with no recent `last_session` activity — candidates to drop or archive-by-removal.
- Completed `next_steps` (`done: true`) under a feature that has since shipped — the progress trail has served its purpose.
- `gotchas` entries that are no longer true, or that duplicate a decision now in the code.
- `blind_spots` are session-scoped and self-replace — don't propose pruning them here.

**Cross-checks:**
- A `## Decided` item duplicated by a `gotcha` or by CLAUDE.md — keep one home, propose removing the copy.
- `blocked_by` edges pointing at a feature that's already `polishing`/`parked`/`superseded` — the block is dead and should be removed.

Use judgment. If nothing is stale and every file is under budget, say so and stop — a clean state needs no pruning.

### Step 2: Present the Proposal

Group candidates by file. Show each with its reason. Be specific enough that the user can judge without opening the files:

```
Prune proposal — .continuity/

decisions/canvas-types.md (41 lines → ~26):
  − [Decided] "Use CALayer for the grid overlay — cheaper than subviews"
      reason: shipped 3 sessions ago, now obvious from CanvasGrid.swift
  − [Ruled out] "Tried Core Animation groups — janky on resize"
      reason: the resize path was rewritten; this dead end can't recur

feature-status.yml:
  − feature "legacy-importer" (parked since Feb, no activity)
  − gotcha "staging DB needs VPN" — reason: staging moved to public endpoint

Nothing to prune in: decisions/sidebar.md, decisions/chat-layout.md
```

### Step 3: Confirm

Ask the user how to proceed. Use AskUserQuestion:
- **Apply all** — make every proposed removal
- **Let me pick** — go through candidates and apply only the ones the user approves
- **Cancel** — change nothing

Never remove anything before this confirmation. The human curates; this command only advises.

### Step 4: Apply and Report

For approved removals, edit the files. Then print a short summary:

```
Pruned:
  decisions/canvas-types.md — 41 → 26 lines (−2 decided, −1 ruled out)
  feature-status.yml — dropped legacy-importer, 1 stale gotcha

Recover anything via: git log -p .continuity/
```

If the user chose Cancel, confirm that nothing changed.

## Guidelines

- **Propose, never presume.** Auto-deletion violates the human-curates bet. Always confirm.
- **Reason per candidate.** "Old" is not a reason. "Shipped 3 sessions ago, now obvious from the code" is.
- **Absorbed ≠ forgotten.** A decision is safe to prune when the code makes it self-evident, not merely because it's old. When unsure, keep it.
- **Git is the safety net.** Say so in the report — it's what makes aggressive pruning safe.
- **Light touch.** This should take under a minute. If the proposal is huge, present the top candidates and note the rest rather than dumping everything.
