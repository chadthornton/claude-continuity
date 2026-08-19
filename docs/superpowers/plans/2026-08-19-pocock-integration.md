# Pocock Integration + Continuity Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Pocock/Superpowers/Continuity skills into a de-conflicted routing table, and add three optional Continuity enhancements (`blocked_by` edges, decision/task markers, fog-of-war section).

**Architecture:** One global CLAUDE.md routing rule (no logic, just a trigger→skill table). Three additive edits to Continuity's source skills/templates, each behaving identically when the new field/section/marker is absent. Verified via scratch-copy before touching source.

**Tech Stack:** Markdown skill files, YAML templates. No code/runtime — these are prompt-instruction documents read by Claude.

**Spec:** `docs/superpowers/specs/2026-08-19-pocock-integration-design.md`

## Global Constraints

- **Source repo only:** all Continuity edits target `~/Projects/claude-continuity` — NEVER the plugin cache `~/.claude/plugins/cache/claude-continuity-local/...` (stale, clobbered on reload).
- **Additive + optional:** ~25 existing projects have populated `.continuity/` dirs. Every enhancement must produce byte-identical startup/wrap-up behavior when its field/section/marker is absent. No existing project's behavior may change.
- **Skill IDs verbatim:** copy exact IDs from the session skill listing. Confirmed prefix is `mattpocock-skills:` (not `mattpocock:`).
- **Routing biases, not gates:** de-confliction rows are preference statements; `tdd`/`diagnosing-bugs` stay model-invocable regardless.
- **Version:** bump `0.3.0` → `0.4.0`; roll the existing `[Unreleased]` retrospect entry into the 0.4.0 cut.
- **Verification level:** scratch-copy test passes BEFORE committing source edits.

---

### Task 1: Global skill-routing rule in ~/.claude/CLAUDE.md

**Files:**
- Modify: `~/.claude/CLAUDE.md` — append a `<rule name="skill-routing">` inside the existing `<rules>` block.

**Interfaces:**
- Consumes: nothing.
- Produces: nothing other tasks depend on. Standalone.

- [ ] **Step 1: Read the current `<rules>` block** to find the exact insertion point (end of the last `<rule>` before `</rules>`). Confirm the file uses `<rule name="...">` children.

- [ ] **Step 2: Verify each skill ID resolves.** For each of these, confirm it appears in the session's available-skills list verbatim: `superpowers:systematic-debugging`, `superpowers:test-driven-development`, `mattpocock-skills:code-review`, `mattpocock-skills:grilling`, `mattpocock-skills:prototype`, `mattpocock-skills:research`, `mattpocock-skills:domain-modeling`, `mattpocock-skills:codebase-design`, `mattpocock-skills:wizard`, `mattpocock-skills:resolving-merge-conflicts`, `claude-continuity:startup`, `claude-continuity:wrap-up`. If any differ, correct to the listed form.

- [ ] **Step 3: Append the rule.** Insert before `</rules>`:

```xml
<rule name="skill-routing">
When a task matches a trigger below, invoke the mapped skill (the using-superpowers gate already forces a pre-action skill check — this decides which skill it lands on). Rows marked "prefer" are de-confliction: both skills are model-invocable, so this states the canonical choice, it does not disable the other.

| Trigger (what you say / what's happening)      | Skill |
|------------------------------------------------|-------|
| bug, throwing, failing test, slow, regression  | superpowers:systematic-debugging (prefer over mattpocock-skills:diagnosing-bugs) |
| new feature or bugfix, build it test-first     | superpowers:test-driven-development (prefer over mattpocock-skills:tdd) |
| review a branch/PR/diff before merge           | mattpocock-skills:code-review |
| stress-test a plan/decision/idea               | mattpocock-skills:grilling |
| sanity-check a state model or UI feel          | mattpocock-skills:prototype |
| research a question against primary sources    | mattpocock-skills:research |
| pin down domain terms or record an ADR         | mattpocock-skills:domain-modeling |
| design or deepen a module's interface          | mattpocock-skills:codebase-design |
| walk a human through steps only they can do    | mattpocock-skills:wizard |
| resolve an in-progress merge/rebase conflict   | mattpocock-skills:resolving-merge-conflicts |
| start/end a session, "what should I work on"   | claude-continuity:startup / claude-continuity:wrap-up |

Not routed here (gated/user-invoked by design; call explicitly when wanted): mattpocock-skills tracker flow (to-tickets, wayfinder, triage, to-spec — need setup-matt-pocock-skills first), grill-me/loop-me/teach (interactive), claude-handoff (spins off a background agent).
</rule>
```

- [ ] **Step 4: Verify the edit.** Re-read the `<rules>` block; confirm the new rule is well-formed XML, inside `<rules>`, and no existing rule (RTK, etc.) was altered.

- [ ] **Step 5: Commit.** This file is in `~/.claude/` (not the continuity repo). Check whether `~/.claude` is a git repo (`git -C ~/.claude rev-parse` ); if yes, commit there; if no, note in the final summary that the CLAUDE.md edit is unversioned and skip the commit.

```bash
git -C ~/.claude rev-parse --is-inside-work-tree 2>/dev/null && git -C ~/.claude add CLAUDE.md && git -C ~/.claude commit -m "feat: add skill-routing rule (Pocock/Superpowers/Continuity de-confliction)" || echo "~/.claude not a git repo — CLAUDE.md edited but not committed"
```

---

### Task 2: Scratch-copy regression harness (AC2 + AC5 baseline)

**Files:**
- Create: `/private/tmp/claude-501/-Users-chadthornton-Projects-INSTALLATION-GARAGE-pocock-migration/eed85b24-808a-4be4-b2e0-32b40fbccae9/scratchpad/continuity-test/` — working copies of real `.continuity/` state to test against.

**Interfaces:**
- Consumes: real `.continuity/feature-status.yml` from `~/Projects/web-pinterest-quickmove` (has the 3-phase-1 cluster).
- Produces: two fixtures — `baseline/` (unmodified) and `enhanced/` (with new fields) — used by Tasks 3-5 to confirm regression-safety and new behavior.

- [ ] **Step 1: Copy a real project's continuity state into scratch.**

```bash
SCRATCH=/private/tmp/claude-501/-Users-chadthornton-Projects-INSTALLATION-GARAGE-pocock-migration/eed85b24-808a-4be4-b2e0-32b40fbccae9/scratchpad/continuity-test
mkdir -p "$SCRATCH/baseline" "$SCRATCH/enhanced"
cp -R ~/Projects/web-pinterest-quickmove/.continuity/* "$SCRATCH/baseline/" 2>/dev/null
cp -R ~/Projects/web-pinterest-quickmove/.continuity/* "$SCRATCH/enhanced/" 2>/dev/null
ls -R "$SCRATCH/baseline"
```

- [ ] **Step 2: Record the baseline startup behavior as a written expectation.** Read `baseline/feature-status.yml`. Manually trace the current `startup/SKILL.md` Step 4 frontier logic against it and write the expected workable/blocked set to `$SCRATCH/baseline-expectation.md` (e.g. "phase-1 features backend-api, board-cache-mru, frontend-ui all workable; phase-2 blocked"). This is the oracle Task 3 must not change.

- [ ] **Step 3: Build the enhanced fixture.** In `enhanced/feature-status.yml`, add `blocked_by: [backend-api]` to `frontend-ai`... (use the real feature name `frontend-ui`). In `enhanced/decisions/`, pick one decisions file (or create `enhanced/decisions/backend-api.md`) and add a `[decision]`-marked and a `[task]`-marked item under `## Open`, plus a `## Not yet specified` section with one fog item. Write `$SCRATCH/enhanced-expectation.md`: "frontend-ui NOT workable while backend-api is building; decision vs task distinguished in brief; fog item surfaced in cold-return."

- [ ] **Step 4: Commit the harness note into the continuity repo** (the fixtures stay in scratch; only a pointer is committed).

```bash
cd ~/Projects/claude-continuity
# no repo file yet — this task produces scratch fixtures only; nothing to commit here.
echo "Scratch fixtures built at $SCRATCH — used to verify Tasks 3-5."
```

---

### Task 3: `blocked_by` — template + startup frontier + wrap-up

**Files:**
- Modify: `~/Projects/claude-continuity/templates/feature-status.yml` — document optional `blocked_by`.
- Modify: `~/Projects/claude-continuity/skills/startup/SKILL.md` — Step 4 frontier clause.
- Modify: `~/Projects/claude-continuity/skills/wrap-up/SKILL.md` — Step 2 record `blocked_by`.

**Interfaces:**
- Consumes: `enhanced/feature-status.yml` fixture from Task 2.
- Produces: `blocked_by: [feature-name]` YAML convention that Task 5's plan-self-review references.

- [ ] **Step 1: Write the failing check.** Against `enhanced/feature-status.yml` (frontend-ui blocked_by backend-api, backend-api status building), trace the CURRENT startup frontier logic. Confirm it INCORRECTLY marks frontend-ui workable (no blocked_by handling exists yet). Record this "fail" in `$SCRATCH/task3-before.md`.

- [ ] **Step 2: Add `blocked_by` to the template.** In `templates/feature-status.yml`, under the `phase:` comment line for `example-feature`, add:

```yaml
    blocked_by: []          # Optional. Sibling feature names that must be polishing/parked/superseded before this is workable. Refines phase within a cluster.
```

- [ ] **Step 3: Add the frontier clause to startup.** In `skills/startup/SKILL.md` Step 4, "Phase frontier logic" paragraph, after the sentence defining workable/blocked, add:

```markdown
**Intra-phase blocking (`blocked_by`):** A feature may carry an optional `blocked_by: [feature-name, ...]` list. Even when its phase is at the frontier, the feature is workable only if every feature it lists is `polishing`, `parked`, or `superseded`. A feature with no `blocked_by` is unaffected — evaluate it exactly as before. In the options list, append `(blocked by {name})` to the description of any feature held back this way, and still allow the user to pick it (blocks are recommendations, not gates — same as phases).
```

- [ ] **Step 4: Add the wrap-up instruction.** In `skills/wrap-up/SKILL.md` Step 2, in the "If the session worked on a feature" bullet list, after the `next` bullet, add:

```markdown
- **blocked_by** (optional) — if this feature can't start until a sibling feature lands, set `blocked_by: [sibling-name]`. Only add it where a real dependency exists; most features need none. Remove the entry once the blocker is done.
```

- [ ] **Step 5: Verify the fix.** Re-trace the amended startup frontier logic against `enhanced/feature-status.yml`. Confirm frontend-ui is now marked blocked (backend-api is `building`, not in the done set). Confirm `baseline/feature-status.yml` (no blocked_by anywhere) produces the SAME workable set as `baseline-expectation.md` from Task 2 Step 2 — this is the AC2 regression gate. Record both in `$SCRATCH/task3-after.md`.

- [ ] **Step 6: Commit.**

```bash
cd ~/Projects/claude-continuity
git add templates/feature-status.yml skills/startup/SKILL.md skills/wrap-up/SKILL.md
git commit -m "feat: optional blocked_by intra-phase edges

Refines phase within same-phase clusters. Additive — features without
blocked_by evaluate exactly as before. Refs spec 2026-08-19."
```

---

### Task 4: Decision/task markers + fog-of-war section

**Files:**
- Modify: `~/Projects/claude-continuity/templates/decisions/_template.md` — document markers + fog section.
- Modify: `~/Projects/claude-continuity/skills/wrap-up/SKILL.md` — Step 3 marker + fog sub-step.
- Modify: `~/Projects/claude-continuity/skills/startup/SKILL.md` — Step 6 use markers; cold-return surfaces fog.

**Interfaces:**
- Consumes: `enhanced/decisions/*.md` fixture from Task 2.
- Produces: `[decision]`/`[task]` open-item convention and `## Not yet specified` section convention.

- [ ] **Step 1: Write the failing check.** Confirm the current `decisions/_template.md` has only `## Decided` and `## Open` (no marker guidance, no fog section) and that startup Step 6 treats all Open items identically. Record in `$SCRATCH/task4-before.md`.

- [ ] **Step 2: Update the decisions template.** Replace `templates/decisions/_template.md` contents with:

```markdown
# Feature Name

## Decided
(none yet)

## Open
<!-- Optionally prefix items to distinguish kinds:
     [decision] a question whose answer is a choice — resolve before building
     [task] queued work, nothing to decide
     Unmarked items are fine and render as before. -->
(none yet)

## Not yet specified
<!-- Optional. Decisions you can see coming but can't phrase precisely yet
     (fog of war). Distinct from feature-status blind_spots (backward-looking
     gotchas). Park the dim view here; it graduates into an Open item once sharp.
     Omit this section entirely if empty. -->
```

- [ ] **Step 3: Add marker + fog handling to wrap-up Step 3.** After the "Add new open questions" bullet block in `skills/wrap-up/SKILL.md` Step 3, add:

```markdown
**Optionally mark open items by kind.** If it clarifies triage, prefix an open item with `[decision]` (answer is a choice, resolve before building) or `[task]` (queued work). Unmarked items are fine — don't force markers.

**Capture fog (optional).** If a decision is clearly coming but you can't phrase it sharply yet, add one line to a `## Not yet specified` section in the decisions file. Don't invent fog — only record a real, not-yet-specifiable decision. This is the low-friction path for side-chat insights (design-brief S5).
```

- [ ] **Step 4: Add marker + fog usage to startup.** In `skills/startup/SKILL.md` Step 6, amend item 5 ("Open questions") to:

```markdown
5. **Open questions** — from the "Open" section, so the main Claude is aware of unresolved issues. If items carry `[decision]`/`[task]` markers, lead with `[decision]` items (they gate building) and list `[task]` items after.
```

  Then in the Cold Return Flow "Since you've been away" block (Step 3c), after the "Open questions still hanging" line, add:

```markdown
> - Not yet specified (fog): {first 1-2 items from the decisions file's `## Not yet specified` section, if present}
```

- [ ] **Step 5: Verify.** Trace amended startup Step 6 against `enhanced/decisions/*.md`: confirm `[decision]` items lead, `[task]` items follow, and cold-return surfaces the fog item. Trace against `baseline/decisions/*.md` (no markers, no fog section): confirm identical-to-before rendering (AC2). Record in `$SCRATCH/task4-after.md`.

- [ ] **Step 6: Commit.**

```bash
cd ~/Projects/claude-continuity
git add templates/decisions/_template.md skills/wrap-up/SKILL.md skills/startup/SKILL.md
git commit -m "feat: optional decision/task markers + fog-of-war section

[decision]/[task] prefixes sharpen Open-item triage; ## Not yet specified
parks coming-but-unphrasable decisions (design-brief S3/S5). Both additive —
unmarked items and absent section render as before. Refs spec 2026-08-19."
```

---

### Task 5: Version bump, changelog, CLAUDE.md doc, plan self-review

**Files:**
- Modify: `~/Projects/claude-continuity/.claude-plugin/plugin.json` — `0.3.0` → `0.4.0`.
- Modify: `~/Projects/claude-continuity/CHANGELOG.md` — cut 0.4.0 from `[Unreleased]` + new entries.
- Modify: `~/Projects/claude-continuity/CLAUDE.md` — document new fields if it enumerates schema (check first).

**Interfaces:**
- Consumes: everything from Tasks 3-4.
- Produces: released 0.4.0.

- [ ] **Step 1: Bump version.** In `.claude-plugin/plugin.json`, change `"version": "0.3.0"` to `"version": "0.4.0"`.

- [ ] **Step 2: Cut the changelog.** In `CHANGELOG.md`, rename `## [Unreleased]` to `## [0.4.0] - 2026-08-19` and add under its `### Added` (keeping the existing retrospect bullet):

```markdown
- **Optional `blocked_by`** — per-feature intra-phase dependency edges. Startup marks a feature unworkable while any sibling it lists is still active. Refines `phase` within same-phase clusters; additive.
- **Decision/task markers** — optional `[decision]`/`[task]` prefixes on Open items; startup leads with decisions.
- **Fog-of-war section** — optional `## Not yet specified` in decision files for coming-but-unphrasable decisions (distinct from `blind_spots`).
```

  Then add a fresh empty `## [Unreleased]` above it.

- [ ] **Step 3: Check CLAUDE.md for a schema list.** Read `~/Projects/claude-continuity/CLAUDE.md`. If it enumerates the per-project files or `feature-status.yml` fields, add one line each for `blocked_by`, the markers, and the fog section. If it doesn't enumerate schema, leave it — don't invent structure.

- [ ] **Step 4: Plan self-review against the spec.** Re-read `docs/superpowers/specs/2026-08-19-pocock-integration-design.md` acceptance criteria 1-6. Confirm each maps to a completed task. Write a one-paragraph verification note listing AC → task and the scratch evidence file for each, to `$SCRATCH/final-verification.md`.

- [ ] **Step 5: Commit.**

```bash
cd ~/Projects/claude-continuity
git add .claude-plugin/plugin.json CHANGELOG.md CLAUDE.md
git commit -m "release: 0.4.0 — blocked_by, decision/task markers, fog-of-war

Cuts 0.4.0 including the previously-unreleased retrospect step."
```

- [ ] **Step 6: Note the rebuild requirement.** In the final summary, remind: the plugin cache must be refreshed (reinstall/reload) for these source changes to take effect in live sessions — they load at session start.

---

## Notes for the executor

- **Do not run `/startup` or `/wrap-up` live against a real project to test** — that mutates real continuity state. All verification is by tracing the amended skill instructions against the scratch fixtures (Tasks 2-4 "verify" steps). These are prompt documents, not code; "the test" is a careful manual trace of the instruction against fixture data, recorded to a scratch file.
- **If a verify step shows the baseline fixture behavior CHANGED** (AC2 regression), stop and do not commit that task — the edit leaked into the no-new-field path. Re-scope the edit to be conditional on the new field's presence.
- **Feature name in the fixture is `frontend-ui`** (not `frontend-ai` — typo guard).
