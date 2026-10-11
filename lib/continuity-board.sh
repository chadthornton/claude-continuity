# continuity-board.sh — the one place that knows how feature-status.yml is laid
# out. Sourced by continuity-state and continuity-audit; anything else that
# needs a row, a step count or the gotchas should call these rather than parse
# the file again.
#
# There is no YAML parser to rely on, so the board is read line by line:
# top-level keys at column 0, rows one level under `features:` / `workflows:`,
# a row's fields one level under the row. Each function reads the board on stdin.
#
#   cb_summary [cut]  the board with the bulk left out: per row its short fields
#                     (lines over <cut> bytes cut), `next_steps` / `steps` /
#                     `claims` as counts, no `summary` / `artifacts` on feature rows; other top-level blocks
#                     in full; each gotcha as its first 100 bytes
#   cb_row <name>     one row's block, verbatim. Exit 1 when there is no such row
#   cb_names          row names, one per line
#   cb_gotchas        the top-level `gotchas:` block, verbatim
#   cb_facts          tab-separated records, one per line:
#                       row     section name status kind serves open done readable has_next_steps has_steps claims_readable
#                       gated   section name step gate  (open steps that carry a gate)
#                       claim   section name status text evidence waits_on   (status: true|false|unknown)
#                       pr      section name number     (each "PR #N" a row mentions)
#                       gotcha  first-line head last-line
#                       gotchalines count
#
# A step is done when it carries `done: true` outside a quoted string. A step or
# claim list this reader can't follow (an unclosed quote, a `>` or `|` block, an
# inline list) is `unreadable` (readable = 0), never a guessed number.

CB_AWK='
function ind(s) { match(s, /^ */); return RLENGTH }
function body(s) { sub(/^ +/, "", s); return s }
function clip(s, n,   t) {
  if (length(s) <= n) return s
  t = substr(s, 1, n)
  sub(/[\300-\367][\200-\277]*$/, "", t)        # never end on half a character
  return t " …[cut]"
}
function keyof(s) { s = body(s); sub(/:.*/, "", s); return s }
function pad(n,   s) { s = ""; while (n-- > 0) s = s " "; return s }
function out(s) { if (mode == "summary") print s }
function flat(s) { gsub(/\t/, " ", s); return s }
function unq(s) { gsub(/\\"/, "\"", s); return s }
# the value after "key:", without quotes or a trailing comment
function val(s) {
  sub(/^[^:]*:[ ]*/, "", s)
  if (s ~ /^"/) { if (match(s, /^"([^"\\]|\\.)*"/)) s = substr(s, 2, RLENGTH - 2); return unq(s) }
  sub(/[ ]+#.*$/, "", s); gsub(/^ +| +$/, "", s)
  if (s ~ /^\047.*\047$/) s = substr(s, 2, length(s) - 2)
  return s
}

# --- steps
# take(key): cut `key: value` out of the item in S and return the value. The
# key must be whole (`text`, not the tail of `context`). A quoted value may hold
# anything. A bare one ends at a comma or brace on a one-line item, at the line
# end on a multi-line one (ML; its lines are joined with \001), and loses a
# trailing comment. A block scalar (`>` or `|`) is not followed: bad = 1.
# (No apostrophes in this program: it sits inside a single-quoted shell string.)
function cutout(   v) {
  v = substr(S, RSTART, RLENGTH); S = substr(S, 1, RSTART - 1) " " substr(S, RSTART + RLENGTH)
  sub(/^[^:]*:[ ]*/, "", v)
  return v
}
function take(key,   v) {
  if (match(S, "(^|[ {,\001])" key ":[ ]*\"([^\"\\\\]|\\\\.)*\"")) {
    v = cutout(); sub(/^"/, "", v); sub(/"$/, "", v)
    return unq(v)
  }
  if (match(S, "(^|[ {,\001])" key ":[ ]*\047([^\047]|\047\047)*\047")) {
    v = cutout(); sub(/^\047/, "", v); sub(/\047$/, "", v); gsub(/\047\047/, "\047", v)
    return v
  }
  if (match(S, "(^|[ {,\001])" key ":[ ]*" (ML ? "[^\001]*" : "[^,}]*"))) {
    v = cutout(); sub(/[ ]+#.*$/, "", v); gsub(/ +$/, "", v)
    if (v ~ /^[>|][+-]?[0-9]*$/) bad = 1
    return v
  }
  return ""
}
function step_close(   t, st, g, ev, w, isdone) {
  if (buf == "") return
  S = buf; buf = ""
  ML = (index(S, "\001") > 0)
  t = S
  gsub(/:[ ]*\047([^\047]|\047\047)*\047/, ": ", t)
  gsub(/"([^"\\]|\\.)*"/, "", t)
  if (t ~ /"/ || t ~ /:[ ]*[>|][+-]?[0-9]*[ ]*(\001|$)/) { bad = 1; return }
  if (counting == "claims") {
    st = take("text"); ev = take("evidence"); w = take("waits_on"); g = tolower(take("status"))
    if (g != "true" && g != "false") g = "unknown"
    if (g == "true") ctrue++; else if (g == "false") cfalse++; else cother++
    if (mode == "facts" && !bad) print "claim\t" top "\t" flat(rname) "\t" g "\t" flat(st) "\t" flat(ev) "\t" flat(w)
    return
  }
  isdone = (t ~ /(^|[ {,])done:[ ]*true([ ,}\001]|$)/)
  if (isdone) ndone++; else nopen++
  if (mode != "facts" || counting != "next_steps" || isdone || t !~ /(^|[ {,])gate:/) return
  st = take("step"); g = take("gate")
  if (!bad) print "gated\t" top "\t" flat(rname) "\t" flat(st) "\t" flat(g)
}
function steps_begin(line, key,   rest) {
  counting = key; nopen = 0; ndone = 0; ctrue = 0; cfalse = 0; cother = 0; bad = 0; buf = ""; LI = -1
  rest = line; sub(/^[^:]*:/, "", rest); sub(/[ ]+#.*$/, "", rest); gsub(/^ +| +$/, "", rest)
  if (rest == "[]") counting_done = 1
  else if (rest != "") { bad = 1; counting_done = 1 }
  else counting_done = 0
}
function steps_feed(line) {
  if (counting_done) return
  if (LI < 0) LI = ind(line)
  if (ind(line) == LI && body(line) ~ /^-( |$)/) { step_close(); buf = line }
  else if (buf == "") bad = 1
  else buf = buf "\001" line
}
function steps_end() {
  if (counting == "") return
  step_close()
  if (bad) out(pad(F) counting ": unreadable")
  else if (counting == "claims") out(pad(F) "claims: " (ctrue + cfalse + cother) " (" ctrue " true, " cfalse " false, " cother " unknown)")
  else if (counting == "next_steps") out(pad(F) counting ": " nopen " open, " ndone " done")
  else out(pad(F) counting ": " (nopen + ndone))
  if (counting == "next_steps") { ropen = nopen; rdone = ndone; rbad = bad }
  if (counting == "claims") rcbad = bad
  counting = ""
}

# --- gotchas, first line of each
function gotcha_close() {
  if (ghead != "") {
    gl[++gn] = "  - " clip(ghead, 100)
    if (mode == "facts") print "gotcha\t" gline "\t" flat(clip(ghead, 100)) "\t" gend
  }
  ghead = ""; gwant = 0
}
function gotchas_end(   i) {
  if (top != "gotchas" || ginline) return
  gotcha_close()
  out("gotchas:  # " gn " entries, the first 100 bytes of each. Full text: continuity-state gotchas")
  for (i = 1; i <= gn; i++) out(gl[i])
  if (mode == "facts") print "gotchalines\t" gbody
}

function row_end() {
  steps_end()
  if (inrow && mode == "facts")
    print "row\t" top "\t" flat(rname) "\t" flat(rstatus) "\t" flat(rkind) "\t" flat(rserves) "\t" ropen "\t" rdone "\t" (rbad ? 0 : 1) "\t" hasns "\t" hassteps "\t" (rcbad ? 0 : 1)
  inrow = 0
}
function top_end() { row_end(); gotchas_end() }
function prs(line,   s, n) {
  s = line
  while (match(s, /PRs? #[0-9]+/)) {
    n = substr(s, RSTART, RLENGTH); sub(/^PRs? #/, "", n)
    if (!((top, rname, n) in seenpr)) { seenpr[top, rname, n] = 1; print "pr\t" top "\t" flat(rname) "\t" n }
    s = substr(s, RSTART + RLENGTH)
  }
}

BEGIN { top = ""; R = -1; F = -1; found = 0; walk = (mode == "summary" || mode == "facts") }

{ sub(/\r$/, ""); blank = ($0 ~ /^[ ]*(#.*)?$/) }

# top-level key
!blank && /^[^ #-]/ {
  if (walk) top_end()
  top = keyof($0); rows = (top == "features" || top == "workflows"); R = -1; inrow = 0; taking = 0
  if (walk) {
    if (top == "gotchas") {
      gn = 0; ghead = ""; gwant = 0; G = -1; gbody = 0
      ginline = ($0 !~ /^gotchas:[ ]*(#.*)?$/)
      if (ginline) out($0)
    } else out($0)
  }
  if (mode == "gotchas" && top == "gotchas") print
  next
}

mode == "gotchas" { if (top == "gotchas") print; next }

mode == "names" || mode == "row" {
  if (!rows) next
  if (!blank && R < 0) R = ind($0)
  if (!blank && ind($0) == R && body($0) !~ /^-/) {
    taking = 0
    if (mode == "names") print keyof($0)
    else if (keyof($0) == want && !found) { found = 1; taking = 1 }
  }
  if (taking) print
  next
}

# summary and facts from here
top == "gotchas" {
  if (ginline) { out($0); next }
  if (blank) next
  gbody++
  if (G < 0) G = ind($0)
  if (ind($0) == G && body($0) ~ /^-( |$)/) {
    gotcha_close()
    gline = NR; gend = NR
    ghead = body($0); sub(/^-[ ]*/, "", ghead)
    if (ghead ~ /^[>|][+-]?[0-9]*$/ || ghead == "") { ghead = ""; gwant = 1 }
    else if (ghead ~ /^"/) ghead = val("x: " ghead)
  } else {
    gend = NR
    if (gwant) { ghead = body($0); gwant = 0 }
  }
  next
}

!rows { out($0); next }

blank { next }

{
  if (R < 0) R = ind($0)
  if (ind($0) == R && body($0) !~ /^-/) {            # a row starts
    row_end(); inrow = 1; F = -1; skipping = 0
    rname = keyof($0); rstatus = ""; rkind = ""; rserves = ""; ropen = 0; rdone = 0; rbad = 0; rcbad = 0; hasns = 0; hassteps = 0
    out(clip($0, cut))
    next
  }
  if (!inrow) next
  if (mode == "facts") prs($0)
  if (F < 0) F = ind($0)
  if (ind($0) == F && body($0) !~ /^-/) {            # a field of the row
    steps_end(); skipping = 0
    k = keyof($0)
    if (k == "status") rstatus = val($0)
    else if (k == "kind") rkind = val($0)
    else if (k == "serves") rserves = val($0)
    if ((k == "summary" || k == "artifacts") && top != "workflows") skipping = 1
    else if (k == "next_steps" || k == "steps" || k == "claims") { steps_begin($0, k); if (k == "steps") hassteps = 1; else if (k == "next_steps") hasns = 1 }
    else out(clip($0, cut))
    next
  }
  if (skipping) next
  if (counting != "") { steps_feed($0); next }
  out(clip($0, cut))                                 # nested under a kept field
}

END {
  if (walk) top_end()
  if (mode == "row") exit(found ? 0 : 1)
}
'

cb_summary() { LC_ALL=C awk -v mode=summary -v cut="${1:-200}" "$CB_AWK"; }
cb_row()     { LC_ALL=C awk -v mode=row -v want="$1" "$CB_AWK"; }
cb_names()   { LC_ALL=C awk -v mode=names "$CB_AWK"; }
cb_gotchas() { LC_ALL=C awk -v mode=gotchas "$CB_AWK"; }
cb_facts()   { LC_ALL=C awk -v mode=facts "$CB_AWK"; }
