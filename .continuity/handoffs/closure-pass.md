<handoff>
<task>closure-pass: build the board review. Steps 1-4 shipped in plugin 0.15.0 on 2026-10-11. Next is step 5, the canonical review page. One commit per step.</task>
<status>Done and released: docs point at docs/principles.md; continuity-state summarises a board over 16 KB (`row <name>`, `gotchas`); lib/continuity-audit prints JSON facts; milestone rows own claims. The page, the /continuity-review skill and the startup/wrap-up offers are not started.</status>
<first-action>
1. Read `docs/principles.md`, then `.continuity/decisions/closure-pass.md`. They are the spec; cite the principles.
2. Run `lib/continuity-audit` in this repo and read its header comment. Its JSON is the only thing the page and skill may read about a board.
3. Work on the branch `closure-pass-1-step-5`, cut from main (0.15.0 holds steps 1-4).
4. Post a short plan for step 5 and get Chad's go-ahead before any code, then the same for each later step.
</first-action>
<stops>
- Every step needs a short plan and Chad's go-ahead before code. He is a product designer and does not read code: show test output, not diffs.
- Chad said the design was getting "network graph-y". The board stores two links only: claims on a milestone and gates on an item. Do not add `serves`, `for` or a bets pointer to the board format. A reviewer infers which bet a row serves; only Chad's correction is stored as `serves`.
- Run the two-reader experiment (its own step on the board) before building the deep review.
- The trial step edits trip-planner, another repo with its own sessions. Do not edit it from here; brief its session.
- Removing /continuity-prune changes every project that uses the plugin: say so in that step's plan.
- Before any merge: code-review skill at high effort, fix Critical/Important, counts in the merge message.
</stops>
<environment>
- Source for the page is in ~/Projects/trip-planner on origin/master: `.continuity/workflows/board-close-out.html` (generic except its title) and `board-close-out-seed.py` (hand-written round 1 seed; the audit's JSON replaces it). Live round-1 page: https://claude.ai/artifact/KMZcxHrWt7HhAh1ZaW8B8e.
- Round 1 facts: 29 rows, 118 KB. Chad set 31 verdicts in about 5 minutes and answered 0 of 27 calls on the separate tab. He reported "conflicting acceptance UI".
- The four page fixes: Close says how many open steps it drops and Merge says where they go; a per-row "Accept recommendation" with bulk as that applied to all; calls sit on the row they block, a few at a time; exercise the write path (write and read back through the page's store) before handing over.
- Page layout decided: milestones on top, rows grouped "needs you" / "moving without you" from the audit's `gated` lists, a "Start an agent" verdict.
- Load the artifact-capabilities skill before writing any page code that stores data.
- Concept map: https://claude.ai/artifact/41N53dC3zxhWDUcdBhCK9Y (source docs/board-review/concept-map.html). Nobody has looked at it rendered; ask Chad to glance at the diagram.
- The awk in lib/continuity-board.sh sits inside a single-quoted shell string: no apostrophes, even in comments. mawk and gawk are installed (brew) for the Linux check: put a dir holding an `awk` symlink first on PATH and run the tests.
- The design session (peer `claude-continuity-7c`, if still running) reviewed steps 1-4 and gave good counter-arguments; ask it before reversing a design decision.
</environment>
<verify>
Scripts get Python scenario tests like `tests/test_continuity_audit.py`; skill edits get a fixture in `tests/skill-scenarios/` run on the old and new SKILL.md (give the test agent every command as `cd <fixture> && <cmd>`; its cwd does not persist). The page is proven by publishing a scratch copy and reading back what it stored. Add a CHANGELOG line under [Unreleased] per plugin change. After each step: mark it done and run continuity-save. After the last: clear `mandate`, `owner` and `in_progress`, then run wrap-up.
</verify>
</handoff>
