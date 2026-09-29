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

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
