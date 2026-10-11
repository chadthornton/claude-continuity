"""Scenario tests for skills/startup/continuity-state. Run: python3 tests/test_continuity_state.py"""
import os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, 'skills', 'startup', 'continuity-state')
# reuse helpers without running the save scenarios
_save_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_continuity_save.py')
ns = {'__file__': _save_py}
exec(open(_save_py).read().split('# 1. Feature branch')[0], ns)
git, write, save, setup, expect, ENV, fails = ns['git'], ns['write'], ns['save'], ns['setup'], ns['expect'], ns['ENV'], ns['fails']


def state(cwd, *args):
    r = subprocess.run([STATE] + list(args), cwd=cwd, env=ENV, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def section(out, name):
    """Lines under '--- name' up to the next '--- ' header."""
    lines, on = [], False
    for ln in out.splitlines():
        if ln.startswith('--- '):
            on = ln == f'--- {name}'
            continue
        if on:
            lines.append(ln)
    return '\n'.join(lines).strip()


# S1. Fresh checkout: board read locally; identity, log and uncommitted files reported.
root, remote, clone, wt = setup()
write(f'{wt}/app.js', 'edited\n')
write(f'{wt}/.continuity/last-activity.txt', 'line1\nsession ended 10:00\n')
rc, out = state(wt)
expect('S1 exit 0', rc == 0, out)
expect('S1 identity line', out.splitlines()[0] == 'checkout: wt  branch: feature', out.splitlines()[:1])
expect('S1 board is local', 'board: local' in out, out)
expect('S1 feature-status content', 'summary: base' in section(out, 'feature-status.yml'), out)
expect('S1 uncommitted lists app.js', section(out, 'uncommitted') == 'app.js', section(out, 'uncommitted'))
expect('S1 log shows init', 'init' in section(out, 'git log'), section(out, 'git log'))
expect('S1 last-activity tail', 'session ended 10:00' in section(out, 'last-activity.txt'), out)
expect('S1 no handoffs', section(out, 'handoffs') == '(none)', section(out, 'handoffs'))
shutil.rmtree(root)

# S2. Stale checkout: another session landed continuity → board read from origin.
root, remote, clone, wt = setup()
write(f'{clone}/.continuity/feature-status.yml', ns['STATUS'].format(push='true').replace('summary: base', 'summary: PEER'))
write(f'{clone}/.continuity/handoffs/a.md', '<handoff>peer</handoff>\n')
git(clone, 'add', '-A'); git(clone, 'commit', '-qm', 'peer board'); git(clone, 'push', '-q', 'origin', 'master')
rc, out = state(wt)
expect('S2 exit 0', rc == 0, out)
expect('S2 board from origin, count', 'board: origin/master (1 continuity commit(s) behind)' in out, out)
expect('S2 origin content shown', 'summary: PEER' in section(out, 'feature-status.yml'), out)
expect('S2 handoffs from origin', section(out, 'handoffs') == '.continuity/handoffs/a.md', section(out, 'handoffs'))
expect('S2 checkout untouched', 'summary: base' in open(f'{wt}/.continuity/feature-status.yml').read(), '')
# show <path> reads from the same source as the board
rc, out = state(wt, 'show', 'handoffs/a.md')
expect('S2 show reads origin', rc == 0 and out.strip() == '<handoff>peer</handoff>', out)
shutil.rmtree(root)

# S3. Local handoffs, legacy and per-feature, listed; show reads the working copy when fresh.
root, remote, clone, wt = setup()
write(f'{wt}/.continuity/handoff.md', 'legacy\n')
write(f'{wt}/.continuity/handoffs/b.md', 'feature b\n')
rc, out = state(wt)
expect('S3 both handoffs listed', section(out, 'handoffs') == '.continuity/handoff.md\n.continuity/handoffs/b.md', section(out, 'handoffs'))
rc, out = state(wt, 'show', 'handoffs/b.md')
expect('S3 show reads working copy', rc == 0 and out.strip() == 'feature b', out)
rc, out = state(wt, 'show', 'decisions/missing.md')
expect('S3 show missing → exit 1', rc == 1, out)
shutil.rmtree(root)

# S4. No .continuity/ → exit 3 pointing at continuity-init.
import tempfile
bare = tempfile.mkdtemp()
git(bare, 'init', '-q')
rc, out = state(bare)
expect('S4 exit 3 + init hint', rc == 3 and 'continuity-init' in out, out)
shutil.rmtree(bare)

# S5. No origin remote → board local, no fetch error noise.
root = tempfile.mkdtemp()
git(root, 'init', '-q', '-b', 'master')
write(f'{root}/.continuity/feature-status.yml', 'features: {}\n')
git(root, 'add', '-A'); git(root, 'commit', '-qm', 'init')
rc, out = state(root)
expect('S5 exit 0, local, quiet', rc == 0 and 'board: local' in out and 'fatal' not in out, out)
shutil.rmtree(root)

# S6. No git at all: board, handoffs and last activity still print; git sections say so.
plain = tempfile.mkdtemp()
write(f'{plain}/.continuity/feature-status.yml', 'features:\n  a: {}\n')
write(f'{plain}/.continuity/handoffs/a.md', 'h\n')
rc, out = state(plain)
expect('S6 exit 0 without git', rc == 0, out)
expect('S6 board printed', 'features:' in section(out, 'feature-status.yml'), out)
expect('S6 handoff listed', section(out, 'handoffs') == '.continuity/handoffs/a.md', out)
expect('S6 git sections marked', section(out, 'git log') == '(not a git repository)', out)
rc, out = state(plain, 'show', 'handoffs/a.md')
expect('S6 show works without git', rc == 0 and out.strip() == 'h', out)
shutil.rmtree(plain)

# S7. This checkout's own landed saves don't make it look stale.
root, remote, clone, wt = setup()
write(f'{wt}/.continuity/decisions/a.md', '# a\n')
rc, o = save(wt)
rc, out = state(wt)
expect('S7 own landed save → board local', 'board: local' in out, (o, out))
write(f'{clone}/.continuity/decisions/p.md', '# peer\n')
git(clone, 'pull', '-q', 'origin', 'master'); git(clone, 'add', '-A'); git(clone, 'commit', '-qm', 'peer'); git(clone, 'push', '-q', 'origin', 'master')
rc, out = state(wt)
expect('S7 a peer commit → stale, counted once', 'board: origin/master (1 continuity commit(s) behind)' in out, out)
shutil.rmtree(root)

# S8. show refuses paths that leave .continuity/.
root, remote, clone, wt = setup()
write(f'{wt}/.env', 'TOKEN=secret\n')
for bad in ['../.env', '/etc/hosts', 'decisions/../../.env']:
    rc, out = state(wt, 'show', bad)
    expect(f'S8 refuses {bad}', rc == 3 and 'secret' not in out and 'localhost' not in out, out)
shutil.rmtree(root)

# S9. Peer commits the branch already absorbed through a sync don't count as behind.
root, remote, clone, wt = setup()
write(f'{wt}/.continuity/decisions/a.md', '# a\n'); save(wt)
git(clone, 'pull', '-q', 'origin', 'master')
write(f'{clone}/.continuity/decisions/p.md', '# P\n'); git(clone, 'add', '-A'); git(clone, 'commit', '-qm', 'P'); git(clone, 'push', '-q', 'origin', 'master')
write(f'{wt}/.continuity/decisions/b.md', '# b\n'); rc, o = save(wt)            # lands b, syncs (absorbs P)
rc, out = state(wt)
expect('S9 synced branch reads local', 'board: local' in out, (o, out))
write(f'{clone}/.continuity/decisions/q.md', '# Q\n'); git(clone, 'pull', '-q', 'origin', 'master')
git(clone, 'add', '-A'); git(clone, 'commit', '-qm', 'Q'); git(clone, 'push', '-q', 'origin', 'master')
rc, out = state(wt)
expect('S9 only Q counts', 'board: origin/master (1 continuity commit(s) behind)' in out, out)
shutil.rmtree(root)

# --- Large boards: above the size limit the board is summarised, one row at a time on request.
def big_board(pad=60):
    filler = ''.join(
        '      - { step: "filler step %d %s", done: %s }\n' % (i, 'x' * 300, 'true' if i % 2 else 'false')
        for i in range(pad))
    return (
        'settings:\n  push_to_default_branch: true\n\n'
        'features:\n'
        '  alpha:\n    status: building\n    phase: 1\n    owner: wt-a\n    next: "Ship alpha"\n'
        '    summary: >\n      Alpha summary text that the dashboard never shows.\n'
        '    next_steps:\n'
        '      - { step: "said \\"done: true }\\" in a note", done: false }\n'
        '      - { step: "second", gate: approval, done: false }\n'
        '      - { step: "third", done: true }\n'
        + filler +
        '    in_progress: "alpha step 2"\n'
        '  beta:\n    status: planned\n    next: "' + 'n' * 400 + '"\n'
        '    next_steps:\n      - step: "block one"\n        done: true\n      - step: "block two"\n        done: false\n'
        '    in_progress: null\n'
        '  gamma:\n    status: parked\n    next_steps: [one, two]\n'
        '  delta:\n    status: polishing\n    next_steps: []\n'
        'workflows:\n  audit:\n    last_run: null\n    summary: "Weekly audit"\n'
        '    steps:\n      - "pull counts"\n      - "write report"\n'
        'last_session:\n  date: 2026-10-11\n  feature: alpha\n  summary: "did things"\n'
        '  blind_spots:\n    - "' + 'b' * 300 + '"\n'
        'gotchas:\n  - "Short gotcha one"\n  - >\n    Folded gotcha whose first line is here\n'
        '    and continues ' + 'g' * 300 + '\n')


# S10. A board over the limit prints a per-row summary: fields kept, steps counted, bulk left out.
plain = tempfile.mkdtemp()
BIG = big_board()
write(f'{plain}/.continuity/feature-status.yml', BIG)
rc, out = state(plain)
sec = section(out, 'feature-status.yml')
expect('S10 exit 0', rc == 0, out[:400])
expect('S10 says it is summarised and how to read a row', 'SUMMARISED' in sec and 'continuity-state row <name>' in sec, sec[:400])
expect('S10 summary under the limit and far smaller than the board',
       len(sec.encode()) < 16384 and len(sec) < len(BIG) / 4, (len(sec), len(BIG)))
expect('S10 one-line steps counted, quoted "done: true" ignored', 'next_steps: 32 open, 31 done' in sec, sec[:900])
expect('S10 multi-line steps counted', 'next_steps: 1 open, 1 done' in sec, sec)
expect('S10 unparseable steps say so, no number', 'next_steps: unreadable' in sec, sec)
expect('S10 empty steps', 'next_steps: 0 open, 0 done' in sec, sec)
expect('S10 row fields kept', all(k in sec for k in ['alpha:', 'status: building', 'phase: 1', 'owner: wt-a', 'in_progress: "alpha step 2"']), sec[:900])
expect('S10 step text and row summaries left out', 'filler step' not in sec and 'Alpha summary text' not in sec, sec[:900])
expect('S10 a long next is cut', 'n' * 400 not in sec and 'n' * 150 in sec, sec)
expect('S10 workflow rows listed with a step count', 'audit:' in sec and 'steps: 2' in sec and 'pull counts' not in sec, sec)
expect('S10 last_session in full', 'b' * 300 in sec and 'feature: alpha' in sec, sec[-900:])
expect('S10 other sections still print', section(out, 'git log') == '(not a git repository)', out[-300:])
shutil.rmtree(plain)

# S11. `row <name>` prints one row with all its steps; an unknown row exits 1 and names the rows.
plain = tempfile.mkdtemp()
write(f'{plain}/.continuity/feature-status.yml', BIG)
rc, out = state(plain, 'row', 'beta')
expect('S11 row prints that row in full', rc == 0 and out.startswith('  beta:') and 'block two' in out and 'n' * 400 in out, out[:300])
expect('S11 row prints nothing of its neighbours', 'filler step' not in out and 'gamma' not in out and 'alpha' not in out, out[:300])
rc, out = state(plain, 'row', 'audit')
expect('S11 workflow rows are readable too', rc == 0 and 'write report' in out and 'last_session' not in out, out)
rc, out = state(plain, 'row', 'nope')
expect('S11 unknown row exits 1 and lists the rows', rc == 1 and 'alpha' in out and 'audit' in out and 'filler' not in out, out)
rc, out = state(plain, 'row')
expect('S11 row with no name is a usage error', rc == 3 and 'usage' in out, out)

# S12. Gotchas: a large board shows the first line of each; `gotchas` prints them in full.
rc, out = state(plain)
sec = section(out, 'feature-status.yml')
expect('S12 gotcha count and first lines', '2 entries' in sec and 'Short gotcha one' in sec and 'Folded gotcha whose first line is here' in sec, sec[-500:])
expect('S12 gotcha bodies left out', 'g' * 300 not in sec, sec[-500:])
rc, out = state(plain, 'gotchas')
expect('S12 gotchas in full on request', rc == 0 and 'g' * 300 in out and 'last_session' not in out and 'did things' not in out, out)
shutil.rmtree(plain)

# S13. A board under the limit prints exactly as before, byte for byte.
plain = tempfile.mkdtemp()
SMALL = big_board(pad=2)
write(f'{plain}/.continuity/feature-status.yml', SMALL)
rc, out = state(plain)
expect('S13 small board verbatim', '--- feature-status.yml\n' + SMALL + '--- handoffs\n' in out and 'SUMMARISED' not in out, out[:300])
shutil.rmtree(plain)

# S14. A stale checkout summarises origin's board, and `row` reads the same source.
root, remote, clone, wt = setup()
write(f'{clone}/.continuity/feature-status.yml', BIG)
git(clone, 'add', '-A'); git(clone, 'commit', '-qm', 'peer big board'); git(clone, 'push', '-q', 'origin', 'master')
rc, out = state(wt)
sec = section(out, 'feature-status.yml')
expect('S14 origin board summarised', 'board: origin/master' in out and 'SUMMARISED' in sec and 'next_steps: 32 open, 31 done' in sec, out[:500])
rc, out = state(wt, 'row', 'beta')
expect('S14 row reads origin', rc == 0 and 'block two' in out, out[:300])
shutil.rmtree(root)

# S15. A cut never lands inside a character.
plain = tempfile.mkdtemp()
write(f'{plain}/.continuity/feature-status.yml',
      'features:\n  a:\n    next: "' + 'é—·' * 200 + '"\n' + ''.join(f'  r{i}:\n    next: "{"z" * 300}"\n' for i in range(80)))
r = subprocess.run([STATE], cwd=plain, env=ENV, capture_output=True)
try:
    r.stdout.decode('utf-8'); ok = True
except UnicodeDecodeError as e:
    ok = False
expect('S15 summary is valid UTF-8', ok and b'SUMMARISED' in r.stdout, r.stdout[:300])
shutil.rmtree(plain)

# S16. A milestone's claims show as a count in the summary, and in full through `row`.
plain = tempfile.mkdtemp()
CLAIMS = ('  launch:\n    kind: milestone\n    status: building\n    claims:\n'
          '      - { text: "claim one text", status: true, evidence: "seen" }\n'
          '      - { text: "claim two text", status: false }\n'
          '      - text: "claim three text"\n        status: unknown\n')
write(f'{plain}/.continuity/feature-status.yml', BIG.replace('workflows:\n', CLAIMS + 'workflows:\n'))
rc, out = state(plain)
sec = section(out, 'feature-status.yml')
expect('S16 claims counted by status', 'claims: 3 (1 true, 1 false, 1 unknown)' in sec and 'kind: milestone' in sec, sec[-1200:])
expect('S16 claim text left out of the summary', 'claim one text' not in sec, sec[-1200:])
rc, out = state(plain, 'row', 'launch')
expect('S16 row shows the claims in full', rc == 0 and 'claim three text' in out and 'evidence: "seen"' in out, out)
shutil.rmtree(plain)

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
