---
name: away
description: Use when the user has to leave mid-task and wants the work to keep going in a Claude Code cloud session: "I need to close my laptop", "send this to the cloud", "I'm heading out, keep going", "/away". Writes a brief from this conversation, pushes the branch, starts the cloud session, and marks the board. Zero questions.
---

# Away — hand this task to a cloud session

The user is leaving mid-task. That's the point: don't wrap up, don't ask anything. Capture what this conversation knows, hand it to a cloud session, and let them close the lid. `/back` brings it home later.

**Run this in the main session, not a subagent.** Only this session has the conversation, and the brief is the only thing the cloud session gets. It sees no transcript and no plugins, and `.env` files aren't uploaded.

## Step 1: Write `.continuity/away.md`

Create `.continuity/` if it doesn't exist. Fill the shape in `${CLAUDE_PLUGIN_ROOT}/templates/away.md`. If that path reads literally, resolve it with `ls -d ~/.claude/plugins/cache/*/claude-continuity/*/templates/away.md | sort -V | tail -1`.

Write it for a capable engineer who has never seen this conversation:
- `<task>`: one line.
- `<in-flight>`: exactly what was half-done: the file, what's written, what's missing.
- `<next>`: the next action with file paths and the command to run. "Continue the importer" fails; "Add `price` to `COLUMNS` in `scripts/import.py`, parsed with `Decimal`" works.
- `<decided>`: every decision from this session, each with its *why*.
- `<stops>`: gated steps, anything needing the user, and anything needing secrets or local-only files. Name those files.
- Keep `<protocol>` and `<status>` as the template has them.

## Step 2: Launch

```bash
<this skill's base directory>/away launch -m "<task, one line>"
```

It commits code plus `away.md` as `wip(away): …` on this branch (branching off the default branch first if needed), pushes, starts the cloud session, and prints `AWAY: <session-id> <url> base=<sha> branch=<branch>`.

- `SKIP:` (exit 3): tell the user the reason in one line and stop. Common ones: origin not on GitHub, detached HEAD.
- `FAILED:` (exit 1): show its output and stop. Don't set a marker, because no session exists.

## Step 3: Mark the board

If `.continuity/feature-status.yml` exists, on the feature being worked on set:

```yaml
away: {session: <id>, url: <url>, base: <sha>, branch: <branch>, since: <now, ISO 8601>}
```

and set `in_progress: "In the cloud — run /back"`. Then run:

```bash
<this skill's base directory>/../wrap-up/continuity-save -m "continuity: {feature} away in the cloud"
```

Report its first line only if it doesn't start with `SAVED`.

## Step 4: Report

```
AWAY: {task} → {url}
Safe to close the lid. Check on it from the Claude app; run /back here when you return.
```

## Guidelines

- **Zero questions**, and under a minute. If the task is unclear, write what you know; the cloud can stop at `<stops>`.
- **Never** push to the default branch; `away launch` handles branching.
- No board? Everything still works except Step 3. `/back` will read the `AWAY:` line from this conversation instead.
