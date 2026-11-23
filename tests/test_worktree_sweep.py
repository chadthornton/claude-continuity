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


def run(cwd, wts, *args, **extra):
    # CONTINUITY_AGENT_SPAWN="": no agent-spawn here (git removal only) unless a test passes a fake.
    env = dict(BASE_ENV, CONTINUITY_LIVE_CWDS=wts['live'], CONTINUITY_SESSION_PID=str(SESSION),
               CONTINUITY_AGENT_SPAWN='', CONTINUITY_MUXY='/nonexistent-muxy')
    env.update(extra)
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

# ── Muxy-held worktrees go through `agent-spawn done` ───────────────────────
# (2026-11-23: --remove ran `git worktree remove` on an agent-spawn worktree;
# its Muxy 2 sidebar entry and terminal were orphaned.) Muxy holds a folder
# when `agent-spawn muxy-project <dir>` answers; done then clears folder,
# terminals, sidebar entry and branch. A folder already gone leaves only the
# entry: `muxy project delete <id> --yes`.
fake = os.path.realpath(tempfile.mkdtemp(prefix='ws-fake-'))
log = os.path.join(fake, 'log')
open(f'{fake}/agent-spawn', 'w').write(f"""#!/bin/bash
echo "agent-spawn $* (in $PWD)" >> {log}
case "$1" in
  muxy-project) printf '%s\\n' "$FAKE_HELD" | grep -qxF -- "$2" && {{ echo "ID-${{2##*/}}"; exit 0; }}; exit 1 ;;
  done) [ "$2" = "${{FAKE_DONE_FAIL:-}}" ] && {{ echo "agent-spawn: '$2' still has 1 unpushed commit — not cleared" >&2; exit 1; }}
        git worktree remove "$PWD/.claude/worktrees/$2" && echo "✓ Agent '$2' is cleared"; exit $? ;;
esac
exit 2
""")
open(f'{fake}/muxy', 'w').write(f'#!/bin/bash\necho "muxy $*" >> {log}\n')
for f in ('agent-spawn', 'muxy'): os.chmod(f'{fake}/{f}', 0o755)
clone2, w2 = setup()
gone = f'{clone2}/.claude/worktrees/gone'
git(clone2, 'worktree', 'add', '-q', '-b', 'worktree-gone', gone, 'HEAD'); shutil.rmtree(gone)
held = '\n'.join([w2['done'], w2['stale'], gone])
kw = dict(CONTINUITY_AGENT_SPAWN=f'{fake}/agent-spawn', CONTINUITY_MUXY=f'{fake}/muxy', FAKE_HELD=held, FAKE_DONE_FAIL='stale')
code, out, err = run(w2['self'], w2, **kw)
expect('list: a gone folder with a sidebar entry is listed', any(l.startswith(gone + '\t') for l in out.splitlines()), out)
open(log, 'w').close()
code, out, err = run(w2['self'], w2, '--remove', **kw)
L = open(log).read(); reg = registered(clone2)
expect('held: removed through agent-spawn done, run in the main checkout', f'agent-spawn done done (in {clone2})' in L, L)
expect('held: …folder gone', not os.path.exists(w2['done']), out + err)
expect('held: …reported REMOVED', f'REMOVED {w2["done"]}' in out, out)
expect('held, done refuses: KEPT with its reason', f'KEPT {w2["stale"]}' in out and 'unpushed' in out, out + err)
expect('held, done refuses: never removed behind its back', f'worktree {w2["stale"]}' in reg and os.path.exists(w2['stale']), reg)
expect('not held (a subagent worktree): git removal, as before', f'worktree {w2["mine"]}' not in reg and 'agent-spawn done mine' not in L, L)
expect('gone folder: its sidebar entry deleted', 'muxy project delete ID-gone --yes' in L, L)
expect('gone folder: reported', f'FORGOT {gone}' in out, out)
expect('exit 1 when something was kept', code == 1, out)

print(f'\n{len(fails)} failed' if fails else '\nall passed')
raise SystemExit(1 if fails else 0)
