# Continuity System Design Brief

## The Problem

Working with Claude Code across sessions on a long-running project (MacTerminal) requires maintaining continuity of **context, direction, and decisions** — not just task state. The current system works but has specific failure modes.

### What works today
- **MEMORY.md** captures stable operational facts (architecture, build commands, preferences). A fresh Claude can build without breaking things.
- **Handoff block** in PLAN.md gives an atomic next task with verification steps. A fresh Claude can start working immediately on a well-scoped unit.
- **CLAUDE.md files** set behavioral constraints and project context.

### What breaks down

1. **Handoff happens too late.** The handoff document gets written at session end, under context pressure. By then, the Claude writing it is degraded and the human is impatient. The handoff should be a natural byproduct of working, not a ceremony.

2. **Direction drift is invisible.** Priorities shift through brainstorm sessions, side chats, and evolving thinking — but the plan still reflects the old priorities until someone explicitly rewrites it. A fresh Claude reads a plan that says "keyboard nav between panes" when the actual priority is now "WebKit canvas types."

3. **Decision rationale is lost.** MEMORY.md captures *what* (architecture facts) and the handoff captures *what's next* (tasks), but neither captures *why* — the reasoning behind decisions, what was explored and rejected, or what's still open. A fresh Claude has to rediscover context that a previous Claude already worked through.

4. **Side-chat insights don't flow back.** Brainstorming happens in separate sessions (sometimes with different Claude instances). Findings from those sessions have no structured path back into the main continuity system. They live in the human's head or in stale chat transcripts.

5. **Context budget anxiety.** Loading continuity documents consumes context that could be used for work. The more comprehensive the continuity system, the less room for actual building. This creates a tension: be thorough (and lose working context) or be minimal (and lose continuity).

## Success Criteria

A better system should satisfy these properties:

### Must have
- **S1: Incremental, not ceremonial.** Continuity state updates as a natural part of working, not as a separate step the human has to remember to trigger.
- **S2: Context-budget aware.** A fresh Claude doing a focused build task should not need to load the full history. Load what's needed, defer the rest.
- **S3: Direction-current.** The system reflects actual current priorities, not the priorities from when someone last remembered to update the plan.
- **S4: Decision-preserving.** A fresh Claude can understand *why* things are the way they are, not just *what* the current state is. Includes what was tried and rejected.
- **S5: Side-chat friendly.** Insights from brainstorm sessions have a clear, low-friction path into the continuity system.

### Nice to have
- **S6: Prunable.** Old decisions and context that are no longer relevant can be removed without breaking anything.
- **S7: Automation-friendly.** Hooks or skills can assist with maintenance, but the system shouldn't *depend* on automation to function.
- **S8: Accident-proof.** If compaction happens unexpectedly, the full transcript is preserved somewhere recoverable.

### Anti-goals
- **A1: No heavyweight infrastructure.** No databases, no embedding systems, no Docker. Markdown files and shell scripts only.
- **A2: No context bloat.** The continuity system should not routinely consume more than ~15-20% of a session's context on startup.
- **A3: No false precision.** Don't track things at a granularity that creates maintenance burden without proportional value. A few sentences about a decision are better than a structured schema nobody fills out.

## Constraints

- Human is a product designer, not an engineer. The system must be low-maintenance from the human's side.
- Multiple Claude instances work on the project (main builder + brainstorm side chats). They share the filesystem but not conversation context.
- Sessions typically don't compact — they end and restart fresh. The handoff moment is session end, not compaction.
- The project is evolving from "terminal app" toward "workspace manager" — the continuity system needs to handle shifting scope gracefully.

## Open Questions

1. **One file or many?** A single PLAN.md is simple but may grow unwieldy. Multiple files scale better but risk context budget overrun on startup. Is there a middle path — e.g., one file with sections that are explicitly marked "load on demand"?

2. **Who curates the decision log?** If it's append-only, it bloats. If it requires human curation, it won't happen. Can Claude curate it as part of the handoff process — pruning stale entries while adding new ones?

3. **How do side-chat insights get captured?** Is it enough to update MEMORY.md or PLAN.md at the end of a brainstorm session? Or does there need to be a more structured "merge" step?

4. **What triggers continuity updates during a session?** The Stop hook could prompt it, but that fires on every response. A PostToolUse hook on Write/Edit could track what changed. Or it could just be a norm: "before ending, update the decisions section."

5. **How does the handoff skill evolve?** Does it become a "session wrap-up" skill that updates decisions + priorities + the atomic next-task block? Or do we keep handoff-author focused on task handoff and add a separate mechanism for the broader context?
