# closure-pass — decisions

Principles: `docs/principles.md` (9 and 10 govern the review). Prototype and notes: branch `prototype/board-review-page`, `docs/board-review/prototype/` (last page: https://claude.ai/artifact/7dVqVsrwDDweUMgHxHM3q8).

## Decided

- The review is a planning table, not a close-out (Chad 2026-10-14) — round-1's verdict page read as hygiene; the static product read was the first version he called "about my product".
- Vocabulary: an area is lasting and carries its open question; an initiative is bounded, with a size and an aspiration; "workstream" retires (Chad 2026-10-19) — trip-planner ran six permanent areas as endless rows, which is how polishing beat open questions.
- Areas, sizes and aspirations are stored on the board, optional (Chad 2026-10-19) — re-inferring them each review was most of the ~150k-token cost per pass.
- The page is one table grouped by area, with Live on top, wind-down suggestions, chores and a checkout bar — four separate panes made Chad ping-pong.
- No designated priorities: activity shows where interest went and Chad picks anything (Chad 2026-10-14) — an inferred top three put a stale row (group-trips) in it.
- Facts look plain; Claude's judgments are marked and overridable — Chad couldn't tell who judged "waiting/ready/resting" or how to disagree.
- Decisions are not answered on the page; a decision session is something to send — "rename the trip" sat beside "where do Plans live on a phone" and neither could be settled from a summary.
- Confirm sends a basket, nothing pre-added, sized by lanes: live 1, reports back 3, quiet 3, running agents counted (Chad 2026-10-19) — Yes/Hold pre-filled eight panes; trip-planner was at capacity before anything was added.
- Routine reviews run as one tool-free call over the review pack; full reviews run as an agent (Chad 2026-10-19) — on trip-planner one call took ~65k tokens and 2m48s against the agent's 128k, agreeing on 16 of 18 suggestions and proposals; full reviews are rare and their best findings came from digging.
- A chore passes all of: no decision pending, nothing a traveller notices, nothing deleted live, no approval named — the reader misfiled two such items as chores.
- The board stores claims, gates and the optional area fields, no `serves`/`for` links, and every new field is optional — no mistake came from a missing link, and this repo's four-row board has no areas.
- A round is marked sent (`applied_at`) after the save and before any agent starts; apply and the skill refuse a sent round (2026-10-19) — a missed spawn shows in wt:status and can be re-run by hand, a second "go" would start every agent twice.

- Initiative rows are two columns, facts as labelled mini rows with empty ones hidden; a board change shows as the row's Next step, its button named by the change (Chad 2026-10-19, 0.17.0) — eight columns needed 1060px, and "close" beside "polishing" read as a second status.
- A row's read is a line of at most 160 characters plus at most three 160-character points, and `read` at most 480, enforced by the checker (2026-10-19) — the brief said "one sentence" with no check, and trip-planner's lines averaged 319 characters, one 913.
- Page notes live in `overrides/<row>.notes` and reach the reviewer through `pack --notes`; apply ignores them; on go a note the review read and that is unchanged is cleared, matched by text in the seed's `notes_read` (Chad 2026-10-19, 0.17.1) — a note should steer one review, and a timestamp would clear notes typed while the reviewer ran.

## Ruled out

- Rule-only recommendations: fired on 0 of 14 trip-planner rows.
- Yes/Hold dispatch with defaults on: doing nothing sent eight panes.
- Grouping by gates ("needs you / moving without you"): an operator's sort; nothing executed in "moving without you".

## Open

- [decision] Rename "workstream" across plugin text: after the trip-planner trial.
