# closure-pass — decisions

Principles: `docs/principles.md` (9 and 10 govern the review). Prototype and notes: branch `prototype/board-review-page`, `docs/board-review/prototype/` (last page: https://claude.ai/artifact/7dVqVsrwDDweUMgHxHM3q8).

## Decided

- Finished steps are sorted before deletion, never just deleted — 83/116 of trip-planner's done steps cited no commit; they held rationale and dead ends git doesn't record.
- The review is a planning table, not a close-out (Chad 2026-10-14) — round-1's verdict page read as hygiene; the static product read was the first version he called "about my product".
- Vocabulary: an area is lasting and carries its open question; an initiative is bounded, with a size and an aspiration; "workstream" retires (Chad 2026-10-19) — trip-planner ran six permanent areas as endless rows, which is how polishing beat open questions.
- Areas, sizes and aspirations are stored on the board, optional (Chad 2026-10-19) — re-inferring them each review was most of the ~150k-token cost per pass.
- The page is one table grouped by area, with Live on top, wind-down suggestions, chores and a checkout bar — four separate panes made Chad ping-pong.
- No designated priorities: activity shows where interest went and Chad picks anything (Chad 2026-10-14) — an inferred top three put a stale row (group-trips) in it.
- Facts look plain; Claude's judgments are marked and overridable — Chad couldn't tell who judged "waiting/ready/resting" or how to disagree.
- Decisions are not answered on the page; a decision session is something to send — "rename the trip" sat beside "where do Plans live on a phone" and neither could be settled from a summary.
- Confirm sends a basket, nothing pre-added, sized by lanes: live 1, reports back 3, quiet 3, running agents counted (Chad 2026-10-19) — Yes/Hold pre-filled eight panes; trip-planner was at capacity before anything was added.
- A chore passes all of: no decision pending, nothing a traveller notices, nothing deleted live, no approval named — the reader misfiled two such items as chores.
- The audit script is the only reader of board storage, and a script never makes a judgment — so storage can change behind it, and every judgment is a reviewer's, marked.
- The board stores claims, gates and the optional area fields, no `serves`/`for` links, and every new field is optional — no mistake came from a missing link, and this repo's four-row board has no areas.

## Ruled out

- Rule-only recommendations: fired on 0 of 14 trip-planner rows.
- Yes/Hold dispatch with defaults on: doing nothing sent eight panes.
- Grouping by gates ("needs you / moving without you"): an operator's sort; nothing executed in "moving without you".

## Open

- [decision] Routine review: 160k tokens, 128k with the review pack (2026-10-19); the rest is turns re-reading context. One model call over the pack, or accept?
- Two readers given the brief placed all 18 trip-planner rows in the same six areas (2026-10-19).
- [decision] Rename "workstream" across plugin text: after the trip-planner trial.
