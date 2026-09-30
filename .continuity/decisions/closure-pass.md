# closure-pass — decisions

## Decided

- Finished steps are sorted before deletion, never just deleted — 83/116 of trip-planner's done steps cited no commit; they held rationale, dead ends and off-repo actions git doesn't record.
- Continuity keeps no ledger; permanent decisions go to the repo's docs/adr/ — keeps the roadmap-adoption.md §5 boundary while preserving rationale.
- Promote to an ADR only when costly to reverse AND not already recorded in code — 2 of 3 trip-planner candidates were already in the db/schema.sql header.
- The closing pass is its own command, not part of wrap-up — it needs code checks and blows the 1-minute budget.

## Open

- [decision] Board-wide pass: run once as a migration, or make it recurring (size-check hook suggests it)?
