"""Unit tests for lib/continuity-commits.sh — the shared rules for which commits
are continuity state. Run: python3 tests/test_continuity_lib.py"""
import os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, 'lib', 'continuity-commits.sh')
_save_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_continuity_save.py')
ns = {'__file__': _save_py}
exec(open(_save_py).read().split('# 1. Feature branch')[0], ns)
git, write, setup, expect, ENV, fails = ns['git'], ns['write'], ns['setup'], ns['expect'], ns['ENV'], ns['fails']


def lib(cwd, call):
    r = subprocess.run(['bash', '-c', f'. "{LIB}" && {call}'], cwd=cwd, env=ENV, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def commit(cwd, msg, files, trailer=None):
    for path, text in files.items():
        write(f'{cwd}/{path}', text)
    git(cwd, 'add', '-A', '-f', *files.keys())
    args = ['commit', '-qm', msg] + (['-m', trailer] if trailer else [])
    git(cwd, *args)
    return git(cwd, 'rev-parse', 'HEAD')


# ── cc_scan: one line per commit in the range, oldest first ─────────────────
root, remote, clone, wt = setup()
landed = commit(wt, 'continuity: landed', {'.continuity/decisions/l.md': 'l\n'})
commit(clone, 'continuity: landed (on master)', {'.continuity/decisions/l.md': 'l\n'}, f'Continuity-Source: {landed}')
git(clone, 'push', '-q', 'origin', 'master')
pending = commit(wt, 'continuity: a', {'.continuity/decisions/a.md': 'a\n'})
mixed = commit(wt, 'code + continuity', {'app.js': 'v2\n', '.continuity/decisions/m.md': 'm\n'})
awaymix = commit(wt, 'away + board', {'.continuity/away.md': 'b\n', '.continuity/decisions/w.md': 'w\n'})
awayonly = commit(wt, 'wip(away): brief only', {'.continuity/away.md': 'b2\n'})
sync = commit(wt, 'continuity: sync', {'.continuity/decisions/s.md': 's\n'}, 'Continuity-Sync: 0123abc')
commit(clone, 'peer board', {'.continuity/decisions/p.md': 'p\n'}); git(clone, 'push', '-q', 'origin', 'master')
git(wt, 'fetch', '-q', 'origin'); git(wt, 'merge', '-q', '--no-edit', 'origin/master')
merge = git(wt, 'rev-parse', 'HEAD')
code = commit(wt, 'code only', {'app.js': 'v3\n'})

rc, out, err = lib(wt, 'cc_scan origin/master origin/master..HEAD')
rows = dict(line.split() for line in out.splitlines())
expect('scan exit 0', rc == 0, err)
expect('landed', rows.get(landed) == 'landed', out)
expect('pending', rows.get(pending) == 'pending', out)
expect('mixed: code + continuity', rows.get(mixed) == 'mixed', out)
expect('mixed: away.md + board', rows.get(awaymix) == 'mixed', out)
expect('away.md alone is not continuity', awayonly not in rows, out)
expect('sync', rows.get(sync) == 'sync', out)
expect('merge', rows.get(merge) == 'merge', out)
expect('code-only commit not listed', code not in rows, out)
expect('oldest first', out.splitlines()[0].startswith(landed), out)
# rev-list options pass through (session-start uses --branches --not <ref>)
rc, out2, err = lib(wt, 'cc_scan origin/master --branches --not origin/master')
expect('rev-list options pass through', pending in out2 and landed in out2, (out2, err))
# cc_pending: just the SHAs continuity-save should land
rc, out3, err = lib(wt, 'cc_pending origin/master origin/master..HEAD')
expect('cc_pending lists pending only', out3.split() == [pending], out3)
shutil.rmtree(root)

# ── cc_default_ref ───────────────────────────────────────────────────────────
root, remote, clone, wt = setup()
rc, out, err = lib(clone, 'cc_default_ref')
expect('default ref from origin/HEAD', out == 'origin/master', out)
git(clone, 'remote', 'set-head', 'origin', '-d')
rc, out, err = lib(clone, 'cc_default_ref')
expect('default ref falls back to origin/master', out == 'origin/master', out)
git(clone, 'branch', '-m', 'master', 'develop'); git(clone, 'push', '-q', 'origin', 'develop')
git(remote, 'symbolic-ref', 'HEAD', 'refs/heads/develop'); git(clone, 'push', '-q', 'origin', '--delete', 'master')
git(clone, 'config', 'remote.origin.followRemoteHEAD', 'never')   # git ≥2.48 re-creates origin/HEAD on fetch
git(clone, 'remote', 'set-head', 'origin', '-d')
git(clone, 'fetch', '-q', '--prune', 'origin')
rc, out, err = lib(clone, 'cc_default_ref')
expect('unknown default → empty, exit 1', out == '' and rc == 1, (rc, out))
shutil.rmtree(root)

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
