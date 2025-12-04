---
title: Erk Hooks
read_when:
  - "working with erk-specific hooks"
  - "understanding context-aware reminders"
  - "modifying project hooks"
---

# Claude Code Hooks in erk

Project-specific guide for using Claude Code hooks in the erk repository.

**General Claude Code hooks reference**: [hooks.md](hooks.md) (in same directory)

## How Hooks Work in This Project

This project uses **dot-agent-kit** to manage Claude Code hooks. This provides:

- **Kit-based organization**: Hooks bundled with related skills, commands, and agents
- **Atomic installation**: Install/remove entire kit including hooks
- **Metadata tracking**: Track hook sources in `dot-agent.toml`
- **Version control**: Hooks are code artifacts in the repository

**Architecture**:

```
packages/dot-agent-kit/src/dot_agent_kit/data/kits/{kit-name}/
├── kit_cli_commands/        # Hook implementation scripts
│   └── {kit-name}/
│       └── {hook_name}.py   # Python script with Click command
├── kit.yaml                 # MUST register hook in TWO places:
│   ├── kit_cli_commands:    # 1. Register script as CLI command
│   └── hooks:               # 2. Register hook lifecycle/matcher
```

**Installation flow**:

1. `dot-agent kit install {kit-name}` reads `kit.yaml`
2. Writes hook configuration to `.claude/settings.json`
3. Tracks installation in `dot-agent.toml` metadata
4. Claude Code reads `.claude/settings.json` at startup
5. Hook fires when lifecycle event + matcher conditions met

**Key difference from native Claude Code hooks**:

- **Native**: Manually edit `.claude/settings.json`, full control over all features
- **dot-agent-kit**: Use kit commands, hooks bundled with related artifacts, currently command-based only

**Related documentation**:

- Kit system overview: `.agent/kits/README.md`
- Technical implementation: `packages/dot-agent-kit/docs/HOOKS.md`

## Current Hooks

This repository includes 4 hooks:

### 1. devrun-reminder-hook

**Matcher**: `*` (all events)

**Purpose**: Remind agents to use devrun agent instead of direct Bash for development tools

**Output**:

```
🔴 CRITICAL: For pytest/pyright/ruff/prettier/make/gt → MUST use devrun agent
(Task tool with subagent_type="devrun"), NOT direct Bash

This includes uv run variants: uv run pytest, uv run pyright, uv run ruff, etc.

WHY: Specialized parsing & cost efficiency
```

**Why**: Development tools have complex output that devrun agent parses efficiently, reducing token costs and improving error handling.

**Location**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/devrun/`

### 2. dignified-python-reminder-hook

**Matcher**: `*.py` (Python files)

**Purpose**: Remind agents to load dignified-python skill before editing Python code

**Output**:

```
🔴 CRITICAL: LOAD dignified-python skill NOW before editing Python

WHY: Ensures LBYL compliance, Python 3.13+ types, ABC interfaces
NOTE: Checklist rules are EXCERPTS - skill contains complete philosophy & rationale
```

**Why**: Ensures Python code follows project coding standards (LBYL exception handling, modern type syntax, ABC interfaces).

**Location**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/dignified-python-313/`

### 3. fake-driven-testing-reminder-hook

**Matcher**: `*.py` (Python files)

**Purpose**: Remind agents to load fake-driven-testing skill before editing tests

**Output**:

```
🔴 CRITICAL: LOAD fake-driven-testing skill NOW before editing Python

WHY: 5-layer defense-in-depth strategy (see skill for architecture)
NOTE: Guides test placement, fake usage, integration class architecture patterns
```

**Why**: Ensures tests follow project testing architecture (fake-driven testing, proper test categorization).

**Location**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/fake-driven-testing/`

### 4. exit-plan-mode-hook

**Matcher**: `ExitPlanMode` (PreToolUse event)

**Purpose**: Prompt user to save or implement plan before exiting Plan Mode

**Behavior**:

- If plan exists for session and no skip marker → Block and instruct Claude to use AskUserQuestion
- If skip marker exists → Delete marker and allow exit
- If no plan → Allow exit

**Output (when blocking)**:

```
❌ Plan detected but not saved

Use AskUserQuestion to ask the user:
- Option A: Save to GitHub
- Option B: Implement immediately
```

**Why**: Prevents losing unsaved plans when exiting Plan Mode. Uses exit code 2 to redirect Claude to ask user preference.

**Location**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/exit_plan_mode_hook.py`

## Common Tasks

### Viewing Installed Hooks

```bash
# List all installed hooks
dot-agent kit list

# Show hook configuration in Claude
/hooks  # Run inside Claude Code session
```

### Modifying an Existing Hook

Hooks are bundled in kits, so modifications require reinstallation:

1. **Edit the hook script**:

   ```bash
   # Example: Edit devrun reminder hook
   vim packages/dot-agent-kit/src/dot_agent_kit/data/kits/devrun/kit_cli_commands/devrun/devrun_reminder_hook.py
   ```

2. **Remove the kit**:

   ```bash
   dot-agent kit remove devrun
   ```

3. **Reinstall the kit**:

   ```bash
   dot-agent kit install devrun
   ```

4. **Verify**:

   ```bash
   # Check hook appears in settings
   cat .claude/settings.json | grep -A 5 "devrun-reminder-hook"

   # Test hook directly
   dot-agent kit-command devrun devrun-reminder-hook
   ```

**Important**: Changes to hook scripts don't take effect until reinstalled. The hook configuration in `.claude/settings.json` is written during `kit install`.

### Creating a New Hook

See comprehensive guide: `packages/dot-agent-kit/docs/HOOKS.md`

**Quick steps**:

1. **Create directory structure**:

   ```bash
   packages/dot-agent-kit/src/dot_agent_kit/data/kits/{kit-name}/
   ├── kit_cli_commands/{kit-name}/{hook_name}.py
   └── kit.yaml
   ```

2. **Implement hook script** (Python + Click):

   ```python
   import click

   @click.command()
   def my_reminder_hook() -> None:
       click.echo("🔴 CRITICAL: Your reminder here")
   ```

3. **Register in kit.yaml** (TWO sections required):

   ```yaml
   kit_cli_commands:
     - name: my-reminder-hook
       script: kit_cli_commands/{kit-name}/{hook_name}.py:{function_name}

   hooks:
     - id: my-reminder-hook
       lifecycle: UserPromptSubmit
       matcher: "*.txt"
       invocation: "dot-agent kit-command {kit-name} my-reminder-hook"
   ```

4. **Install and test**:
   ```bash
   dot-agent kit install {kit-name}
   dot-agent kit-command {kit-name} my-reminder-hook  # Test directly
   ```

### Testing Hooks

**Test hook script independently**:

```bash
# Run hook command directly
dot-agent kit-command {kit-name} {hook-name}

# Or run Python script directly
python packages/dot-agent-kit/src/dot_agent_kit/data/kits/{kit-name}/kit_cli_commands/{kit-name}/{hook_name}.py
```

**Test hook in Claude Code**:

```bash
# Enable debug output
claude --debug

# Trigger hook by creating matching context
# Example: For *.py matcher, open Python file
claude "Show me example.py"
```

**Common test cases**:

- Hook output appears correctly
- Exit code 0 shows reminder (doesn't block)
- Exit code 2 blocks operation
- Timeout doesn't cause hangs
- Matcher fires on correct files/events

## Troubleshooting

### Hook Not Firing

**Check 1: Hook installed correctly**

```bash
# Verify hook in settings.json
cat .claude/settings.json | grep -A 10 "hooks"

# Verify kit installed
dot-agent kit list
```

**Check 2: Matcher conditions met**

```bash
# Example: *.py matcher requires Python files in context
# Try explicitly referencing matching file
claude "Read example.py"
```

**Check 3: Lifecycle event firing**

```bash
# Use debug mode to see hook execution
claude --debug
```

**Common causes**:

- Hook not installed (run `dot-agent kit install {kit-name}`)
- Matcher doesn't match current context
- Hook script has errors (test independently)
- Claude Code settings cache stale (restart Claude)

### Hook Script Errors

**Check 1: Test script independently**

```bash
# Run hook command directly
dot-agent kit-command {kit-name} {hook-name}

# Check exit code
echo $?  # Should be 0 or 2
```

**Check 2: Check function name**

```python
# Function name MUST match file name
# File: devrun_reminder_hook.py
def devrun_reminder_hook():  # ✅ Matches
    pass

def reminder_hook():  # ❌ Doesn't match
    pass
```

**Check 3: Verify kit.yaml registration**

```yaml
# BOTH sections required
kit_cli_commands:
  - name: my-hook # ✅ Registered

hooks:
  - id: my-hook # ✅ Registered
```

### Hook Output Not Showing

**Check 1: Exit code**

```bash
# Exit 0 shows as reminder
# Exit 2 shows as error (blocks operation)
# Other exit codes logged but may not show
```

**Check 2: Output format**

```python
# Use click.echo(), not print()
import click

@click.command()
def my_hook() -> None:
    click.echo("Message here")  # ✅ Correct
    print("Message here")  # ❌ May not show
```

**Check 3: Debug mode**

```bash
# See all hook execution details
claude --debug
```

### Hook Modifications Not Taking Effect

**Solution**: Reinstall kit after changes

```bash
# Remove kit
dot-agent kit remove {kit-name}

# Reinstall kit
dot-agent kit install {kit-name}

# Verify changes
dot-agent kit-command {kit-name} {hook-name}
```

**Why**: Hook configuration is written to `.claude/settings.json` during installation. Source file changes don't auto-update installed hooks.

---

## Additional Resources

- **General Claude Code Hooks Guide**: [hooks.md](hooks.md)
- **Official Claude Code Hooks**: https://code.claude.com/docs/en/hooks
- **Official Hooks Guide**: https://code.claude.com/docs/en/hooks-guide.md
- **dot-agent-kit Hook Development**: `../../packages/dot-agent-kit/docs/HOOKS.md`
- **Kit System Overview**: `../../.agent/kits/README.md`
- **Project Glossary**: `../glossary.md`
