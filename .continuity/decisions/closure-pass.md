# closure-pass — decisions

Project principles: `docs/principles.md`. Concept map: https://claude.ai/artifact/41N53dC3zxhWDUcdBhCK9Y (source `docs/board-review/concept-map.html`).

## Decided

- Finished steps are sorted before deletion, never just deleted — 83/116 of trip-planner's done steps cited no commit; they held rationale, dead ends and off-repo actions git doesn't record.
- Permanent decisions go to the repo's docs/adr/; promote only when costly to reverse AND not already recorded in code — 2 of 3 trip-planner candidates were already in the schema header.
- The closing pass is a board review, not a close-out (Chad 2026-10-11) — he wants it at startup when no session is waiting, on request, and sometimes at wrap-up; closing rows is one verdict among several, with "start an agent" as another.
- The review has two depths: quick (script facts only) and deep (recommendations and a reflection) — the trip-planner round cost three audits and a publish, too much for every startup.
- The review absorbs /continuity-prune — same job; prune's decision-file checks become audit findings on the row, with a chat fallback when the page can't publish.
- One canonical page ships in the plugin; each project publishes its own copy and records the URL on its board — the trip-planner page was already generic except its title.
- The model is seven nouns: bet, principle, workstream, milestone, claim, item, open question (bet added by Chad 2026-10-11, since rows serve bets and the map needed the thing they point at) — a tracker or wayfinder map is storage for items or questions, not a concept.
- Rows serve bets; principles judge decisions — on trip-planner 5 of 11 rows mapped cleanly to a bet, 2 were forced (group-trips, city-browse) and 4 had none; P1–P6 are constraints.
- A milestone is a row with `kind: milestone` that owns claims (text, status, evidence), not work — invite-rehearsal's checklist was already 22 rows of that shape; a false claim can be fixed by rewording it.
- No lanes: whose call a thing is lives per item in the existing `gate:` field; the page computes "needs you" and "moving without you" — a lane per row would hide the lists migration inside a product row.
- Every new field is optional — this repo's four-row board has no bets file and must keep working.
- A tracker lives in the repo (local markdown), not GitHub Issues — principle 7; both eval readers refused the external tracker.
- The audit script is the only reader of board storage — so splitting the board into one file per workstream later is invisible to the page and skills.

## Open

- [decision] One file per workstream: after the review page is in use, or sooner if agents keep colliding on the board?
- [decision] Which link fields ship first; lean `serves` only.
- [decision] How often the deep reflection runs; it costs a model call.
- [question] Does trip-planner's `lists` row move its open questions to an in-repo wayfinder map? Needs Chad to run /setup-matt-pocock-skills there.
