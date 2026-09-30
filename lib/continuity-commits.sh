# continuity-commits.sh — the one set of rules for which commits are continuity
# state. Sourced (bash) by continuity-save, continuity-state, away and the
# SessionStart / WorktreeRemove hooks, so they can't drift apart again.
#
# A commit that touches .continuity/ is one of:
#   landed   already on the default branch (a Continuity-Source trailer there names it)
#   sync     a continuity-save re-sync that copied the default branch's board
#   merge    a merge commit — its parents carry the edits
#   mixed    also touches code or .continuity/away.md: lands only when its branch merges
#   pending  continuity-only and not yet landed — what continuity-save lands
# Commits touching only last-activity.txt or away.md aren't continuity at all.

CC_EXCL=':(exclude).continuity/last-activity.txt'
CC_AWAYX=':(exclude).continuity/away.md'

# cc_default_ref — print origin/<default>: origin/HEAD, else origin/main or
# origin/master. Prints nothing and returns 1 when it can't tell.
cc_default_ref() {
  local d
  d=$(git symbolic-ref --short -q refs/remotes/origin/HEAD 2>/dev/null) && { echo "$d"; return 0; }
  for d in main master; do
    git show-ref -q --verify "refs/remotes/origin/$d" 2>/dev/null && { echo "origin/$d"; return 0; }
  done
  return 1
}

# cc_landed_sources <default-ref> — SHAs already landed (Continuity-Source trailers).
cc_landed_sources() {
  git log "$1" -n 500 --format='%(trailers:key=Continuity-Source,valueonly,separator=%x0a)' 2>/dev/null | grep -v '^$'
}

# cc_scan <default-ref> <rev-list args…> — "<sha> <kind>" per continuity commit in
# the range, oldest first. One git log pass, whatever the range size.
cc_scan() {
  local dref="$1"; shift
  local landed; landed=$(cc_landed_sources "$dref")
  git log --reverse --full-diff --name-only \
      --format='@%H %P%x09%(trailers:key=Continuity-Sync,valueonly,separator=%x20)' \
      "$@" -- .continuity "$CC_EXCL" "$CC_AWAYX" 2>/dev/null |
  CC_LANDED="$landed" awk '
    BEGIN { landed = "\n" ENVIRON["CC_LANDED"] "\n" }
    function flush() {
      if (sha == "") return
      if (index(landed, "\n" sha "\n")) kind = "landed"
      else if (sync)                    kind = "sync"
      else if (parents > 1)             kind = "merge"
      else if (mixed)                   kind = "mixed"
      else                              kind = "pending"
      print sha, kind
    }
    /^@/ {
      flush()
      split(substr($0, 2), f, "\t")
      parents = split(f[1], p, " ") - 1; sha = p[1]
      sync = (f[2] != ""); mixed = 0
      next
    }
    /^$/ { next }
    { if ($0 !~ /^\.continuity\// || $0 == ".continuity/away.md") mixed = 1 }
    END { flush() }
  '
}

# cc_pending <default-ref> <rev-list args…> — just the pending SHAs, oldest first.
cc_pending() {
  cc_scan "$@" | awk '$2 == "pending" { print $1 }'
}

# cc_behind <default-ref> — how many continuity commits on the default branch
# this checkout lacks, not counting its own landed saves (their
# Continuity-Source is in HEAD) or peer commits a sync already copied in.
cc_behind() {
  local dref="$1" n=0 c src s absorbed synced
  git diff --quiet HEAD "$dref" -- .continuity "$CC_EXCL" "$CC_AWAYX" 2>/dev/null && { echo 0; return; }
  synced=$(git log HEAD -n 200 --format='%(trailers:key=Continuity-Sync,valueonly,separator=%x0a)' 2>/dev/null | grep -v '^$')
  while IFS=$'\t' read -r c src; do
    [ -n "$c" ] || continue
    [ -n "$src" ] && git merge-base --is-ancestor "$src" HEAD 2>/dev/null && continue
    absorbed=""
    for s in $synced; do git merge-base --is-ancestor "$c" "$s" 2>/dev/null && { absorbed=1; break; }; done
    [ -n "$absorbed" ] && continue
    n=$((n + 1))
  done < <(git log --format='%H%x09%(trailers:key=Continuity-Source,valueonly,separator=%x20)' "HEAD..$dref" -- .continuity 2>/dev/null)
  echo "$n"
}
