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
  d=$(git symbolic-ref --short -q refs/remotes/origin/HEAD 2>/dev/null) \
    && git rev-parse -q --verify "$d^{commit}" >/dev/null && { echo "$d"; return 0; }   # not a dangling origin/HEAD
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
# the range, oldest first, from one git log pass (plus one to find sync commits).
# --no-renames: a code file moved into .continuity/ must show its old path too,
# or the commit would look continuity-only and its code would get landed.
cc_scan() {
  local dref="$1"; shift
  local landed sync
  landed=$(cc_landed_sources "$dref")
  # Sync commits are found by the message line, not a parsed trailer block, so a
  # commit-msg hook appending text after it doesn't hide one.
  sync=$(git log --format=%H --grep='^Continuity-Sync:' "$@" -- .continuity "$CC_EXCL" "$CC_AWAYX" 2>/dev/null)
  git log --reverse --full-diff --name-only --no-renames --format='%x01%H %P' \
      "$@" -- .continuity "$CC_EXCL" "$CC_AWAYX" 2>/dev/null |
  CC_LANDED="$landed" CC_SYNC="$sync" awk '
    BEGIN {
      landed = "\n" ENVIRON["CC_LANDED"] "\n"; synced = "\n" ENVIRON["CC_SYNC"] "\n"
      SOH = sprintf("%c", 1)   # commit headers start with \001, which no path can
    }
    function flush() {
      if (sha == "") return
      if (index(landed, "\n" sha "\n"))      kind = "landed"
      else if (index(synced, "\n" sha "\n")) kind = "sync"
      else if (parents > 1)                  kind = "merge"
      else if (mixed)                        kind = "mixed"
      else                                   kind = "pending"
      print sha, kind
    }
    substr($0, 1, 1) == SOH {
      flush()
      parents = split(substr($0, 2), p, " ") - 1; sha = p[1]; mixed = 0
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
  local own one
  while IFS=$'\t' read -r c src; do
    [ -n "$c" ] || continue
    own=""   # a resolve lands several of our commits at once: any one makes it ours
    for one in $src; do git merge-base --is-ancestor "$one" HEAD 2>/dev/null && { own=1; break; }; done
    [ -n "$own" ] && continue
    absorbed=""
    for s in $synced; do git merge-base --is-ancestor "$c" "$s" 2>/dev/null && { absorbed=1; break; }; done
    [ -n "$absorbed" ] && continue
    n=$((n + 1))
  done < <(git log --format='%H%x09%(trailers:key=Continuity-Source,valueonly,separator=%x20)' "HEAD..$dref" -- .continuity 2>/dev/null)
  echo "$n"
}
