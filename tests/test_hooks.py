"""Scenario tests for the SessionStart and WorktreeRemove hooks. Run: python3 tests/test_hooks.py"""
import json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hooks')
# reuse helpers without running the save scenarios
_save_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_continuity_save.py')
src = open(_save_py).read().split('# 1. Feature branch')[0]
ns = {'__file__': _save_py}
exec(src, ns)
git, write, save, setup, expect, ENV, fails = ns['git'], ns['write'], ns['save'], ns['setup'], ns['expect'], ns['ENV'], ns['fails']


def hook(name, payload):
    r = subprocess.run(['bash', f'{HOOKS}/{name}'], input=json.dumps(payload), env=ENV,
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


# session-start: no .continuity → init notice in hookSpecificOutput
import tempfile
bare = tempfile.mkdtemp()
rc, out, err = hook('session-start.sh', {'cwd': bare})
j = json.loads(out)
expect('ss init notice shape', j['hookSpecificOutput']['hookEventName'] == 'SessionStart'
       and 'continuity-init' in j['hookSpecificOutput']['additionalContext'], out)

# conflict leaves an unlanded continuity commit on 'feature'
root, remote, clone, wt = setup()
write(f'{clone}/.continuity/feature-status.yml', ns['STATUS'].format(push='true').replace('summary: base', 'summary: PEER'))
git(clone, 'commit', '-qam', 'peer'); git(clone, 'push', '-q', 'origin', 'master')
write(f'{wt}/.continuity/feature-status.yml', ns['STATUS'].format(push='true').replace('summary: base', 'summary: OURS'))
rc, out = save(wt)
expect('setup conflict', rc == 2, out)
git(clone, 'fetch', '-q', 'origin')
rc, out, err = hook('session-start.sh', {'cwd': clone})
expect('ss flags stranded from main checkout', 'CONTINUITY NOT LANDED: 1' in out and 'feature' in out, out + err)
rc, out, err = hook('worktree-remove.sh', {'worktree_path': wt, 'cwd': wt})
expect('wr blocks unlanded commit', rc == 2 and 'not on origin/master' in err, (rc, err))

# resolve: take master's version + re-apply ours by hand, save again
git(wt, 'fetch', '-q', 'origin')
git(wt, 'restore', '--source=origin/master', '--', '.continuity')
write(f'{wt}/.continuity/feature-status.yml', ns['STATUS'].format(push='true').replace('summary: base', 'summary: MERGED'))
r = subprocess.run([ns['SAVE'], '--resolve', '-m', 'continuity: resolve'], cwd=wt, env=ENV, capture_output=True, text=True)
out = r.stdout + r.stderr
expect('resolve exit 0', r.returncode == 0, out)
expect('resolve landed merged content', 'summary: MERGED' in ns['remote_file'](clone, '.continuity/feature-status.yml'), out)
expect('resolve kept code off master', ns['remote_file'](clone, 'app.js') == 'v1', out)
r2 = subprocess.run([ns['SAVE']], cwd=wt, env=ENV, capture_output=True, text=True)
expect('after resolve, plain save is a no-op', r2.returncode == 0 and 'nothing new' in r2.stdout, r2.stdout)
rc, out2, err = hook('session-start.sh', {'cwd': clone})
expect('ss silent after resolve', out2 == '', out2)
rc, out2, err = hook('worktree-remove.sh', {'worktree_path': wt})
expect('wr allows after resolve', rc == 0, err)

# dirty .continuity blocks removal
root2, _, clone2, wt2 = setup()
write(f'{wt2}/.continuity/decisions/z.md', '# z\n')
rc, out, err = hook('worktree-remove.sh', {'worktree_path': wt2})
expect('wr blocks dirty', rc == 2 and 'uncommitted' in err, (rc, err))
write(f'{wt2}/.continuity/last-activity.txt', 'x')
os.remove(f'{wt2}/.continuity/decisions/z.md')
rc, out, err = hook('worktree-remove.sh', {'worktree_path': wt2})
expect('wr allows clean (last-activity ignored)', rc == 0, (rc, err))
rc, out, err = hook('session-start.sh', {'cwd': clone2})
expect('ss silent when nothing stranded', out == '', out)

# landed commit is not flagged
write(f'{wt2}/.continuity/decisions/y.md', '# y\n')
rc, o = save(wt2)
rc, out, err = hook('session-start.sh', {'cwd': clone2})
expect('ss silent after landing (trailer match)', out == '', out)
rc, out, err = hook('worktree-remove.sh', {'worktree_path': wt2})
expect('wr allows after landing', rc == 0, (rc, err))

# away.md is branch content, not continuity state: neither hook reports it
root3, _, clone3, wt3 = setup()
write(f'{wt3}/.continuity/away.md', '<away>brief</away>\n')
rc, out, err = hook('worktree-remove.sh', {'worktree_path': wt3})
expect('wr ignores uncommitted away.md', rc == 0, (rc, err))
git(wt3, 'add', '-f', '.continuity/away.md'); git(wt3, 'commit', '-qm', 'wip(away): x')
rc, out, err = hook('worktree-remove.sh', {'worktree_path': wt3})
expect('wr ignores committed away.md', rc == 0, (rc, err))
rc, out, err = hook('session-start.sh', {'cwd': clone3})
expect('ss ignores away.md commits', out == '', out)

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
