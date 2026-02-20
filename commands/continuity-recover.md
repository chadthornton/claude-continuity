---
name: continuity-recover
description: Recover continuity state from a past session transcript (JSONL). Use when a session ended without a clean wrap-up — context exhaustion, crash, or forgot to run /wrap-up.
---

# Recover Continuity State from Transcript

Reconstruct `.continuity/` artifacts from a session transcript JSONL, producing the same result as if `/wrap-up` had been run at the end of that session.

## Prerequisites

This command needs a session transcript (JSONL file) to work with.

## Flow

### Step 1: Resolve the Transcript

The user provides either:
- A **session ID** (UUID like `2a8e332a-7477-4819-bd9f-22252c9b5025`)
- A **file path** to a JSONL transcript

If a session ID is given, search for a matching JSONL file under `~/.claude/projects/`. Use Glob to find files matching `**/{session-id}.jsonl`.

If no transcript is found, tell the user and stop. Suggest they check the session ID or provide the path directly.

### Step 2: Check for `.continuity/`

If `.continuity/` doesn't exist in the current project:

1. **Ask the user** using AskUserQuestion with two options:
   - "Run /continuity-init first (Recommended)" — this sets up features properly with user input
   - "Create minimal scaffold" — just enough structure to write recovery artifacts

2. If the user picks `/continuity-init`, run it and then continue with Step 3.

3. If the user picks minimal scaffold, create the structure using the **exact template** from the plugin. Read the template file at `${CLAUDE_PLUGIN_ROOT}/templates/feature-status.yml` and copy it to `.continuity/feature-status.yml`. Create the `.continuity/decisions/` directory. Do NOT improvise the YAML format — use the template exactly as-is.

Recovery needs somewhere to write — don't proceed without the directory.

### Step 3: Extract Session Narrative

Launch a **subagent** (Task tool, `general-purpose` type) to read the transcript and produce a structured summary.

The subagent prompt must include ALL of the following. Do not paraphrase — include this structure verbatim in the prompt:

---

**How to read the transcript:**

The file at `{path}` is JSONL — one JSON object per line. Lines are very long (often 5000+ chars). The `Read` tool will truncate them. Do NOT use `Read` to parse this file.

Instead, use Bash to run a Python script that extracts the conversation:

```python
import json, sys
with open(sys.argv[1]) as f:
    for line in f:
        r = json.loads(line)
        if r.get("type") == "user":
            msg = r.get("message", {})
            content = msg.get("content", "")
            if isinstance(content, str):
                print(f"USER: {content[:2000]}")
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        print(f"USER: {c['text'][:2000]}")
        elif r.get("type") == "assistant":
            msg = r.get("message", {})
            for c in msg.get("content", []):
                if isinstance(c, dict):
                    if c.get("type") == "text":
                        print(f"ASSISTANT: {c['text'][:2000]}")
                    elif c.get("type") == "tool_use":
                        print(f"TOOL_USE: {c.get('name', '?')}({json.dumps(c.get('input', {}))[:500]})")
        elif r.get("type") == "tool_result":
            content = r.get("content", "")
            if isinstance(content, str):
                print(f"TOOL_RESULT: {content[:500]}")
```

Write this script to `/tmp/parse_continuity_transcript.py` and run it with `python3 /tmp/parse_continuity_transcript.py "{path}"`. The output will be a readable conversation log. Read THAT output to produce the summary.

If the output is very large (>200 lines), focus on the first and last third — the middle is usually implementation details.

**What to produce:**

Return a structured summary in EXACTLY this format (use these headings):

**Goal:** One sentence — what the session was trying to accomplish.

**Features:** List each feature area as a short kebab-case name suitable for a YAML key and filename (e.g., `ingest-pipeline`, `semantic-search`). For each, include a one-line summary and a status: `exploring`, `building`, `polishing`, `parked`, or `planned`.

**Decisions:** Bullet list. Each entry MUST follow this format:
- `{feature-name}`: {what was decided} — {why it was decided}
Example: `ingest-pipeline`: Use SQLite FTS5 for full-text search — simpler than Elasticsearch, sufficient for single-user bookmark volumes.

**Open questions:** Bullet list with context. Each entry MUST follow this format:
- `{feature-name}`: {question} — {known constraints or tradeoffs}

**Implemented:** List of files created/modified and any git commits made.

**Session ending:** One of: `clean` (user explicitly wrapped up), `abrupt` (context exhaustion, crash), or `abandoned` (user just stopped). Include one sentence of evidence.

**Unfinished work:** What was in progress but not completed. Include the specific next action and relevant file paths. If nothing was unfinished, say "None."

---

Additional guidance for the subagent:
- If the transcript has fewer than 50 records, prefix the response with "⚠️ Short transcript — limited signal."
- Focus on *decisions and state changes*, not a blow-by-blow replay.
- Keep the entire response under 500 words. This feeds into ~30-line artifacts, not a report.

### Step 4: Generate Continuity Artifacts

Using the subagent's summary, prepare the artifacts to write. Read the current state of each file first — **merge, don't clobber**.

#### feature-status.yml
- Read existing `.continuity/feature-status.yml`
- For each feature area identified in the transcript:
  - If the feature already exists, update its `status`, `next`, and `summary` fields
  - If it's new, add it
  - Don't remove features that weren't mentioned — they're still valid
- Set `in_progress` to a task description if the session ended mid-stream, otherwise `null`
- Update `last_session` with the date, a one-sentence summary, and the primary feature area

#### decisions/{feature}.md
- For each feature area with decisions or open questions:
  - If the file exists, read it and merge new entries
  - If it doesn't exist, create it from the template
  - Add new decided items to "## Decided" — each with rationale
  - Add new open questions to "## Open" — each with context
  - Don't duplicate entries that already exist
  - Prune if the file would exceed ~30 lines (old decided items absorbed into codebase can go)

#### handoff.md
- Only create this if the session ended mid-stream (abrupt ending with unfinished work)
- Follow the handoff format from the wrap-up skill:

```xml
<handoff>
<!--
  Claude: Read ONLY this block first.
  Start with <first-action>, expand context only if stuck.
-->

<task>Single atomic deliverable</task>
<status>in-progress</status>

<first-action>
What to do next — specific file path and 3-5 bullets.
</first-action>

<verify>
How to confirm it works.
</verify>
</handoff>
```

- If the session ended cleanly and a `handoff.md` exists, note this to the user but don't delete it — let them decide (the original session may have had context we don't).

### Step 5: Preview Before Writing

Show the user exactly what will be written or changed. For each file:

- If it's a **new file**, show the full content
- If it's an **existing file being updated**, show what's changing (added/removed/modified entries)

Ask for confirmation before writing. The user should be able to:
- Approve all changes
- Skip specific files
- Edit the proposed changes (by telling you what to adjust)

### Step 6: Write Files

Apply the approved changes.

### Step 7: Confirm

Print a summary in the same format as wrap-up:

```
Recovered from session {session-id}:
  feature-status.yml — {feature}: {old-status} → {new-status}
  decisions/{feature}.md — +{n} decided, +{n} open
  handoff.md — created (session ended mid-stream)
```

## Edge Cases

- **Transcript too short** (< 50 records): Warn that there may not be enough signal. Proceed if the user wants to try, but set expectations.
- **Session already wrapped up**: If the transcript shows `/wrap-up` was run, or the `.continuity/` state already reflects the session's work, tell the user and skip gracefully. Don't duplicate effort.
- **Multiple feature areas**: Create or update decision files for each. The `last_session.feature` in status should reflect the primary area.
- **Existing state conflicts**: When merging, existing entries take precedence. New entries are appended. Show the user any conflicts.

## Guidelines

- **This is recovery, not archaeology.** Extract what `/wrap-up` would have produced, not a full session history.
- **Same quality bar as wrap-up.** Decisions need rationale. Open questions need context. Status updates need to be accurate.
- **Speed matters less here than accuracy.** Unlike wrap-up (< 1 minute), recovery can take a bit longer since it's parsing a transcript. But don't over-produce — the artifacts should still be concise.
- **When in doubt, show the user.** If the transcript is ambiguous about a decision or status, flag it in the preview and let the user decide.
