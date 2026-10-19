"""Scenario tests for lib/continuity-review-oneshot. Run: python3 tests/test_review_oneshot.py
A stand-in `claude` (CONTINUITY_REVIEW_CLAUDE) answers from a script, so no tokens are spent."""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ONESHOT = os.path.join(ROOT, 'lib', 'continuity-review-oneshot')
fails = []


def expect(name, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + name)
    if not ok:
        fails.append(name)
        print('   ', str(detail)[:700])


GOOD = {'mode': 'routine', 'since': '2026-10-05', 'read': 'Quiet window.', 'chore_groups': [],
        'initiatives': [{'row': 'a', 'line': 'Moving.', 'recent': [], 'proposal': None, 'suggest': {'action': 'keep', 'reason': 'Live.'}}]}
BAD = dict(GOOD, mode='deep')
AUDIT = {'rows': [{'name': 'a', 'gated': []}]}


def stand_in(answers, wrap='array', error=False):
    """A `claude` that logs its arguments and stdin, then prints the next answer in Claude Code's JSON shape."""
    d = tempfile.mkdtemp()
    json.dump(answers, open(f'{d}/answers.json', 'w'))
    open(f'{d}/claude', 'w').write(f'''#!/usr/bin/env python3
import json, sys, os
d = {d!r}
n = len([f for f in os.listdir(d) if f.startswith('call')])
open(f'{{d}}/call{{n}}.args', 'w').write(json.dumps(sys.argv[1:]))
open(f'{{d}}/call{{n}}.stdin', 'w').write(sys.stdin.read())
answers = json.load(open(f'{{d}}/answers.json'))
text = answers[min(n, len(answers) - 1)]
result = {{"type": "result", "is_error": {error!r}, "result": text, "usage": {{"input_tokens": 10, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 0, "output_tokens": 500}}}}
print(json.dumps([{{"type": "system"}}, result] if {wrap!r} == 'array' else result))
''')
    os.chmod(f'{d}/claude', 0o755)
    return d


def run(answers, **kw):
    d = stand_in(answers, **kw)
    w = tempfile.mkdtemp()
    open(f'{w}/pack.md', 'w').write('# Review pack\nmode: routine\nPACK-MARKER\n')
    json.dump(AUDIT, open(f'{w}/audit.json', 'w'))
    env = dict(os.environ, CONTINUITY_REVIEW_CLAUDE=f'{d}/claude')
    r = subprocess.run([ONESHOT, f'{w}/pack.md', f'{w}/audit.json', f'{w}/out.json'], env=env, capture_output=True, text=True, timeout=60)
    calls = sorted(f for f in os.listdir(d) if f.endswith('.args'))
    info = {'rc': r.returncode, 'out': r.stdout + r.stderr, 'calls': len(calls),
            'args': [json.load(open(f'{d}/{c}')) for c in calls],
            'stdin': [open(f'{d}/{c[:-5]}.stdin').read() for c in calls],
            'review': json.load(open(f'{w}/out.json')) if os.path.exists(f'{w}/out.json') else None}
    shutil.rmtree(d); shutil.rmtree(w)
    return info


# O1. A good answer: one call, no tools, the brief as system prompt, the pack on stdin; output written; tokens reported.
i = run([json.dumps(GOOD)])
a = i['args'][0] if i['args'] else []
expect('O1 exit 0, one call', i['rc'] == 0 and i['calls'] == 1, i['out'])
expect('O1 tools off, settings and MCP skipped, JSON output', '--tools' in a and a[a.index('--tools') + 1] == '' and '--strict-mcp-config' in a and '--setting-sources' in a and 'json' in a, a)
expect('O1 brief as system prompt, pack on stdin', '--system-prompt' in a and 'Reviewer brief' in a[a.index('--system-prompt') + 1] and 'PACK-MARKER' in i['stdin'][0], (a[:6], i['stdin'][0][:200]))
expect('O1 review written', i['review'] == GOOD, i['review'])
expect('O1 tokens reported', '1510 in' in i['out'] or ('1010' in i['out'] and '500' in i['out']), i['out'])

# O2. A fenced answer in the single-object output shape is unwrapped.
i = run(['```json\n' + json.dumps(GOOD) + '\n```'], wrap='object')
expect('O2 fence stripped, object shape read', i['rc'] == 0 and i['review'] == GOOD, i['out'])

# O3. A malformed answer gets one retry carrying the checker's complaints.
i = run([json.dumps(BAD), json.dumps(GOOD)])
expect('O3 retried once, then OK', i['rc'] == 0 and i['calls'] == 2 and i['review'] == GOOD, i['out'])
expect('O3 retry names the problem', i['calls'] == 2 and 'mode' in i['stdin'][1] and 'continuity-review-check' in i['stdin'][1], i['stdin'][1:])

# O4. Still malformed after the retry: exit 1, the problems shown, the last answer kept for a look.
i = run([json.dumps(BAD), json.dumps(BAD)])
expect('O4 gives up after one retry', i['rc'] == 1 and i['calls'] == 2 and 'mode' in i['out'], i['out'])

# O5. Claude reports an error: exit 1, said plainly, no retry.
i = run(['Not logged in'], error=True)
expect('O5 an error from claude stops it', i['rc'] == 1 and i['calls'] == 1 and 'Not logged in' in i['out'], i['out'])

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
