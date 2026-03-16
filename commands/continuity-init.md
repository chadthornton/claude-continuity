---
name: continuity-init
description: Scaffold a .continuity/ directory in the current project for cross-session continuity tracking.
---

# Initialize Continuity Tracking

Set up the `.continuity/` directory structure for this project.

## Steps

1. Check if `.continuity/` already exists. If so, inform the user and ask if they want to reset or abort.

2. Create the directory structure:
   ```
   .continuity/
   ├── feature-status.yml
   └── decisions/
   ```

3. Ask the user: "What are the main feature areas for this project?" Use AskUserQuestion if there are obvious candidates from the codebase, or just ask for a free-text list.

4. Ask: "Do these features have a strict build order (phases)? If so, I'll number them — Phase 1 must complete before Phase 2 can start, etc." If yes, assign `phase: N` in the order the user listed them. If no, omit the `phase` field entirely.

5. Create `feature-status.yml` with the identified features:
   ```yaml
   features:
     feature-name:
       status: planned    # exploring | building | polishing | parked | planned
       phase: 1           # Only if user opted into phases. Omit otherwise.
       next: (to be determined)
       summary: Brief description
       next_steps: []     # Plain strings or {step, done} objects

   in_progress: null

   last_session:
     date: (today)
     summary: Initialized continuity tracking
     feature: null
   ```

6. For each feature area, create a `decisions/{feature-name}.md`:
   ```markdown
   # Feature Name

   ## Decided
   (none yet)

   ## Open
   (none yet)
   ```

7. If you can infer any existing decisions or open questions from the project's CLAUDE.md, PLAN.md, or other documentation, offer to pre-populate the decision files. Ask before writing — the user should confirm.

8. Print a summary of what was created.

9. Remind the user to add `.continuity/last-activity.txt` to their `.gitignore` if the project is version-controlled (it contains transient session data).
