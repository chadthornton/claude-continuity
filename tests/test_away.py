"""Scenario tests for skills/away/away. A bare remote + clone; a second clone plays
the cloud by pushing claude/* branches; a fake `claude` prints the real launch lines.
Run: python3 tests/test_away.py"""
import os, shutil, stat, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AWAY = os.path.join(ROOT, 'skills', 'away', 'away')
GIT = os.environ.get('GIT', shutil.which('git') or '/usr/bin/git')
FAKE_SESSION = 'session_01FAKEabc123'
FAKE_CLAUDE = r'''#!/bin/bash
printf '%s\n' "$*" >> "$(dirname "$0")/claude.log"
if [ "$1" = "--cloud" ]; then
  [ -n "${FAKE_CLAUDE_FAIL:-}" ] && { echo "Error: Cloud sessions are disabled by your organization's policy."; exit 1; }
  printf 'Created cloud session: Fake task\nView: https://claude.ai/code/session_01FAKEabc123?from=cli&m=0\nResume with: claude --teleport session_01FAKEabc123\n'
  exit 0
fi
if [ "$1" = "-p" ]; then
  [ -n "${FAKE_CLAUDE_FAIL:-}" ] && { echo "{\"ok\":false,\"session_id\":\"$4\",\"error\":\"Session not found: $4\"}"; exit 1; }
  echo "{\"ok\":true,\"session_id\":\"$4\",\"url\":\"https://claude.ai/code/$4\"}"; exit 0
fi
exit 2
'''
fails = []


def expect(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f'\n     {detail}'))
    if not cond:
        fails.append(name)


def git(cwd, *a, check=True, env=None):
    r = subprocess.run((GIT,) + a, cwd=cwd, env=env or BASE_ENV, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f'git {a} in {cwd}: {r.stdout}{r.stderr}')
    return r.stdout.strip()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w').write(text)


BASE_ENV = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t',
                GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@t')


def setup():
    """→ dict(root, remote, clone, env). clone is on main, pushed, with a .continuity board."""
    root = tempfile.mkdtemp(prefix='away-')
    bindir = os.path.join(root, 'bin'); os.makedirs(bindir)
    fake = os.path.join(bindir, 'claude'); write(fake, FAKE_CLAUDE)
    os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
    env = dict(BASE_ENV, AWAY_CLAUDE=fake, AWAY_ALLOW_ANY_ORIGIN='1')
    remote = os.path.join(root, 'remote.git')
    git(root, 'init', '-q', '--bare', '-b', 'main', remote)
    clone = os.path.join(root, 'clone')
    git(root, 'clone', '-q', remote, clone)
    write(f'{clone}/.continuity/feature-status.yml', 'settings:\n  push_to_default_branch: true\nfeatures:\n  a:\n    status: building\n')
    write(f'{clone}/app.js', 'v1\n')
    git(clone, 'add', '-A'); git(clone, 'commit', '-q', '-m', 'init'); git(clone, 'push', '-q', 'origin', 'main')
    git(clone, 'remote', 'set-head', 'origin', '-a')
    return dict(root=root, remote=remote, clone=clone, env=env, log=os.path.join(bindir, 'claude.log'))


def run_away(ctx, cwd, *args, **extra_env):
    env = dict(ctx['env'], **extra_env)
    r = subprocess.run([AWAY] + list(args), cwd=cwd, env=env, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def remote_show(ctx, ref, path):
    git(ctx['clone'], 'fetch', '-q', 'origin')
    return git(ctx['clone'], 'show', f'{ref}:{path}', check=False)


def claude_log(ctx):
    return open(ctx['log']).read() if os.path.exists(ctx['log']) else ''


# ── launch ───────────────────────────────────────────────────────────────────
# L1. From main: branches off, never touches origin/main, prints AWAY line.
c = setup(); cl = c['clone']
main_before = git(cl, 'rev-parse', 'origin/main')
write(f'{cl}/.continuity/away.md', '<away>brief</away>\n'); write(f'{cl}/app.js', 'v2-wip\n')
rc, out = run_away(c, cl, 'launch', '-m', 'fix "quoted" thing')
branch = git(cl, 'branch', '--show-current')
expect('L1 exit 0', rc == 0, out)
expect('L1 AWAY line', out.startswith(f'AWAY: {FAKE_SESSION} https://claude.ai/code/{FAKE_SESSION}') and f'branch={branch}' in out, out)
expect('L1 base is HEAD', f'base={git(cl, "rev-parse", "HEAD")}' in out, out)
expect('L1 branched off main', branch.startswith('away-'), branch)
git(cl, 'fetch', '-q', 'origin')
expect('L1 origin/main untouched', git(cl, 'rev-parse', 'origin/main') == main_before, out)
expect('L1 code pushed on branch', remote_show(c, f'origin/{branch}', 'app.js') == 'v2-wip', out)
expect('L1 away.md pushed on branch', remote_show(c, f'origin/{branch}', '.continuity/away.md') == '<away>brief</away>', out)
expect('L1 quoted task kept', git(cl, 'log', '-1', '--format=%s') == 'wip(away): fix "quoted" thing', git(cl, 'log', '-1', '--format=%s'))
expect('L1 prompt sent', '--cloud Read .continuity/away.md and follow it exactly.' in claude_log(c), claude_log(c))
shutil.rmtree(c['root'])

# L2. On a slash branch: other .continuity edits stay out of the WIP commit.
c = setup(); cl = c['clone']
git(cl, 'switch', '-q', '-c', 'feature/x')
write(f'{cl}/.continuity/away.md', '<away>brief</away>\n'); write(f'{cl}/app.js', 'v2\n')
write(f'{cl}/.continuity/feature-status.yml', 'settings:\n  push_to_default_branch: true\nfeatures:\n  a:\n    status: polishing\n')
rc, out = run_away(c, cl, 'launch', '-m', 'x')
expect('L2 exit 0', rc == 0, out)
expect('L2 stays on feature/x', git(cl, 'branch', '--show-current') == 'feature/x', out)
names = git(cl, 'show', '--name-only', '--format=', 'HEAD').splitlines()
expect('L2 WIP has code + away.md', 'app.js' in names and '.continuity/away.md' in names, names)
expect('L2 WIP excludes board edits', '.continuity/feature-status.yml' not in names, names)
pending = (git(cl, 'diff', '--name-only'), git(cl, 'diff', '--cached', '--name-only'))
expect('L2 board edit still pending, unstaged', pending == ('.continuity/feature-status.yml', ''), pending)
expect('L2 slash branch pushed', remote_show(c, 'origin/feature/x', 'app.js') == 'v2', out)
shutil.rmtree(c['root'])

# L3. No away.md → exit 3, nothing launched.
c = setup(); cl = c['clone']
rc, out = run_away(c, cl, 'launch')
expect('L3 exit 3', rc == 3 and 'away.md' in out, out)
expect('L3 nothing launched', claude_log(c) == '', claude_log(c))
shutil.rmtree(c['root'])

# L4. Origin not on github.com and no test seam → exit 3.
c = setup(); cl = c['clone']
write(f'{cl}/.continuity/away.md', 'b\n')
rc, out = run_away(c, cl, 'launch', AWAY_ALLOW_ANY_ORIGIN='')
expect('L4 exit 3', rc == 3 and 'github.com' in out, out)
expect('L4 nothing launched', claude_log(c) == '', claude_log(c))
shutil.rmtree(c['root'])

# L5. Cloud launch fails → exit 1 with the CLI's words; branch was still pushed.
c = setup(); cl = c['clone']
write(f'{cl}/.continuity/away.md', 'b\n')
rc, out = run_away(c, cl, 'launch', FAKE_CLAUDE_FAIL='1')
expect('L5 exit 1', rc == 1 and out.startswith('FAILED'), out)
expect('L5 CLI error surfaced', 'disabled by your organization' in out, out)
shutil.rmtree(c['root'])

# L6. Push rejected (remote branch moved) → exit 1, no cloud session started.
c = setup(); cl = c['clone']
git(cl, 'switch', '-q', '-c', 'feat'); git(cl, 'push', '-q', '-u', 'origin', 'feat')
other = os.path.join(c['root'], 'other'); git(c['root'], 'clone', '-q', '-b', 'feat', c['remote'], other)
write(f'{other}/app.js', 'peer\n'); git(other, 'commit', '-qam', 'peer'); git(other, 'push', '-q')
write(f'{cl}/.continuity/away.md', 'b\n'); write(f'{cl}/app.js', 'mine\n')
rc, out = run_away(c, cl, 'launch')
expect('L6 exit 1', rc == 1 and 'push' in out, out)
expect('L6 nothing launched', claude_log(c) == '', claude_log(c))
shutil.rmtree(c['root'])

# ── park ─────────────────────────────────────────────────────────────────────
c = setup(); cl = c['clone']
rc, out = run_away(c, cl, 'park', FAKE_SESSION)
expect('P1 exit 0', rc == 0 and out.startswith('PARKING'), out)
log = claude_log(c)
expect('P1 sends park message to the session',
       '-p Stop at the next clean point' in log and f'--cloud {FAKE_SESSION} --output-format json' in log, log)
expect('P1 message names the parked commit', '"away: parked"' in log, log)
rc, out = run_away(c, cl, 'park', FAKE_SESSION, FAKE_CLAUDE_FAIL='1')
expect('P2 failure exit 1', rc == 1 and 'Session not found' in out, out)
rc, out = run_away(c, cl, 'park')
expect('P3 no id → exit 3', rc == 3, out)
shutil.rmtree(c['root'])
# LAND_TESTS

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
