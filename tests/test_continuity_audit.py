"""Scenario tests for lib/continuity-audit. Run: python3 tests/test_continuity_audit.py"""
import json, os, shutil, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, 'lib', 'continuity-audit')
# reuse helpers without running the save scenarios
_save_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_continuity_save.py')
ns = {'__file__': _save_py}
exec(open(_save_py).read().split('# 1. Feature branch')[0], ns)
git, write, expect, ENV, fails = ns['git'], ns['write'], ns['expect'], ns['ENV'], ns['fails']


def audit(cwd, **env):
    """Run the audit; returns (exit code, parsed JSON or None, raw output)."""
    e = dict(ENV); e.setdefault('CONTINUITY_AUDIT_WT', 'false'); e.update(env)   # the real wt:status takes seconds
    r = subprocess.run([AUDIT], cwd=cwd, env=e, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    try:
        return r.returncode, json.loads(r.stdout), r.stdout + r.stderr
    except ValueError:
        return r.returncode, None, r.stdout + r.stderr


def row(doc, name):
    return next((r for r in doc['rows'] if r['name'] == name), None)


def repo(board, files=None, when=None):
    """A git repo holding .continuity/feature-status.yml (+ files), committed at `when` (epoch seconds)."""
    d = tempfile.mkdtemp()
    git(d, 'init', '-q', '-b', 'master')
    write(f'{d}/.continuity/feature-status.yml', board)
    for path, text in (files or {}).items():
        write(f'{d}/{path}', text)
    commit(d, 'init', when)
    return d


def commit(d, msg, when=None):
    e = dict(ENV)
    if when:
        e['GIT_AUTHOR_DATE'] = e['GIT_COMMITTER_DATE'] = f'{int(when)} +0000'
    subprocess.run(['git', 'add', '-A'], cwd=d, env=e, check=True)
    subprocess.run(['git', 'commit', '-qm', msg], cwd=d, env=e, check=True)


def fake_gh(body):
    """A directory holding an executable `gh` that runs `body`."""
    d = tempfile.mkdtemp()
    p = os.path.join(d, 'gh')
    write(p, '#!/bin/bash\n' + body + '\n')
    os.chmod(p, 0o755)
    return d, p


BOARD = '''settings:
  push_to_default_branch: true
features:
  shipping:
    status: building
    serves: fast-checkout
    next: "Wire the carrier API (PR #12)"
    next_steps:
      - { step: "Pick a carrier", done: true }
      - { step: "Wire the carrier API, see PR #12 and PRs #14", done: false }
      - { step: "Charge real cards, gate: none yet", done: false, gate: approval }
      - { step: "Choose the label size", gate: "decision: A6 or 4x6?", done: false }
      - { step: "Old gated thing", gate: approval, done: true }
  finished:
    status: polishing
    next: "Nothing left"
    next_steps:
      - { step: "Only step", done: true }
  resting:
    status: parked
    next_steps: []
  tangled:
    status: building
    next_steps: [a, b]
  block-style:
    kind: milestone
    status: building
    next_steps:
      - step: "First"
        done: true
      - step: "Second"
        gate: approval
        done: false
workflows:
  weekly-audit:
    trigger: "Weekly"
    summary: "Run the audit"
    steps:
      - "pull counts"
  misfiled:
    status: building
    next: "This is a feature"
    next_steps:
      - { step: "Do it (PR #12)", done: false }
last_session:
  date: 2026-10-11
  feature: shipping
'''

# A1. Rows: counts, status, section, and the flags the review acts on.
d = repo(BOARD)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('A1 exit 0 and valid JSON', rc == 0 and doc is not None, raw[:400])
doc = doc or {'rows': [], 'prs': {'items': []}}
expect('A1 every row listed, features then workflows',
       [r['name'] for r in doc['rows']] == ['shipping', 'finished', 'resting', 'tangled', 'block-style', 'weekly-audit', 'misfiled'],
       [r['name'] for r in doc['rows']])
s = row(doc, 'shipping') or {}
expect('A1 open and done counted', (s.get('open'), s.get('done')) == (3, 2), s)
expect('A1 status, section, serves', (s.get('status'), s.get('section'), s.get('serves')) == ('building', 'features', 'fast-checkout'), s)
expect('A1 a row with open steps is not flagged finished', 'no_open_steps' not in s.get('flags', ['x']), s)
f = row(doc, 'finished') or {}
expect('A1 polishing row with zero open steps flagged', 'no_open_steps' in f.get('flags', []), f)
expect('A1 a parked row with no steps is not flagged finished', 'no_open_steps' not in (row(doc, 'resting') or {}).get('flags', ['x']), row(doc, 'resting'))
t = row(doc, 'tangled') or {}
expect('A1 unreadable steps: no counts, not flagged finished',
       t.get('steps_readable') is False and t.get('open') is None and 'no_open_steps' not in t.get('flags', ['x']), t)
b = row(doc, 'block-style') or {}
expect('A1 multi-line steps counted; kind read', (b.get('open'), b.get('done'), b.get('kind')) == (1, 1, 'milestone'), b)
expect('A1 a row that names nothing it serves is not a finding',
       f.get('serves') is None and not any('serves' in x for r in doc['rows'] for x in r['flags']), doc['rows'])
m = row(doc, 'misfiled') or {}
expect('A1 feature-shaped row under workflows flagged', 'feature_under_workflows' in m.get('flags', []) and m.get('section') == 'workflows', m)
expect('A1 a real workflow is not flagged', (row(doc, 'weekly-audit') or {}).get('flags', ['x']) == [], row(doc, 'weekly-audit'))

# A2. Gated items: open steps only, with the step and the gate; text inside a step is not a gate.
g = s.get('gated', [])
expect('A2 two open gated steps on shipping', len(g) == 2, g)
expect('A2 approval gate', {'step': 'Charge real cards, gate: none yet', 'gate': 'approval'} in g, g)
expect('A2 decision gate keeps its question', {'step': 'Choose the label size', 'gate': 'decision: A6 or 4x6?'} in g, g)
expect('A2 multi-line gated step', b.get('gated') == [{'step': 'Second', 'gate': 'approval'}], b.get('gated'))

# A3. PR references without gh: numbers and rows still reported, state unknown, exit 0.
prs = doc.get('prs', {})
expect('A3 gh missing: source says so', prs.get('source') == 'unavailable', prs)
by = {p['number']: p for p in prs.get('items', [])}
expect('A3 PR numbers found once each', sorted(by) == [12, 14], sorted(by))
expect('A3 PR 12 lists both rows that cite it', by.get(12, {}).get('rows') == ['shipping', 'misfiled'], by.get(12))
expect('A3 state unknown without gh', all(p.get('state') == 'unknown' for p in by.values()), by)

# A4. gh present: states come from one listing; a PR gh does not know stays unknown.
ghdir, gh = fake_gh('echo \'[{"number":12,"state":"MERGED"},{"number":99,"state":"OPEN"}]\'')
rc, doc2, raw = audit(d, CONTINUITY_AUDIT_GH=gh)
by = {p['number']: p for p in (doc2 or {'prs': {'items': []}})['prs']['items']}
expect('A4 states from gh', rc == 0 and by.get(12, {}).get('state') == 'MERGED' and by.get(14, {}).get('state') == 'unknown', raw[:300])
expect('A4 source is gh', (doc2 or {}).get('prs', {}).get('source') == 'gh', raw[:300])
# gh installed but failing (logged out): same as missing.
ghdir2, gh2 = fake_gh('echo "gh: not logged in" >&2; exit 4')
rc, doc3, raw = audit(d, CONTINUITY_AUDIT_GH=gh2)
expect('A4 failing gh: exit 0, source unavailable', rc == 0 and (doc3 or {}).get('prs', {}).get('source') == 'unavailable', raw[:300])
for x in (d, ghdir, ghdir2):
    shutil.rmtree(x)

# A5. Sizes: the board, and each decisions file against the ~30-line budget.
now = time.time()
day = 86400
GOTCHA_BOARD = BOARD + '''gotchas:
  - "Old gotcha: the harness needs CI=1"
  - >
    Folded gotcha about the gateway
    that runs on to a second line
'''
d = repo(GOTCHA_BOARD, {
    '.continuity/decisions/shipping.md': '# shipping\n' + '- a decision — because\n' * 40,
    '.continuity/decisions/small.md': '# small\n- one — why\n',
}, when=now - 40 * day)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
doc = doc or {}
expect('A5 board size', doc.get('board', {}).get('bytes') == len(GOTCHA_BOARD.encode()) and doc.get('board', {}).get('lines') == GOTCHA_BOARD.count('\n'), doc.get('board'))
dec = {x['path']: x for x in doc.get('decisions', [])}
big, small = dec.get('.continuity/decisions/shipping.md', {}), dec.get('.continuity/decisions/small.md', {})
expect('A5 decisions files sized', (big.get('lines'), small.get('lines')) == (41, 2), dec)
expect('A5 only the long one is over budget', big.get('over_budget') is True and small.get('over_budget') is False, dec)

# A6. Gotchas: first lines, age from git history, and the list against its cap.
g = doc.get('gotchas', {})
e = g.get('entries', [])
expect('A6 two gotchas, first lines', [x.get('head') for x in e] == ['Old gotcha: the harness needs CI=1', 'Folded gotcha about the gateway'], e)
expect('A6 age is the days since the line was last edited', [x.get('age_days') for x in e] == [40, 40], e)
expect('A6 last_edited is that date', all(x.get('last_edited') == time.strftime('%Y-%m-%d', time.gmtime(now - 40 * day)) for x in e), e)
expect('A6 under the cap', (g.get('count'), g.get('lines'), g.get('cap'), g.get('over_cap')) == (2, 4, 10, False), g)
# Edit one gotcha 3 days ago: only that one gets younger.
write(f'{d}/.continuity/feature-status.yml', GOTCHA_BOARD.replace('needs CI=1', 'needs CI=1 and TZ=UTC'))
commit(d, 'touch a gotcha', when=now - 3 * day)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
e = (doc or {}).get('gotchas', {}).get('entries', [])
expect('A6 an edited gotcha is younger, its neighbour is not', [x.get('age_days') for x in e] == [3, 40], e)
# Past the cap.
write(f'{d}/.continuity/feature-status.yml', BOARD + 'gotchas:\n' + ''.join(f'  - "gotcha {i}"\n' for i in range(12)))
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
g = (doc or {}).get('gotchas', {})
expect('A6 over the cap', (g.get('count'), g.get('over_cap')) == (12, True), g)
shutil.rmtree(d)

# A7. Secret-looking strings: where and what kind, never the value.
TOKEN = 'ghp_' + 'A1b2C3d4E5' * 3 + 'f6G7h8'
d = repo(BOARD, {
    '.continuity/decisions/shipping.md': '# shipping\n- use the bot token ' + TOKEN + ' — temporary\n',
    '.continuity/handoffs/shipping.md': 'line one\nAWS key AKIAABCDEFGHIJKLMNOP here\napi_key = "abcdef0123456789abcdef"\n',
    '.continuity/decisions/clean.md': '# clean\n- token rotation is weekly — policy\n',
})
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
sec = (doc or {}).get('secrets', [])
found = {(x.get('path'), x.get('line'), x.get('kind')) for x in sec}
expect('A7 github token located', ('.continuity/decisions/shipping.md', 2, 'github-token') in found, sec)
expect('A7 aws key and assigned key located',
       ('.continuity/handoffs/shipping.md', 2, 'aws-access-key') in found and ('.continuity/handoffs/shipping.md', 3, 'assigned-secret') in found, sec)
expect('A7 prose about tokens is not a finding', not any(x.get('path', '').endswith('clean.md') for x in sec), sec)
expect('A7 the secret itself is never printed', TOKEN not in raw and 'AKIAABCDEFGHIJKLMNOP' not in raw and 'abcdef0123456789abcdef' not in raw, raw[:200])
shutil.rmtree(d)

# A8. Files that are not the record's plain text: binaries and other formats.
d = repo(BOARD, {
    '.continuity/workflows/page.html': '<html>review page</html>\n',
    '.continuity/decisions/shipping.md': '# shipping\n',
    '.continuity/last-activity.txt': 'ended\n',
})
with open(f'{d}/.continuity/shot.png', 'wb') as fh:
    fh.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\x00binary')
commit(d, 'add a screenshot')
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
uf = {x['path']: x for x in (doc or {}).get('unexpected_files', [])}
expect('A8 the binary and the html are listed, nothing else',
       sorted(uf) == ['.continuity/shot.png', '.continuity/workflows/page.html'], sorted(uf))
expect('A8 binary flagged, html not', uf.get('.continuity/shot.png', {}).get('binary') is True and uf.get('.continuity/workflows/page.html', {}).get('binary') is False, uf)
expect('A8 sizes reported', uf.get('.continuity/workflows/page.html', {}).get('bytes') == 25, uf)
shutil.rmtree(d)

# A9. The smallest board, no git, none of the optional fields: empty findings, not errors.
plain = tempfile.mkdtemp()
write(f'{plain}/.continuity/feature-status.yml', 'features:\n  a:\n    status: planned\n    next: Define scope\n    next_steps: []          # none yet\ngotchas: []\n')
rc, doc, raw = audit(plain, CONTINUITY_AUDIT_GH='no-such-gh-binary')
doc = doc or {}
expect('A9 exit 0 without git', rc == 0 and doc.get('rows', [{}])[0].get('name') == 'a', raw[:300])
expect('A9 empty findings', (doc.get('secrets'), doc.get('unexpected_files'), doc.get('decisions'), doc.get('prs', {}).get('items')) == ([], [], [], []), doc)
expect('A9 no gotchas', (doc.get('gotchas', {}).get('count'), doc.get('gotchas', {}).get('entries')) == (0, []), doc.get('gotchas'))
write(f'{plain}/.continuity/feature-status.yml', 'features:\n  a:\n    status: planned\ngotchas:\n  - "No history here"\n')
rc, doc, raw = audit(plain, CONTINUITY_AUDIT_GH='no-such-gh-binary')
e = (doc or {}).get('gotchas', {}).get('entries', [{}])
expect('A9 without git a gotcha has no age', rc == 0 and e[0].get('head') == 'No history here' and e[0].get('age_days') is None, e)
shutil.rmtree(plain)

# A10. No .continuity/ → exit 3, nothing on stdout.
bare = tempfile.mkdtemp()
r = subprocess.run([AUDIT], cwd=bare, env=ENV, capture_output=True, text=True)
expect('A10 exit 3 with a hint', r.returncode == 3 and r.stdout == '' and 'continuity-init' in r.stderr, r.stdout + r.stderr)
shutil.rmtree(bare)

# A11. Milestones: a row of claims, each with a status and the evidence for it.
MILESTONE = '''features:
  invite-email:
    kind: milestone
    status: building
    next: "Three guests join on 2026-11-07"
    claims:
      - { text: "Both mails arrive, status: delivered", status: true, evidence: "Real send 2026-10-10: neither in spam" }
      - { text: "Sign-up works on a phone", status: true }
      - { text: "Pasted places make a list", status: false, evidence: "One-line paste made a junk place", waits_on: "the import fix" }
      - text: "Peek at each other's lists"
        status: unknown
      - { text: "No status given" }
  plain:
    status: building
    next_steps:
      - { step: "Work", done: false }
'''
d = repo(MILESTONE)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
m = row(doc or {'rows': []}, 'invite-email') or {}
c = m.get('claims', [])
expect('A11 five claims, in order', [x.get('text') for x in c] == ['Both mails arrive, status: delivered', 'Sign-up works on a phone', 'Pasted places make a list', "Peek at each other's lists", 'No status given'], c)
expect('A11 statuses; a missing one is unknown', [x.get('status') for x in c] == ['true', 'true', 'false', 'unknown', 'unknown'], c)
expect('A11 evidence kept, absent is null', (c + [{}] * 5)[0].get('evidence') == 'Real send 2026-10-10: neither in spam' and (c + [{}] * 5)[1].get('evidence') is None, c)
expect('A11 what a claim waits on', (c + [{}] * 5)[2].get('waits_on') == 'the import fix' and (c + [{}] * 5)[0].get('waits_on') is None, c)
expect('A11 a true claim with no evidence flags the row', 'true_claim_without_evidence' in m.get('flags', []), m.get('flags'))
expect('A11 a milestone with no steps is not flagged finished', 'no_open_steps' not in m.get('flags', ['x']), m.get('flags'))
expect('A11 a row without claims has an empty list and no flag', (row(doc or {'rows': []}, 'plain') or {}).get('claims') == [] and (row(doc or {'rows': []}, 'plain') or {}).get('flags') == [], row(doc or {'rows': []}, 'plain'))
write(f'{d}/.continuity/feature-status.yml', MILESTONE.replace('{ text: "Sign-up works on a phone", status: true }', '{ text: "Sign-up works on a phone", status: true, evidence: "Walked at 390px" }'))
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('A11 with evidence on every true claim the flag clears', (row(doc or {'rows': []}, 'invite-email') or {}).get('flags') == [], raw[:300])
shutil.rmtree(d)

# A12. A board made from the plugin's template audits clean.
d = repo(open(os.path.join(ROOT, 'templates', 'feature-status.yml')).read())
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
rows = (doc or {}).get('rows', [])
expect('A12 template board: one readable row, no flags', rc == 0 and len(rows) == 1 and rows[0].get('steps_readable') is True and rows[0].get('flags') == [] and rows[0].get('claims') == [], raw[:400])
expect('A12 template board: no findings', (doc or {}).get('secrets') == [] and (doc or {}).get('gotchas', {}).get('count') == 0, raw[:400])
shutil.rmtree(d)

# --- Review findings, 2026-10-11.
TOK = 'ghp_' + 'Z9y8X7w6V5' * 3 + 'u4T3s2'
HARD = '''features:
  ms:
    kind: milestone
    status: building
    claims:
      - { text: "Token TOKEN works", status: true, evidence: "seen" }
      - { text: 'single 5" screen', status: true }
      - { text: "never closed, status: true }
  tricky:
    status: building
    next_steps:
      - { step: "Rotate TOKEN", gate: approval, done: false }
      - { step: 'set done: true in config', done: false }
      - { context: "ctx here", step: "real step", gate: "decision: which?", done: false }
  folded:
    status: building
    next_steps:
      - step: >
          Fold then mark done: true
        done: false
  blocky:
    kind: milestone
    claims:
      - text: A guest can open the invite, on a phone
        status: true  # checked 10/10
        evidence: walked it, twice
      - context: "ctx here"
        text: "real text"
        status: false
    next_steps:
      - step: Ship it, carefully
        gate: approval # Chad
        done: false
  bare:
    status: building
    next: "No step list at all"
workflows:
  ms:
    trigger: "Weekly"
    summary: "Cites PR #5"
    steps:
      - "look"
gotchas:
  - "token is TOKEN"
  - >
    Folded gotcha body
    second line
'''.replace('TOKEN', TOK)
d = repo(HARD, when=now - 90 * day)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
doc = doc or {'rows': []}
def frow(name, section='features'):
    return next((r for r in doc['rows'] if r['name'] == name and r['section'] == section), {})
# R1. A secret is never printed, wherever on the board it sits.
expect('R1 secret found on the board', any(x.get('kind') == 'github-token' for x in doc.get('secrets', [])), doc.get('secrets'))
expect('R1 secret not repeated in steps, claims or gotchas', TOK not in raw and 'redacted' in raw, raw.count(TOK))
# R4. A claim the reader can't follow is reported, not dropped.
expect('R4 unreadable claims flagged', frow('ms').get('claims_readable') is False and 'claims_unreadable' in frow('ms').get('flags', []), frow('ms'))
expect('R4 readable claims say so', frow('blocky').get('claims_readable') is True, frow('blocky'))
# R6. done: true inside single quotes or a folded block is not a done step.
t = frow('tricky')
expect('R6 single-quoted "done: true" is still open', (t.get('open'), t.get('done')) == (3, 0), t)
expect('R6 a folded step is unreadable, never guessed', frow('folded').get('steps_readable') is False and frow('folded').get('open') is None, frow('folded'))
# R7. Keys match whole, not as the tail of another key.
expect('R7 step is not taken from "context"', {'step': 'real step', 'gate': 'decision: which?'} in t.get('gated', []), t.get('gated'))
bc = frow('blocky').get('claims', [])
expect('R7 claim text is not taken from "context"', len(bc) == 2 and bc[1].get('text') == 'real text', bc)
# R5. Multi-line items: commas stay, trailing comments go.
expect('R5 bare text keeps its comma', len(bc) == 2 and bc[0].get('text') == 'A guest can open the invite, on a phone', bc)
expect('R5 status and evidence read past a comment', len(bc) == 2 and bc[0].get('status') == 'true' and bc[0].get('evidence') == 'walked it, twice', bc)
expect('R5 gate without its comment, step with its comma', frow('blocky').get('gated') == [{'step': 'Ship it, carefully', 'gate': 'approval'}], frow('blocky').get('gated'))
# R8. Same name under features and workflows: facts stay with their own row.
expect('R8 workflow keeps its PR, takes no claims', frow('ms', 'workflows').get('prs') == [5] and frow('ms', 'workflows').get('claims') == [] and frow('ms', 'workflows').get('flags') == [], frow('ms', 'workflows'))
expect('R8 feature keeps its claims, takes no PR', frow('ms').get('prs') == [], frow('ms'))
# R11. A building row with no step list is not "finished".
expect('R11 no step list is not no_open_steps', 'no_open_steps' not in frow('bare').get('flags', ['x']), frow('bare'))
# R10. A folded gotcha's age follows its newest line.
write(f'{d}/.continuity/feature-status.yml', HARD.replace('second line', 'second line, rewritten'))
commit(d, 'rewrite a gotcha body', when=now - 2 * day)
rc, doc2, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
ages = [x.get('age_days') for x in (doc2 or {}).get('gotchas', {}).get('entries', [])]
expect('R10 editing a gotcha body makes it younger', ages == [90, 2], ages)
shutil.rmtree(d)

# R2/R3. Every file about to be the record is scanned: odd names and not-yet-committed ones.
d = repo(BOARD, {'.continuity/decisions/café.md': '# c\napi_key = "abcdef0123456789abcdef"\n'})
write(f'{d}/.continuity/handoffs/new.md', 'AWS AKIAABCDEFGHIJKLMNOP\n')
write(f'{d}/.continuity/decisions/fresh.md', '# fresh\n' + '- x — y\n' * 35)
write(f'{d}/.gitignore', '.continuity/ignored.bin\n')
write(f'{d}/.continuity/ignored.bin', 'x\n')
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
found = {(x.get('path'), x.get('kind')) for x in (doc or {}).get('secrets', [])}
expect('R2 non-ASCII file name scanned', ('.continuity/decisions/café.md', 'assigned-secret') in found, found)
expect('R3 uncommitted file scanned', ('.continuity/handoffs/new.md', 'aws-access-key') in found, found)
expect('R3 uncommitted decisions file sized', any(x['path'].endswith('fresh.md') and x['over_budget'] for x in (doc or {}).get('decisions', [])), (doc or {}).get('decisions'))
expect('R3 ignored files stay out', not any('ignored' in x['path'] for x in (doc or {}).get('unexpected_files', [])), (doc or {}).get('unexpected_files'))
shutil.rmtree(d)

# R12. A board saved with Windows line endings reads the same.
d = repo(BOARD.replace('\n', '\r\n'))
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('R12 CRLF board: same rows and counts', [r['name'] for r in (doc or {'rows': []})['rows']][:2] == ['shipping', 'finished'] and (row(doc or {'rows': []}, 'shipping') or {}).get('open') == 3, raw[:300])
shutil.rmtree(d)

AREAS = '''areas:
  - name: Place knowledge
    what: What Jauntfully knows about each place.
    open_question: "What is a place's description for?"
  - name: Empty area
    what: Nothing lives here yet.
    open_question: Who would use it?
features:
  enrichment:
    status: polishing
    area: Place knowledge
    size: XL
    aspiration: "Every place is real, open and well described."
    inferred: [size, aspiration]
    next_steps:
      - { step: "one", done: false }
  stray:
    status: building
    area: Nowhere
    size: XXL
    next_steps: []
'''

# AR1. Areas are listed with how many initiatives name each; an area nobody names is empty.
d = repo(AREAS)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('AR1 areas listed in order, counted, empty one marked', (doc or {}).get('areas') == [
    {'name': 'Place knowledge', 'what': 'What Jauntfully knows about each place.', 'open_question': "What is a place's description for?", 'initiatives': 1, 'empty': False},
    {'name': 'Empty area', 'what': 'Nothing lives here yet.', 'open_question': 'Who would use it?', 'initiatives': 0, 'empty': True}], raw[:600])
expect('AR1 areas readable', (doc or {}).get('areas_readable') is True, raw[:300])
shutil.rmtree(d)

# AR2. An initiative reports its area, size, aspiration and which fields Claude inferred;
#      a missing area or a size outside S/M/L/XL is reported and the value kept.
d = repo(AREAS)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
e = row(doc or {'rows': []}, 'enrichment') or {}
s = row(doc or {'rows': []}, 'stray') or {}
expect('AR2 fields read', [e.get(k) for k in ('area', 'size', 'aspiration', 'inferred')] ==
       ['Place knowledge', 'XL', 'Every place is real, open and well described.', ['size', 'aspiration']], e)
expect('AR2 a good initiative has no area flags', not {'unknown_area', 'unknown_size'} & set(e.get('flags', [])), e.get('flags'))
expect('AR2 unknown area and size flagged, values kept', {'unknown_area', 'unknown_size'} <= set(s.get('flags', [])) and s.get('size') == 'XXL' and s.get('area') == 'Nowhere', s)
shutil.rmtree(d)

# AR4. Malformed areas: an unnamed area is listed with a null name; a block-scalar field makes the list unreadable;
#      a folded aspiration is reported as null rather than ">"; nothing crashes.
d = repo(AREAS.replace('  - name: Empty area\n', '  - what_only: x\n    name: ""\n'))
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('AR4 unnamed area listed with a null name', rc == 0 and any(a.get('name') is None for a in (doc or {}).get('areas', [])), raw[:600])
shutil.rmtree(d)
d = repo(AREAS.replace("    what: What Jauntfully knows about each place.\n", "    what: >\n      Folded text.\n")
              .replace('    aspiration: "Every place is real, open and well described."\n', '    aspiration: >\n      Folded aspiration.\n'))
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('AR4 block scalar in areas: exit 0, not readable', rc == 0 and (doc or {}).get('areas_readable') is False, raw[:600])
expect('AR4 folded aspiration is null, not ">"', (row(doc or {'rows': []}, 'enrichment') or {}).get('aspiration') is None, raw[:600])
shutil.rmtree(d)

# AR3. A board without areas: an empty list, null fields, no new flags.
d = repo(BOARD)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
r = row(doc or {'rows': []}, 'shipping') or {}
expect('AR3 no areas: empty list, readable', (doc or {}).get('areas') == [] and (doc or {}).get('areas_readable') is True, raw[:300])
expect('AR3 no areas: row fields null, nothing inferred', [r.get(k) for k in ('area', 'size', 'aspiration', 'inferred')] == [None, None, None, []], r)
shutil.rmtree(d)

DAY = 86400
NOW = int(time.time())

def edit_row(d, old, new, when):
    p = f'{d}/.continuity/feature-status.yml'
    write(p, open(p).read().replace(old, new, 1))
    commit(d, 'edit', when)

# W1. With no last review, the window is the last 14 days; board edits inside it count per row.
d = repo(BOARD, when=NOW - 40 * DAY)
edit_row(d, '"Nothing left"', '"Nothing left at all"', NOW - 30 * DAY)        # finished: outside the window
edit_row(d, '"Pick a carrier"', '"Pick a carrier (UPS)"', NOW - 5 * DAY)    # shipping: inside
edit_row(d, '"Only step"', '"Only step, done"', NOW - 2 * DAY)              # finished: inside
edit_row(d, '"Pick a carrier (UPS)"', '"Pick a carrier (DHL)"', NOW - 1 * DAY)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary', CONTINUITY_AUDIT_WT='false')
w = (doc or {}).get('review') or {}
expect('W1 no last review: 14-day window', w.get('last_review') is None and w.get('since') == time.strftime('%Y-%m-%d', time.gmtime(NOW - 14 * DAY)), w)
act = lambda n: (row(doc or {'rows': []}, n) or {}).get('activity') or {}
expect('W1 edits inside the window counted per row', act('shipping').get('board_edits') == 2 and act('finished').get('board_edits') == 1, (act('shipping'), act('finished')))
expect('W1 edit dates listed', act('shipping').get('dates') == sorted(time.strftime('%Y-%m-%d', time.gmtime(NOW - k * DAY)) for k in (5, 1)), act('shipping'))
expect('W1 untouched row: zero', act('resting').get('board_edits') == 0, act('resting'))

# W2. A last review in settings sets the window.
edit_row(d, '  push_to_default_branch: true\n', '  push_to_default_branch: true\n  last_review: ' + time.strftime('%Y-%m-%d', time.gmtime(NOW - 2 * DAY - 3600)) + '\n', NOW - 1 * DAY + 60)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary', CONTINUITY_AUDIT_WT='false')
expect('W2 last review read', ((doc or {}).get('review') or {}).get('last_review') == time.strftime('%Y-%m-%d', time.gmtime(NOW - 2 * DAY - 3600)), (doc or {}).get('review'))
expect('W2 only edits since the review count', act('shipping').get('board_edits') == 1 and act('finished').get('board_edits') == 1, (act('shipping'), act('finished')))
shutil.rmtree(d)

# W3. Cited PRs that merged inside the window count; older or unmerged ones don't.
d = repo(BOARD, when=NOW - 40 * DAY)
m = lambda k: time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(NOW - k * DAY))
ghdir, gh = fake_gh("echo '[{\"number\":12,\"state\":\"MERGED\",\"mergedAt\":\"%s\"},{\"number\":14,\"state\":\"MERGED\",\"mergedAt\":\"%s\"}]'" % (m(2), m(30)))
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH=gh, CONTINUITY_AUDIT_WT='false')
expect('W3 one cited PR merged in the window', act('shipping').get('prs_merged') == [12], act('shipping'))
expect('W3 a row citing only an old PR: none', act('misfiled').get('prs_merged') == [12] and act('finished').get('prs_merged') == [], (act('misfiled'), act('finished')))
shutil.rmtree(d); shutil.rmtree(ghdir)

# W4. Sessions come from wt:status. An agent the board names as a row's owner is on that row;
#     a worktree merely named like a row is a name match; other sessions are listed unmatched.
d = repo(BOARD.replace('  shipping:\n    status: building\n', '  shipping:\n    status: building\n    owner: ship-1\n', 1))
wtdir, wt = fake_gh(r"""printf 'repo\tpath\tname\tverdict\tstate\tuncommitted\tunpushed\tbranch\tlock_pid\tactivity\n'
printf '/r\t/r/w/ship-1\tship-1\trunning\trunning\t0\t0\tship-1-pr\t\tworking\n'
printf '/r\t/r/w/finished-2\tfinished-2\trunning\trunning\t0\t0\tfinished-2\t\tidle (replied)\n'
printf '/r\t/r/w/random-x\trandom-x\tfinished\tidle\t0\t0\tx\t\t\n'""")
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary', CONTINUITY_AUDIT_WT=wt)
s = (doc or {}).get('sessions') or {}
got = {i.get('name'): (i.get('row'), i.get('match'), i.get('verdict'), i.get('activity')) for i in s.get('items', [])}
expect('W4 sessions read from wt:status', s.get('source') == 'wt' and len(got) == 3, s)
expect('W4 owner match', got.get('ship-1') == ('shipping', 'owner', 'running', 'working'), got)
expect('W4 name match', got.get('finished-2') == ('finished', 'name', 'running', 'idle (replied)'), got)
expect('W4 unmatched session listed', got.get('random-x') == (None, None, 'finished', None), got)

# W5. Without wt:status the audit says so and carries on.
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary', CONTINUITY_AUDIT_WT='/no/such/wt-status')
expect('W5 no wt:status: unavailable, exit 0', rc == 0 and (doc or {}).get('sessions') == {'source': 'unavailable', 'items': []}, raw[:400])
shutil.rmtree(d); shutil.rmtree(wtdir)

# P1. settings.product_doc is reported with whether the file exists; unset is null.
d = repo(BOARD.replace('  push_to_default_branch: true\n', '  push_to_default_branch: true\n  product_doc: docs/principles.md\n  review_url: "https://claude.ai/artifact/abc"\n', 1), files={'docs/principles.md': '# Bets\n'})
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary', CONTINUITY_AUDIT_WT='false')
expect('P1b review_url reported', (doc or {}).get('review_url') == 'https://claude.ai/artifact/abc', (doc or {}).get('review_url'))
expect('P1 product doc found', (doc or {}).get('product_doc') == {'path': 'docs/principles.md', 'exists': True}, (doc or {}).get('product_doc'))
os.remove(f'{d}/docs/principles.md')
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary', CONTINUITY_AUDIT_WT='false')
expect('P1 moved or deleted doc reported missing', (doc or {}).get('product_doc') == {'path': 'docs/principles.md', 'exists': False}, (doc or {}).get('product_doc'))
shutil.rmtree(d)
d = repo(BOARD)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary', CONTINUITY_AUDIT_WT='false')
expect('P1 unset: null', 'product_doc' in (doc or {}) and doc['product_doc'] is None, raw[:300])
shutil.rmtree(d)

# B1. A stale checkout: another session landed continuity on origin. The audit reads origin's
#     board, as continuity-state does, and says so; a current checkout reads its own.
setup = ns['setup']
root, remote, clone, wt = setup()
rc, doc, raw = audit(wt, CONTINUITY_AUDIT_GH='no-such-gh-binary', CONTINUITY_AUDIT_WT='false')
expect('B1 current checkout: board local', ((doc or {}).get('board') or {}).get('source') == 'local', raw[:300])
write(f'{clone}/.continuity/feature-status.yml', ns['STATUS'].format(push='true').replace('features:\n', 'features:\n  peerrow:\n    status: building\n', 1))
git(clone, 'add', '-A'); git(clone, 'commit', '-qm', 'peer board'); git(clone, 'push', '-q', 'origin', 'master')
git(wt, 'fetch', '-q', 'origin')
rc, doc, raw = audit(wt, CONTINUITY_AUDIT_GH='no-such-gh-binary', CONTINUITY_AUDIT_WT='false')
expect('B1 stale checkout: board from origin', ((doc or {}).get('board') or {}).get('source') == 'origin/master', raw[:300])
expect('B1 origin rows read', row(doc or {'rows': []}, 'peerrow') is not None, [r['name'] for r in (doc or {'rows': []})['rows']])
expect('B1 peer edit counted as activity', ((row(doc or {'rows': []}, 'peerrow') or {}).get('activity') or {}).get('board_edits') == 1, row(doc or {'rows': []}, 'peerrow'))
expect('B1 checkout untouched', 'peerrow' not in open(f'{wt}/.continuity/feature-status.yml').read(), '')
shutil.rmtree(root)

# G1. Re-learned markers on a gotcha are counted with their dates, including on a folded gotcha's later lines.
d = repo(BOARD.split('gotchas:')[0] + 'gotchas:\n'
         '  - "Test agents drop the PATH prefix (re-learned 2026-10-12) (re-learned 2026-10-19)"\n'
         '  - >\n    The docs site builds with Hugo 0.121 exactly;\n    newer versions break the theme (re-learned 2026-10-03)\n'
         '  - "Never re-learned"\n')
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
ents = ((doc or {}).get('gotchas') or {}).get('entries') or []
expect('G1 markers read per gotcha', [e.get('relearned') for e in ents] == [['2026-10-12', '2026-10-19'], ['2026-10-03'], []], ents)
shutil.rmtree(d)

# --- Review findings, 2026-10-19.

# F1. A row name that looks like a token's tail stays whole and keeps its edits; it is not a
#     secret. A real token in a step is still found and blanked.
SK = 'sk-' + 'Q' * 24
d = repo('features:\n  task-queue-retry-and-backoff:\n    status: building\n    next_steps:\n'
         f'      - {{ step: "Rotate {SK} soon", done: false, gate: approval }}\n', when=NOW - 40 * DAY)
edit_row(d, 'status: building', 'status: polishing', NOW - 2 * DAY)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
r = row(doc or {'rows': []}, 'task-queue-retry-and-backoff')
expect('F1 row keeps its exact name', r is not None, [x['name'] for x in (doc or {'rows': []})['rows']])
expect('F1 row keeps its edits', ((r or {}).get('activity') or {}).get('board_edits') == 1, (r or {}).get('activity'))
sec = [(x['line'], x['kind']) for x in (doc or {}).get('secrets', [])]
expect('F1 the row name is not a secret; the token is', sec == [(5, 'api-key')], sec)
expect('F1 token never printed', SK not in raw and 'redacted' in raw, raw[:300])
shutil.rmtree(d)

# F4. The commit that creates the board counts as an edit of each row it creates,
#     as a root commit and as a later one.
d = repo(BOARD, when=NOW - 1 * DAY)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('F4 board created in a root commit: rows edited', ((row(doc or {'rows': []}, 'shipping') or {}).get('activity') or {}).get('board_edits') == 1, raw[:300])
shutil.rmtree(d)
d = tempfile.mkdtemp()
git(d, 'init', '-q', '-b', 'master'); write(f'{d}/README', 'x\n'); commit(d, 'readme', NOW - 3 * DAY)
write(f'{d}/.continuity/feature-status.yml', BOARD); commit(d, 'board', NOW - 1 * DAY)
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('F4 board created after a first commit: rows edited', ((row(doc or {'rows': []}, 'shipping') or {}).get('activity') or {}).get('board_edits') == 1, raw[:300])
shutil.rmtree(d)

# F6. One edit counts once: a continuity-save landed copy and its source, or a sync and the
#     peer commit it copied, are one edit when both are in history. A sync whose peer
#     commit is not in history is the only record of that edit and counts.
root, remote, clone, wt = ns['setup']()
B6 = 'settings:\n  push_to_default_branch: true\nfeatures:\n  alpha:\n    status: building\n  gamma:\n    status: planned\n    next: one\n    summary: two\n  beta:\n    status: building\n'
write(f'{wt}/.continuity/feature-status.yml', B6); ns['save'](wt)
git(clone, 'pull', '-q', '--ff-only')
p = f'{clone}/.continuity/feature-status.yml'; write(p, open(p).read().replace('  beta:\n    status: building', '  beta:\n    status: polishing'))
git(clone, 'commit', '-qam', 'peer edits beta'); git(clone, 'push', '-q', 'origin', 'master')
git(wt, 'fetch', '-q', 'origin')
p = f'{wt}/.continuity/feature-status.yml'; write(p, open(p).read().replace('  alpha:\n    status: building', '  alpha:\n    status: polishing'))
rc6, out6 = ns['save'](wt)
eds = lambda doc: {n: ((row(doc or {'rows': []}, n) or {}).get('activity') or {}).get('board_edits') for n in ('alpha', 'beta')}
rc, doc, raw = audit(wt, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('F6 branch only: own edits and the synced peer edit count once', eds(doc) == {'alpha': 2, 'beta': 2}, (eds(doc), out6))
# Merge once (boards equal: git follows one side), then both sides edit again, so the
# next merge's board differs from both parents and git walks both.
git(wt, 'merge', '-q', '--no-edit', 'origin/master')
p =f'{wt}/.continuity/feature-status.yml'; write(p, open(p).read().replace('  alpha:\n    status: polishing', '  alpha:\n    status: parked'))
git(wt, 'commit', '-qam', 'local alpha edit')
git(clone, 'pull', '-q', '--ff-only')
p = f'{clone}/.continuity/feature-status.yml'; write(p, open(p).read().replace('  beta:\n    status: polishing', '  beta:\n    status: parked'))
git(clone, 'commit', '-qam', 'peer edits beta again'); git(clone, 'push', '-q', 'origin', 'master')
git(wt, 'fetch', '-q', 'origin')
git(wt, 'merge', '-q', '--no-edit', 'origin/master')
rc, doc, raw = audit(wt, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('F6 after merging the default branch: still once each', eds(doc) == {'alpha': 3, 'beta': 3}, eds(doc))
shutil.rmtree(root)

# F3. Each session says whether it is running now: wt:status state "running", nothing else.
d = repo(BOARD)
wtdir, wt = fake_gh(r"""printf 'repo\tpath\tname\tverdict\tstate\tuncommitted\tunpushed\tbranch\tlock_pid\tactivity\n'
printf '/r\t/r/w/shipping-1\tshipping-1\trunning\trunning\t0\t0\tb\t\tworking\n'
printf '/r\t/r/w/finished-2\tfinished-2\tsafe\tended\t0\t0\tb\t\tidle (replied)\n'
printf '/r\t/r/w/resting-1\tresting-1\torphan\t\t0\t0\t\t\t\n'""")
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary', CONTINUITY_AUDIT_WT=wt)
got = {i.get('name'): i.get('running') for i in ((doc or {}).get('sessions') or {}).get('items', [])}
expect('F3 running only when state is running', got == {'shipping-1': True, 'finished-2': False, 'resting-1': False}, got)
shutil.rmtree(d); shutil.rmtree(wtdir)

# F6b. After the branch merges into the default branch, its edit still counts once
#      (git's default log would drop the source and the echo rule the copy).
root, remote, clone, wt = ns['setup']()
write(f'{wt}/.continuity/feature-status.yml', B6); ns['save'](wt)
write(f'{wt}/app.js', 'v2\n'); git(wt, 'commit', '-qam', 'code')
git(clone, 'pull', '-q', '--ff-only'); git(clone, 'merge', '-q', '--no-ff', '--no-edit', 'feature')
rc, doc, raw = audit(clone, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('F6b merged branch: edit counted once on the default branch', eds(doc) == {'alpha': 1, 'beta': 1}, eds(doc))
shutil.rmtree(root)

# F3b. An orphan worktree is never running, whatever its state says.
d = repo(BOARD)
wtdir, wt = fake_gh(r"""printf 'repo\tpath\tname\tverdict\tstate\tuncommitted\tunpushed\tbranch\tlock_pid\tactivity\n'
printf '/r\t/r/w/shipping-1\tshipping-1\torphan\trunning\t0\t0\tb\t\tworking\n'""")
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary', CONTINUITY_AUDIT_WT=wt)
expect('F3b orphan not running', [i.get('running') for i in ((doc or {}).get('sessions') or {}).get('items', [])] == [False], raw[:300])
shutil.rmtree(d); shutil.rmtree(wtdir)

# F1b. Settings values and serves are blanked like other free text.
d = repo('settings:\n  review_url: "https://x.test/?k=' + SK + '"\nfeatures:\n  a:\n    status: building\n    serves: "' + SK + '"\n')
rc, doc, raw = audit(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('F1b token in settings or serves never printed', rc == 0 and SK not in raw, raw[:300])
shutil.rmtree(d)

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
