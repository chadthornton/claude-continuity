"""Scenario tests for lib/continuity-review-seed. Run: python3 tests/test_review_seed.py"""
import copy, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, 'lib', 'continuity-review-seed')
fails = []


def expect(name, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + name)
    if not ok:
        fails.append(name)
        print('   ', str(detail)[:700])


def seed(review, audit, project='demo', notes=None):
    d = tempfile.mkdtemp()
    rp, ap = os.path.join(d, 'review.json'), os.path.join(d, 'audit.json')
    json.dump(review, open(rp, 'w')); json.dump(audit, open(ap, 'w'))
    extra = []
    if notes is not None:
        np_ = os.path.join(d, 'overrides.json'); json.dump(notes, open(np_, 'w')); extra = ['--notes', np_]
    r = subprocess.run([SEED, rp, ap, project] + extra, capture_output=True, text=True)
    try:
        return r.returncode, json.loads(r.stdout), r.stdout + r.stderr
    except ValueError:
        return r.returncode, None, r.stdout + r.stderr


AUDIT = {
    'review': {'last_review': None, 'since': '2026-10-05'},
    'board': {'path': '.continuity/feature-status.yml', 'source': 'local', 'bytes': 100, 'lines': 10},
    'product_doc': {'path': 'docs/bets.md', 'exists': True},
    'areas': [{'name': 'Lists', 'what': 'Board says lists.', 'open_question': 'Board question?', 'initiatives': 1, 'empty': False}],
    'rows': [
        {'name': 'lists', 'section': 'features', 'status': 'building', 'open': 5, 'done': 3,
         'gated': [{'step': 'Ship it', 'gate': 'approval'}, {'step': 'Pick', 'gate': 'decision: A or B?'}],
         'area': 'Lists', 'size': 'L', 'aspiration': 'Board aspiration.', 'inferred': [],
         'activity': {'board_edits': 3, 'dates': ['2026-10-06', '2026-10-06', '2026-10-12'], 'prs_merged': [103]}, 'flags': []},
        {'name': 'quiet', 'section': 'features', 'status': 'parked', 'open': 1, 'done': 0, 'gated': [],
         'area': None, 'size': 'S', 'aspiration': None, 'inferred': ['size'],
         'activity': {'board_edits': 0, 'dates': [], 'prs_merged': []}, 'flags': []},
    ],
    'sessions': {'source': 'wt', 'items': [{'name': 'lists-4', 'branch': 'b', 'verdict': 'running', 'state': 'running', 'activity': 'idle (replied)', 'running': True, 'row': 'lists', 'match': 'owner'}]},
    'gotchas': {'count': 0, 'lines': 0, 'cap': 10, 'over_cap': False, 'entries': []},
}
REVIEW = {
    'mode': 'full', 'since': '2026-10-05', 'read': 'Lists took the window.',
    'areas': [
        {'name': 'Lists', 'what': 'Where places come from.', 'open_question': 'When does a list travel?', 'starters': []},
        {'name': 'Jaunts', 'what': 'Outings on the day.', 'open_question': 'What does a morning need?',
         'starters': [{'title': 'Morning-of chooser', 'aspiration': 'Pick in a minute.', 'size': 'M', 'first_session': 'think', 'brief': 'Walk a morning.'}]},
    ],
    'initiatives': [
        {'row': 'lists', 'line': 'Soaking; calls wait on you.', 'points': ['PR 3b waits on you.'], 'recent': [{'what': 'Add all', 'when': '2026-10-12', 'evidence': 'PR #103'}],
         'proposal': None, 'suggest': {'action': 'keep', 'reason': 'Live.'},
         'area': 'Lists', 'size': 'XL', 'aspiration': 'Reviewer aspiration.', 'progress': 'about a third', 'progress_basis': 'Two of six builds.'},
        {'row': 'quiet', 'line': 'Nothing moved.', 'recent': [],
         'proposal': {'kind': 'think', 'title': 'Agree what is next', 'brief': 'Read and agree.', 'comes_back': 'Straight away.'},
         'suggest': {'action': 'park', 'reason': 'Nothing due.'},
         'area': 'Jaunts', 'size': 'M', 'aspiration': 'Quiet aspiration.', 'progress': 'not started', 'progress_basis': 'No steps done.'},
    ],
    'chore_groups': [{'title': 'Guards', 'code_area': 'the add handler', 'why_together': 'Same file.',
                      'items': [{'row': 'lists', 'title': 'Cap pastes', 'step': 'Cap paste size'}]}],
}

rc, doc, raw = seed(REVIEW, AUDIT)
by = {i['row']: i for i in (doc or {}).get('initiatives', [])}

# D1. One document: header facts, the read, lanes.
expect('D1 exit 0, JSON out', rc == 0 and doc is not None, raw[:500])
expect('D1 header', doc and doc.get('project') == 'demo' and doc.get('since') == '2026-10-05' and doc.get('mode') == 'full' and doc.get('read') == 'Lists took the window.', doc)
expect('D1 lanes 1/3/3', doc and doc.get('lanes') == {'live': 1, 'back': 3, 'quiet': 3}, (doc or {}).get('lanes'))

# D2. A field the reader confirmed on the board wins and is a fact; an inferred or missing one is the reviewer's and marked.
l, q = by.get('lists', {}), by.get('quiet', {})
expect('D2 confirmed size and aspiration kept as facts', l.get('size') == 'L' and l.get('aspiration') == 'Board aspiration.' and 'size' not in l.get('judged', []) and 'aspiration' not in l.get('judged', []), l)
expect('D2 inferred size replaced by the reviewer, marked', q.get('size') == 'M' and 'size' in q.get('judged', []), q)
expect('D2 missing area and aspiration from the reviewer, marked', q.get('area') == 'Jaunts' and {'area', 'aspiration'} <= set(q.get('judged', [])), q)
expect('D2 progress, line, proposal, suggest always marked', {'progress', 'line', 'suggest'} <= set(q.get('judged', [])), q.get('judged'))

# D3. Facts come across from the audit.
expect('D3 counts, status, waiting', (l.get('open'), l.get('done'), l.get('status'), l.get('waiting')) == (5, 3, 'building', 2), l)
expect('D3 activity and running session', l.get('activity', {}).get('board_edits') == 3 and l.get('running') == 'lists-4' and l.get('running_idle') is True, l)
expect('D3 points carried and marked', l.get('points') == ['PR 3b waits on you.'] and 'points' in l.get('judged', []) and q.get('points') == [], (l, q))
expect('D3 reviewer judgments carried', l.get('line') == 'Soaking; calls wait on you.' and l.get('recent', [{}])[0].get('evidence') == 'PR #103' and q.get('proposal', {}).get('kind') == 'think', (l, q))

# D4. Areas: the reviewer's list, each with its initiative count; starters kept; chores and sessions carried.
areas = {a['name']: a for a in (doc or {}).get('areas', [])}
expect('D4 areas counted', areas.get('Lists', {}).get('initiatives') == 1 and areas.get('Jaunts', {}).get('initiatives') == 1, areas)
expect('D4 starters kept', areas.get('Jaunts', {}).get('starters', [{}])[0].get('title') == 'Morning-of chooser', areas.get('Jaunts'))
expect('D4 chores and sessions carried', (doc or {}).get('chore_groups', [{}])[0].get('title') == 'Guards' and (doc or {}).get('sessions', [{}])[0].get('name') == 'lists-4', doc)

# D5. Routine mode: no reviewer areas, so the board's areas are used.
routine = copy.deepcopy(REVIEW); routine['mode'] = 'routine'; del routine['areas']
for i in routine['initiatives']:
    for k in ('area', 'size', 'aspiration', 'progress', 'progress_basis'):
        i.pop(k)
rc, doc5, raw = seed(routine, AUDIT)
expect('D5 routine uses the board areas', rc == 0 and [a['name'] for a in doc5['areas']] == ['Lists'] and doc5['areas'][0]['open_question'] == 'Board question?', raw[:500])
expect('D5 routine keeps board sizes', {i['row']: i.get('size') for i in doc5['initiatives']} == {'lists': 'L', 'quiet': 'S'}, doc5['initiatives'])

# D6. A review the checker rejects is not seeded.
bad = copy.deepcopy(REVIEW); bad['initiatives'][0]['size'] = 'XXL'
rc, doc6, raw = seed(bad, AUDIT)
expect('D6 malformed review refused, nothing printed as JSON', rc == 1 and doc6 is None and 'size' in raw, raw[:400])

# F3. An ended or orphan worktree on a row is not a running agent.
ended = copy.deepcopy(AUDIT)
ended['sessions']['items'] = [
    {'name': 'quiet-1', 'branch': 'b', 'verdict': 'safe', 'state': 'ended', 'activity': 'idle (replied)', 'row': 'quiet', 'match': 'name', 'running': False},
    dict(AUDIT['sessions']['items'][0], running=True)]
rc, doc7, raw = seed(REVIEW, ended)
run = {i['row']: i.get('running') for i in (doc7 or {}).get('initiatives', [])}
expect('F3 seed: only a running session marks its row', rc == 0 and run == {'lists': 'lists-4', 'quiet': None}, run)

# D8. The seed records exactly the notes the review read, so "go" can clear those and keep newer ones.
rc, doc8, raw8 = seed(REVIEW, AUDIT, notes={'lists': {'notes': 'Carrier first', 'size': 'L'}, 'quiet': {'size': 'S'}, 'gone': {'notes': 'old row'}})
expect('D8 notes read, keyed by row, only rows with a note', rc == 0 and (doc8 or {}).get('notes_read') == {'lists': 'Carrier first', 'gone': 'old row'}, raw8[:600])
expect('D8 without --notes: none read', (doc or {}).get('notes_read') == {}, (doc or {}).get('notes_read'))

d9 = tempfile.mkdtemp(); bad = os.path.join(d9, 'bad.json'); open(bad, 'w').write('{not json')
rp, ap = os.path.join(d9, 'r.json'), os.path.join(d9, 'a.json'); json.dump(REVIEW, open(rp, 'w')); json.dump(AUDIT, open(ap, 'w'))
r9 = subprocess.run([SEED, rp, ap, 'demo', '--notes', bad], capture_output=True, text=True)
expect('D8 malformed notes file: still seeds, no notes read, says so', r9.returncode == 0 and json.loads(r9.stdout or '{}').get('notes_read') == {} and 'notes' in r9.stderr, r9.stdout[:200] + r9.stderr)

# D9. An entry that isn't a document is skipped, not fatal.
rc, doc9, raw9 = seed(REVIEW, AUDIT, notes={'x': 'str', 'lists': {'notes': 'n'}})
expect('D9 non-object entry skipped', rc == 0 and (doc9 or {}).get('notes_read') == {'lists': 'n'}, raw9[:400])

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
