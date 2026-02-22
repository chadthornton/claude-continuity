---
name: plugin-doctor
description: Diagnose Claude Code plugin issues — loading failures, missing components, stale cache, hooks not firing. Use when a plugin isn't working as expected, components aren't discovered, or after making changes that don't take effect. Also use when user says "plugin not working", "skill not showing up", "hook not firing", "command missing", or "plugin debug".
---

# Plugin Doctor

Diagnose and fix Claude Code plugin issues using a structured decision tree and a self-improving known-issues database.

## Version

```yaml
version: 1.0.0
changelog:
  - 1.0.0: Initial release — 10 seed issues, 5-step diagnostic process
```

## Diagnostic Process

### Step 1: Identify the Symptom

Ask the user (or infer from context) which category their issue falls into:

1. **Plugin not loading at all** — installed but nothing works
2. **Components missing** — plugin loads but skills/commands/hooks/agents aren't discovered
3. **Hooks not firing** — hook is defined but never triggers
4. **Stale/outdated** — made changes but old behavior persists
5. **Other / not sure** — collect diagnostics first

### Step 2: Check Known Issues

Before investigating, scan the known issues database below for a match. If one matches, jump to its fix — don't re-derive the solution.

### Step 3: Branch Diagnosis

Follow the decision tree for the identified symptom category:

#### Plugin not loading at all

```
Installed via marketplace or --plugin-dir?
├── Marketplace install
│   ├── Check installed_plugins.json exists and has entry
│   ├── Check cache directory has content
│   └── Check plugin.json is valid JSON
└── --plugin-dir
    ├── Is the path absolute and valid?
    ├── Is plugin.json at {path}/.claude-plugin/plugin.json?
    └── Are you using outputStyle: compact? (known conflict)
```

Run:
```bash
cat ~/.claude/plugins/installed_plugins.json 2>/dev/null | python3 -m json.tool
ls -la {path}/.claude-plugin/ 2>/dev/null
```

#### Components missing (skills/commands/hooks/agents)

```
What type of component?
├── Skill not discovered
│   ├── Is it at skills/{name}/SKILL.md? (exact path required)
│   ├── Does SKILL.md have YAML frontmatter with name + description?
│   └── Are skills/ and .claude-plugin/ siblings? (not nested)
├── Command not discovered
│   ├── Is it at commands/{name}.md?
│   ├── Does it have YAML frontmatter with name + description?
│   └── Same sibling check as skills
├── Hook not discovered
│   ├── Is hooks.json at hooks/hooks.json?
│   ├── Is hooks.json valid JSON array?
│   └── Does each hook have type, matcher, and hooks fields?
└── Agent not discovered
    ├── Is it at agents/{name}.md?
    └── Does it have YAML frontmatter with name + description?
```

Run:
```bash
# Validate structure — commands/skills/hooks dirs must be siblings of .claude-plugin/
ls -la {path}/.claude-plugin/ {path}/commands/ {path}/skills/ {path}/hooks/ {path}/agents/ 2>/dev/null
```

#### Hooks not firing

```
Hook type?
├── Plugin hook (in hooks/hooks.json)
│   ├── Format: hooks.json wraps hooks inside { "hooks": [...] }
│   ├── Is the event type correct? (PreToolUse, PostToolUse, Stop, etc.)
│   └── Does the matcher pattern match the tool name?
└── Settings hook (in .claude/settings.json)
    ├── Format: settings.json uses direct hook objects, NOT wrapped
    └── Different structure than plugin hooks
```

Run:
```bash
cat {path}/hooks/hooks.json 2>/dev/null | python3 -m json.tool
```

#### Stale/outdated

```
How was the plugin installed?
├── Marketplace
│   ├── Cache may be stale — delete cache + reinstall
│   ├── Version bump in plugin.json alone doesn't refresh file content
│   └── Check gitCommitSha in installed_plugins.json vs current repo HEAD
└── --plugin-dir
    ├── Changes should be live after restart (no cache)
    └── Did you restart Claude Code? (required for all plugin changes)
```

Run:
```bash
# Check cache contents
ls -la ~/.claude/plugins/cache/ 2>/dev/null
# Check installed versions
cat ~/.claude/plugins/installed_plugins.json 2>/dev/null | python3 -m json.tool
```

### Step 4: Run Diagnostics

If the known issues and decision tree didn't resolve it, collect comprehensive diagnostics:

```bash
# Installation state
cat ~/.claude/plugins/installed_plugins.json 2>/dev/null | python3 -m json.tool

# Marketplace registry
cat ~/.claude/plugins/known_marketplaces.json 2>/dev/null | python3 -m json.tool

# Plugin structure validation
ls -la {path}/.claude-plugin/
ls -la {path}/commands/ {path}/skills/ {path}/hooks/ {path}/agents/ 2>/dev/null

# Path portability check — absolute paths break when shared
grep -rn '/Users/\|/home/' {path}/ --include='*.md' --include='*.json' --include='*.sh' 2>/dev/null

# Hook format check
cat {path}/hooks/hooks.json 2>/dev/null | python3 -m json.tool
```

Present findings and suggest fixes.

### Step 5: Resolution

After identifying the issue:

1. Explain what went wrong and why
2. Provide the specific fix (commands to run or files to edit)
3. Remind the user to **restart Claude Code** — all plugin changes require a restart
4. If this was a new issue not in the database, note it for future reference

---

## Known Issues Database

```yaml
issues:
  - id: stale-plugin-cache
    symptoms:
      - Plugin changes not reflected after marketplace reinstall
      - Old skill/command content persists
      - Version bump acknowledged but files unchanged
    cause: >
      Marketplace cache (~/.claude/plugins/cache/) doesn't auto-refresh
      when source repo files change. Version bump in plugin.json updates
      metadata but cached file content may be stale.
    fix: >
      Delete the plugin's cache directory and reinstall:
      rm -rf ~/.claude/plugins/cache/{marketplace}/{plugin}/
      Then reinstall from marketplace and restart Claude Code.
    severity: common

  - id: plugin-dir-print-mode-conflict
    symptoms:
      - --plugin-dir flag causes immediate exit or no output
      - Plugin works in normal mode but fails with --print or -p flag
      - "outputStyle: compact" in settings breaks --plugin-dir
    cause: >
      The --plugin-dir flag conflicts with outputStyle settings,
      particularly "compact" mode. This is a known Claude Code bug.
    fix: >
      Remove or change outputStyle in ~/.claude/settings.json before
      using --plugin-dir. Or use marketplace install instead.
    severity: moderate

  - id: manifest-wrong-location
    symptoms:
      - Plugin not recognized despite having plugin.json
      - "Not a valid plugin" errors
    cause: >
      plugin.json must be at {root}/.claude-plugin/plugin.json,
      not at {root}/plugin.json. The .claude-plugin/ directory is
      the plugin manifest directory.
    fix: >
      Move plugin.json into .claude-plugin/:
      mkdir -p .claude-plugin && mv plugin.json .claude-plugin/
    severity: common

  - id: components-inside-claude-plugin
    symptoms:
      - Plugin loads but no skills/commands/hooks discovered
      - Structure looks correct but nothing works
    cause: >
      Component directories (commands/, skills/, hooks/, agents/)
      must be siblings of .claude-plugin/, not inside it.
    fix: |
      Correct structure:
        my-plugin/
        ├── .claude-plugin/
        │   └── plugin.json
        ├── commands/
        ├── skills/
        ├── hooks/
        └── agents/

      Wrong structure:
        my-plugin/
        └── .claude-plugin/
            ├── plugin.json
            ├── commands/    <-- wrong!
            └── skills/      <-- wrong!
    severity: common

  - id: hook-format-mismatch
    symptoms:
      - Hook defined but never fires
      - Hook works in settings.json but not in plugin
      - "hooks" field missing or malformed
    cause: >
      Plugin hooks (hooks/hooks.json) use a wrapped format with a
      top-level "hooks" array. Settings hooks (.claude/settings.json)
      use a different direct format. Mixing formats causes silent failure.
    fix: |
      Plugin hooks/hooks.json format:
      {
        "hooks": [
          {
            "type": "PreToolUse",
            "matcher": "Bash",
            "hooks": [
              { "type": "command", "command": "echo check" }
            ]
          }
        ]
      }
    severity: moderate

  - id: skill-not-discovered
    symptoms:
      - Skill doesn't appear in available skills list
      - /skill-name doesn't trigger
      - SKILL.md exists but isn't found
    cause: >
      Skills must be at skills/{name}/SKILL.md with YAML frontmatter
      containing at minimum 'name' and 'description'. The directory
      name should match the skill name. Missing frontmatter or wrong
      path causes silent non-discovery.
    fix: >
      Verify: skills/{name}/SKILL.md exists, has --- delimited YAML
      frontmatter with 'name' and 'description' fields. Restart
      Claude Code after fixing.
    severity: common

  - id: local-marketplace-version-pin
    symptoms:
      - Reinstalled plugin but content unchanged
      - Version bumped but old files served
      - installed_plugins.json shows new version but behavior is old
    cause: >
      Local marketplace reinstall picks up version from plugin.json
      but may serve cached file content. The gitCommitSha in
      installed_plugins.json may not match the current repo HEAD.
    fix: >
      1. Delete cache: rm -rf ~/.claude/plugins/cache/{marketplace}/{plugin}/
      2. Uninstall: remove entry from installed_plugins.json
      3. Reinstall from marketplace
      4. Restart Claude Code
    severity: moderate

  - id: plugin-dir-not-persisted
    symptoms:
      - Plugin works in one session but gone in the next
      - --plugin-dir must be re-specified each time
    cause: >
      The --plugin-dir flag only loads the plugin for the current
      session. It is not persisted across sessions. Use marketplace
      install for persistent plugins.
    fix: >
      For persistent installation, publish to a local marketplace
      or use the marketplace install flow. --plugin-dir is for
      development and testing only.
    severity: low

  - id: hardcoded-paths
    symptoms:
      - Plugin works on one machine but not another
      - Paths break when project moves
      - Errors referencing /Users/username/... or /home/username/...
    cause: >
      Absolute paths in plugin files break portability. Use
      ${CLAUDE_PLUGIN_ROOT} variable which resolves to the plugin's
      root directory at runtime.
    fix: >
      Replace absolute paths with ${CLAUDE_PLUGIN_ROOT}:
      Bad:  /Users/me/plugins/my-plugin/templates/foo.yml
      Good: ${CLAUDE_PLUGIN_ROOT}/templates/foo.yml
    severity: moderate

  - id: no-hot-reload
    symptoms:
      - Changed a file but behavior hasn't updated
      - Edited SKILL.md but old description shows
      - Updated hooks.json but old hook runs
    cause: >
      Claude Code does not hot-reload plugin files. All changes to
      plugin components (skills, commands, hooks, agents, plugin.json)
      require restarting Claude Code to take effect.
    fix: >
      Restart Claude Code after any plugin file change.
      For rapid iteration during development, use --plugin-dir
      (still requires restart, but avoids cache issues).
    severity: common
```

## Guidelines

- **Check known issues first.** Most plugin problems are repeats of known issues. Don't re-derive what's already documented.
- **Always end with "restart Claude Code."** It's the most common missed step.
- **Collect before concluding.** Run the diagnostic commands to confirm your hypothesis before declaring a fix.
- **Be specific about paths.** "Check the plugin directory" is vague. "Check {path}/.claude-plugin/plugin.json" is actionable.
- **This database is self-improving.** If you diagnose a new issue not listed above, tell the user it would be valuable to add it to the known issues database for future sessions.
