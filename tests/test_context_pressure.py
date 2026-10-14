"""Scenario tests for the PostToolUse context-pressure hook. Run: python3 tests/test_context_pressure.py"""
import json, os, subprocess, sys, tempfile

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hooks')
fails = []
# the caller's own threshold or project must not leak into the scenarios
BASE_ENV = {k: v for k, v in os.environ.items() if k not in ('CONTINUITY_HANDOFF_PCT', 'CLAUDE_PROJECT_DIR')}


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
                       env=dict(BASE_ENV, CONTINUITY_CONTEXT_DIR=ctx, **env), capture_output=True, text=True)
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

# an unusable threshold falls back to 60 instead of switching the notice off
meter(ctx, 's10', 700_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': 's10', 'cwd': cwd}, CONTINUITY_HANDOFF_PCT='60%')
expect('bad CONTINUITY_HANDOFF_PCT falls back to 60', 'CONTEXT HANDOFF' in out and err == '', (rc, out, err))

# a compaction drops usage well below the threshold: the notice is armed again for the next climb
meter(ctx, 's11', 700_000, 1_000_000)
hook(ctx, {'session_id': 's11', 'cwd': cwd})
meter(ctx, 's11', 590_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': 's11', 'cwd': cwd})
meter(ctx, 's11', 700_000, 1_000_000)
rc, out2, err = hook(ctx, {'session_id': 's11', 'cwd': cwd})
expect('a dip just under the threshold does not re-arm', out == '' and out2 == '', (out, out2))
meter(ctx, 's11', 200_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': 's11', 'cwd': cwd})
meter(ctx, 's11', 650_000, 1_000_000)
rc, out2, err = hook(ctx, {'session_id': 's11', 'cwd': cwd})
expect('re-armed after usage falls below half the threshold', out == '' and 'CONTEXT HANDOFF' in out2, (out, out2))

# several tool calls in one turn run the hook at once: still one notice
meter(ctx, 's12', 700_000, 1_000_000)
procs = [subprocess.Popen(['bash', f'{HOOKS}/context-pressure.sh'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          text=True, env=dict(BASE_ENV, CONTINUITY_CONTEXT_DIR=ctx)) for _ in range(8)]
outs = [p.communicate(json.dumps({'session_id': 's12', 'cwd': cwd}))[0] for p in procs]
expect('one notice from 8 concurrent runs', sum('CONTEXT HANDOFF' in o for o in outs) == 1, outs)

# the session may have cd'd below the project root
sub = f'{cwd}/packages/api'; os.makedirs(sub)
subprocess.run(['git', 'init', '-q', cwd], check=True)
meter(ctx, 's13', 700_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': 's13', 'cwd': sub})
expect('fires from a subdirectory of the project', 'CONTEXT HANDOFF' in out, (rc, out, err))
meter(ctx, 's14', 700_000, 1_000_000)
rc, out, err = hook(ctx, {'session_id': 's14', 'cwd': '/'}, CLAUDE_PROJECT_DIR=cwd)
expect('fires when only CLAUDE_PROJECT_DIR names the project', 'CONTEXT HANDOFF' in out, (rc, out, err))

# a status line written in shell may quote its numbers
open(f'{ctx}/s15.json', 'w').write('{"used": "700000", "size": "1000000"}')
rc, out, err = hook(ctx, {'session_id': 's15', 'cwd': cwd})
expect('numeric strings in the meter file are read', 'CONTEXT HANDOFF' in out, (rc, out, err))

# session end clears this session's meter files and leaves other sessions' alone
rc, out, err = hook(ctx, {'session_id': 's1', 'cwd': cwd}, name='session-end.sh')
left = sorted(os.listdir(ctx))
expect('session end clears its own meter files', rc == 0 and 's1.json' not in left and 's1.told' not in left, left)
expect('session end leaves other sessions alone', 's2.json' in left and 's2.told' in left, left)

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
