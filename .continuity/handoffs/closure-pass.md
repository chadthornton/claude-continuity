<handoff>
<task>closure-pass: build the board review as a planning table. Steps 1-8 are done (6 = areas 974aa1a, 7 = audit facts a6fe49c, 8 = reviewer brief cc82efa and fixes). Next is step 9, the page; Chad owes a decision on review cost first. One commit per step, on branch closure-pass-1-step-5 cut from main.</task>
<status>Released in 0.15.0: the large-board summary, lib/continuity-audit, milestone claims. Recorded, not released: principles 9 and 10 in docs/principles.md (on the branch), the rewritten decisions file and steps. The design came from seven prototypes on trip-planner's real board, committed to branch prototype/board-review-page with docs/board-review/prototype/NOTES.md; the last page is https://claude.ai/artifact/7dVqVsrwDDweUMgHxHM3q8 (data inlined, 2026-10-14).</status>
<first-action>
1. Read docs/principles.md (9, 10), .continuity/decisions/closure-pass.md and docs/board-review/prototype/NOTES.md on the prototype branch.
2. Ask Chad the review-cost decision (decisions file, Open), then post a short plan for step 9 and get his go-ahead.
</first-action>
<stops>
- Every step needs a short plan and Chad's go-ahead before code. He is a product designer and does not read code: show test output, not diffs.
- Step 10 removes /continuity-prune for every project using the plugin: say so in its plan.
- Trip-planner is another repo with its own sessions. Read it, never edit it; the trial step briefs its session.
- Before any merge: code-review skill at high effort, fix Critical/Important, counts in the merge message.
</stops>
<environment>
- The scratchpad is cleared after a few days: commit prototypes and reader outputs you want to keep.
- A reader pass on trip-planner's raw 94 KB board cost 140k-216k tokens. Feed readers the audit and `continuity-state` summary, not the board file.
- The awk in lib/continuity-board.sh sits inside a single-quoted shell string: no apostrophes, even in comments. mawk and gawk are installed for the Linux check.
- Other sessions land on main in parallel (context notice, task-sync): fetch and read CHANGELOG before each step; wrap-up's SKILL.md changed on 2026-10-1x.
</environment>
<verify>
Scripts get Python scenario tests like tests/test_continuity_audit.py; skill edits get a fixture in tests/skill-scenarios/ run on the old and new SKILL.md. The page is proven by publishing a scratch copy and reading back what it stored. A CHANGELOG line under [Unreleased] per plugin change. After each step: mark it done and run continuity-save. After the last: clear mandate, owner and in_progress, then wrap-up.
</verify>
</handoff>
