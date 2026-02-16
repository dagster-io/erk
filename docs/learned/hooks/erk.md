---
title: Erk Hooks
last_audited: "2026-02-03 00:00 PT"
audit_result: edited
read_when:
  - "working with erk-specific hooks"
  - "understanding context-aware reminders"
  - "modifying project hooks"
  - "creating project-scoped hooks"
  - "using logged_hook or hook_command decorators"
  - "creating hooks that only fire in managed projects"
---

# Claude Code Hooks in erk

Project-specific guide for using Claude Code hooks in the erk repository.

**General Claude Code hooks reference**: [hooks.md](hooks.md) (in same directory)

## How Hooks Work in This Project

Hooks are configured in `.claude/settings.json`. Most hook logic lives in `src/erk/cli/commands/exec/scripts/` as Click commands invoked via `erk exec <hook-name>`.

**Architecture**:

```
.claude/
├── settings.json                              # Hook configuration
└── hooks/
    └── fake-driven-testing-reminder.sh        # Simple shell reminder
src/erk/
├── hooks/
│   └── decorators.py                          # logged_hook, hook_command, HookContext
└── cli/commands/exec/scripts/
    ├── user_prompt_hook.py                    # UserPromptSubmit hook
    ├── pre_tool_use_hook.py                   # PreToolUse hook for Write|Edit
    └── exit_plan_mode_hook.py                 # PreToolUse hook for ExitPlanMode
```

**How hooks fire**:

1. Claude Code reads `.claude/settings.json` at startup
2. Hook fires when lifecycle event + matcher conditions met
3. Hook command is executed (e.g., `erk exec user-prompt-hook`), output shown to Claude

**Related documentation**:

- Hook decorator source: `src/erk/hooks/decorators.py`
- Hook scripts: `src/erk/cli/commands/exec/scripts/`

## Current Hooks

The hooks configured in `.claude/settings.json`:

### 1. user-prompt-hook

**Event**: `UserPromptSubmit` | **Matcher**: `*` (all prompts)

**Invocation**: `ERK_HOOK_ID=user-prompt-hook erk exec user-prompt-hook`

**Purpose**: Consolidated hook that handles session ID persistence and opt-in coding reminders.

**Behavior**:

- Persists session ID to `.erk/scratch/current-session-id`
- Emits devrun reminder if `devrun` capability is installed
- Emits tripwires reminder if `tripwires` capability is installed
- Emits explore-docs reminder if `explore-docs` capability is installed

Reminders are opt-in via capability marker files in `.erk/capabilities/`.

**Location**: `src/erk/cli/commands/exec/scripts/user_prompt_hook.py`

### 2. fake-driven-testing-reminder

**Event**: `UserPromptSubmit` | **Matcher**: `*` (all prompts)

**Invocation**: `.claude/hooks/fake-driven-testing-reminder.sh`

**Purpose**: Simple shell script reminder to load/abide by fake-driven-testing rules.

**Location**: `.claude/hooks/fake-driven-testing-reminder.sh`

### 3. pre-tool-use-hook (dignified-python reminder)

**Event**: `PreToolUse` | **Matcher**: `Write|Edit`

**Invocation**: `ERK_HOOK_ID=pre-tool-use-hook erk exec pre-tool-use-hook`

**Purpose**: Emits dignified-python coding standards reminder when editing `.py` files.

**Behavior**:

- Reads `tool_input.file_path` from stdin JSON
- If file is `.py` and `dignified-python` capability is installed, emits reminder
- Never blocks (always exit code 0)

**Location**: `src/erk/cli/commands/exec/scripts/pre_tool_use_hook.py`

### 4. exit-plan-mode-hook

**Event**: `PreToolUse` | **Matcher**: `ExitPlanMode`

**Invocation**: `ERK_HOOK_ID=exit-plan-mode-hook erk exec exit-plan-mode-hook`

**Purpose**: Prompt user to save or implement plan before exiting Plan Mode.

**Behavior**:

- If plan exists for session and no skip marker: Block (exit code 2) and instruct Claude to use AskUserQuestion
- If implement-now or incremental-plan marker exists: Allow exit (delete marker)
- If plan-saved marker exists: Block with "session complete" message
- If no plan: Allow exit

**Location**: `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py`

#### Marker State Machine

The exit-plan-mode hook uses marker files in `.erk/scratch/sessions/<session-id>/` for state management:

| Marker                                     | Created By                     | Lifecycle | Effect When Present          |
| ------------------------------------------ | ------------------------------ | --------- | ---------------------------- |
| `exit-plan-mode-hook.plan-saved.marker`    | `plan-save-to-issue`           | Reusable  | Block exit, show "complete"  |
| `exit-plan-mode-hook.implement-now.marker` | Agent (`erk exec marker`)      | One-time  | Allow exit                   |
| `objective-context.marker`                 | `/erk:objective-next-plan`     | One-time  | Suggests `--objective-issue` |
| `incremental-plan.marker`                  | `/local:incremental-plan-mode` | One-time  | Allow exit, skip save        |

**Lifecycle semantics:**

- **Reusable markers** persist across hook invocations (not deleted when read)
- **One-time markers** are consumed (deleted) after being processed

**Critical**: Never delete `plan-saved` marker when blocking. It represents a state ("plan is saved") not a one-time action. Deleting it would enable duplicate plan creation on retry.

See [Session Deduplication](../planning/session-deduplication.md) for the full deduplication pattern.

### 5. PostToolUse ruff formatter

**Event**: `PostToolUse` | **Matcher**: `Write|Edit`

**Invocation**: Inline shell command that runs `uv run ruff format` on `.py` files.

**Purpose**: Auto-formats Python files after Write/Edit operations.

## Project-Scoped Hook Pattern

Hooks use `HookContext.is_erk_project` to silently skip execution when not in a managed project (one with a `.erk` directory).

### Why Project Scoping?

In multi-project environments, hooks would fire in ALL repositories. This causes:

- Confusing reminders in unrelated projects
- Performance overhead from unnecessary hook execution

### Using HookContext for Project Scoping

The `hook_command` decorator from `erk.hooks.decorators` provides `HookContext` injection:

```python
from erk.hooks.decorators import HookContext, hook_command

@hook_command(name="my-hook")
def my_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
    if not hook_ctx.is_erk_project:
        return
    click.echo("Reminder for erk projects only")
```

**HookContext fields**:

| Field            | Type           | Description                               |
| ---------------- | -------------- | ----------------------------------------- |
| `session_id`     | `str \| None`  | Claude session ID from stdin JSON         |
| `repo_root`      | `Path`         | Path to the git repository root           |
| `scratch_dir`    | `Path \| None` | Session-scoped scratch directory          |
| `is_erk_project` | `bool`         | True if `repo_root/.erk` directory exists |

### Hook Decorators

Two decorators in `src/erk/hooks/decorators.py`:

- **`@logged_hook`**: Captures stdin, stdout/stderr, timing, and exit status. Writes hook execution logs. Optionally injects `HookContext` if function signature accepts `hook_ctx` parameter.
- **`@hook_command(name=...)`**: Combines `@click.command`, `@click.pass_context`, and `@logged_hook` into a single decorator.

## Common Tasks

### Viewing Installed Hooks

```bash
# View hooks in settings.json
cat .claude/settings.json | grep -A 10 "hooks"
```

### Modifying an Existing Hook

1. **Edit the hook script** in `src/erk/cli/commands/exec/scripts/`:

   ```bash
   vim src/erk/cli/commands/exec/scripts/user_prompt_hook.py
   ```

2. **Verify**: Run tests for the hook.

### Creating a New Hook

**Quick steps**:

1. **Create hook script** in `src/erk/cli/commands/exec/scripts/`:

   ```python
   import click
   from erk.hooks.decorators import HookContext, hook_command

   @hook_command(name="my-new-hook")
   def my_new_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
       if not hook_ctx.is_erk_project:
           return
       click.echo("Your reminder here")
   ```

2. **Register in `src/erk/cli/commands/exec/group.py`**: Import and add to exec group.

3. **Register in `.claude/settings.json`**:

   ```json
   {
     "hooks": {
       "UserPromptSubmit": [
         {
           "matcher": "*",
           "hooks": [
             {
               "type": "command",
               "command": "ERK_HOOK_ID=my-new-hook erk exec my-new-hook",
               "timeout": 30
             }
           ]
         }
       ]
     }
   }
   ```

## Troubleshooting

### Hook Not Firing

**Check 1: Hook installed correctly**

```bash
# Verify hook in settings.json
cat .claude/settings.json | grep -A 10 "hooks"
```

**Check 2: Matcher conditions met** - ensure the lifecycle event and matcher pattern match.

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

### Hook Output Not Showing

**Check 1: Exit code** - Exit 0 shows as reminder, exit 2 blocks operation.

**Check 2: Output format** - Use `click.echo()`, not `print()`.

### Hook Modifications Not Taking Effect

**Solution**: Restart Claude Code after changes to `.claude/settings.json` or hook scripts.

Claude Code caches hook configuration at startup, so changes require a restart to take effect.

---

## Additional Resources

- **General Claude Code Hooks Guide**: [hooks.md](hooks.md)
- **Hook Decorators**: `src/erk/hooks/decorators.py`
- **Hook Scripts**: `src/erk/cli/commands/exec/scripts/`
- **Project Glossary**: `../glossary.md`
