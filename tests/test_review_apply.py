"""Scenario tests for lib/continuity-review-apply. Run: python3 tests/test_review_apply.py"""
import json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLY = os.path.join(ROOT, 'lib', 'continuity-review-apply')
_audit_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_continuity_audit.py')
ns = {'__file__': _audit_py}
exec(open(_audit_py).read().split('BOARD = ')[0], ns)
write, expect, ENV, fails, repo, audit, row = ns['write'], ns['expect'], ns['ENV'], ns['fails'], ns['repo'], ns['audit'], ns['row']

BOARD = '''settings:
  push_to_default_branch: true
features:
  lists:
    status: building
    size: L
    next: "Ship lists"
    next_steps:
      - { step: "One", done: false }
  discovery:
    status: parked
    size: M
    inferred: [size]
    next_steps: []
  quiet:
    status: polishing
    next_steps: []
gotchas:
  - "Keep this gotcha"
'''

SEED = {
    'project': 'demo', 'mode': 'full', 'since': '2026-10-05', 'generated': '2026-10-19T10:00Z', 'read': 'r',
    'areas': [{'name': 'Lists', 'what': "Where a trip's places come from.", 'open_question': 'When does a list travel: "now" or later?', 'starters': [
                  {'title': 'Morning-of chooser', 'aspiration': 'Pick a jaunt in a minute.', 'size': 'M', 'first_session': 'think', 'brief': 'Walk a real morning.'}], 'initiatives': 2},
              {'name': 'Running', 'what': 'Keeping it up.', 'open_question': 'What to build ahead?', 'starters': [], 'initiatives': 1}],
    'initiatives': [
        {'row': 'lists', 'area': 'Lists', 'size': 'L', 'aspiration': 'Lists are how places reach a trip.', 'judged': ['area', 'aspiration', 'line', 'recent', 'progress', 'proposal', 'suggest']},
        {'row': 'discovery', 'area': 'Lists', 'size': 'M', 'aspiration': 'Suggestions arrive.', 'judged': ['area', 'size', 'aspiration', 'line', 'recent', 'progress', 'proposal', 'suggest']},
        {'row': 'quiet', 'area': 'Running', 'size': 'S', 'aspiration': 'It stays up.', 'judged': ['area', 'size', 'aspiration', 'line', 'recent', 'progress', 'proposal', 'suggest']},
    ],
}
OVERRIDES = {'discovery': {'size': 'L', 'at': 'x'}, 'quiet': {'keep': True, 'area': 'Lists', 'at': 'x'}}
ROUND = {'generated': '2026-10-19T10:00Z', 'confirmed_at': '2026-10-19T11:00Z', 'items': [
    {'key': 's:0:0', 'kind': 'think', 'title': 'Start: Morning-of chooser', 'label': 'Morning-of chooser', 'area': 'Lists', 'size': 'M', 'aspiration': 'Pick a jaunt in a minute.', 'brief': 'Walk a real morning.'},
    {'key': 'p:lists', 'kind': 'decision', 'row': 'lists', 'title': 'Whole list', 'brief': 'Pick.'}]}


def files(d, seed=SEED, overrides=OVERRIDES, rnd=ROUND):
    out = {}
    for name, data in (('seed', seed), ('overrides', overrides), ('round', rnd)):
        p = f'{d}/../{os.path.basename(d)}-{name}.json'
        json.dump(data, open(p, 'w')); out[name] = p
    return out


def apply(d, f, *extra):
    r = subprocess.run([APPLY, f['seed'], f['overrides'], f['round'], '2026-10-19'] + list(extra), cwd=d, env=ENV, capture_output=True, text=True)
    try:
        return r.returncode, json.loads(r.stdout), r.stdout + r.stderr
    except ValueError:
        return r.returncode, None, r.stdout + r.stderr


d = repo(BOARD)
f = files(d)
rc, summary, raw = apply(d, f, '--review-url', 'https://claude.ai/artifact/abc')
board = open(f'{d}/.continuity/feature-status.yml').read()
rc2, doc, raw2 = audit(d)
R = lambda n: row(doc or {'rows': []}, n) or {}

# Y1. Settings: last review and the page URL.
expect('Y1 exit 0, summary JSON', rc == 0 and summary is not None, raw[:500])
expect('Y1 last_review and review_url set', (doc or {}).get('review', {}).get('last_review') == '2026-10-19' and 'review_url: "https://claude.ai/artifact/abc"' in board, board[:300])
expect('Y1 existing setting kept', 'push_to_default_branch: true' in board, board[:300])

# Y2. Areas from a full review replace the board's list; the board still reads.
expect('Y2 areas written and readable', [a['name'] for a in (doc or {}).get('areas', [])] == ['Lists', 'Running'] and (doc or {}).get('areas_readable') is True, (doc or {}).get('areas'))
expect('Y2 quotes and apostrophes survive', ((doc or {}).get('areas') or [{}])[0].get('open_question') == 'When does a list travel: "now" or later?' and ((doc or {}).get('areas') or [{}])[0].get('what') == "Where a trip's places come from.", (doc or {}).get('areas'))

# Y3. Per initiative: a confirmed field stays; a judged one is written and marked inferred; a correction is written and leaves inferred.
expect('Y3 confirmed size untouched, judged area and aspiration written as inferred',
       (R('lists').get('size'), R('lists').get('area'), sorted(R('lists').get('inferred', []))) == ('L', 'Lists', ['area', 'aspiration']), R('lists'))
expect('Y3 corrected size written, no longer inferred', R('discovery').get('size') == 'L' and 'size' not in R('discovery').get('inferred', []), R('discovery'))
expect('Y3 corrected area wins over the review', R('quiet').get('area') == 'Lists' and 'area' not in R('quiet').get('inferred', []) and R('quiet').get('size') == 'S', R('quiet'))
expect('Y3 step counts unchanged', (R('lists').get('open'), R('lists').get('done')) == (1, 0), R('lists'))

# Y4. A starter sent this round becomes an initiative; the summary names it.
s = R('morning-of-chooser')
expect('Y4 starter row added as exploring', s.get('status') == 'exploring' and s.get('area') == 'Lists' and s.get('size') == 'M' and sorted(s.get('inferred', [])) == ['aspiration', 'size'], s)
expect('Y4 new row indented like the others', '\n  morning-of-chooser:\n    status: exploring\n' in board, board[-400:])
expect('Y4 summary names the new row', (summary or {}).get('added_rows') == ['morning-of-chooser'], summary)

# Y5. Nothing else on the board moved.
expect('Y5 gotcha and next kept', 'Keep this gotcha' in board and 'next: "Ship lists"' in board, board)
expect('Y5 every row still listed', [r['name'] for r in doc['rows']] == ['lists', 'discovery', 'quiet', 'morning-of-chooser'] if doc else False, [r['name'] for r in (doc or {'rows': []})['rows']])

# Y6. Applying the same round twice changes nothing more.
before = open(f'{d}/.continuity/feature-status.yml').read()
rc, summary, raw = apply(d, f, '--review-url', 'https://claude.ai/artifact/abc')
expect('Y6 idempotent', rc == 0 and open(f'{d}/.continuity/feature-status.yml').read() == before and (summary or {}).get('added_rows') == [], raw[:400])
shutil.rmtree(d)

# Y7. Routine review: no areas written; overrides still applied; an unconfirmed round is refused.
d = repo(BOARD)
routine = dict(SEED, mode='routine')
f = files(d, seed=routine)
rc, summary, raw = apply(d, f)
rc2, doc, raw2 = audit(d)
expect('Y7 routine: no areas block written', 'areas:' not in open(f'{d}/.continuity/feature-status.yml').read(), '')
expect('Y7 routine: correction still applied', (row(doc, 'discovery') or {}).get('size') == 'L', row(doc, 'discovery'))
f = files(d, rnd=dict(ROUND, confirmed_at=None))
rc, summary, raw = apply(d, f)
expect('Y7 unconfirmed round refused, exit 1', rc == 1 and 'not confirmed' in raw, raw[:300])
f = files(d, rnd=dict(ROUND, generated='2026-10-01T00:00Z'))
rc, summary, raw = apply(d, f)
expect('Y7 round from another review refused', rc == 1 and 'another review' in raw, raw[:300])
shutil.rmtree(d)

# Y8. --url-only records the page URL alone, before any round exists.
d = repo(BOARD)
r = subprocess.run([APPLY, '--url-only', 'https://claude.ai/artifact/xyz'], cwd=d, env=ENV, capture_output=True, text=True)
b = open(f'{d}/.continuity/feature-status.yml').read()
expect('Y8 url recorded, nothing else changed', r.returncode == 0 and 'review_url: "https://claude.ai/artifact/xyz"' in b and b.replace('  review_url: "https://claude.ai/artifact/xyz"\n', '') == BOARD, (r.stdout + r.stderr, b[:300]))
shutil.rmtree(d)

# --- Review findings, 2026-10-19.
import datetime, yaml
TODAY = datetime.date(2026, 10, 19)   # the writer leaves the date bare, so YAML reads a date

def applied(board, seed=SEED):
    """Apply the standard round to `board`; returns (exit, board text, parsed board or the YAML error)."""
    d = repo(board)
    rc, summary, raw = apply(d, files(d, seed=seed), '--review-url', 'https://claude.ai/artifact/abc')
    text = open(f'{d}/.continuity/feature-status.yml').read()
    shutil.rmtree(d)
    try:
        return rc, text, yaml.safe_load(text)
    except yaml.YAMLError as e:
        return rc, text, e

top_keys = lambda text: [l.split(':')[0] for l in text.splitlines() if l[:1].isalpha()]

# F2a. settings: placed after features: is edited where it is, not added a second time.
later = BOARD.replace('settings:\n  push_to_default_branch: true\n', '') + 'settings:\n  push_to_default_branch: true\n'
rc, text, y = applied(later)
expect('F2a later settings: one block', top_keys(text).count('settings') == 1, text)
expect('F2a later settings: keys merged', isinstance(y, dict) and y.get('settings') == {'push_to_default_branch': True, 'last_review': TODAY, 'review_url': 'https://claude.ai/artifact/abc'}, (y if not isinstance(y, dict) else y.get('settings')))

# F2b. Flow-style settings (what continuity-save's hint writes) become a block that keeps every key.
for flow in ('settings: { push_to_default_branch: true }\n', 'settings: {push_to_default_branch: true, note: "a, b"}  # opt in\n', 'settings: {}\n'):
    rc, text, y = applied(BOARD.replace('settings:\n  push_to_default_branch: true\n', flow))
    want = {'last_review': TODAY, 'review_url': 'https://claude.ai/artifact/abc'}
    if 'push' in flow: want['push_to_default_branch'] = True
    if 'note' in flow: want['note'] = 'a, b'
    expect(f'F2b flow settings {flow.strip()!r}: valid YAML with every key', rc == 0 and isinstance(y, dict) and y.get('settings') == want, (rc, text[:200], y if not isinstance(y, dict) else y.get('settings')))
    expect(f'F2b flow settings {flow.strip()!r}: features untouched', isinstance(y, dict) and list(y.get('features', {})) == ['lists', 'discovery', 'quiet', 'morning-of-chooser'], text[:400])

# F2c. Flow settings this writer can't follow (a nested map) are refused: exit non-zero, board untouched.
odd = BOARD.replace('settings:\n  push_to_default_branch: true\n', 'settings: { push_to_default_branch: true, x: { y: 1 } }\n')
d = repo(odd)
rc, summary, raw = apply(d, files(d))
expect('F2c unreadable flow settings: refused, board untouched', rc != 0 and open(f'{d}/.continuity/feature-status.yml').read() == odd, (rc, raw[:300]))
shutil.rmtree(d)

# F2d. areas: placed after features: is replaced where it is, not added a second time.
rc, text, y = applied(BOARD + 'areas:\n  - name: "Old"\n    what: "x"\n    open_question: "y?"\n')
expect('F2d later areas: one block', top_keys(text).count('areas') == 1, text)
expect('F2d later areas: replaced by the review', isinstance(y, dict) and [a['name'] for a in y.get('areas') or []] == ['Lists', 'Running'], text[-500:])

# F5. A round already applied (applied_at set when its sessions started) is refused, board untouched.
d = repo(BOARD)
rc, summary, raw = apply(d, files(d, rnd=dict(ROUND, applied_at='2026-10-19T12:00Z')))
expect('F5 applied round refused, board untouched', rc == 1 and 'already applied' in raw and open(f'{d}/.continuity/feature-status.yml').read() == BOARD, (rc, raw[:300]))
shutil.rmtree(d)

# F8. A starter whose name is taken by another row gets its own row (-2) and the summary maps
#     its key to that row; applying again adds nothing and maps it to the same row.
#     A label with no letters to make a name from becomes "starter".
taken = BOARD.replace('  quiet:\n', '  morning-of-chooser:\n    status: polishing\n    next_steps: []\n  quiet:\n', 1)
d = repo(taken)
odd_round = dict(ROUND, items=ROUND['items'] + [{'key': 's:1:0', 'kind': 'think', 'label': '日本語', 'area': 'Lists', 'size': 'S', 'aspiration': 'A.', 'brief': 'B.'}])
f = files(d, rnd=odd_round)
rc, summary, raw = apply(d, f)
rc2, doc, raw2 = audit(d)
names = [r['name'] for r in (doc or {'rows': []})['rows']]
expect('F8 taken name: a new row beside the old one', rc == 0 and names.count('morning-of-chooser') == 1 and 'morning-of-chooser-2' in names and 'starter' in names, (names, raw[:300]))
expect('F8 summary maps each starter key to its row', (summary or {}).get('starters') == {'s:0:0': 'morning-of-chooser-2', 's:1:0': 'starter'} and (summary or {}).get('added_rows') == ['morning-of-chooser-2', 'starter'], summary)
before = open(f'{d}/.continuity/feature-status.yml').read()
rc, summary, raw = apply(d, f)
expect('F8 applied again: nothing added, same map', rc == 0 and open(f'{d}/.continuity/feature-status.yml').read() == before and (summary or {}).get('added_rows') == [] and (summary or {}).get('starters') == {'s:0:0': 'morning-of-chooser-2', 's:1:0': 'starter'}, (summary, raw[:300]))
shutil.rmtree(d)

# F2e. --url-only on a board the writer refuses: exit non-zero, board untouched.
d = repo(odd)
r = subprocess.run([APPLY, '--url-only', 'https://claude.ai/artifact/xyz'], cwd=d, env=ENV, capture_output=True, text=True)
expect('F2e url-only refused write reported', r.returncode != 0 and open(f'{d}/.continuity/feature-status.yml').read() == odd, (r.returncode, r.stderr[:200]))
shutil.rmtree(d)

# N1. What each override document becomes once the round is sent: applied corrections and a "keep" go (the
#     board holds them now; keep answered this review's suggestion), a note this review read and that is
#     unchanged goes, a note edited or written since stays; a document left empty is deleted (null); one
#     that would not change is not listed.
d = repo(BOARD)
seed_n = dict(SEED, notes_read={'discovery': 'Carrier first', 'quiet': 'Ask Sam', 'gone': 'old row'})
ov_n = {'discovery': {'size': 'L', 'notes': 'Carrier first', 'at': 'x'},
        'quiet': {'keep': True, 'area': 'Lists', 'notes': 'Ask Sam, then park', 'at': 'x'},
        'lists': {'notes': 'Written after the review', 'at': 'x'}}
rc, summary, raw = apply(d, files(d, seed=seed_n, overrides=ov_n))
expect('N1 read note and corrections go; edited note stays; untouched doc unlisted',
       rc == 0 and (summary or {}).get('overrides_next') == {'discovery': None, 'quiet': {'notes': 'Ask Sam, then park'}}, raw[:700])
rc, summary, raw = apply(d, files(d))
expect('N1 seed without notes_read: corrections still cleared, every doc emptied',
       rc == 0 and (summary or {}).get('overrides_next') == {'discovery': None, 'quiet': None}, raw[:600])
rc, summary, raw = apply(d, files(d, seed=SEED, overrides={'lists': {'notes': 'Not yet read', 'at': 'x'}}))
expect('N1 a note no review read: nothing changes', rc == 0 and (summary or {}).get('overrides_next') == {}, raw[:600])
rc, summary, raw = apply(d, files(d, seed=seed_n, overrides=ov_n, rnd=dict(ROUND, confirmed_at=None)))
expect('N1 unconfirmed round: refused, nothing listed', rc == 1 and summary is None, raw[:300])
shutil.rmtree(d)

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
