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

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
