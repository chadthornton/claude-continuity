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
    e = dict(ENV); e.update(env)
    r = subprocess.run([AUDIT], cwd=cwd, env=e, capture_output=True, text=True)
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
expect('A1 rows with no serves flagged, rows with it not',
       'no_serves' in f.get('flags', []) and 'no_serves' not in s.get('flags', ['x']), (s, f))
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

# A8. Files that are not the record's plain text: binaries and other formats, tracked ones only.
d = repo(BOARD, {
    '.continuity/workflows/page.html': '<html>review page</html>\n',
    '.continuity/decisions/shipping.md': '# shipping\n',
    '.continuity/last-activity.txt': 'ended\n',
})
with open(f'{d}/.continuity/shot.png', 'wb') as fh:
    fh.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\x00binary')
commit(d, 'add a screenshot')
write(f'{d}/.continuity/untracked.bin', 'not committed\n')
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
expect('A9 a board that never uses serves says so', doc.get('uses_serves') is False, doc.get('uses_serves'))
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

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
