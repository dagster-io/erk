# Hook Development Guide

Complete guide for creating, modifying, and managing Claude Code hooks in dot-agent kits.

## Overview

Hooks are automated triggers that run commands at specific lifecycle events in Claude Code. They enable kits to provide contextual reminders, run validations, or perform automated actions based on the user's current context.

## Table of Contents

- [Hook Architecture](#hook-architecture)
- [Official Claude Code Hooks Capabilities](#official-claude-code-hooks-capabilities)
- [Capabilities Not Yet Implemented](#capabilities-not-yet-implemented)
- [dot-agent-kit vs Native Claude Code Hooks](#dot-agent-kit-vs-native-claude-code-hooks)
- [Creating a New Hook](#creating-a-new-hook)
- [Modifying Existing Hooks](#modifying-existing-hooks)
- [Hook Configuration](#hook-configuration)
- [Testing Hooks](#testing-hooks)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Hook Architecture

### How Hooks Work

1. **Definition**: Hooks are defined in `kit.yaml` with two required sections
2. **Installation**: `erk kit install` writes hook configuration to:
   - `kits.toml` (kit metadata)
   - `.claude/settings.json` (Claude Code configuration)
3. **Execution**: When lifecycle event fires, Claude Code:
   - Runs the invocation command
   - Captures output
   - Displays as `<reminder>` block to the assistant

### Hook Flow Diagram

```
kit.yaml                    Installation                Runtime
┌──────────────┐           ┌─────────────┐           ┌──────────────┐
│ kit_cli_     │           │             │           │              │
│ commands:    │ ───────►  │ dot-agent   │ ───────► │ Claude Code  │
│  - script    │           │ kit install │           │ reads        │
│              │           │             │           │ settings.json│
│ hooks:       │           │ Writes to:  │           │              │
│  - id        │           │ • .toml     │           │ Fires on     │
│  - lifecycle │           │ • .json     │           │ event        │
│  - matcher   │           │             │           │              │
└──────────────┘           └─────────────┘           └──────────────┘
```

## Official Claude Code Hooks Capabilities

**Official Documentation**: [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)

Claude Code provides comprehensive hook capabilities beyond what dot-agent-kit currently implements:

- **10 lifecycle events**: UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse, Notification, Stop, SubagentStop, PreCompact, SessionStart, SessionEnd
- **Two hook types**: Command-based (shell commands) and prompt-based (LLM evaluation)
- **Tool-specific matchers**: Target specific tools like Bash, Task, Grep, Read, Edit, Write, WebFetch, WebSearch, MCP tools
- **Decision control via JSON**: Hooks can programmatically allow/deny/block operations and modify tool parameters via structured JSON responses
- **Plugin hook system**: Advanced integration capabilities for complex workflows

**Current dot-agent-kit implementation**:

This package currently implements **command-based hooks only**, primarily using the `UserPromptSubmit` lifecycle event with file glob matchers (e.g., `*.py`, `*`). This covers the most common use case: providing contextual reminders and guidance when agents interact with specific file types.

**For full capabilities**, see the official documentation. The architecture described in this guide is compatible with all Claude Code hook features, but dot-agent-kit's kit.yaml schema currently supports command-based hooks only.

## Capabilities Not Yet Implemented

The following Claude Code hook capabilities are **not yet supported** by dot-agent-kit:

### Prompt-Based Hooks

**What they are**: Hooks that use Claude Haiku to evaluate a prompt and return structured JSON decisions.

**Example use case**: "Evaluate if this bash command is safe to run" - LLM analyzes command and returns allow/deny decision.

**Why not yet implemented**: Requires additional kit.yaml schema fields for prompt configuration and response handling.

### Tool-Specific Matchers

**What they are**: Matchers that target specific tool executions (e.g., `Bash`, `Task`, `Grep`).

**Example use case**: Hook that fires only before `Bash` tool use to validate shell commands.

**Current workaround**: Use file glob matchers (`*`, `*.py`) which match based on context files, not tool execution.

### Decision Control JSON

**What it is**: Structured JSON responses from hooks that programmatically control tool execution:

- `allow` - Permit operation with message
- `deny` - Refuse operation silently
- `block` - Refuse operation with error message
- `updatedInput` - Modify tool parameters before execution

**Example use case**: Hook that adds safety flags to dangerous commands or blocks operations on production files.

**Current workaround**: Command-based hooks can only show reminders (exit 0) or blocking errors (exit 2), not modify parameters.

### Additional Lifecycle Events

**Currently supported**: `UserPromptSubmit` only

**Not yet supported**:

- `PreToolUse` - Before any tool execution (useful for validation)
- `PermissionRequest` - Before permission dialogs (useful for auto-approval)
- `PostToolUse` - After tool execution (useful for side effects)
- `SessionStart` - At session initialization (useful for environment setup)
- `SessionEnd` - At session termination (useful for cleanup)
- `Stop`, `SubagentStop`, `PreCompact`, `Notification`

**Why not yet implemented**: Kit.yaml schema currently only defines `lifecycle` field with `UserPromptSubmit` validation. Adding support requires schema expansion and testing for each lifecycle event's unique behavior.

### Plugin Hook System

**What it is**: Advanced hook integration capabilities for complex workflows and third-party tools.

**Why not yet implemented**: Requires additional infrastructure beyond kit-based hook management.

## dot-agent-kit vs Native Claude Code Hooks

### Comparison Table

| Feature               | dot-agent-kit                                                | Native Claude Code                                         |
| --------------------- | ------------------------------------------------------------ | ---------------------------------------------------------- |
| **Organization**      | Kit-based: hooks bundled with related skills/commands/agents | Manual: edit `.claude/settings.json` directly              |
| **Installation**      | Atomic: `erk kit install {kit}` installs all artifacts       | Manual: copy/paste hook configuration                      |
| **Removal**           | Atomic: `erk kit remove {kit}` removes all artifacts         | Manual: delete hook entries from settings.json             |
| **Metadata Tracking** | Tracked in `kits.toml` with source information               | No metadata tracking                                       |
| **Version Control**   | Hooks are code artifacts in repository                       | Configuration-only (settings.json)                         |
| **Portability**       | Project-portable: kits work across projects                  | Must manually replicate per project                        |
| **Hook Types**        | Command-based only (currently)                               | Command-based AND prompt-based                             |
| **Lifecycle Events**  | UserPromptSubmit only (currently)                            | All 10 lifecycle events                                    |
| **Matchers**          | File globs only (`*.py`, `*`)                                | File globs AND tool matchers (Bash, Task, etc.)            |
| **Decision Control**  | Exit codes only (0 = show, 2 = block)                        | Full JSON decision control (allow/deny/block/updatedInput) |
| **Use Cases**         | Kit-bundled hooks, project-shared patterns                   | Full control, all features, one-off hooks                  |

### When to Use dot-agent-kit

✅ **Use dot-agent-kit hooks when**:

- Hooks are part of a reusable kit with related skills/commands
- You want atomic installation/removal across projects
- You need version control and metadata tracking
- Standard command-based reminders are sufficient
- Team collaboration: hooks should be shared via repository

### When to Use Native Claude Code Hooks

✅ **Use native hooks (manual settings.json) when**:

- You need prompt-based hooks (LLM evaluation)
- You need tool-specific matchers (Bash, Task, etc.)
- You need decision control JSON (allow/deny/block/updatedInput)
- You need lifecycle events beyond UserPromptSubmit
- One-off hooks specific to your workflow
- Maximum flexibility and control

**Both approaches are compatible**: You can use dot-agent-kit hooks alongside manually-configured hooks. They all live in `.claude/settings.json` and work together.

## Creating a New Hook

### Step 1: Create Directory Structure

```bash
packages/dot-agent-kit/src/dot_agent_kit/data/kits/{kit-name}/
├── kit_cli_commands/
│   ├── __init__.py
│   └── {kit-name}/
│       ├── __init__.py
│       └── {hook_name}.py
└── kit.yaml
```

**Naming Convention**: Use `{kit-name}-reminder-hook` pattern for consistency.

### Step 2: Implement Hook Script

Create `{hook_name}.py`:

```python
#!/usr/bin/env python3
"""
{Kit Name} Reminder Command

Outputs the {kit-name} reminder for UserPromptSubmit hook.
This command is invoked via erk kit exec {kit-name} {hook-name}.
"""

import click


@click.command()
def {function_name}() -> None:
    """Output {kit-name} reminder for UserPromptSubmit hook."""
    click.echo("🔴 CRITICAL: Your reminder text here")
    click.echo("")
    click.echo("WHY: Brief explanation")


if __name__ == "__main__":
    {function_name}()
```

**Critical Requirements**:

- Function name MUST match file name (snake_case)
- Use `click.echo()` not `print()`
- Keep logic simple - hooks run on every matching event
- Output plain text (no special tags required)

### Step 3: Configure kit.yaml

Add both sections to `kit.yaml`:

```yaml
name: { kit-name }
version: 0.1.0
description: Your kit description
license: MIT

# Section 1: Define the CLI command
kit_cli_commands:
  - name: { hook-name } # Kebab-case
    path: kit_cli_commands/{kit-name}/{hook_script}.py
    description: Output reminder for UserPromptSubmit hook

# Section 2: Configure the hook
hooks:
  - id: { hook-name } # Must match kit_cli_commands name
    lifecycle: UserPromptSubmit
    matcher: "*" # or "*.py" for Python files only
    invocation: erk kit exec {kit-name} {hook-name}
    description: Hook description
    timeout: 30
```

**Both sections are REQUIRED** - the hook won't work with only one.

### Step 4: Install and Test

```bash
# In development mode (with symlinks)
uv pip install -e packages/dot-agent-kit --force-reinstall --no-deps
erk kit install {kit-name}

# Test the hook directly
erk kit exec {kit-name} {hook-name}

# Verify installation
erk kit show {kit-name}
```

## Modifying Existing Hooks

### Renaming a Hook

When renaming a hook (e.g., `compliance-reminder-hook` → `dignified-python-reminder-hook`):

1. **Rename the script file**:

   ```bash
   mv old_name.py new_name.py
   ```

2. **Update function name in script**:

   ```python
   # Old
   def old_function_name() -> None:

   # New
   def new_function_name() -> None:
   ```

3. **Update kit.yaml** (both sections):

   ```yaml
   kit_cli_commands:
     - name: new-hook-name
       path: kit_cli_commands/{kit}/{new_name}.py

   hooks:
     - id: new-hook-name
       invocation: erk kit exec {kit} new-hook-name
   ```

4. **Reinstall the kit**:
   ```bash
   uv pip install -e packages/dot-agent-kit --force-reinstall --no-deps
   erk kit remove {kit-name}
   erk kit install {kit-name}
   ```

### Common Pitfall: Function Name Mismatch

**Error**: `Warning: Command '{hook}' does not have expected function '{function_name}'`

**Cause**: Function name doesn't match file name

**Fix**: Ensure function name matches file name (with underscores):

- File: `my_reminder_hook.py`
- Function: `def my_reminder_hook()`

## Hook Configuration

### Lifecycle Events

Currently supported:

- `UserPromptSubmit` - Fires when user submits a prompt

### Matcher Patterns

| Pattern      | Behavior                           | Example Use Case           |
| ------------ | ---------------------------------- | -------------------------- |
| `*`          | Fires on every prompt              | General reminders          |
| `*.py`       | Fires when Python files in context | Language-specific guidance |
| `*.{ts,tsx}` | Multiple extensions                | Framework-specific hints   |
| `Makefile`   | Specific file name                 | Build system reminders     |

### Timeout Configuration

- Default: 30 seconds
- Keep hooks fast - they run frequently
- Avoid complex logic or network calls

## Testing Hooks

### Manual Testing

```bash
# Test hook execution directly
erk kit exec {kit-name} {hook-name}

# Should output plain text reminder:
# 🔴 CRITICAL: Your reminder text here
#
# WHY: Brief explanation
```

### Verification Checklist

- [ ] Hook appears in `erk kit show {kit-name}`
- [ ] Hook ID in `kits.toml` matches kit.yaml
- [ ] Hook configuration in `.claude/settings.json`
- [ ] Direct execution produces expected output
- [ ] Function name matches file name

### Testing in Claude Code

After installation, hooks will fire automatically:

- Matcher `*` hooks appear on every prompt
- Matcher `*.py` hooks appear when Python files are in context

## Common Patterns

### Reminder Hooks

Most common pattern - provides contextual reminders:

```python
@click.command()
def devrun_reminder_hook() -> None:
    """Output devrun agent reminder for UserPromptSubmit hook."""
    click.echo(
        "🔴 CRITICAL: For pytest/pyright/ruff/prettier/make/gt → MUST use devrun agent "
        '(Task tool with subagent_type="devrun"), NOT direct Bash\n'
        "\n"
        "This includes uv run variants: uv run pytest, uv run pyright, uv run ruff, etc.\n"
        "\n"
        "WHY: Specialized parsing & cost efficiency"
    )
```

### Conditional Output

For more complex scenarios:

```python
@click.command()
@click.option('--verbose', is_flag=True, help='Show detailed reminder')
def conditional_hook(verbose: bool) -> None:
    """Output conditional reminder based on context."""
    if verbose:
        click.echo("🔴 CRITICAL: Detailed reminder with multiple lines")
        click.echo("• Point 1")
        click.echo("• Point 2")
    else:
        click.echo("🔴 CRITICAL: Brief reminder")
```

### Multi-Kit Coordination

Hooks from different kits can work together:

- Use unique IDs following `{kit-name}-reminder-hook` pattern
- Different matchers prevent conflicts
- Order of execution determined by `.claude/settings.json`

## Troubleshooting

### Hook Not Firing

**Check**:

1. Hook appears in `erk kit show {kit-name}`
2. `.claude/settings.json` contains hook configuration
3. Matcher pattern matches current context
4. No syntax errors in hook script

### Installation Issues

**Problem**: Changes not reflected after editing

**Solution**:

```bash
# Force reinstall package and kit
uv pip install -e packages/dot-agent-kit --force-reinstall --no-deps
erk kit remove {kit-name}
erk kit install {kit-name}
```

### Common Errors

| Error                           | Cause                   | Solution                          |
| ------------------------------- | ----------------------- | --------------------------------- |
| `No such command '{hook-name}'` | Function name mismatch  | Ensure function matches file name |
| `Missing artifact`              | kit.yaml path incorrect | Verify path in kit_cli_commands   |
| `Hook not in settings.json`     | Installation failed     | Remove and reinstall kit          |
| `No output shown`               | Script error or timeout | Test hook script independently    |

## Best Practices

### DO

- ✅ Use consistent naming: `{kit-name}-reminder-hook`
- ✅ Keep hooks fast and simple
- ✅ Output clear, concise reminder text
- ✅ Test hooks before committing
- ✅ Use appropriate matchers (not everything needs `*`)

### DON'T

- ❌ Use underscores in hook IDs (use kebab-case)
- ❌ Forget either kit_cli_commands or hooks section
- ❌ Include complex logic in hooks
- ❌ Make network calls or slow operations

## Related Documentation

- [ARTIFACT_LIFECYCLE.md](ARTIFACT_LIFECYCLE.md) - General artifact management
- [KIT_CLI_COMMANDS.md](KIT_CLI_COMMANDS.md) - Kit CLI command patterns
- [DEVELOPING.md](../DEVELOPING.md) - Kit development workflow
- [GLOSSARY.md](GLOSSARY.md) - Terminology and concepts
