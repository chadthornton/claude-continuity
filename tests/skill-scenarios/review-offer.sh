#!/bin/bash
# Fixture for the one-line board review offer in /startup and wrap-up.
#   review-offer.sh <dir> due      9 features, never reviewed, last session 2 days
#                                  ago, clean stop: startup's dashboard should end
#                                  with "A board review is due (last one (none
#                                  yet)). Say "review the board" ..."
#   review-offer.sh <dir> resume   reviewed 10 days ago (due), but `alpha` is in
#                                  progress with a handoff from today: startup
#                                  fast-resumes and must say nothing about reviews
#   review-offer.sh <dir> wrapup   the session finished one step each on alpha, beta
#                                  and gamma: wrap-up's summary should end with
#                                  "Several features changed. Say "review the board" ..."
# Checkout at <dir>/work. Check: grep -c 'review the board' on the agent's final reply
# (1 for due and wrapup, 0 for resume).
set -euo pipefail
root="$1"; mode="$2"; rm -rf "$root"; mkdir -p "$root"; cd "$root"
git init -q --bare -b main origin.git
git clone -q origin.git work 2>/dev/null; cd work
git config user.email t@t; git config user.name t
mkdir -p .continuity/decisions .continuity/handoffs
d() { date -v-"$1"d +%F 2>/dev/null || date -d "-$1 days" +%F; }
lr=""; [ "$mode" = resume ] && lr="  last_review: $(d 10)"
ls_date=$(d 2); [ "$mode" = resume ] && ls_date=$(date +%F)
{
  echo "settings:"; echo "  push_to_default_branch: true"; [ -n "$lr" ] && echo "$lr"
  echo "features:"
  for f in alpha beta gamma delta epsilon zeta eta theta iota; do
    echo "  $f:"; echo "    status: building"; echo "    next: \"Next $f step\""
    echo "    next_steps:"; echo "      - { step: \"$f step one\", done: false }"; echo "      - { step: \"$f step two\", done: false }"
    [ "$mode" = resume ] && [ "$f" = alpha ] && echo "    in_progress: \"alpha step one\""
  done
  echo "last_session:"; echo "  date: $ls_date"; echo "  feature: alpha"; echo "  summary: \"Worked on alpha\""
} > .continuity/feature-status.yml
[ "$mode" = resume ] && printf '<handoff>\n<task>alpha: finish step one</task>\n<first-action>Run the alpha tests</first-action>\n</handoff>\n' > .continuity/handoffs/alpha.md
echo "# app" > README.md
git add -A; git commit -qm init; git push -q origin HEAD:main
echo "checkout: $root/work"
