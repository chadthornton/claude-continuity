<handoff>
<task>closure-pass: fix the pre-merge code review's findings on branch closure-pass-1-step-5 (pushed; 13 steps of the board-review plan done through 865b003, e2e2540, 21928d0), then merge, then release 0.16.0 (waits for Chad's "ship it"), then the trip-planner trial. One commit per fix group.</task>
<status>Everything in the plan is built and tested: 474 checks pass under macOS awk, mawk and gawk; scenario fixtures review-go, review-offer and relearned-gotcha pass with the edited skills. The code-review skill ran once at high effort (guarded tier: board writes, agent spawning) on 2026-10-19 and returned the 10 findings below. None are fixed yet. Nothing is merged or released.</status>
<first-action>
0. `git fetch -q origin && git switch closure-pass-1-step-5` (pushed; this branch holds all the code).
1. Read docs/principles.md (9, 10) and .continuity/decisions/closure-pass.md, then skills/continuity-review/SKILL.md and CLAUDE.md's architecture list.
2. Fix each finding test first (a scenario that fails before the fix), or dismiss it with a one-line reason for the merge message. Findings, as reported:
   1. lib/continuity-audit ~98: secret redaction runs over row names; `task-queue-retry-and-backoff` matches `sk-…` and becomes `ta[redacted:api-key]`, so edits, checker, seed and apply miss the row. Redact only free text, never names.
   2. lib/continuity-board.sh cb_set_setting / cb_set_areas: insert a new `settings:`/`areas:` before the first other top-level key without checking for a later one; flow-style `settings: { … }` gets an indented key under it (invalid YAML). Handle a later block and flow style.
   3. lib/continuity-review-seed ~42: any wt:status row counts as running (ended/safe/orphan too); only activity "idle…" escapes. Count only verdict/state running.
   4. lib/continuity-audit ~126: `NR == FNR` two-file awk breaks when b.old is empty (board-creating or root commit): rows created then get no edits.
   5. SKILL.md step 6 writes applied_at but nothing reads it: a second "go" re-applies and re-spawns. Apply and the page must refuse or show an applied round.
   6. lib/continuity-audit ~121: board edits count a continuity-save landed copy and its source commit twice; use the landed/sync rules in lib/continuity-commits.sh.
   7. lib/continuity-review-pack ~131: `git log --since=YYYY-MM-DD` means that date at the current time of day, not midnight UTC; use `--since=@<epoch>` from the audit.
   8. lib/continuity-review-apply ~83: a starter whose slug matches an existing row is skipped silently (then SKILL treats the old row as new); a label with no ASCII letters gives an empty slug and a `:` row header.
   9. commands/continuity-prune.md: retiring prune drops trimming over-budget decisions files; the review never acts on audit decisions[].over_budget. Give the reviewer/page a way to propose trimming, or keep prune's trim for one release.
   10. lib/continuity-review-pack ~33: the pack re-runs the audit (13 s on trip-planner) after SKILL step 2 built one; accept the audit path instead, so pack, checker and seed share one set of facts.
3. Post the fix list (fixed / dismissed) to Chad, merge with `review: <n> critical, <n> important (<n> fixed, <n> dismissed)`, then ask for "ship it" before the release.
</first-action>
<stops>
- Chad is a product designer and does not read code: show test output, not diffs.
- The release changes the plugin in every project on Chad's machine and retires /continuity-prune: wait for his explicit "ship it" before bumping and installing (gotcha: bump .claude-plugin/{plugin,marketplace}.json, then `claude plugin marketplace update claude-continuity-local && claude plugin update claude-continuity@claude-continuity-local`).
- Trip-planner is another repo with its own sessions: never edit it. The trial briefs its session (peer trip-planner-aa or whichever is running): set settings.product_doc to docs/product-principles.md, run /continuity-review in full mode, Chad uses the page, apply on go; measure board bytes vs the 2026-09-28 baseline and tokens spent. Also tell it the readers saw phone-jaunts-board-2 working on a step the board holds for Chad's approval (~Oct 21) and PR #97 missing from its board.
- One code-review round only (guardrails); a second only if a Critical was fixed.
</stops>
<environment>
- Scratchpad files are cleared after a few days; keep what matters in commits. Prototype history is on branch prototype/board-review-page (docs/board-review/prototype/NOTES.md, step8/).
- Audit tests default CONTINUITY_AUDIT_WT=false (the real wt:status takes ~9 s). Skill fixtures need a stand-in agent-spawn and, for running sessions, a stand-in zsh (see review-go.sh).
- mawk rejects a local variable named like a function; the awk in continuity-board.sh sits in single-quoted shell strings, so no apostrophes. Run the suite under all three awks: a dir with an `awk` symlink first on PATH.
- Measured: one-call routine review on trip-planner 61k tokens, 1m53s.
</environment>
<verify>
Each fix: a failing scenario test first, then green; the whole suite under macOS awk, mawk and gawk. CHANGELOG [Unreleased] already describes the release; add a Fixed line only where behaviour users see changed. After the release and trial: clear mandate, owner and in_progress on closure-pass, then wrap-up.
</verify>
</handoff>
