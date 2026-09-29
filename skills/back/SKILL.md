---
name: back
description: Use when the user returns after /away sent this session's task to a cloud session: "I'm back", "bring it back from the cloud", "/back". Parks the cloud session, fast-forwards its commits into this worktree, and briefs the user.
---

# Back — take the cloud's work home

`/away` handed this task to a cloud session. Stop it at a clean point, bring its commits into this branch, and tell the user what happened.

## Step 1: Find the session

Read `away:` from the feature in `.continuity/feature-status.yml`: `session`, `base` and `branch`. With no board, use the `AWAY: <session-id> <url> base=<sha> branch=<branch>` line from earlier in this conversation. With neither, say `Nothing is away from this checkout.` and stop.

If the current branch isn't `branch`, switch to it first: `git switch <branch>`.

## Step 2: Park it

```bash
<this skill's base directory>/../away/away park <session>
```

On `FAILED`, show the line and continue to Step 3 anyway. The cloud may already have parked itself.

## Step 3: Land it

```bash
<this skill's base directory>/../away/away land <base>
```

This waits up to 5 minutes for the cloud's `away: parked` commit.

- `LANDED` or `ALREADY LANDED` → Step 4.
- `NOT PARKED` (exit 4): ask once with AskUserQuestion, **"The cloud hasn't parked yet ({its line}). Take what's there now, or keep waiting?"** Options: **Take what's there now** / **Keep waiting**. Take → re-run with `--take`. Wait → re-run as is. When the line says no branch exists yet, offer only Keep waiting.
- `DIVERGED` (exit 5): show its output and stop. Don't merge; the user decides.
- `FAILED` (exit 1): show it and stop.

## Step 4: Brief and clean up

1. Read `.continuity/away.md` (now the cloud's version) for `<status>` and `<next>`.
2. `git rm -q .continuity/away.md && git commit -q -m "away: back"`, then push the branch. Commit only that deletion, so `continuity-save` never sees `away.md` mixed with board changes.
3. On the board: remove `away:`, set `in_progress` to `<next>` in one line (or `null` if the task is done), and mark any `next_steps` the cloud finished as `done: true`. Then run `<this skill's base directory>/../wrap-up/continuity-save -m "continuity: {feature} back from the cloud"`.
4. Report:

```
BACK: {n} cloud commits landed on {branch}.
Status: {<status>, one or two lines}
Next: {<next>}
```

The cloud session stays in the user's list at claude.ai/code; archiving it there is optional.
