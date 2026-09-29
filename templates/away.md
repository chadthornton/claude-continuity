<away>
<task>{what we're doing, one line}</task>
<in-flight>{what was mid-way when the user left: the half-done edit, the command about to run}</in-flight>
<next>{the exact next action, with file paths and the command to run}</next>
<decided>
- {decision} — {why}
</decided>
<stops>
- {each gated step, and anything needing the user}
- Secrets and local-only files (.env, data not in git) are not in the cloud. If a step needs them, stop and say so in <status>; don't work around it.
</stops>
<protocol>You are continuing this task in a cloud session; the user is away. Work on the branch you were given. Commit and push after each step. Don't edit anything under .continuity/ except this file. When you finish, get stuck, or are told to stop: rewrite <status> and <next> below, then make a final commit titled "away: parked" and push.</protocol>
<status>Not started.</status>
</away>
