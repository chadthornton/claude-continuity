# Continuity System Proposal

## Overview

A lightweight system for maintaining context, direction, and decision rationale across Claude Code sessions on long-running projects. Designed for a workflow where a product designer works with multiple Claude instances (main builder + brainstorm side chats) on an evolving project.

Companion document: `continuity-design-brief.md` (problem statement and success criteria).

## Design Principles

1. **Context-budget first.** The main session starts with a focused brief (~500 tokens), not a document dump. Heavier context is loaded selectively based on what the user chose to work on.
2. **Two light ceremonies, not one heavy one.** A startup triage at session start and a quick wrap-up at session end, rather than a panic handoff when context runs out.
3. **Smart narrator, not a checklist.** The startup agent reads past decisions and uses judgment about what to surface — flagging things that are relevant to this session, staying quiet when nothing needs attention.
4. **Separate what changes at different rates.** Stable facts (MEMORY.md), current status (YAML), and decision rationale (per-feature markdown) live in different files because they have different lifecycles.
5. **Fail gracefully.** If the wrap-up doesn't happen (abrupt exit, forgot), a SessionEnd hook captures minimal activity data automatically. The system degrades to "slightly stale" rather than "completely lost."

## File Structure

```
.claude/continuity/
├── feature-status.yml        # Dashboard data — status, next move per feature
├── last-activity.txt         # Auto-written by SessionEnd hook
└── decisions/
    ├── canvas-types.md       # Decided + open items for this feature
    ├── sidebar.md
    ├── tab-splits.md
    └── browsing-ux.md
```

### feature-status.yml

Machine-readable dashboard state. Updated by the wrap-up skill. ~20 lines.

```yaml
features:
  canvas-types:
    status: exploring       # exploring | building | polishing | parked | planned
    next: WebKit prototype
    summary: WKWebView as new SplitNode leaf type
  sidebar:
    status: exploring
    next: File browser (NSOutlineView)
    summary: Replace flat project list with directory tree
  tab-splits:
    status: parked
    next: Keyboard nav between panes
    summary: Functional — splits, tabs, drag-drop all working
  browsing-ux:
    status: planned
    next: Scrollbar conversation markers
    summary: UX concepts documented in browsing-ideas.md

in_progress: null           # Set when mid-stream on a task
                            # e.g., "Refactoring SplitNode to support generic pane types"

last_session:
  date: 2026-02-13
  summary: Designed continuity system (this proposal)
  feature: null             # Which feature area was worked on, if any
```

### decisions/{feature}.md

Per-feature context file. Carries both decided items and open questions, co-located because they're closely related (decisions create open questions; resolving open questions produces decisions). Curated by the wrap-up skill — old resolved items get pruned, new decisions and questions get added.

```markdown
# Canvas Types

## Decided
- WKWebView directly in AppKit, not SwiftUI hosting views.
  App is pure AppKit; bridging adds complexity for no gain.
- New leaf type in SplitNode enum alongside terminal panes.
  Extends existing split/tab architecture rather than replacing it.

## Open
- Keyboard focus: WKWebView aggressively captures input.
  Cmd+D/T/W shortcuts may not fire when web pane has focus.
  Need explicit first-responder management.
- Sandbox: requires "Outgoing Connections (Client)" entitlement.
  Not yet added to MacTerminal target.
- Memory: each WKWebView spawns a WebKit process.
  May need shared WKProcessPool if many web tabs open.
```

Guidelines for these files:
- Keep entries as brief prose, not structured schemas (anti-goal A3).
- "Decided" items should include the *why*, not just the *what*. One sentence of rationale is enough.
- "Open" items should describe the question and any known constraints.
- During wrap-up, prune decided items that are old and fully absorbed into the codebase (they live in MEMORY.md or the code itself at that point). Prune open items that have been resolved.
- Aim for each file to stay under ~30 lines. If it's growing past that, it's time to prune.

### last-activity.txt

Auto-written by the SessionEnd hook. Minimal machine-readable snapshot of what was happening when the session ended. The startup agent reads this to detect stale state or unfinished work.

```
session_end: 2026-02-13T16:45:00
feature: canvas-types
last_tool: Edit on SplitNode.swift
uncommitted_changes: true
files_touched: SplitNode.swift, ContentAreaViewController.swift
```

## Skills

### Startup Skill

Runs at the beginning of a session (invoked by user or automatically). Executes as a subagent to protect the main session's context budget.

**Inputs it reads:**
- `feature-status.yml` (~20 lines)
- `last-activity.txt` (if present)
- Recent git log (last 5 commits, via shell)
- `git diff --name-only` (uncommitted changes)

**Flow:**

```
1. Check for mid-stream work:
   - in_progress set in feature-status.yml?
   - Uncommitted changes detected?
   - last-activity.txt newer than feature-status.yml?

   If yes → "You were mid-stream on X. Pick up where you left off?"
            [Yes | No, show me the board]
            If yes → load decisions/{feature}.md for that feature
                   → hand off focused brief to main session
                   → done

2. Render dashboard:
   ┌────────────────┬───────────┬────────────────────┐
   │ Area           │ Status    │ Next move          │
   ├────────────────┼───────────┼────────────────────┤
   │ Canvas Types   │ exploring │ WebKit prototype   │
   │ Sidebar        │ exploring │ File browser       │
   │ Tab/Splits     │ parked    │ Keyboard nav       │
   │ Browsing UX    │ planned   │ Scrollbar markers  │
   └────────────────┴───────────┴────────────────────┘

3. Ask work mode:
   → [Build feature | Polish/UX | Harden | Architecture | Brainstorm]

4. If mode involves a feature area, ask which:
   → [Canvas Types | Sidebar | Tab/Splits | Browsing UX]

5. Load decisions/{chosen-feature}.md

6. Compose brief for main session (~500 tokens):
   - What the user chose (mode + area)
   - Current status and next move for that feature
   - Key decisions (so main Claude works within them)
   - Open questions (so main Claude is aware of unresolved issues)
   - Any contextual flags the agent judges worth surfacing
     (e.g., "the keyboard focus question will come up as soon
     as you start the WebKit prototype")
   - Relevant file paths

7. Return brief to main session.
```

The "contextual flags" step is the smart narrator — the agent reads the decided/open items and uses judgment about what's relevant to this specific session. Not a formal checklist, just an informed perspective.

### Wrap-up Skill

Runs at end of session (invoked by user). Evolves from the current handoff-author skill.

**What it updates:**

1. **feature-status.yml** — Update status, next move, summary, last_session fields for the feature that was worked on. Set or clear `in_progress`.

2. **decisions/{feature}.md** — Add new decisions with rationale. Add new open questions discovered during work. Prune items that are resolved or fully absorbed. Keep under ~30 lines.

3. **Handoff block** (if mid-stream) — Write/update a `<handoff>` block in PLAN.md with the atomic next task, following the existing handoff-author format. Only needed when stopping mid-task; clean stopping points don't need one.

**What it does NOT do:**
- Rewrite the full PLAN.md reference sections
- Update MEMORY.md (that's the auto-memory system's job)
- Generate a comprehensive session summary

The wrap-up should take < 1 minute. If it feels heavy, it's doing too much.

## Hooks

### SessionEnd Hook

**Purpose:** Automatic safety net for abrupt exits. Writes `last-activity.txt`.

**Implementation:** ~15 lines of bash.

```bash
#!/bin/bash
# .claude/hooks/session-end.sh
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
CWD=$(echo "$INPUT" | jq -r '.cwd')
CONTINUITY_DIR="$CWD/.claude/continuity"

mkdir -p "$CONTINUITY_DIR"

# Get git state
UNCOMMITTED=$(cd "$CWD" && git diff --name-only 2>/dev/null | head -10)
HAS_CHANGES=$( [ -n "$UNCOMMITTED" ] && echo "true" || echo "false" )

cat > "$CONTINUITY_DIR/last-activity.txt" << EOF
session_end: $(date -u +%Y-%m-%dT%H:%M:%S)
uncommitted_changes: $HAS_CHANGES
files_touched:
$UNCOMMITTED
EOF
```

**Hook config** (in `.claude/settings.json`):
```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/session-end.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

### PreCompact Hook

**Purpose:** Insurance — save the full transcript if compaction ever triggers accidentally.

**Implementation:** ~10 lines of bash.

```bash
#!/bin/bash
# .claude/hooks/pre-compact.sh
INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')
BACKUP_DIR="$HOME/.claude/transcript-backups"

mkdir -p "$BACKUP_DIR"
cp "$TRANSCRIPT" "$BACKUP_DIR/$(date +%Y%m%d-%H%M%S).jsonl"

# Keep only last 20 backups
ls -t "$BACKUP_DIR"/*.jsonl 2>/dev/null | tail -n +21 | xargs rm -f 2>/dev/null
```

## How It Addresses the Design Brief

| Criterion | How addressed |
|-----------|---------------|
| S1: Incremental | Two light ceremonies (startup + wrap-up) instead of one heavy handoff. SessionEnd hook as safety net for abrupt exits. |
| S2: Context-budget | Startup agent runs as subagent, reads ~50 lines total, hands off ~500 token brief. Main session stays clean. |
| S3: Direction-current | feature-status.yml is the source of truth, updated at wrap-up. Startup agent reads it fresh each session. |
| S4: Decision-preserving | Per-feature decisions files carry rationale + open questions. Startup agent includes relevant decisions in brief. Smart narrator flags what matters. |
| S5: Side-chat friendly | Any session can update feature-status.yml and the relevant decisions file. No special merge step — just edit the files. Add norm to CLAUDE.md for brainstorm sessions. |
| S6: Prunable | Decision files are curated during wrap-up. YAML fields overwritten. Nothing is append-only. |
| S7: Automation-friendly | Hooks assist but system works with manual file edits. Skills help but aren't required. |
| S8: Accident-proof | PreCompact hook saves transcript. SessionEnd hook saves activity state. |
| A1: No heavy infra | Markdown + YAML + two bash scripts. |
| A2: No context bloat | Subagent startup keeps main context clean. Per-feature loading means you only get what's relevant. |
| A3: No false precision | Prose decisions, not structured schemas. Brief narration, not formal checklists. |

## Migration from Current System

1. Create `.claude/continuity/` directory and initial files based on current PLAN.md content.
2. Move feature-relevant information from PLAN.md reference sections into per-feature decision files.
3. Build and test the two hooks (SessionEnd + PreCompact).
4. Build the startup skill.
5. Evolve handoff-author into the wrap-up skill.
6. Add a line to CLAUDE.md instructing brainstorm sessions to update continuity files.
7. PLAN.md becomes lighter — just the `<handoff>` block (for mid-stream tasks) and the architecture reference (which is stable and rarely loaded).

## Open Questions for v1

1. **Where do these files live?** `.claude/continuity/` keeps them with the Claude config but outside the repo. Alternatively they could live in the project directory (e.g., `xterm-woes/.continuity/`). Tradeoff: repo-local is more portable, `.claude/` is more private.

2. **Feature area lifecycle.** When is a new feature area added? When is one archived? For now, manually — the wrap-up skill could suggest adding a new area if work doesn't fit existing ones.

3. **Cross-feature decisions.** Some decisions span features (e.g., "stay pure AppKit"). These could live in a `decisions/_general.md` or in MEMORY.md. Start without this and see if it's needed.

4. **Tuning the smart narrator.** How aggressive should the startup agent be about surfacing past decisions? Start conservative (only flag things directly relevant to the chosen task) and tune based on experience.

5. **MacTerminal integration.** Long-term, the dashboard could render in MacTerminal's sidebar rather than as CLI text. This is a feature area unto itself — don't block v1 on it.
