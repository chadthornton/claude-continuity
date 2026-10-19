"""Scenario tests for lib/continuity-review-pack. Run: python3 tests/test_review_pack.py"""
import os, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, 'lib', 'continuity-review-pack')
_audit_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_continuity_audit.py')
ns = {'__file__': _audit_py}
exec(open(_audit_py).read().split('BOARD = ')[0], ns)
write, expect, ENV, fails, repo, commit, fake_gh = ns['write'], ns['expect'], ns['ENV'], ns['fails'], ns['repo'], ns['commit'], ns['fake_gh']

DAY = 86400
NOW = int(time.time())


def pack(cwd, *args, **env):
    e = dict(ENV); e.setdefault('CONTINUITY_AUDIT_WT', 'false'); e.update(env)
    r = subprocess.run([PACK] + list(args), cwd=cwd, env=e, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout + r.stderr


def section(out, title):
    """Text under '## title' up to the next '## ' heading."""
    lines, on = [], False
    for ln in out.splitlines():
        if ln.startswith('## '):
            on = ln[3:].startswith(title)
            continue
        if on:
            lines.append(ln)
    return '\n'.join(lines)


BOARD = '''settings:
  product_doc: docs/bets.md
features:
  busy:
    status: building
    next: "Ship the busy thing"
    next_steps:
      - { step: "Busy step one, see PR #7", done: false }
      - { step: "Busy step two", gate: approval, done: false }
      - { step: "Busy finished step", done: true }
      - step: "Busy finished block step"
        done: true
  quiet:
    status: polishing
    next: "Nothing much"
    next_steps:
      - { step: "Quiet step text", done: false }
gotchas:
  - "Never log.error in the worker: it emails the owner"
'''
DECISIONS = '''# busy
## Decided
- Decided thing that stays out of the pack
## Ruled out
- Tried the slow way
## Open
- [decision] Which carrier?
'''

d = repo(BOARD, files={'.continuity/decisions/busy.md': DECISIONS, '.continuity/handoffs/busy.md': '<handoff><stops>- The jscpd check needs Chad to say ship it</stops></handoff>\n', '.continuity/handoffs/quiet.md': 'quiet handoff text\n', 'docs/bets.md': '# Bets\nLead with the morning-of moment.\n'}, when=NOW - 40 * DAY)
p = f'{d}/.continuity/feature-status.yml'
write(p, open(p).read().replace('Busy step one', 'Busy step one, now with detail', 1))
commit(d, 'busy: add detail to step one', NOW - 2 * DAY)
write(f'{d}/app.js', 'code\n'); commit(d, 'feat: real code change', NOW - 2 * DAY)
ghdir, gh = fake_gh("echo '[{\"number\":7,\"title\":\"Busy thing lands\",\"mergedAt\":\"%s\"}]'" %
                    time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(NOW - 1 * DAY)))

# K1. Routine pack: the audit, moved initiatives in full with their open decisions, quiet ones as one line,
#     gotchas, commits and merged PRs in the window.
rc, out = pack(d, CONTINUITY_AUDIT_GH=gh)
expect('K1 exit 0', rc == 0, out[:600])
expect('K1 header names mode and window', 'mode: routine' in out and 'since: ' in out, out[:400])
expect('K1 audit JSON included', '"rows"' in section(out, 'Audit'), section(out, 'Audit')[:300])
moved = section(out, 'Moved')
expect('K1 moved initiative in full', 'Busy step one, now with detail' in moved and 'Busy step two' in moved, moved[:600])
expect('K1 its open questions and dead ends, not its decided list',
       'Which carrier?' in moved and 'Tried the slow way' in moved and 'Decided thing' not in moved, moved[:800])
quiet = section(out, 'Quiet')
expect('K1 quiet initiative as one line, steps left out', 'quiet' in quiet and 'Quiet step text' not in out, quiet)
expect('K1 gotchas in full', 'emails the owner' in section(out, 'Gotchas'), section(out, 'Gotchas'))
expect('K1 merged PRs with titles', '#7' in section(out, 'Merged') and 'Busy thing lands' in section(out, 'Merged'), section(out, 'Merged'))
expect('K1 moved initiative carries its handoff', 'needs Chad to say ship it' in moved, moved[:900])
expect('K1 a quiet initiative handoff stays out', 'quiet handoff text' not in out, '')
expect('K1 finished steps left out and counted', 'Busy finished' not in moved and '2 finished steps left out' in moved, moved[:800])
expect('K1 commits list code changes, not board saves', 'feat: real code change' in section(out, 'Commits') and 'busy: add detail' not in section(out, 'Commits'), section(out, 'Commits'))
expect('K1 commit total stated', '1 code commit in the window' in section(out, 'Commits'), section(out, 'Commits'))
expect('K1 audit section leaves out gotcha entries', '"entries"' not in section(out, 'Audit'), '')
expect('K1 routine leaves out the product document', 'Lead with the morning-of moment' not in out, '')

# K2. Full pack adds the product document and every initiative in full.
rc, out = pack(d, '--full', CONTINUITY_AUDIT_GH=gh)
expect('K2 full: product document included', rc == 0 and 'Lead with the morning-of moment' in section(out, 'Product document'), out[:400])
expect('K2 full: quiet initiative in full too', 'Quiet step text' in out, '')
expect('K2 full keeps finished steps', 'Busy finished step' in out and 'Busy finished block step' in out, '')
expect('K2 header says full', 'mode: full' in out, out[:300])

# K5. --notes prints the reader's notes from the page; a row gone from the board says so; no file prints none.
nf = f'{d}/../overrides.json'
write(nf, '{"busy": {"notes": "Carrier first\\nthen ship", "size": "L"}, "quiet": {"size": "S"}, "gone": {"notes": "old"}}')
rc, out = pack(d, '--notes', nf, CONTINUITY_AUDIT_GH=gh)
notes = section(out, 'Your notes')
expect('K5 note on its row, one line', rc == 0 and '- busy: Carrier first / then ship' in notes, notes)
expect('K5 a row without a note stays out', 'quiet' not in notes, notes)
expect('K5 a note on a row gone from the board is marked', '- gone (not on the board): old' in notes, notes)
rc, out = pack(d, '--full', '--notes', nf, CONTINUITY_AUDIT_GH=gh)
expect('K5 --notes works beside --full', 'mode: full' in out and 'Carrier first' in section(out, 'Your notes'), out[:300])
rc, out = pack(d, CONTINUITY_AUDIT_GH=gh)
expect('K5 no notes file: none', section(out, 'Your notes').strip() == '(none)', section(out, 'Your notes'))
os.remove(nf)

# K6. An overrides entry that isn't a document is skipped; the other notes still print.
write(nf, '{"x": "str", "busy": {"notes": "Ask Sam"}}')
rc, out = pack(d, '--notes', nf, CONTINUITY_AUDIT_GH=gh)
expect('K6 non-document entry skipped, notes still printed', '- busy: Ask Sam' in section(out, 'Your notes'), section(out, 'Your notes'))
os.remove(nf)

# K3. Without gh the PR section says so; the rest is still there.
rc, out = pack(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('K3 no gh: says unavailable, exit 0', rc == 0 and 'unavailable' in section(out, 'Merged'), section(out, 'Merged'))
expect('K3 no gh: moved initiative still found from board edits', 'Busy step two' in section(out, 'Moved'), section(out, 'Moved')[:300])

# K4. A product document the board names but that is missing is reported, not guessed.
os.remove(f'{d}/docs/bets.md')
rc, out = pack(d, '--full', CONTINUITY_AUDIT_GH=gh)
expect('K4 missing product document reported', rc == 0 and 'missing' in section(out, 'Product document'), section(out, 'Product document'))
# F3. A worktree that ended on a row does not make it "moved".
wtdir, wt = fake_gh(r"""printf 'repo\tpath\tname\tverdict\tstate\tuncommitted\tunpushed\tbranch\tlock_pid\tactivity\n'
printf '/r\t/r/w/quiet-1\tquiet-1\tsafe\tended\t0\t0\tb\t\tidle (replied)\n'""")
rc, out = pack(d, CONTINUITY_AUDIT_GH=gh, CONTINUITY_AUDIT_WT=wt)
expect('F3 pack: ended session leaves its row quiet', 'Quiet step text' not in section(out, 'Moved') and '- quiet' in section(out, 'Quiet'), section(out, 'Moved')[:300])
shutil.rmtree(wtdir)
shutil.rmtree(d); shutil.rmtree(ghdir)

# F7. The window starts at midnight UTC on the review date: a code commit one minute after
#     midnight that day is in it, whatever time the pack runs.
import calendar
day = time.strftime('%Y-%m-%d', time.gmtime(NOW - 3 * DAY))
d = repo('settings:\n  last_review: ' + day + '\nfeatures:\n  a:\n    status: building\n', when=NOW - 40 * DAY)
write(f'{d}/app.js', 'x\n'); commit(d, 'feat: just after midnight', calendar.timegm(time.strptime(day + ' 00:01', '%Y-%m-%d %H:%M')))
rc, out = pack(d, CONTINUITY_AUDIT_GH='no-such-gh-binary')
expect('F7 commit just after midnight on the review date is in the window', 'just after midnight' in section(out, 'Commits'), section(out, 'Commits'))
shutil.rmtree(d)

print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
