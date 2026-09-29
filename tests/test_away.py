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
  [ -n "${FAKE_CLAUDE_BOGUS:-}" ] && { echo "Error: invalid session_token for this account"; exit 1; }
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
    try:
        r = subprocess.run([AWAY] + list(args), cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return 124, 'TIMEOUT: away hung'
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

# L7. Untracked files (local data, stray secrets) are never pushed; launch names them.
c = setup(); cl = c['clone']
git(cl, 'switch', '-q', '-c', 'feat')
write(f'{cl}/.continuity/away.md', 'b\n'); write(f'{cl}/app.js', 'v2\n')
write(f'{cl}/data/widgets.csv', 'id,name\n'); write(f'{cl}/.env', 'TOKEN=secret\n')
rc, out = run_away(c, cl, 'launch', '-m', 'x')
names = git(cl, 'show', '--name-only', '--format=', 'HEAD').splitlines()
expect('L7 exit 0', rc == 0, out)
expect('L7 tracked change committed', 'app.js' in names, names)
expect('L7 untracked data + .env not committed', 'data/widgets.csv' not in names and '.env' not in names, names)
expect('L7 launch names the untracked files', 'data/widgets.csv' in out and '.env' in out, out)
shutil.rmtree(c['root'])

# L8. Nothing to commit → still a fresh WIP commit, so base is unique to this /away.
c = setup(); cl = c['clone']
git(cl, 'switch', '-q', '-c', 'feat')
write(f'{cl}/.continuity/away.md', 'b\n'); git(cl, 'add', '-f', '.continuity/away.md'); git(cl, 'commit', '-qm', 'brief already committed')
before = git(cl, 'rev-parse', 'HEAD')
rc, out = run_away(c, cl, 'launch', '-m', 'x')
expect('L8 exit 0', rc == 0, out)
expect('L8 base is a new commit', f'base={before}' not in out and git(cl, 'rev-parse', 'HEAD~1') == before, out)
shutil.rmtree(c['root'])

# L9. Output mentioning session_… without a created session → FAILED, no bogus AWAY line.
c = setup(); cl = c['clone']
write(f'{cl}/.continuity/away.md', 'b\n')
rc, out = run_away(c, cl, 'launch', FAKE_CLAUDE_BOGUS='1')
expect('L9 exit 1, no AWAY line', rc == 1 and 'AWAY:' not in out and out.startswith('FAILED'), out)
shutil.rmtree(c['root'])

# L10. Default branch unknown (no origin/HEAD, not main/master) → refuse, nothing committed.
c = setup(); cl = c['clone']
git(cl, 'branch', '-m', 'main', 'develop'); git(cl, 'push', '-q', 'origin', 'develop')
git(c['remote'], 'symbolic-ref', 'HEAD', 'refs/heads/develop'); git(cl, 'push', '-q', 'origin', '--delete', 'main')
git(cl, 'config', 'remote.origin.followRemoteHEAD', 'never')   # git ≥2.48 would re-create origin/HEAD on fetch
git(cl, 'remote', 'set-head', 'origin', '-d'); git(cl, 'fetch', '-q', '--prune', 'origin')
write(f'{cl}/.continuity/away.md', 'b\n'); write(f'{cl}/app.js', 'v2\n')
head = git(cl, 'rev-parse', 'HEAD')
rc, out = run_away(c, cl, 'launch')
expect('L10 exit 3', rc == 3 and 'default branch' in out, out)
expect('L10 nothing committed', git(cl, 'rev-parse', 'HEAD') == head, out)
shutil.rmtree(c['root'])

# L11. A .continuity/ edit already staged doesn't ride along in the WIP commit.
c = setup(); cl = c['clone']
git(cl, 'switch', '-q', '-c', 'feat')
write(f'{cl}/.continuity/away.md', 'b\n')
write(f'{cl}/.continuity/feature-status.yml', 'features:\n  a:\n    status: polishing\n'); git(cl, 'add', '.continuity/feature-status.yml')
rc, out = run_away(c, cl, 'launch')
names = git(cl, 'show', '--name-only', '--format=', 'HEAD').splitlines()
expect('L11 staged board edit not in WIP', rc == 0 and '.continuity/feature-status.yml' not in names, (out, names))
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
# ── land ─────────────────────────────────────────────────────────────────────
def launched():
    """A context whose clone has run `away launch` on branch feat → (ctx, base sha)."""
    c = setup(); cl = c['clone']
    git(cl, 'switch', '-q', '-c', 'feat')
    write(f'{cl}/.continuity/away.md', '<away><status>Not started.</status></away>\n'); write(f'{cl}/app.js', 'wip\n')
    rc, out = run_away(c, cl, 'launch', '-m', 't')
    assert rc == 0, out
    return c, git(cl, 'rev-parse', 'HEAD')


def cloud_push(c, start, branch, commits, date=None):
    """Play the cloud: from commit `start`, push claude/<branch> with [(path, text, subject)]."""
    d = tempfile.mkdtemp(dir=c['root'])
    git(c['root'], 'clone', '-q', c['remote'], d)
    git(d, 'checkout', '-q', '-b', f'claude/{branch}', start)
    env = dict(BASE_ENV, **({'GIT_COMMITTER_DATE': date, 'GIT_AUTHOR_DATE': date} if date else {}))
    for path, text, subject in commits:
        write(f'{d}/{path}', text); git(d, 'add', '-A', env=env); git(d, 'commit', '-qm', subject, env=env)
    git(d, 'push', '-q', 'origin', f'claude/{branch}')
    return git(d, 'rev-parse', 'HEAD')


FAST = ('--timeout', '2', '--interval', '1')
PARKED = [('app.js', 'cloud step 1\n', 'step 1'),
          ('.continuity/away.md', '<away><status>Did step 1.</status></away>\n', 'away: parked')]

# D1. Picks the descendant among decoys, fast-forwards, pushes, deletes the claude/ branch.
c, base = launched(); cl = c['clone']
init = git(cl, 'rev-parse', 'origin/main')
cloud_push(c, init, 'decoy', [('app.js', 'decoy\n', 'away: parked')])
tip = cloud_push(c, base, 'real', PARKED)
rc, out = run_away(c, cl, 'land', base, *FAST)
expect('D1 exit 0', rc == 0 and out.startswith('LANDED: 2 cloud commit(s) from claude/real onto feat'), out)
expect('D1 HEAD is the cloud tip', git(cl, 'rev-parse', 'HEAD') == tip, out)
expect('D1 branch pushed', git(cl, 'ls-remote', 'origin', 'refs/heads/feat').split()[0] == tip, out)
remote_heads = git(cl, 'ls-remote', 'origin', 'refs/heads/claude/*')
expect('D1 claude/real deleted, decoy kept', 'claude/real' not in remote_heads and 'claude/decoy' in remote_heads, remote_heads)
expect('D1 lists cloud commits', 'step 1' in out and 'away: parked' in out, out)
# Review Focus 4: a second /back says ALREADY LANDED
rc, out = run_away(c, cl, 'land', base, *FAST)
expect('D1b rerun → ALREADY LANDED exit 0', rc == 0 and out.startswith('ALREADY LANDED'), out)
git(cl, 'push', '-q', 'origin', f'{tip}:refs/heads/claude/real')   # as if the delete had failed
rc, out = run_away(c, cl, 'land', base, *FAST)
expect('D1c branch still on origin → ALREADY LANDED', rc == 0 and out.startswith('ALREADY LANDED'), out)
shutil.rmtree(c['root'])

# D2. Not parked yet → exit 4; --take lands the current tip.
c, base = launched(); cl = c['clone']
tip = cloud_push(c, base, 'busy', [('app.js', 'half\n', 'step 1')])
rc, out = run_away(c, cl, 'land', base, *FAST)
expect('D2 exit 4', rc == 4 and out.startswith('NOT PARKED') and 'claude/busy' in out and '"step 1"' in out, out)
expect('D2 HEAD unchanged', git(cl, 'rev-parse', 'HEAD') == base, out)
rc, out = run_away(c, cl, 'land', base, '--take', *FAST)
expect('D2 --take lands', rc == 0 and git(cl, 'rev-parse', 'HEAD') == tip, out)
shutil.rmtree(c['root'])

# D3. No claude/* branch yet → exit 4.
c, base = launched(); cl = c['clone']
rc, out = run_away(c, cl, 'land', base, *FAST)
expect('D3 exit 4', rc == 4 and 'no claude/* branch builds on' in out, out)
shutil.rmtree(c['root'])

# D4. Local .continuity/-only commit after base (the board marker) is replayed on top.
c, base = launched(); cl = c['clone']
write(f'{cl}/.continuity/feature-status.yml', 'settings:\n  push_to_default_branch: true\nfeatures:\n  a:\n    status: building\n    away: {session: x}\n')
git(cl, 'commit', '-qam', 'continuity: away marker'); marker = git(cl, 'rev-parse', 'HEAD')
tip = cloud_push(c, base, 'real', PARKED)
rc, out = run_away(c, cl, 'land', base, *FAST)
expect('D4 exit 0', rc == 0, out)
kept = subprocess.run([GIT, 'merge-base', '--is-ancestor', marker, 'HEAD'], cwd=cl).returncode == 0
expect('D4 marker keeps its SHA (continuity-save tracks it)', kept, git(cl, 'log', '--oneline', '-4'))
expect('D4 cloud work on top, parked last', git(cl, 'log', '-1', '--format=%s') == 'away: parked'
       and git(cl, 'show', 'HEAD:app.js') == 'cloud step 1', git(cl, 'log', '--oneline', '-4'))
shutil.rmtree(c['root'])

# D5. Local code commit after base → exit 5, nothing moved.
c, base = launched(); cl = c['clone']
write(f'{cl}/app.js', 'local edit\n'); git(cl, 'commit', '-qam', 'local code')
head = git(cl, 'rev-parse', 'HEAD')
cloud_push(c, base, 'real', PARKED)
rc, out = run_away(c, cl, 'land', base, *FAST)
expect('D5 exit 5', rc == 5 and out.startswith('DIVERGED') and 'local code' in out and 'step 1' in out, out)
expect('D5 HEAD unchanged', git(cl, 'rev-parse', 'HEAD') == head, out)
shutil.rmtree(c['root'])

# D6. Uncommitted tracked change → exit 5.
c, base = launched(); cl = c['clone']
cloud_push(c, base, 'real', PARKED)
write(f'{cl}/app.js', 'dirty\n')
rc, out = run_away(c, cl, 'land', base, *FAST)
expect('D6 exit 5', rc == 5 and 'uncommitted' in out, out)
shutil.rmtree(c['root'])

# D7. Cloud edited the board too → marker cherry-pick conflicts → exit 5, HEAD restored.
c, base = launched(); cl = c['clone']
write(f'{cl}/.continuity/feature-status.yml', 'features:\n  a:\n    status: LOCAL\n')
git(cl, 'commit', '-qam', 'continuity: away marker')
head = git(cl, 'rev-parse', 'HEAD')
cloud_push(c, base, 'real', [('.continuity/feature-status.yml', 'features:\n  a:\n    status: CLOUD\n', 'board'),
                             ('app.js', 'x\n', 'away: parked')])
rc, out = run_away(c, cl, 'land', base, *FAST)
expect('D7 exit 5', rc == 5 and 'conflict' in out.lower(), out)
expect('D7 HEAD restored', git(cl, 'rev-parse', 'HEAD') == head and git(cl, 'status', '--porcelain') == '', out)
shutil.rmtree(c['root'])

# D9. An option without its value → usage error, not a hang.
c, base = launched(); cl = c['clone']
rc, out = run_away(c, cl, 'land', base, '--timeout')
expect('D9 exit 3, no hang', rc == 3 and 'usage' in out, out)
shutil.rmtree(c['root'])

# D8 (Review Focus 3). Two descendants: the newer one wins.
c, base = launched(); cl = c['clone']
cloud_push(c, base, 'a-old', [('app.js', 'old\n', 'away: parked')], date='2026-01-01T00:00:00')
new = cloud_push(c, base, 'z-new', [('app.js', 'new\n', 'away: parked')], date='2026-06-01T00:00:00')
rc, out = run_away(c, cl, 'land', base, *FAST)
expect('D8 newest descendant wins', rc == 0 and git(cl, 'rev-parse', 'HEAD') == new, out)
shutil.rmtree(c['root'])

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
