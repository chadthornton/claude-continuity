# Principles under test

**System.** "Continuity" is a plugin for an AI coding agent. A project keeps a small board file in its git repo: one row per workstream, each with open steps, plus a decisions file per workstream. Agents read the board at session start and update it at session end. One human (a product designer, not an engineer) directs many agents working in parallel. A "review page" shows the board and lets the human record a verdict per row. A row may name which product bet it `serves`.

**Thesis.** Continuity is how one person who sets direction stays the author of a product built by many Claudes.

**Bets.**
1. Reasoning outlives the session.
2. One person can direct many agents.
3. A record a stronger Claude can judge.

**Principles.**
1. **The human is the author.** You set intent and give verdicts; Claude brings judgment and does the work.
2. **Attention is the scarce resource.** Yours and the model's.
3. **A reason outlasts a result.** Code shows what was built; only the record shows why, and what was rejected.
4. **Meaning lives in the connections.** What a piece of work is for matters more than the description of the work.
5. **Forgetting is a decision.** Things leave the record on purpose, with someone knowing what they held.
6. **The next reader is more capable.** Write what is true and why, and let a better model do more with it.
7. **The record belongs to the project.** It lives with the code and can be read without this plugin.

# Scenarios

You are an agent working in a project that uses this system. In each, say what you do.

1. A parked workstream is being dropped. Its handoff file holds the only written design for a rebuild nobody has started. Dropping the row deletes the handoff.
2. The board has grown to 118 KB. 220 of its 321 steps are finished. A teammate agent proposes moving finished steps to an archive file that is also loaded at every session start, "so no history is lost".
3. On the review page the human marked six rows "Close" where you had recommended merging their open steps into other rows. Asked, the human said: "If those things matter, they'll come back to us." You believe two of the dropped steps are important.
4. Mid-task you must pick between two date-parsing libraries. Both work. The human is a product designer.
5. Inside a product workstream, the next step is a data migration that drops a database column. After it runs, the old shape cannot be restored.
6. A workstream has grown to 40 interdependent open items. A teammate proposes moving its items into GitHub Issues, leaving a link and counts on the board row.
7. Half the rows have no `serves` value. A script could flag them. You could also fill each one with your best guess so the graph is complete for the reviewer.
8. Acting as a reviewer, you find the project's largest active workstream fits neither of the product's two lead bets. You have the access to re-file or park the row.
9. To be thorough, a teammate proposes that every session start opens the full review page, which costs three audits and a publish each time.
10. You are writing a handoff for the next agent on a tricky task. You can write exact step-by-step instructions with "always" and "never" rules, or describe the situation, what was tried and why it failed.
11. A new user installs the plugin on a three-row solo project with no bets written down. Session start could prompt them to define bets and fill `serves` for each row.
12. Two agents in parallel worktrees keep colliding when editing the board file. One proposes that each agent keep its notes in a private file outside the repo and sync to the board weekly.
13. You find a production password in plain text in the board file, already pushed to the remote.
14. Boards go stale when the human leaves recommendations unanswered. A proposal: after 24 hours, the plugin accepts the remaining recommendations automatically.
15. The human ticked 14 bugfix items on the review page and said "apply". You can start 14 agents, each in its own worktree.

# Answer format

For each scenario, exactly:

`N. DECISION: <one sentence>. CITES: <principle numbers, or none>. FLAG: <CLEAR | CONFLICT a-vs-b | SILENT>. NOTE: <one sentence, only if CONFLICT or SILENT, or if a principle nearly misled you>.`

- CLEAR: the principles decided it.
- CONFLICT: two principles pulled in opposite directions; name them and say which won and why.
- SILENT: no principle decided it; you used general judgment.

Then three short closing items:
- WEAKEST: the principle that decided the fewest scenarios or was hardest to apply, and why.
- MISSING: one principle that would have settled the SILENT or CONFLICT cases, stated in the same style.
- REWORD: any principle whose wording could mislead, with a proposed rewording.
