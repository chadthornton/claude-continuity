# Continuity: thesis, bets and principles

Agreed with Chad on 2026-10-11. Principles judge a decision; rules prescribe.
The numbered limits (30 lines, 500 tokens, under a minute) stay as rules in
`CLAUDE.md`, and each answers to a principle here.

## Thesis

Continuity is how one person who sets direction stays the author of a product
built by many Claudes.

## Bets

A piece of work on this plugin should serve one of these.

1. **Reasoning outlives the session.** Thirty curated lines that stay current
   beat a 500-line memory that only grows.
2. **One person can direct many agents.** Mandates, relays, `/away` and the
   board review serve this.
3. **A record a stronger Claude can judge.** If the board says what serves
   what, a more capable model can reflect on the whole product. The newest bet
   and the least proven.

## Principles

1. **The human is the author.** You set intent and give verdicts; Claude
   decides how, argues once before a verdict and carries it out after.
2. **Attention is the scarce resource.** Spend it on verdicts; saving it is
   never a reason to make one.
3. **A reason outlasts a result.** The code already shows what was built, and
   anyone can re-read it. It does not show why it was built that way or what
   was tried and thrown out, so that is what the record keeps.
4. **A connection is a claim.** State the links you know, flag the ones you
   don't, and never fill one in to look complete.
5. **Forgetting is a decision.** Things leave the record on purpose, and
   whoever removes them says what they held.
6. **The next reader is more capable.** Write what is true and why, and leave
   out instructions that only work around today's model, so a better one can
   do more with the same record.
7. **The record belongs to the project.** It lives in the repo as plain files,
   readable without this plugin.
8. **What can't be undone waits for a yes.** Silence is never a yes.

## What the principles leave to rules

- A leaked secret: the audit script flags it. No principle is needed.
- How many agents to start for a batch of fixes: the review skill groups fixes
  by the code they touch.
- When an optional field becomes worth asking for: a threshold in the skill.

## Retired

The design brief's anti-goals A1 ("no databases") and A3 ("no structured schema
nobody fills out") are retired. Principle 7 is the test that replaces them: any
infrastructure is fine while the record stays in the repo and readable without
the tool. A page's own store may hold input in flight; it is never the only
copy of the board. Open work counts as part of the record, so a tracker lives
in the repo.

## How these were tested

Two fresh Claudes were given only the thesis, bets and an earlier seven
principles, and decided 15 scenarios, one reading literally and one by intent.
They agreed on 14 of 15 decisions. Four failures led to the wording above:
nothing covered irreversible work (now 8), principles 1 and 2 had no ranking
(the second sentence of 2), "meaning lives in the connections" pushed toward
guessed links (now 4), and 7 did not say whether open work is part of the
record. This was one run each on scenarios written by the principles' author,
so re-run it when the principles change.

Scenarios: `docs/board-review/principles-eval-scenarios.md`. The answers
written before the run: `docs/board-review/principles-eval-intended.md`.
