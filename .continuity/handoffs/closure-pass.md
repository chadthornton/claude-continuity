<handoff>
<task>closure-pass: build the board review, steps 1 → 8 in feature-status.yml, one commit per step. Nothing is built yet; a whole session on 2026-10-11 went to the design.</task>
<status>Done so far: the model, the project principles and a tested build order are written down. No plugin code has changed.</status>
<first-action>
1. Read `docs/principles.md`, then `.continuity/decisions/closure-pass.md`. They are the spec. The principles are taken literally in this project; cite them.
2. Check `ls docs/principles.md`. If it is missing, your branch lacks the docs commit: run `git merge board-review` (a local branch, not pushed, holding the docs).
3. Chad said "start the board review agent" on 2026-10-11, so the build may begin. Post a short plan for step 1 and get his go-ahead on it, then the same for each later step.
</first-action>
<stops>
- Every step needs a short plan and Chad's go-ahead before code (his engineering guardrails). He is a product designer and does not read code: show test output, not diffs.
- Step 8 edits trip-planner, another repo with its own sessions. Do not edit it from here; brief its session.
- The trip-planner `lists` wayfinder trial needs Chad to type /setup-matt-pocock-skills and /wayfinder himself.
- Removing /continuity-prune and changing the board schema change every project that uses the plugin: say so in the plan for that step.
</stops>
<environment>
- Source material is in ~/Projects/trip-planner on origin/master: `.continuity/workflows/board-close-out.html` (the page, generic except its title), `board-close-out-seed.py` (hand-written round 1 seed), `handoffs/invite-rehearsal-checklist.md` (the claims shape). Live page: https://claude.ai/artifact/KMZcxHrWt7HhAh1ZaW8B8e.
- Round 1 facts: 29 rows, 101 open steps, 118 KB. Chad set 31 verdicts in about 5 minutes and answered 0 of 27 calls on the separate tab. He reported "conflicting acceptance UI".
- The four page fixes: Close says how many open steps it drops and Merge says where they go; a per-row "Accept recommendation" with bulk as that applied to all; calls sit on the row they block, a few at a time; exercise the write path (write and read back through the page's store) before handing over.
- Load the artifact-capabilities skill before writing any page code that stores data.
- Skill edits are scenario-tested (see gotchas in feature-status.yml). Several sessions work this repo in parallel: fetch and read CHANGELOG first.
- The principles eval can be re-run: `docs/board-review/principles-eval-scenarios.md`.
</environment>
<verify>
Per step: scripts and hooks get Python scenario tests like `tests/test_continuity_state.py`; skill edits get a fixture in `tests/skill-scenarios/`; the page is proven by publishing a scratch copy and reading back what it stored. Add a CHANGELOG line under [Unreleased] for each plugin change. After each step ships: mark it done and run continuity-save. After the last: clear `mandate`, `owner` and `in_progress`, then run wrap-up.
</verify>
</handoff>
