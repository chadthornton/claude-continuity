"""Scenario tests for worktree-sweep: bare remote + clone + worktrees in each state.

Run: python3 tests/test_worktree_sweep.py   (GIT=/usr/bin/git to pin a git)

Seams: CONTINUITY_LIVE_CWDS (newline list of cwds with a live claude; replaces
the pgrep/lsof scan) and CONTINUITY_SESSION_PID (this session's claude pid;
replaces the parent-process walk).
"""
import os, shutil, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP = os.path.join(ROOT, 'skills', 'wrap-up', 'worktree-sweep')
GIT = os.environ.get('GIT', shutil.which('git') or '/usr/bin/git')
BASE_ENV = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t',
                GIT_COMMITTER_EMAIL='t@t')
fails = []

ME = os.getpid()          # alive: stands in for ANOTHER running session
SESSION = os.getppid()    # alive: stands in for THIS session's claude pid
DEAD = 999999             # not running


def sh(cwd, *args, env=None, check=True):
    r = subprocess.run(args, cwd=cwd, env=env or BASE_ENV, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f'{args} in {cwd}: {r.stdout}{r.stderr}')
    return r


def git(cwd, *a):
    return sh(cwd, GIT, *a).stdout.strip()


def expect(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f'\n     {detail}'))
    if not cond:
        fails.append(name)


def setup():
    root = os.path.realpath(tempfile.mkdtemp(prefix='ws-'))
    remote = os.path.join(root, 'remote.git')
    git(root, 'init', '-q', '--bare', '-b', 'master', remote)
    clone = os.path.join(root, 'clone')
    git(root, 'clone', '-q', remote, clone)
    open(f'{clone}/.gitignore', 'w').write('.claude/worktrees/\n')
    git(clone, 'add', '-A'); git(clone, 'commit', '-q', '-m', 'init'); git(clone, 'push', '-q', 'origin', 'master')
    wts = {}
    for n in ['done', 'dirty', 'ahead', 'live', 'mine', 'other', 'stale', 'self']:
        p = f'{clone}/.claude/worktrees/{n}'
        git(clone, 'worktree', 'add', '-q', '-b', f'worktree-{n}', p, 'HEAD')
        wts[n] = p
    open(f"{wts['dirty']}/scratch.txt", 'w').write('x\n')
    git(wts['ahead'], 'commit', '-q', '--allow-empty', '-m', 'local only')
    git(clone, 'worktree', 'lock', '--reason', f'claude agent mine (pid {SESSION} start Mon)', wts['mine'])
    git(clone, 'worktree', 'lock', '--reason', f'claude agent other (pid {ME} start Mon)', wts['other'])
    git(clone, 'worktree', 'lock', '--reason', f'claude session stale (pid {DEAD} start Mon)', wts['stale'])
    return clone, wts


def run(cwd, wts, *args):
    env = dict(BASE_ENV, CONTINUITY_LIVE_CWDS=wts['live'], CONTINUITY_SESSION_PID=str(SESSION))
    r = sh(cwd, SWEEP, *args, env=env, check=False)
    return r.returncode, r.stdout, r.stderr


def registered(clone):
    return git(clone, 'worktree', 'list', '--porcelain')


clone, wts = setup()

# ── list mode (run from the `self` worktree, as a session working there would) ─
code, out, err = run(wts['self'], wts)
listed = {line.split('\t')[0] for line in out.splitlines() if line}
expect('list exits 0', code == 0, err)
expect('clean + pushed → listed', wts['done'] in listed, out)
expect('locked by THIS session (its subagents) → listed', wts['mine'] in listed, out)
expect('lock held by a dead pid → listed', wts['stale'] in listed, out)
expect('uncommitted → not listed', wts['dirty'] not in listed, out)
expect('commit on no remote → not listed', wts['ahead'] not in listed, out)
expect('live claude working there → not listed', wts['live'] not in listed, out)
expect('locked by ANOTHER live session → not listed', wts['other'] not in listed, out)
expect('the checkout the session runs in → not listed', wts['self'] not in listed, out)
expect('list mode removes nothing', all(f'worktree {p}' in registered(clone) for p in wts.values()))
expect('each row carries a reason', all('\t' in line for line in out.splitlines() if line), out)

# ── remove mode ──────────────────────────────────────────────────────────────
code, out, err = run(wts['self'], wts, '--remove')
reg = registered(clone)
expect('remove exits 0', code == 0, out + err)
for n in ['done', 'mine', 'stale']:
    expect(f'removed: {n}', f'worktree {wts[n]}' not in reg and not os.path.exists(wts[n]), out + err)
for n in ['dirty', 'ahead', 'live', 'other', 'self']:
    expect(f'kept: {n}', f'worktree {wts[n]}' in reg, out + err)
expect('branches survive removal', 'worktree-done' in git(clone, 'branch', '--list', 'worktree-done'))
expect('dirty work untouched', os.path.exists(f"{wts['dirty']}/scratch.txt"))

# ── nothing to do ────────────────────────────────────────────────────────────
code, out, err = run(wts['self'], wts)
expect('second run lists nothing', out.strip() == '', out)

print(f'\n{len(fails)} failed' if fails else '\nall passed')
raise SystemExit(1 if fails else 0)
