#!/bin/bash
# Prints a one-line notice if the project has no .continuity/ directory.
# Helps users discover the continuity system in new projects.

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')

if [ ! -d "$CWD/.continuity" ]; then
  echo '{"additionalContext": "This project has no .continuity/ directory. Run /continuity-init to enable cross-session continuity tracking (feature status, decisions, open questions)."}'
fi

exit 0
