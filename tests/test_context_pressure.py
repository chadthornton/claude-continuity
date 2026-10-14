"""Scenario tests for the PostToolUse context-pressure hook. Run: python3 tests/test_context_pressure.py"""
import json, os, subprocess, sys, tempfile

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hooks')
fails = []


def expect(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f'\n     {detail}'))
    if not cond:
        fails.append(name)


def project(continuity=True):
    d = tempfile.mkdtemp()
    if continuity:
        os.makedirs(f'{d}/.continuity')
    return d


def meter(ctx, session, used, size):
    with open(f'{ctx}/{session}.json', 'w') as f:
        json.dump({'used': used, 'size': size}, f)


def hook(ctx, payload, name='context-pressure.sh', **env):
    r = subprocess.run(['bash', f'{HOOKS}/{name}'], input=json.dumps(payload),
                       env=dict(os.environ, CONTINUITY_CONTEXT_DIR=ctx, **env), capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


ctx = tempfile.mkdtemp()
cwd = project()

# below the threshold: silent, and nothing is marked as told
meter(ctx, 's1', 599_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': 's1', 'cwd': cwd})
expect('silent below 60%', rc == 0 and out == '', (rc, out, err))

# at the threshold: one notice, in the PostToolUse shape, naming the figures and the next move
meter(ctx, 's1', 600_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': 's1', 'cwd': cwd})
j = json.loads(out) if out else {}
msg = j.get('hookSpecificOutput', {}).get('additionalContext', '')
expect('fires at 60%', rc == 0 and j.get('hookSpecificOutput', {}).get('hookEventName') == 'PostToolUse'
       and msg.startswith('CONTEXT HANDOFF') and '60%' in msg and 'wrap-up' in msg, (rc, out, err))
expect('notice gives the measured figures', '600000' in msg and '1000000' in msg, msg)

# once per session, even as usage keeps climbing
meter(ctx, 's1', 800_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': 's1', 'cwd': cwd})
expect('silent after the first notice', rc == 0 and out == '', (rc, out, err))

# the threshold is a share of the model's own window, not a token count
meter(ctx, 's2', 120_000, 200_000)
rc, out, err = hook(ctx, {'session_id': 's2', 'cwd': cwd})
expect('fires at 60% of a 200K window', 'CONTEXT HANDOFF' in out, (rc, out, err))
meter(ctx, 's3', 120_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': 's3', 'cwd': cwd})
expect('silent at 12% of a 1M window', out == '', out)

# a subagent shares its parent's session id: it is not told, and it does not use up the parent's notice
meter(ctx, 's4', 700_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': 's4', 'cwd': cwd, 'agent_id': 'a1', 'agent_type': 'Explore'})
expect('silent in a subagent', rc == 0 and out == '', (rc, out, err))
rc, out, err = hook(ctx, {'session_id': 's4', 'cwd': cwd})
expect('parent still told after its subagent ran', 'CONTEXT HANDOFF' in out, (rc, out, err))

# nothing measured: stay silent rather than guess
rc, out, err = hook(ctx, {'session_id': 'never-metered', 'cwd': cwd})
expect('silent with no meter file', rc == 0 and out == '', (rc, out, err))
open(f'{ctx}/s5.json', 'w').write('not json')
rc, out, err = hook(ctx, {'session_id': 's5', 'cwd': cwd})
expect('silent on an unreadable meter file', rc == 0 and out == '', (rc, out, err))
meter(ctx, 's6', 700_000, 0)
rc, out, err = hook(ctx, {'session_id': 's6', 'cwd': cwd})
expect('silent when the window size is unknown', rc == 0 and out == '', (rc, out, err))
rc, out, err = hook(ctx, {'cwd': cwd})
expect('silent with no session id', rc == 0 and out == '', (rc, out, err))

# a session id is only ever used as a file name inside the meter directory
meter(ctx, 's7', 700_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': '../' + os.path.basename(ctx) + '/s7', 'cwd': cwd})
expect('silent on a session id with a path in it', rc == 0 and out == '', (rc, out, err))

# the notice sends the agent to wrap-up, so a project without a board gets none
meter(ctx, 's8', 700_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': 's8', 'cwd': project(continuity=False)})
expect('silent without .continuity', rc == 0 and out == '', (rc, out, err))

# the threshold can be moved
meter(ctx, 's9', 450_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': 's9', 'cwd': cwd}, CONTINUITY_HANDOFF_PCT='40')
expect('CONTINUITY_HANDOFF_PCT moves the threshold', 'CONTEXT HANDOFF' in out and '45%' in out, (rc, out, err))

# session end clears this session's meter files and leaves other sessions' alone
rc, out, err = hook(ctx, {'session_id': 's1', 'cwd': cwd}, name='session-end.sh')
left = sorted(os.listdir(ctx))
expect('session end clears its own meter files', rc == 0 and 's1.json' not in left and 's1.told' not in left, left)
expect('session end leaves other sessions alone', 's2.json' in left and 's2.told' in left, left)

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
