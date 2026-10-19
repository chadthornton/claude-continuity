"""Scenario tests for skills/continuity-review/page.html: its script runs in node against a stand-in store.
Run: python3 tests/test_review_page.py   (needs node)"""
import json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'skills', 'continuity-review', 'page.html')
fails = []


def expect(name, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + name)
    if not ok:
        fails.append(name)
        print('   ', str(detail)[:700])


if not shutil.which('node'):
    print('SKIP: node not installed'); sys.exit(0)

SCRIPT = re.search(r'<script>\n(.*)</script>', open(PAGE).read(), re.S).group(1)

# A stand-in for the viewer: a DOM just deep enough for the page, a db whose snapshots the test drives,
# and a log of every write. Each scenario is a list of steps: ["seed", doc] | ["click", {dataset}] |
# ["change", {dataset}, value]; the harness prints JSON of what the page showed and wrote.
HARNESS = r'''
const fs = require("fs");
const [script, stepsFile, canWrite] = process.argv.slice(2);
const steps = JSON.parse(fs.readFileSync(stepsFile, "utf8"));
const els = {}, listeners = {}, writes = [], subs = {};
const el = id => els[id] || (els[id] = { id, innerHTML: "", textContent: "", hidden: false });
global.document = { getElementById: el, addEventListener: (t, f) => (listeners[t] = f) };
global.window = { scrollY: 0, scrollTo() {} };
const snap = (id, data) => ({ id, exists: data != null, data: () => data, metadata: { hasPendingWrites: false } });
const db = {
  doc: path => ({ path,
    onSnapshot: (cb) => { subs[path] = cb; cb(snap(path.split("/").pop(), null)); },
    set: data => { writes.push({ path, data: JSON.parse(JSON.stringify(data)) }); return Promise.resolve(); } }),
  collection: path => ({ limit: () => ({ onSnapshot: (cb) => { subs[path] = cb; cb({ docs: [], metadata: { hasPendingWrites: false } }); } }) }),
};
const user = { can: () => canWrite === "1" };
window.claude = { use: name => Promise.resolve(name === "db" ? db : name === "user" ? user : null) };
global.window.claude = window.claude;
const strip = s => s.replace(/<[^>]+>/g, " ").replace(/&[a-z]+;/g, " ").replace(/\s+/g, " ").trim();
// eval runs this repo's own page script (extracted from page.html), never outside input.
eval(script);
(async () => {
  await new Promise(r => setTimeout(r, 0)); await new Promise(r => setTimeout(r, 0));
  const shots = [];
  for (const s of steps) {
    if (s[0] === "seed") subs["review/current"](snap("current", s[1]));
    if (s[0] === "click") listeners.click({ target: { closest: () => ({ dataset: s[1] }) } });
    if (s[0] === "change") listeners.change({ target: Object.assign({ dataset: s[1] }, { value: s[2] }) });
    await new Promise(r => setTimeout(r, 0));
    shots.push({ app: els.app.innerHTML, co: els.co ? els.co.innerHTML : "", title: el("title").textContent, note: el("note").textContent });
  }
  console.log(JSON.stringify({ shots, writes }));
})();
'''

REVIEW = {
    'project': 'demo', 'mode': 'full', 'since': '2026-10-05', 'read': 'Lists took the window.', 'generated': '2026-10-19T10:00Z',
    'board_source': 'local', 'lanes': {'live': 1, 'back': 3, 'quiet': 3},
    'areas': [{'name': 'Lists', 'what': 'Where places come from.', 'open_question': 'When does a list travel?', 'starters': [], 'initiatives': 2},
              {'name': 'Jaunts', 'what': 'Outings on the day.', 'open_question': 'What does a morning need?', 'initiatives': 0,
               'starters': [{'title': 'Morning-of chooser', 'aspiration': 'Pick in a minute.', 'size': 'M', 'first_session': 'think', 'brief': 'Walk a morning.'}]}],
    'initiatives': [
        {'row': 'lists', 'section': 'features', 'status': 'building', 'open': 5, 'done': 3, 'gated': [{'step': 'Pick', 'gate': 'decision: A or B?'}], 'waiting': 1,
         'activity': {'board_edits': 3, 'dates': ['2026-10-06', '2026-10-12'], 'prs_merged': [103]}, 'flags': [],
         'running': None, 'running_idle': False, 'area': 'Lists', 'size': 'L', 'aspiration': 'Board aspiration.', 'progress': 'about a third', 'progress_basis': 'Two of six.',
         'line': 'Calls wait on you.', 'recent': [], 'proposal': {'kind': 'decision', 'title': 'Whole list on the trip', 'brief': 'Pick on a preview.', 'comes_back': 'Straight away.'},
         'suggest': {'action': 'keep', 'reason': 'Live.'}, 'judged': ['line', 'recent', 'progress', 'proposal', 'suggest']},
        {'row': 'discovery', 'section': 'features', 'status': 'parked', 'open': 2, 'done': 4, 'gated': [], 'waiting': 0,
         'activity': {'board_edits': 0, 'dates': [], 'prs_merged': []}, 'flags': [],
         'running': None, 'running_idle': False, 'area': 'Lists', 'size': 'M', 'aspiration': 'Suggestions arrive.', 'progress': 'about a third', 'progress_basis': 'Queue built.',
         'line': 'Nothing moved.', 'recent': [], 'proposal': None,
         'suggest': {'action': 'merge', 'into': 'lists', 'reason': 'Lists covers it.'}, 'judged': ['size', 'aspiration', 'line', 'recent', 'progress', 'proposal', 'suggest']},
    ],
    'chore_groups': [{'title': 'Guards', 'code_area': 'the add handler', 'why_together': 'Same file.', 'items': [{'row': 'lists', 'title': 'Cap pastes', 'step': 'Cap paste size'}]}],
    'sessions': [],
}


def run(steps, can_write=True):
    d = tempfile.mkdtemp()
    sp, hp = os.path.join(d, 'steps.json'), os.path.join(d, 'h.js')
    json.dump(steps, open(sp, 'w')); open(hp, 'w').write(HARNESS)
    sc = os.path.join(d, 'page.js'); open(sc, 'w').write(SCRIPT)
    r = subprocess.run(['node', hp, open(sc).read(), sp, '1' if can_write else '0'], capture_output=True, text=True, timeout=60)
    shutil.rmtree(d)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {'shots': [], 'writes': [], 'error': r.stdout + r.stderr}


def text(html):
    return re.sub(r'\s+', ' ', re.sub(r'&[a-z]+;', ' ', re.sub(r'<[^>]+>', ' ', html))).strip()


# G1. Nothing seeded: the page says so and offers no checkout.
out = run([['seed', None]])
expect('G1 empty store: says no review yet', out['shots'] and 'No review has been seeded yet' in out['shots'][-1]['app'], out.get('error') or out['shots'][-1:])

# G2. Seeded: title, area with its open question, a starter, a judged size marked, a confirmed one not.
out = run([['seed', REVIEW]])
s = out['shots'][-1] if out['shots'] else {}
app = s.get('app', '')
expect('G2 title from the project', s.get('title') == 'demo board review', s.get('title'))
expect('G2 area and open question', 'When does a list travel?' in app and 'Morning-of chooser' in app, text(app)[:400])
lists_row = app.split('data-toggle="lists"')[1].split('</tr>')[0] if 'data-toggle="lists"' in app else ''
disc_row = app.split('data-toggle="discovery"')[1].split('</tr>')[0] if 'data-toggle="discovery"' in app else ''
expect('G2 a size the board confirmed is not marked', 'class="tag"' not in lists_row.split('select')[1] if 'select' in lists_row else False, lists_row[:600])
expect('G2 a size Claude guessed is marked', 'data-ov="size"' in disc_row and '>Claude<' in disc_row.split('data-ov="size"')[1].split('</td>')[0], disc_row[:600])
expect('G2 merge suggestion listed under winding down', 'merge into lists' in app, text(app)[-600:])
expect('G2 checkout empty', 'This round is empty' in s.get('co', ''), text(s.get('co', '')))

# G3. Add, then Confirm: the round is written with the item, then with a confirmed time.
out = run([['seed', REVIEW], ['click', {'add': 'p:lists'}], ['click', {'add': 'c:0'}], ['click', {'confirm': '1'}]])
rounds = [w['data'] for w in out['writes'] if w['path'] == 'round/current']
expect('G3 adding writes the round', len(rounds) >= 2 and [i['key'] for i in rounds[1]['items']] == ['p:lists', 'c:0'] and rounds[1]['confirmed_at'] is None, rounds)
expect('G3 confirm stamps the round', rounds and rounds[-1]['confirmed_at'] and rounds[-1]['generated'] == '2026-10-19T10:00Z', rounds[-1:] if rounds else out)
expect('G3 checkout shows confirmed and what happens next', 'Confirmed' in out['shots'][-1]['co'] and 'A new pane opens to settle' in text(out['shots'][-1]['co']), text(out['shots'][-1]['co']))

# G4. Correcting a size writes an override and the cell becomes yours.
out = run([['seed', REVIEW], ['change', {'ov': 'size', 'row': 'discovery'}, 'L']])
ov = [w for w in out['writes'] if w['path'] == 'overrides/discovery']
disc = out['shots'][-1]['app'].split('data-toggle="discovery"')[1].split('</tr>')[0]
expect('G4 override written', ov and ov[-1]['data'].get('size') == 'L', out['writes'])
expect('G4 corrected size shown as yours, not Claude', 'size you' in disc and '<option selected>L</option>' in disc and '>Claude<' not in disc.split('data-ov="size"')[1].split('</td>')[0], disc[:700])

# G5. Keep it overrides a wind-down suggestion.
out = run([['seed', REVIEW], ['click', {'keep': 'discovery'}]])
ov = [w for w in out['writes'] if w['path'] == 'overrides/discovery']
expect('G5 keep written, suggestion gone', ov and ov[-1]['data'].get('keep') is True and 'merge into lists' not in out['shots'][-1]['app'] and 'You kept' in out['shots'][-1]['app'], text(out['shots'][-1]['app'])[-400:])

# G6. A viewer who can't write sees no controls and writes nothing.
out = run([['seed', REVIEW], ['click', {'add': 'p:lists'}]], can_write=False)
expect('G6 read-only: no Add, no Confirm, no writes', 'data-add=' not in out['shots'][-1]['app'] and 'data-confirm' not in out['shots'][-1]['co'] and not out['writes'], out['writes'])

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
