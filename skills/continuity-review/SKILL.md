---
name: continuity-review
description: Use when the user wants to review the board and decide where attention and agents go next — "review the board", "board review", "what should we work on across the project", "plan the next round", "/continuity-review" — or accepts the review offered at startup or wrap-up. Builds a review, publishes or refreshes the project's review page, and on "go" applies the confirmed round and starts the sessions. Replaces /continuity-prune.
---

# Board review

The review settles where attention and agents go next; what the product should
be is decided in sessions with the user (principles 9 and 10 in the plugin's
`docs/principles.md`). The page is the user's; the board is the record.

`<base>` is this skill's directory; the scripts are in `<base>/../../lib/`.
Work files go in a fresh directory under your scratchpad (`$W` below).

## 1. Review

1. If the board is stale (`continuity-state` prints `board: origin/...`), sync
   `.continuity/` from origin first, as wrap-up's Step 0 does.
2. `<lib>/continuity-audit > $W/audit.json`.
3. Mode: **full** when the user asks for it or the audit has no `areas`;
   **routine** otherwise.
4. `<lib>/continuity-review-pack [--full] > $W/pack.md`.
5. The reviewer:
   - **routine**: `<lib>/continuity-review-oneshot $W/pack.md $W/audit.json $W/review.json`.
     One tool-free call, one retry on checker complaints. If it exits 1, tell
     the user in one line and run the full-mode agent below in routine mode.
   - **full**: start one agent (Agent tool, general-purpose) told to follow
     `<base>/reviewer.md` in full mode, read `$W/pack-full.md` (build it with
     `--full`), reach past the pack only where the brief allows, write
     `$W/review.json`, and run `continuity-review-check` with the audit until
     it prints OK.
6. `<lib>/continuity-review-seed $W/review.json $W/audit.json <project> > $W/seed.json`,
   where `<project>` is the repository's directory name.

## 2. The page

The audit's `review_url` names the project's page.

- **No page yet:** copy `<base>/page.html` to `$W/page.html`, set its `<title>`
  to `<project> Board Review`, and publish it with the Artifact tool, icon
  `compass`, capabilities
  `{"db": {"rules": [{"path": "review", "write": "admin"}]}, "user": {}}`.
  Record the URL at once: `<lib>/continuity-review-apply --url-only <url>`,
  then `continuity-save -m "continuity: review page for <project>"`.
- **Then, either way:** write `$W/seed.json` to `review/current` with
  `write_db` (`set`; read it first and pass `if_version` when it exists). Your
  corrections and the last round stay in the page's store; a round from an
  older review is ignored by the page.

Tell the user in two lines: the link, and "Add what you want this round,
confirm, then tell me go." Stop here until they say go.

Without the Artifact tool (a cloud session, a page that won't publish), give
the review in chat instead: the read, then one AskUserQuestion with
`multiSelect` listing the proposed sessions, starters, chores and board
changes. Treat the answer as a confirmed round.

## 3. On "go"

1. Read `round/current` and the `overrides` collection with `read_db` into
   `$W/round.json` and `$W/overrides.json` (overrides as one object keyed by
   row). If the round is not confirmed, or its `generated` differs from the
   seed's, say so and stop. Re-run the audit into `$W/audit-go.json` for what
   is running now; where it can't see sessions (`sessions.source` is
   `unavailable`), use the review's `$W/audit.json`.
2. Sync the board as in step 1.1, then
   `<lib>/continuity-review-apply $W/seed.json $W/overrides.json $W/round.json <today> --review-url <url>`.
   It writes your corrections, a full review's areas and sizes, the last-review
   date and any starters as new initiatives; it prints the rows it added.
3. **Board changes** (round items with `kind: board`). For each, show what it
   removes: the open steps (`continuity-state row <name>`), whether a handoff
   and a decisions file exist, and where a merge sends the open steps. Ask once
   with AskUserQuestion (`multiSelect`, one option per change). Carry out only
   what is ticked:
   - **park**: set `status: parked`; nothing is removed.
   - **close**: delete the row. First sort its finished steps: anything holding
     a reason or a dead end goes to its decisions file, the rest goes. Keep the
     decisions file; delete the handoff after printing what it held.
   - **merge into X**: move its open steps to the end of X's `next_steps`;
     append each of its decisions file's Decided, Ruled out and Open entries
     to the same section of X's, marked `(from {row})` (create X's file if
     needed), and delete its file; sort its finished steps as for close; delete the row.
4. **Capacity.** Agents already running each fill one place in the
   reports-back lane. Each new pane this round fills one place in its lane:
   live for decision, think and starters; reports back for continue; quiet for
   chores. A message to an agent already running fills nothing. Compare with
   the page's lanes (1, 3, 3). If a lane would go over, propose holding the
   items in it that come last in the round, and ask once (AskUserQuestion) whether to hold
   those. Held items stay proposed; a held starter keeps its new row.
5. **Sessions.** For each session item, in one batch:
   - An initiative with a running agent (the audit's `sessions`): send that
     agent the brief with SendMessage, worded as the handoff below would be
     for its kind; don't start another. If the board doesn't name it as
     `owner`, set `owner` to it.
   - Otherwise pick `{row}-{N}` (lowest N whose `.claude/worktrees/{row}-{N}`
     doesn't exist), set `owner: {row}-{N}`, and write
     `.continuity/handoffs/{row}.md` from the item's brief, in the shape
     wrap-up's handoffs use (`<task>`, `<status>`, `<first-action>`,
     `<stops>`, `<verify>`), with the branch `{row}-{N}-step-1`:
     - **decision**: first action is to put the calls in front of the user on
       a decision page (options, evidence, a recommendation), settle them
       together and record each in `decisions/{row}.md` with its reason. Build
       nothing.
     - **think**: work out with the user what this should be; build nothing
       until they agree a direction, then record it and the next steps.
     - **continue**: carry on the next step the board already holds, then
       wrap up.
     - **starter** (an item whose key starts `s:`): the row
       `continuity-review-apply` added; treat as think.
   - **chores**: one agent per group, named `chores-{N}`, with the group's
     items and why they go together as its prompt; it opens a PR per group,
     marks an item's step done on the board when the step is there, and asks
     before anything the chore rule excludes (the Chores rule in
     `<base>/reviewer.md`; quote it in the prompt).
   Then save once (`continuity-save -m "continuity: review round <date>"`) and
   start each agent as wrap-up's relay steps 4 and 5 do (`agent-spawn {name}
   --prompt "/startup"`, judged by its exit status, its `Open it:` line copied
   into the report). A chore agent gets `--prompt` with its brief instead.
6. Mark the round applied (`update` `round/current` with `applied_at`) and
   delete the override documents the apply step wrote to the board.
7. Report one line per item: what started where, what got a message, what was
   held, what changed on the board. End with `Check on them: agent-spawn status`
   when anything started.

## Rules

- The page shows facts plainly and marks Claude's judgments; never present a
  judgment as a fact in chat either.
- Nothing starts without a confirmed round; nothing is removed without a yes
  per change (principle 8).
- Saving continuity never ships code: only `continuity-save` touches the board.
