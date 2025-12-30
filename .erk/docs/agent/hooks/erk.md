---
title: Erk Hooks
read_when:
  - "working with erk-specific hooks"
  - "understanding context-aware reminders"
  - "modifying project hooks"
  - "creating project-scoped hooks"
  - "testing hooks with @project_scoped decorator"
  - "using @project_scoped decorator"
  - "creating hooks that only fire in managed projects"
---

# Claude Code Hooks in erk

Project-specific guide for using Claude Code hooks in the erk repository.

**General Claude Code hooks reference**: [hooks.md](hooks.md) (in same directory)

## How Hooks Work in This Project

Hooks are configured in `.claude/settings.json` and their scripts live in `.claude/hooks/`.

**Architecture**:

```
.claude/
├── settings.json            # Hook configuration
└── hooks/
    └── {kit-name}/
        └── {hook_name}.py   # Python script with Click command
```

**How hooks fire**:

1. Claude Code reads `.claude/settings.json` at startup
2. Hook fires when lifecycle event + matcher conditions met
3. Hook script is executed, output shown to user

**Related documentation**:

- Technical implementation: `packages/erk-kits/docs/HOOKS.md`

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

**Location**: `packages/erk-kits/src/erk_kits/data/kits/devrun/`

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

**Location**: `packages/erk-kits/src/erk_kits/data/kits/dignified-python-313/`

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

**Location**: `packages/erk-kits/src/erk_kits/data/kits/fake-driven-testing/`

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

**Location**: `packages/erk-kits/src/erk_kits/data/kits/erk/kit_cli_commands/erk/exit_plan_mode_hook.py`

## Project-Scoped Hooks

Hooks can be decorated with `@project_scoped` to silently skip execution when not in a managed project (one with `.erk/kits.toml`).

### Why Use Project-Scoped Hooks?

In monorepo or multi-project environments, hooks installed at the user level (`~/.claude/`) would fire in ALL repositories, even those not using erk-kits. This causes:

- Confusing reminders in unrelated projects
- Performance overhead from unnecessary hook execution
- Noise in projects that don't need the guidance

### Using the Decorator

```python
from erk_kits.hooks.decorators import project_scoped

@click.command()
@project_scoped  # Add AFTER @click.command()
def my_reminder_hook() -> None:
    click.echo("🔴 CRITICAL: Your reminder here")
```

**Behavior**:

| Scenario                         | Behavior                        |
| -------------------------------- | ------------------------------- |
| In repo with `.erk/kits.toml`    | Hook fires normally             |
| In repo without `.erk/kits.toml` | Hook exits silently (no output) |
| Not in git repo                  | Hook exits silently             |

### Current Project-Scoped Hooks

All erk reminder hooks use this decorator:

- `devrun-reminder-hook`
- `dignified-python-reminder-hook`
- `fake-driven-testing-reminder-hook`
- `session-id-injector-hook`
- `tripwires-reminder-hook`
- `exit-plan-mode-hook`

### Detection Utility

The `@project_scoped` decorator uses `is_in_managed_project()` internally. You can use this directly for more complex conditional logic:

```python
from erk_kits.hooks.scope import is_in_managed_project

@click.command()
def my_hook() -> None:
    if not is_in_managed_project():
        # Custom handling for non-managed projects
        click.echo("ℹ️ Tip: Install erk-kits for full features")
        return

    # Normal hook logic
    click.echo("🔴 CRITICAL: Your reminder")
```

**Function signature**:

```python
def is_in_managed_project() -> bool:
    """Check if current directory is in a managed project.

    Returns True if:
    1. Current directory is inside a git repository
    2. Repository root contains .erk/kits.toml

    Returns False otherwise (fails silently, no exceptions).
    """
```

## Common Tasks

### Viewing Installed Hooks

```bash
# Show hook configuration in Claude
/hooks  # Run inside Claude Code session

# View hooks in settings.json
cat .claude/settings.json | grep -A 10 "hooks"
```

### Modifying an Existing Hook

1. **Edit the hook script** in `.claude/hooks/{kit-name}/`:

   ```bash
   vim .claude/hooks/devrun/devrun_reminder_hook.py
   ```

2. **Verify**:

   ```bash
   # Test hook directly
   python .claude/hooks/devrun/devrun_reminder_hook.py
   ```

### Creating a New Hook

See comprehensive guide: `packages/erk-kits/docs/HOOKS.md`

**Quick steps**:

1. **Create hook script** in `.claude/hooks/{kit-name}/`:

   ```python
   import click

   @click.command()
   def my_reminder_hook() -> None:
       click.echo("🔴 CRITICAL: Your reminder here")
   ```

2. **Register in `.claude/settings.json`**:

   ```json
   {
     "hooks": {
       "UserPromptSubmit": [
         {
           "matcher": "*.txt",
           "hooks": ["python .claude/hooks/{kit-name}/my_reminder_hook.py"]
         }
       ]
     }
   }
   ```

3. **Test**:
   ```bash
   python .claude/hooks/{kit-name}/my_reminder_hook.py
   ```

### Testing Hooks

**Test hook script independently**:

```bash
# Run Python script directly
python .claude/hooks/{kit-name}/{hook_name}.py
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

### Testing Project-Scoped Hooks

When testing hooks that use `@project_scoped`, you must mock `is_in_managed_project` to return `True`, otherwise the hook will silently exit before your test logic runs.

**Pattern**:

```python
from unittest.mock import patch
from click.testing import CliRunner

def test_my_scoped_hook() -> None:
    runner = CliRunner()

    with patch("erk_kits.hooks.decorators.is_in_managed_project", return_value=True):
        result = runner.invoke(my_hook)

    assert result.exit_code == 0
    assert "expected output" in result.output
```

**Common mistake** (causes silent test failures):

```python
# ❌ WRONG - Hook silently exits, test passes but doesn't test anything
def test_my_hook() -> None:
    runner = CliRunner()
    result = runner.invoke(my_hook)
    assert result.exit_code == 0  # Passes but hook didn't run!
```

**Testing unmanaged project behavior**:

```python
def test_hook_silent_in_unmanaged_project() -> None:
    runner = CliRunner()

    with patch("erk_kits.hooks.decorators.is_in_managed_project", return_value=False):
        result = runner.invoke(my_hook)

    assert result.exit_code == 0
    assert result.output == ""  # No output when not in managed project
```

**Important**: The patch target is always `erk_kits.hooks.decorators.is_in_managed_project`, regardless of where your hook is defined. This is because the decorator imports and uses the function at decoration time.

## Troubleshooting

### Hook Not Firing

**Check 1: Hook installed correctly**

```bash
# Verify hook in settings.json
cat .claude/settings.json | grep -A 10 "hooks"

# Verify kit installed
erk kit list
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

- Hook not configured in `.claude/settings.json`
- Matcher doesn't match current context
- Hook script has errors (test independently)
- Claude Code settings cache stale (restart Claude)

### Hook Script Errors

**Check 1: Test script independently**

```bash
# Run hook script directly
python .claude/hooks/{kit-name}/{hook-name}.py

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

**Check 3: Verify settings.json registration**

```bash
# Check hook appears in settings
cat .claude/settings.json | grep -A 5 "{hook-name}"
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

**Solution**: Restart Claude Code after changes to `.claude/settings.json` or hook scripts.

Claude Code caches hook configuration at startup, so changes require a restart to take effect.

---

## Additional Resources

- **General Claude Code Hooks Guide**: [hooks.md](hooks.md)
- **Official Claude Code Hooks**: https://code.claude.com/docs/en/hooks
- **Official Hooks Guide**: https://code.claude.com/docs/en/hooks-guide.md
- **erk-kits Hook Development**: `../../packages/erk-kits/docs/HOOKS.md`
- **Project Glossary**: `../glossary.md`
