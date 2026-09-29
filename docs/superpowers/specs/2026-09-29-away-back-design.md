# /away and /back — hand mid-stream work to a cloud session and take it back

Date: 2026-09-29 · Status: approved design, pending implementation plan

## Problem

Chad often has to close the laptop mid-task: not at a stopping point, which is the point. Today the work just stops. Claude Code cloud sessions keep running with the lid closed, but nothing moves a live local task into one, and nothing brings the result back into the local session afterwards.

## Goals

- `/away`: in under a minute, with no questions, send *this session's* task to a cloud session that continues it.
- `/back`: in the same local session later, stop the cloud work at a clean point, pull its commits into this worktree, and brief the user.
- Code never lands on the default branch as a side effect.
- Works with `.continuity/` when present and updates the board, so other checkouts see the work is in the cloud.

Non-goals: sending several sessions at once; teleporting the cloud conversation back (the user chose "pull into this session"); a "peek without stopping" mode; carrying the local conversation itself (no CLI path exists; only the Desktop app's **Continue in** can).

## Facts this design rests on (spike, 2026-09-29, Claude Code 2.1.285)

1. `claude -p --cloud "task"` is refused: creating a cloud session is interactive only. Under a pseudo-terminal (`script -q <log> claude --cloud "task" </dev/null`) it prints `Created cloud session: <title>`, `View: https://claude.ai/code/<session-id>?…`, and `Resume with: claude --teleport <session-id>`, then exits 0.
2. The cloud session clones the current branch from GitHub (push first), then works on a harness-named branch `claude/<slug>` cut from that commit. It cannot push to the original branch. Its commits descend from the launch commit.
3. `claude -p "<msg>" --cloud <session-id> --output-format json` returns `{"ok":true,…}` and the session acts on the message (about 1 minute in the spike).
4. Cloud sessions do not load local plugins or user skills, and `.env`-style files are not uploaded. The brief must be self-contained plain text.
5. No CLI command reports whether a cloud session is working or idle. Progress is observable only through pushed commits.

## User flow

**`/away`** (main session, not a subagent — only it has the conversation):
1. Write `.continuity/away.md` from the conversation (shape below).
2. Run `away launch`: commit uncommitted work and `away.md` as `wip(away): <task>`, push the branch, launch the cloud session, print its ID.
3. Set `away:` on the feature in `feature-status.yml` and run `continuity-save`.
4. Report: `AWAY: <task> → <session url>. Safe to close the lid. Run /back when you return.`

**`/back`** (same local session):
1. Run `away park <session>`: tell the cloud to stop at the next clean point.
2. Run `away land <base-sha>`: wait for the parked tip, fast-forward, push, delete the `claude/` branch.
3. Brief from `away.md`'s `<status>` and `<next>` plus the cloud's commit list; delete `away.md` in an `away: back` commit; clear `away:`; `continuity-save`.

## Components

### `skills/away/SKILL.md`
Triggers: `/away`, "I need to close my laptop", "send this to the cloud", "I'm heading out". Zero questions. Writes `away.md`, calls `away launch`, sets the marker, reports. On a launch failure it reports the error and sets no marker.

### `skills/back/SKILL.md`
Triggers: `/back`, "I'm back", "bring it back from the cloud". Reads the marker, calls `away park` then `away land`. The only question in either skill: on `land` timeout, **Take what's there now / Keep waiting**. Finds the script at `<this skill's base directory>/../away/away` (the pattern startup uses for `continuity-save`).

### `skills/away/away` (bash; exit codes in the style of `continuity-save`)

`away launch [-m "<task one-liner>"]`
- Requires a git repo whose `origin` is on github.com; otherwise exit 3 with the reason. A bundled upload could not push results back.
- If on the default branch, first `git switch -c away-<YYYYMMDD-HHMM>` so code never goes to the default branch.
- `git add -A`, commit `wip(away): <task>` (skipped if nothing changed), `git push -u origin <branch>`.
- Launch under `script` with the prompt `Read .continuity/away.md and follow it exactly.`, capture the session ID with a regex on `session_[A-Za-z0-9]+`.
- Print `AWAY: <session-id> <url> base=<sha>`; exit 0. Launch failure: print the CLI's output, exit 1 (the pushed WIP commit is harmless).
- Test seam: `AWAY_CLAUDE` overrides the `claude` binary.

`away park <session-id>`
- `claude -p "<park message>" --cloud <session-id> --output-format json`; exit 0 on `"ok":true`, else print the error, exit 1.
- Park message: `Stop at the next clean point: commit your work, rewrite <status> and <next> in .continuity/away.md, then make a final commit titled "away: parked" and push.`

`away land <base-sha> [--timeout <sec>=300]`
- Poll `git ls-remote origin 'refs/heads/claude/*'` every 10s; fetch candidates; the cloud branch is the one whose history contains `<base-sha>`. With several, prefer the newest tip.
- Done waiting when the tip commit's subject is `away: parked`. On timeout: print the tip and its subject, exit 4.
- Local commits after `<base-sha>`: if any touches paths outside `.continuity/`, exit 5 and print both sides (no merge). `.continuity/`-only commits (e.g. the session-ID marker save) are replayed on top of the cloud tip with `cherry-pick`.
- Fast-forward the branch to the result, push it, delete the remote `claude/` branch (its content is now contained in the branch), exit 0.

### `templates/away.md`
```xml
<away>
<task>{what we're doing, one line}</task>
<in-flight>{what was mid-way when the user left: the half-done edit, the command about to run}</in-flight>
<next>{the exact next action, with file paths}</next>
<decided>{decisions made this session, each with its why}</decided>
<stops>{gated steps; anything needing the user; anything needing secrets (.env is not uploaded) — stop and note it here instead of working around it}</stops>
<protocol>Work on the branch you were given. Commit and push after each step. Don't edit anything else under .continuity/. When you finish, get stuck, or are told to stop: rewrite <status> and <next> below, then make a final commit titled "away: parked" and push.</protocol>
<status>Not started.</status>
</away>
```

### `continuity-save` and hooks
Exclude `.continuity/away.md` exactly as `last-activity.txt` is excluded (`EXCL`), in `continuity-save` and wherever the hooks match continuity paths. `away.md` then travels only on the feature branch: added in the WIP commit, edited by the cloud in ordinary commits, deleted by `/back`. It never needs merging on the default branch.

### Board marker
On the worked-on feature: `away: {session: <id>, url: <url>, base: <sha>, since: <ISO datetime>}`. `continuity-save` lands it on `origin/<default>`.

### Startup
A feature with `away:` renders as `☁ {feature} — in the cloud since {since} ({url}). Run /back to bring it home.` and counts as owned elsewhere, so fast-resume doesn't start the same work.

## Error handling

| Situation | Behaviour |
|---|---|
| No GitHub `origin`, or push rejected | `/away` refuses (exit 3/1) and says why; nothing launched, no marker |
| Cloud launch fails (auth, org policy, no ID in output) | Report the CLI output; no marker; the WIP commit stays pushed on the feature branch |
| `/back` finds no `claude/*` branch descending from base | Exit 4 after timeout; the cloud may not have pushed yet. Offer Take / Keep waiting (Take is unavailable without a branch) |
| Parked tip never appears | Exit 4 → ask Take what's there now / Keep waiting |
| Local code commits made while away | Exit 5, show both sides, stop; the user decides |
| Cloud edited `.continuity/` beyond `away.md` | `land`'s `.continuity/` cherry-pick may conflict → abort the cherry-pick, exit 5, report |
| Secrets needed in the cloud | `away.md` `<stops>` tells the cloud to stop and note it |

## Testing

- `tests/test_away.py` (pattern of `test_continuity_save.py`: bare remote + clone; a second clone plays the cloud by pushing `claude/…` branches; a fake `claude` on `AWAY_CLAUDE` prints the real launch lines and logs `-p` messages):
  - launch from the default branch creates `away-…` and never moves `origin/<default>`;
  - launch parses the session ID and base; launch without a GitHub origin exits 3;
  - `away.md` is left out of `continuity-save` commits;
  - land picks the descendant `claude/` branch among decoys; waits for `away: parked`; times out with exit 4;
  - land replays a local `.continuity/`-only commit, refuses a local code commit with exit 5, deletes the `claude/` branch after landing.
- One skill scenario in `tests/skill-scenarios/`: a mid-task conversation yields an `away.md` whose `<next>` names a file and command, and whose `<decided>` entries carry a why.
- Before release: one real `/away` → `/back` round trip on a throwaway branch, as in the spike.

## Docs
CHANGELOG `[Unreleased]` entries for both skills and the `continuity-save` exclusion; README command table gains `/away` and `/back`.
