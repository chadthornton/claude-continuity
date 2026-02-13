# Design Conversation — 2026-02-13

Origin session for the claude-continuity plugin. Captured from a Claude Code conversation in the xterm-woes project.

## Starting Point

Chad raised two issues with the current handoff system (handoff-author plugin):

1. **Handoffs happen too late** — written at session end under context pressure, often rushed or incomplete.
2. **Phase-based plans don't match reality** — priorities shift through brainstorm side-chats but the plan still reflects old priorities. Wanted to move to a feature-areas model.

Current priorities for MacTerminal had shifted away from tab/split keyboard navigation toward:
- WebKit canvas types (WKWebView as a new pane type)
- Sidebar file browser (NSOutlineView directory tree, VS Code style)

## Research Phase

Launched parallel research agents to investigate:

### Claude Code hooks & context management
- 14 lifecycle hook events available (SessionStart, Stop, PreCompact, SessionEnd, etc.)
- PreCompact fires before auto-compaction, receives transcript_path — can archive full conversation
- SessionEnd fires on exit, can run shell scripts for cleanup
- Async hooks (Jan 2026) run in background without blocking
- Claude Code now has native "session memory" (v2.1.31, Feb 2026) — automatic background extraction of key info

### Community approaches
- **Continuous-Claude-v3**: Maximalist — PostgreSQL, FAISS, 109 skills, 30 hooks. "Compound, don't compact."
- **Claude-Mem**: Progressive summarization, ~600 token median injection
- **Claude Context OS**: Minimalist — 47-line CLAUDE.md, everything else externalized and loaded on demand
- **Multiple `/handoff` + `/pickup` implementations**: Independent convergence on this pattern

### Key finding from research
People who are happiest keep it simple. No evidence that complex memory systems actually improve outcomes. Community is saturated with memory tools, starved for proof.

### Side-chat problem
Least-solved problem in the space. No good solution exists for merging brainstorm insights back into a build workflow. Boris Cherny (Claude Code creator) just uses shared CLAUDE.md + auto memory as the unification layer.

## Design Evolution

### Three-layer model (initial idea)
1. MEMORY.md — stable facts
2. PLAN.md — feature areas + status + "do this next"
3. JOURNAL.md — chronological decisions, research, open questions

Chad noted JOURNAL.md overlaps with what handoff-author already does. Question became: what shape should this take?

### Information lifecycle insight
Different types of info change at different rates and serve different readers:
- Architecture facts → rarely change → every Claude reads them
- Current priorities → change when direction shifts → next Claude starting work
- Decision rationale → every session that makes decisions → a Claude that needs context
- Open questions → constantly → brainstorm sessions

### Startup skill idea (breakthrough)
Chad proposed: instead of loading documents, have an active triage step at session start. A subagent that reads lightweight state and presents a dashboard + recommendation.

Key insight: the startup should include **work modes** — not just "which feature" but "what energy do I have":
- Build feature
- Polish / UX details
- Harden (tests, stability)
- Architecture / planning
- Brainstorm

These serve as an emotional compass, not just project management. Lets the user gravitate toward where they want to focus.

### Dashboard design
Settled on: formatted table printed to terminal, then AskUserQuestion for mode → area selection. The startup agent narrates 2-3 sentences of context bridge (connecting last session to this one) rather than dumping a "Recent Context" section.

### Design brief
Wrote formal success criteria (see `continuity-design-brief.md`). Key criteria:
- S1: Incremental, not ceremonial
- S2: Context-budget aware
- S3: Direction-current
- S4: Decision-preserving
- S5: Side-chat friendly

### Gap analysis
Checked proposal against brief. Two gaps identified:

**Gap 1: Fragile session endings.** If wrap-up doesn't run, status goes stale.
- Solution: SessionEnd hook auto-writes `last-activity.txt` with minimal git state.

**Gap 2: Decision rationale has no home.**
- Solution: Per-feature `decisions/{feature}.md` files carrying both "Decided" and "Open" sections.
- Co-locating decisions and open questions preserves their relationship (decisions create open questions; resolving questions produces decisions).

### Smart narrator vs checklist
Debated whether to force a formal preflight checklist reviewing past decisions. Settled on: the startup agent reads the decisions file and uses judgment about what to surface. "Thoughtful project manager, not a checklist." The co-location of decided + open items gives the agent the data; the brief gives it the delivery mechanism.

Can be tuned over time — start conservative, add structure if decisions aren't being considered.

## Final Design

### Files (per-project, in `.continuity/`)
- `feature-status.yml` — dashboard data, ~20 lines
- `decisions/{feature}.md` — decided + open items per feature, curated, ~30 lines each
- `last-activity.txt` — auto-written by SessionEnd hook
- `handoff.md` — only when mid-stream, written by wrap-up skill

### Skills
- **startup** — reads status + git + last-activity, renders dashboard, asks mode/area, loads relevant decisions, hands off focused brief
- **wrap-up** — updates feature-status.yml + relevant decisions file, writes handoff if mid-stream

### Hooks
- **SessionEnd** — writes `last-activity.txt` (automatic safety net)
- **PreCompact** — copies transcript JSONL to `~/.claude/transcript-backups/` (insurance)

### Anti-goals
- No databases, embeddings, Docker
- No context bloat (< 15-20% of session on startup)
- No false precision (prose over schemas)
- No scoring/grading on wrap-up (unlike handoff-author's 80% threshold)

## Open Questions Remaining

1. Feature area lifecycle — when to add/archive areas
2. Cross-feature decisions — may need a `_general.md` if they come up
3. Tuning the smart narrator — how aggressive to be about surfacing decisions
4. MacTerminal integration — long-term, dashboard could render in the sidebar
5. Decision log evidence — experiment: does forcing consideration of past decisions improve outcomes?
