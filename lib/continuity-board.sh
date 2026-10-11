# continuity-board.sh — the one place that knows how feature-status.yml is laid
# out. Sourced by continuity-state; anything else that needs a row, a step count
# or the gotchas should call these rather than parse the file again.
#
# There is no YAML parser to rely on, so the board is read line by line:
# top-level keys at column 0, rows one level under `features:` / `workflows:`,
# a row's fields one level under the row. Each function reads the board on stdin.
#
#   cb_summary [cut]  the board with the bulk left out: per row its short fields
#                     (lines over <cut> bytes cut), `next_steps` / `steps` as
#                     counts, no `summary` / `artifacts`; other top-level blocks
#                     in full; each gotcha as its first 100 bytes
#   cb_row <name>     one row's block, verbatim. Exit 1 when there is no such row
#   cb_names          row names, one per line
#   cb_gotchas        the top-level `gotchas:` block, verbatim
#
# A step is done when it carries `done: true` outside a quoted string. A step
# list this reader can't follow prints `unreadable`, never a guessed number.

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

# --- step counting
function step_close(   t) {
  if (buf == "") return
  t = buf; buf = ""
  gsub(/"([^"\\]|\\.)*"/, "", t)
  if (t ~ /"/) { bad = 1; return }
  if (t ~ /(^|[ {,])done:[ ]*true([ ,}]|$)/) ndone++; else nopen++
}
function steps_begin(line, key,   rest) {
  counting = key; nopen = 0; ndone = 0; bad = 0; buf = ""; LI = -1
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
  else buf = buf " " line
}
function steps_end() {
  if (counting == "") return
  step_close()
  if (bad) print pad(F) counting ": unreadable"
  else if (counting == "next_steps") print pad(F) counting ": " nopen " open, " ndone " done"
  else print pad(F) counting ": " (nopen + ndone)
  counting = ""
}

# --- gotchas, first line of each
function gotcha_close() {
  if (ghead != "") { gl[++gn] = "  - " clip(ghead, 100) }
  ghead = ""; gwant = 0
}
function gotchas_end(   i) {
  if (top != "gotchas" || ginline) return
  gotcha_close()
  print "gotchas:  # " gn " entries, the first 100 bytes of each. Full text: continuity-state gotchas"
  for (i = 1; i <= gn; i++) print gl[i]
}

function row_end() { steps_end(); inrow = 0 }
function top_end() { row_end(); gotchas_end() }

BEGIN { top = ""; R = -1; F = -1; found = 0 }

{ blank = ($0 ~ /^[ ]*(#.*)?$/) }

# top-level key
!blank && /^[^ #-]/ {
  if (mode == "summary") top_end()
  top = keyof($0); rows = (top == "features" || top == "workflows"); R = -1; inrow = 0; taking = 0
  if (mode == "summary") {
    if (top == "gotchas") {
      gn = 0; ghead = ""; gwant = 0; G = -1
      ginline = ($0 !~ /^gotchas:[ ]*(#.*)?$/)
      if (ginline) print
    } else print
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

# mode == summary from here
top == "gotchas" {
  if (ginline) { print; next }
  if (blank) next
  if (G < 0) G = ind($0)
  if (ind($0) == G && body($0) ~ /^-( |$)/) {
    gotcha_close()
    ghead = body($0); sub(/^-[ ]*/, "", ghead)
    if (ghead ~ /^[>|][+-]?[0-9]*$/ || ghead == "") { ghead = ""; gwant = 1 }
  } else if (gwant) { ghead = body($0); gwant = 0 }
  next
}

!rows { print; next }

blank { next }

{
  if (R < 0) R = ind($0)
  if (ind($0) == R && body($0) !~ /^-/) {            # a row starts
    row_end(); inrow = 1; F = -1; skipping = 0
    print clip($0, cut)
    next
  }
  if (!inrow) next
  if (F < 0) F = ind($0)
  if (ind($0) == F && body($0) !~ /^-/) {            # a field of the row
    steps_end(); skipping = 0
    k = keyof($0)
    if (k == "summary" || k == "artifacts") skipping = 1
    else if (k == "next_steps" || k == "steps") steps_begin($0, k)
    else print clip($0, cut)
    next
  }
  if (skipping) next
  if (counting != "") { steps_feed($0); next }
  print clip($0, cut)                                # nested under a kept field
}

END {
  if (mode == "summary") top_end()
  if (mode == "row") exit(found ? 0 : 1)
}
'

cb_summary() { LC_ALL=C awk -v mode=summary -v cut="${1:-200}" "$CB_AWK"; }
cb_row()     { LC_ALL=C awk -v mode=row -v want="$1" "$CB_AWK"; }
cb_names()   { LC_ALL=C awk -v mode=names "$CB_AWK"; }
cb_gotchas() { LC_ALL=C awk -v mode=gotchas "$CB_AWK"; }
