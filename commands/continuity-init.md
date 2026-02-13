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

4. Create `feature-status.yml` with the identified features:
   ```yaml
   features:
     feature-name:
       status: planned    # exploring | building | polishing | parked | planned
       next: (to be determined)
       summary: Brief description

   in_progress: null

   last_session:
     date: (today)
     summary: Initialized continuity tracking
     feature: null
   ```

5. For each feature area, create a `decisions/{feature-name}.md`:
   ```markdown
   # Feature Name

   ## Decided
   (none yet)

   ## Open
   (none yet)
   ```

6. If you can infer any existing decisions or open questions from the project's CLAUDE.md, PLAN.md, or other documentation, offer to pre-populate the decision files. Ask before writing — the user should confirm.

7. Print a summary of what was created.

8. Remind the user to add `.continuity/last-activity.txt` to their `.gitignore` if the project is version-controlled (it contains transient session data).
