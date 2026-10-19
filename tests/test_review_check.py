"""Scenario tests for lib/continuity-review-check. Run: python3 tests/test_review_check.py"""
import copy, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, 'lib', 'continuity-review-check')
fails = []


def expect(name, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + name)
    if not ok:
        fails.append(name)
        print('   ', str(detail)[:600])


def check(review, audit=None):
    """Run the checker; returns (exit code, output)."""
    d = tempfile.mkdtemp()
    rp = os.path.join(d, 'review.json')
    json.dump(review, open(rp, 'w'))
    args = [CHECK, rp]
    if audit is not None:
        ap = os.path.join(d, 'audit.json')
        json.dump(audit, open(ap, 'w'))
        args.append(ap)
    r = subprocess.run(args, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


GOOD = {
    'mode': 'full',
    'since': '2026-10-05',
    'read': 'Lists took most of the effort; nothing owns the morning-of choice.',
    'areas': [
        {'name': 'Jaunts', 'what': 'Ready outings chosen on the day.', 'open_question': 'What does a traveler need to pick in a minute?',
         'starters': [{'title': 'Morning-of chooser', 'aspiration': 'Pick a jaunt in a minute.', 'size': 'M', 'first_session': 'think', 'brief': 'Walk a real morning with Chad.'}]},
        {'name': 'Lists', 'what': 'Where places come from.', 'open_question': 'When does a list travel?', 'starters': []},
    ],
    'initiatives': [
        {'row': 'lists', 'line': 'The second build is soaking; three calls wait on you.',
         'recent': [{'what': 'Add all puts a list on the trip', 'when': '2026-10-12', 'evidence': 'PR #103'}],
         'proposal': {'kind': 'decision', 'title': 'Whole list on the trip', 'brief': 'Pick on a preview.', 'comes_back': 'Straight away.'},
         'suggest': {'action': 'keep', 'reason': 'Live work.'},
         'area': 'Lists', 'size': 'L', 'aspiration': 'Lists are how places reach a trip.', 'progress': 'about a third', 'progress_basis': 'Two of six builds shipped.'},
        {'row': 'discovery', 'line': 'Nothing moved.', 'recent': [], 'proposal': None,
         'suggest': {'action': 'merge', 'into': 'lists', 'reason': 'Lists now covers suggestions.'},
         'area': 'Lists', 'size': 'L', 'aspiration': 'Suggestions arrive and are kept or dropped fast.', 'progress': 'about a third', 'progress_basis': 'Queue built, being retired.'},
    ],
    'chore_groups': [
        {'title': 'Safety limits on adding places', 'code_area': 'the server code that receives pastes',
         'items': [{'row': 'lists', 'title': 'Refuse an oversized paste', 'step': 'Cap paste size at 64 KB before parsing'}],
         'why_together': 'Same handler.'},
    ],
}

AUDIT = {'rows': [
    {'name': 'lists', 'gated': [{'step': 'Ship the blurb change', 'gate': 'approval'}]},
    {'name': 'discovery', 'gated': []},
]}

# C1. A well-formed full review passes, with and without the audit to check against.
rc, out = check(GOOD)
expect('C1 good full review passes', rc == 0, out)
rc, out = check(GOOD, AUDIT)
expect('C1 good full review passes against its audit', rc == 0, out)

# C2. A routine review needs no areas or sizes.
routine = copy.deepcopy(GOOD); routine['mode'] = 'routine'; del routine['areas']
for i in routine['initiatives']:
    for k in ('area', 'size', 'aspiration', 'progress', 'progress_basis'):
        del i[k]
rc, out = check(routine)
expect('C2 routine review without area fields passes', rc == 0, out)


def bad(name, mutate, needle, audit=None):
    r = copy.deepcopy(GOOD); mutate(r)
    rc, out = check(r, audit)
    expect(name, rc == 1 and needle in out, out)


# C3. Each malformed part is named.
bad('C3 missing read', lambda r: r.pop('read'), 'read')
bad('C3 unknown mode', lambda r: r.update(mode='deep'), 'mode')
bad('C3 size outside S/M/L/XL', lambda r: r['initiatives'][0].update(size='XXL'), 'size')
bad('C3 full mode without areas', lambda r: r.pop('areas'), 'areas')
bad('C3 proposal kind unknown', lambda r: r['initiatives'][0]['proposal'].update(kind='build'), 'proposal')
bad('C3 merge names no target', lambda r: r['initiatives'][1]['suggest'].pop('into'), 'into')
bad('C3 recent date not a date', lambda r: r['initiatives'][0]['recent'][0].update(when='last week'), 'when')
bad('C3 initiative names an area not listed', lambda r: r['initiatives'][0].update(area='Nowhere'), 'Nowhere')
bad('C3 starter size XL', lambda r: r['areas'][0]['starters'][0].update(size='XL'), 'starter')

# C4. The chore rule: nothing needing approval, nothing destructive, nothing gated on the board.
bad('C4 chore naming ship it', lambda r: r['chore_groups'][0]['items'][0].update(step='Wait for ship it, then cap paste size'), 'chore')
bad('C4 chore deleting live data', lambda r: r['chore_groups'][0]['items'][0].update(step='Delete old backups on the server'), 'chore')
bad('C4 chore that is a gated step', lambda r: r['chore_groups'][0]['items'][0].update(step='Ship the blurb change'), 'gated', AUDIT)

# C5. Against the audit: a row the board doesn't have is named.
bad('C5 unknown row', lambda r: r['initiatives'][0].update(row='nosuch'), 'nosuch', AUDIT)

# C6. Not JSON at all.
d = tempfile.mkdtemp(); p = os.path.join(d, 'r.json'); open(p, 'w').write('{not json')
r = subprocess.run([CHECK, p], capture_output=True, text=True)
expect('C6 invalid JSON: exit 1, says so', r.returncode == 1 and 'JSON' in r.stdout + r.stderr, r.stdout + r.stderr)

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
