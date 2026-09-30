"""Scenario tests for continuity-save: bare remote + clone + worktree.

Run: python3 tests/test_continuity_save.py   (GIT=/usr/bin/git to pin a git)
"""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE = os.path.join(ROOT, 'skills', 'wrap-up', 'continuity-save')
GIT = os.environ.get('GIT', shutil.which('git') or '/usr/bin/git')
ENV = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t',
           GIT_COMMITTER_EMAIL='t@t', PATH=os.environ.get('TEST_PATH', os.environ['PATH']))
fails = []


def sh(cwd, *args, check=True):
    r = subprocess.run(args, cwd=cwd, env=ENV, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f'{args} in {cwd}: {r.stdout}{r.stderr}')
    return r


def git(cwd, *a, check=True):
    return sh(cwd, GIT, *a, check=check).stdout.strip()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w').write(text)


def save(cwd, msg='continuity: test'):
    r = sh(cwd, SAVE, '-m', msg, check=False)
    return r.returncode, (r.stdout + r.stderr).strip()


def expect(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f'\n     {detail}'))
    if not cond:
        fails.append(name)


STATUS = 'settings:\n  push_to_default_branch: {push}\nlast_session:\n  date: 2026-09-25\n  summary: base\nfeatures:\n  a: 1\n'


def setup(push=True):
    root = tempfile.mkdtemp(prefix='cs-')
    remote = os.path.join(root, 'remote.git')
    git(root, 'init', '-q', '--bare', '-b', 'master', remote)
    clone = os.path.join(root, 'clone')
    git(root, 'clone', '-q', remote, clone)
    write(f'{clone}/.continuity/feature-status.yml', STATUS.format(push='true' if push else 'false'))
    write(f'{clone}/.gitignore', '.continuity/last-activity.txt\n')
    write(f'{clone}/app.js', 'v1\n')
    git(clone, 'add', '-A'); git(clone, 'commit', '-q', '-m', 'init'); git(clone, 'push', '-q', 'origin', 'master')
    git(clone, 'remote', 'set-head', 'origin', '-a')
    wt = os.path.join(root, 'wt')
    git(clone, 'worktree', 'add', '-q', '-b', 'feature', wt)
    return root, remote, clone, wt


def remote_file(clone, path):
    git(clone, 'fetch', '-q', 'origin')
    return git(clone, 'show', f'origin/master:{path}', check=False)


def remote_paths_changed(clone, since):
    return git(clone, 'diff', '--name-only', since, 'origin/master').splitlines()


# 1. Feature branch with an unmerged code commit: only .continuity lands on master.
root, remote, clone, wt = setup()
write(f'{wt}/app.js', 'v2-WIP\n'); git(wt, 'commit', '-qam', 'code wip')
write(f'{wt}/.continuity/feature-status.yml', STATUS.format(push='true').replace('summary: base', 'summary: s1'))
write(f'{wt}/.continuity/decisions/a.md', '# a\n')
write(f'{wt}/.continuity/last-activity.txt', 'transient\n')
write(f'{wt}/staged-other.txt', 'x\n'); git(wt, 'add', 'staged-other.txt')
before = git(clone, 'rev-parse', 'origin/master')
rc, out = save(wt)
expect('1 exit 0', rc == 0, out)
expect('1 summary landed on master', 'summary: s1' in remote_file(clone, '.continuity/feature-status.yml'), out)
expect('1 decisions file landed', remote_file(clone, '.continuity/decisions/a.md') == '# a', out)
expect('1 code NOT shipped', remote_file(clone, 'app.js') == 'v1', out)
chg = remote_paths_changed(clone, before)
expect('1 only .continuity changed on master', chg and all(p.startswith('.continuity/') for p in chg), chg)
expect('1 last-activity not committed', 'last-activity' not in git(wt, 'log', '-1', '--name-only'), out)
expect('1 other staged file left staged, uncommitted', 'staged-other.txt' in git(wt, 'diff', '--cached', '--name-only'), out)
expect('1 trailer present', 'Continuity-Source:' in git(clone, 'log', '-1', '--format=%B', 'origin/master'), out)
rc2, out2 = save(wt)
expect('1b rerun is a no-op', rc2 == 0 and 'nothing new' in out2, out2)
shutil.rmtree(root)

# 2. Master moved (another session's unrelated continuity + code) since the branch was cut.
root, remote, clone, wt = setup()
write(f'{clone}/.continuity/decisions/b.md', '# b from peer\n'); write(f'{clone}/app.js', 'v1-master\n')
git(clone, 'add', '-A'); git(clone, 'commit', '-qm', 'peer'); git(clone, 'push', '-q', 'origin', 'master')
write(f'{wt}/.continuity/decisions/a.md', '# a\n')
rc, out = save(wt)
expect('2 exit 0', rc == 0, out)
expect('2 peer file kept', remote_file(clone, '.continuity/decisions/b.md') == '# b from peer', out)
expect('2 ours landed', remote_file(clone, '.continuity/decisions/a.md') == '# a', out)
expect('2 master code untouched', remote_file(clone, 'app.js') == 'v1-master', out)
shutil.rmtree(root)

# 3. Conflict: both sides rewrote last_session.summary — nothing pushed, exit 2.
root, remote, clone, wt = setup()
write(f'{clone}/.continuity/feature-status.yml', STATUS.format(push='true').replace('summary: base', 'summary: PEER'))
git(clone, 'commit', '-qam', 'peer ls'); git(clone, 'push', '-q', 'origin', 'master')
head_before = git(clone, 'rev-parse', 'origin/master')
write(f'{wt}/.continuity/feature-status.yml', STATUS.format(push='true').replace('summary: base', 'summary: OURS'))
rc, out = save(wt)
expect('3 exit 2', rc == 2, out)
expect('3 CONFLICT reported', 'CONFLICT' in out, out)
git(clone, 'fetch', '-q', 'origin')
expect('3 master unchanged', git(clone, 'rev-parse', 'origin/master') == head_before, out)
expect('3 committed on branch', 'OURS' in git(wt, 'show', 'HEAD:.continuity/feature-status.yml'), out)
expect('3 worktree clean', git(wt, 'status', '--porcelain') == '', git(wt, 'status', '--porcelain'))
shutil.rmtree(root)

# 4. Setting absent/false: commit on branch, no push.
root, remote, clone, wt = setup(push=False)
write(f'{wt}/.continuity/decisions/a.md', '# a\n')
head_before = git(clone, 'rev-parse', 'origin/master')
rc, out = save(wt)
expect('4 exit 0', rc == 0, out)
expect('4 says branch only', 'SAVED ON BRANCH ONLY' in out, out)
git(clone, 'fetch', '-q', 'origin')
expect('4 master unchanged', git(clone, 'rev-parse', 'origin/master') == head_before, out)
shutil.rmtree(root)

# 5. On master itself, local master only has the continuity commit.
root, remote, clone, wt = setup()
write(f'{clone}/.continuity/decisions/m.md', '# m\n')
rc, out = save(clone)
expect('5 exit 0', rc == 0, out)
expect('5 landed', remote_file(clone, '.continuity/decisions/m.md') == '# m', out)
expect('5 local master == origin/master', git(clone, 'rev-parse', 'master') == git(clone, 'rev-parse', 'origin/master'), out)
shutil.rmtree(root)

# 6. No remote at all.
root = tempfile.mkdtemp(prefix='cs-')
git(root, 'init', '-q', '-b', 'master')
write(f'{root}/.continuity/feature-status.yml', STATUS.format(push='true'))
rc, out = save(root)
expect('6 exit 0 local only', rc == 0 and 'no origin remote' in out, out)
expect('6 committed', git(root, 'log', '--oneline') != '', out)
shutil.rmtree(root)

# 7. Mixed commit (code + continuity in one commit) is never pushed.
root, remote, clone, wt = setup()
write(f'{wt}/app.js', 'v2\n'); write(f'{wt}/.continuity/decisions/x.md', '# x\n')
git(wt, 'add', '-A'); git(wt, 'commit', '-qm', 'mixed')
head_before = git(clone, 'rev-parse', 'origin/master')
rc, out = save(wt)
expect('7 skipped note', 'skipped commits that mix code' in out, out)
git(clone, 'fetch', '-q', 'origin')
expect('7 master unchanged', git(clone, 'rev-parse', 'origin/master') == head_before, out)
shutil.rmtree(root)

# 8. away.md rides only on the branch: never committed by save, never landed.
root, remote, clone, wt = setup()
write(f'{wt}/.continuity/away.md', '<away>brief</away>\n')
write(f'{wt}/.continuity/decisions/a.md', '# a\n')
rc, out = save(wt)
expect('8 exit 0', rc == 0, out)
expect('8 decisions landed', remote_file(clone, '.continuity/decisions/a.md') == '# a', out)
expect('8 away.md not on master', remote_file(clone, '.continuity/away.md') == '', out)
expect('8 away.md left uncommitted', '?? .continuity/away.md' in git(wt, 'status', '--porcelain'), git(wt, 'status', '--porcelain'))
# 8b. a continuity-only commit that also touches away.md is treated as mixed: never landed
git(wt, 'add', '.continuity/away.md')
write(f'{wt}/.continuity/decisions/b.md', '# b\n'); git(wt, 'add', '.continuity/decisions/b.md')
git(wt, 'commit', '-qm', 'hand commit with away.md')
rc, out = save(wt)
expect('8b skipped as mixed', 'skipped commits that mix code' in out, out)
expect('8b away.md still not on master', remote_file(clone, '.continuity/away.md') == '', out)
shutil.rmtree(root)

# 9. --resolve grafts .continuity/ without away.md.
root, remote, clone, wt = setup()
write(f'{wt}/.continuity/away.md', '<away>brief</away>\n'); git(wt, 'add', '-f', '.continuity/away.md')
git(wt, 'commit', '-qm', 'wip(away): x')
write(f'{wt}/.continuity/decisions/r.md', '# r\n')
r = subprocess.run([SAVE, '--resolve', '-m', 'continuity: resolve'], cwd=wt, env=ENV, capture_output=True, text=True)
expect('9 resolve exit 0', r.returncode == 0, r.stdout + r.stderr)
expect('9 resolve landed decisions', remote_file(clone, '.continuity/decisions/r.md') == '# r', r.stdout)
expect('9 resolve left away.md off master', remote_file(clone, '.continuity/away.md') == '', r.stdout)
shutil.rmtree(root)

# 10. The PR-conflict case from trip-planner: the branch saved, then master's board
#     moved on. After the branch's next save it must match master, so a PR merges clean.
def pr_merges_clean(clone):
    git(clone, 'fetch', '-q', 'origin')
    r = subprocess.run([GIT, 'merge-tree', '--write-tree', 'origin/master', 'origin/feature'], cwd=clone, env=ENV, capture_output=True, text=True)
    return r.returncode == 0, r.stdout
root, remote, clone, wt = setup()
write(f'{wt}/app.js', 'feature code\n'); git(wt, 'commit', '-qam', 'feature code')
write(f'{wt}/.continuity/feature-status.yml', STATUS.format(push='true').replace('summary: base', 'summary: s1'))
rc, out = save(wt)
expect('10 first save landed', rc == 0 and 'landed' in out, out)
git(clone, 'pull', '-q', 'origin', 'master')
write(f'{clone}/.continuity/feature-status.yml', STATUS.format(push='true').replace('summary: base', 'summary: PEER'))
git(clone, 'commit', '-qam', 'peer moves the board'); git(clone, 'push', '-q', 'origin', 'master')
write(f'{wt}/.continuity/decisions/b.md', '# b\n')
rc, out = save(wt)
expect('10 second save exit 0', rc == 0, out)
git(wt, 'push', '-q', 'origin', 'feature')          # the user pushes the branch for a PR
ok, detail = pr_merges_clean(clone)
expect('10 PR merges clean after the save', ok, detail)
expect('10 branch .continuity == master .continuity',
       git(wt, 'rev-parse', 'HEAD:.continuity') == git(clone, 'rev-parse', 'origin/master:.continuity'), out)
expect('10 sync commit carries the trailer', 'Continuity-Sync:' in git(wt, 'log', '-1', '--format=%B'), git(wt, 'log', '-1', '--format=%B'))
expect('10 code untouched on master', remote_file(clone, 'app.js') == 'v1', out)
# 11. The sync commit is never landed again, nor flagged.
head_before = git(clone, 'rev-parse', 'origin/master')
rc, out = save(wt)
expect('11 rerun lands nothing new', rc == 0 and 'nothing new' in out, out)
git(clone, 'fetch', '-q', 'origin')
expect('11 master unchanged', git(clone, 'rev-parse', 'origin/master') == head_before, out)
r = subprocess.run(['bash', os.path.join(ROOT, 'hooks', 'worktree-remove.sh')], input='{"worktree_path": "%s"}' % wt, env=ENV, capture_output=True, text=True)
expect('11 worktree-remove allows', r.returncode == 0, r.stderr)
r = subprocess.run(['bash', os.path.join(ROOT, 'hooks', 'session-start.sh')], input='{"cwd": "%s"}' % clone, env=ENV, capture_output=True, text=True)
expect('11 session-start silent', r.stdout.strip() == '', r.stdout)
shutil.rmtree(root)

# 12. A skipped mixed commit blocks the sync, so its .continuity edits aren't dropped.
root, remote, clone, wt = setup()
write(f'{wt}/app.js', 'v2\n'); write(f'{wt}/.continuity/decisions/mixed.md', '# mixed\n')
git(wt, 'add', '-A'); git(wt, 'commit', '-qm', 'mixed')
write(f'{wt}/.continuity/decisions/c.md', '# c\n')
rc, out = save(wt)
expect('12 mixed file kept on branch', os.path.exists(f'{wt}/.continuity/decisions/mixed.md'), out)
expect('12 no sync commit on the branch', git(wt, 'log', '--grep=Continuity-Sync', '--format=%h', 'origin/master..HEAD') == '', out)
shutil.rmtree(root)

# 13. On the default branch itself there is nothing to sync.
root, remote, clone, wt = setup()
write(f'{clone}/.continuity/decisions/d.md', '# d\n')
rc, out = save(clone)
expect('13 no sync commit on master', rc == 0 and git(clone, 'log', '--grep=Continuity-Sync', '--format=%h') == '', out)
shutil.rmtree(root)

# 14. Merging origin/master into the branch (the usual PR fix) must not disable the sync.
root, remote, clone, wt = setup()
write(f'{wt}/.continuity/feature-status.yml', STATUS.format(push='true').replace('summary: base', 'summary: s1'))
rc, out = save(wt)
git(clone, 'pull', '-q', 'origin', 'master')
write(f'{clone}/.continuity/decisions/p.md', '# peer\n'); write(f'{clone}/lib.js', 'peer code\n')
git(clone, 'add', '-A'); git(clone, 'commit', '-qm', 'peer'); git(clone, 'push', '-q', 'origin', 'master')
write(f'{wt}/.continuity/decisions/f.md', '# f, committed but not yet landed\n'); git(wt, 'add', '-A'); git(wt, 'commit', '-qm', 'continuity: f')
git(wt, 'fetch', '-q', 'origin'); git(wt, 'merge', '-q', '--no-edit', 'origin/master')
write(f'{wt}/.continuity/decisions/e.md', '# e\n')
rc, out = save(wt)
expect('14 merge not reported as mixed', 'skipped commits' not in out, out)
expect('14 branch synced with master', git(wt, 'rev-parse', 'HEAD:.continuity') == git(wt, 'rev-parse', 'origin/master:.continuity'), out)
shutil.rmtree(root)

# 15. While /away's brief is on the branch, no sync (it would widen /back's replay).
root, remote, clone, wt = setup()
write(f'{wt}/.continuity/away.md', '<away/>\n'); git(wt, 'add', '-f', '.continuity/away.md'); git(wt, 'commit', '-qm', 'wip(away): x')
git(clone, 'pull', '-q', 'origin', 'master')
write(f'{clone}/.continuity/decisions/p.md', '# peer\n'); git(clone, 'add', '-A'); git(clone, 'commit', '-qm', 'peer'); git(clone, 'push', '-q', 'origin', 'master')
write(f'{wt}/.continuity/feature-status.yml', STATUS.format(push='true').replace('summary: base', 'summary: away'))
rc, out = save(wt)
expect('15 marker landed', rc == 0 and 'landed' in out, out)
expect('15 no sync while away', git(wt, 'log', '--grep=Continuity-Sync', '--format=%h', 'origin/master..HEAD') == '', out)
shutil.rmtree(root)

# 16. Moving a code file into .continuity/ is a code change: it must never land.
root, remote, clone, wt = setup()
git(wt, 'mv', 'app.js', '.continuity/app.js'); git(wt, 'commit', '-qm', 'move app.js into continuity')
write(f'{wt}/.continuity/decisions/r.md', '# r\n')
rc, out = save(wt)
expect('16 app.js still on master', remote_file(clone, 'app.js') == 'v1', out)
expect('16 the move was held back as mixed', 'skipped commits' in out, out)
shutil.rmtree(root)

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
