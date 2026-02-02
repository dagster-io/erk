---
title: Interactive Claude Configuration
read_when:
  - "configuring Claude CLI launches from erk commands"
  - "understanding permission modes for interactive Claude sessions"
  - "working with dangerous flags for Claude permissions"
  - "implementing commands that launch Claude interactively"
category: reference
tripwires:
  - action: "confusing `dangerous` with `allow_dangerous`"
    warning: "`dangerous` forces skip all prompts (--dangerously-skip-permissions). `allow_dangerous` allows user opt-in (--allow-dangerously-skip-permissions). They have different behaviors."
  - action: "passing non-None override values when wanting to preserve config"
    warning: "Pass None to preserve config value. Pass value to override. with_overrides(model_override=False) disables model, should be model_override=None."
  - action: "forgetting that CLI flags always override config file values"
    warning: "The with_overrides() pattern ensures CLI flags take precedence. Never read config directly when overrides are present."
---

# Interactive Claude Configuration

## Overview

`InteractiveClaudeConfig` controls how erk commands launch Claude Code interactively. It's configured via `[interactive-claude]` section in `~/.erk/config.toml` and can be overridden by CLI flags.

**Source:** `packages/erk-shared/src/erk_shared/context/types.py`

## Configuration Structure

```python
@dataclass(frozen=True)
class InteractiveClaudeConfig:
    model: str | None
    verbose: bool
    permission_mode: ClaudePermissionMode
    dangerous: bool
    allow_dangerous: bool
```

### Fields

| Field             | Type                   | Default         | Description                                     |
| ----------------- | ---------------------- | --------------- | ----------------------------------------------- |
| `model`           | `str \| None`          | `None`          | Claude model to use (e.g., `"claude-opus-4-5"`) |
| `verbose`         | `bool`                 | `False`         | Whether to show verbose output                  |
| `permission_mode` | `ClaudePermissionMode` | `"acceptEdits"` | Permission mode for Claude CLI                  |
| `dangerous`       | `bool`                 | `False`         | Force skip all permission prompts               |
| `allow_dangerous` | `bool`                 | `False`         | Allow user to opt into skipping prompts         |

## Permission Modes

```python
ClaudePermissionMode = Literal["default", "acceptEdits", "plan", "bypassPermissions"]
```

| Mode                | CLI Flag                              | Behavior                               |
| ------------------- | ------------------------------------- | -------------------------------------- |
| `default`           | (none)                                | Default mode with permission prompts   |
| `acceptEdits`       | `--permission-mode acceptEdits`       | Accept edits without prompts           |
| `plan`              | `--permission-mode plan`              | Plan mode for exploration and planning |
| `bypassPermissions` | `--permission-mode bypassPermissions` | Bypass all permissions                 |

## Dangerous Flags: Two Distinct Meanings

**Critical:** There are TWO separate dangerous flags with different meanings:

### `dangerous` Field

**Maps to:** `--dangerously-skip-permissions`

**Behavior:** Forces Claude to skip permission prompts for the entire session

**When to use:**

- Automated workflows where prompts would block
- Scripts that need unattended execution
- CI/CD pipelines

**Config example:**

```toml
[interactive-claude]
dangerous = true
```

### `allow_dangerous` Field

**Maps to:** `--allow-dangerously-skip-permissions`

**Behavior:** Allows the USER to opt into skipping prompts during a session, but doesn't force it

**When to use:**

- Interactive workflows where user might want to skip prompts later
- Commands that launch Claude for manual work
- Developer productivity (user decides whether to skip)

**Config example:**

```toml
[interactive-claude]
allow_dangerous = true
```

### Comparison Table

| Aspect             | `dangerous`                      | `allow_dangerous`                      |
| ------------------ | -------------------------------- | -------------------------------------- |
| CLI Flag           | `--dangerously-skip-permissions` | `--allow-dangerously-skip-permissions` |
| Auto-skips prompts | ✅ Yes                           | ❌ No                                  |
| User can skip      | ✅ Yes                           | ✅ Yes                                 |
| Default behavior   | Skip all                         | Prompt normally                        |
| Use case           | Automation                       | Developer productivity                 |

## Config File Location

`~/.erk/config.toml`

**Section:** `[interactive-claude]`

**Example:**

```toml
[interactive-claude]
model = "claude-opus-4-5"
verbose = false
permission_mode = "acceptEdits"
dangerous = false
allow_dangerous = true
```

## Default Configuration

When no config file exists, erk uses:

```python
InteractiveClaudeConfig(
    model=None,
    verbose=False,
    permission_mode="acceptEdits",
    dangerous=False,
    allow_dangerous=False,
)
```

## Override Pattern: `with_overrides()`

Commands override config values using `with_overrides()`:

```python
config = ic_config.with_overrides(
    permission_mode_override="plan",
    model_override=None,
    dangerous_override=None,
    allow_dangerous_override=None,
)
```

**Critical rule:** Pass `None` to preserve the config value, pass a value to override.

| Override Value | Result                  |
| -------------- | ----------------------- |
| `"plan"`       | Forces plan mode        |
| `None`         | Keeps config file value |
| `True`         | Forces enabled          |
| `False`        | Forces disabled         |

### Example: Force Plan Mode

**Use case:** `erk objective next-plan` always uses plan mode, regardless of config

```python
config = ic_config.with_overrides(
    permission_mode_override="plan",  # Force plan mode
    model_override=None,              # Keep config value
    dangerous_override=None,          # Keep config value
    allow_dangerous_override=None,    # Keep config value
)
```

### Example: Conditional Override from CLI Flag

**Use case:** CLI `-d` flag enables `allow_dangerous`

```python
# If user passed -d flag
dangerous_flag = True

config = ic_config.with_overrides(
    permission_mode_override=None,
    model_override=None,
    dangerous_override=None,
    allow_dangerous_override=True if dangerous_flag else None,
    # ^^^^^ Ternary: True if flag present, None to preserve config
)
```

**Why the ternary:**

- `-d` present: `allow_dangerous_override=True` → enables it
- `-d` absent: `allow_dangerous_override=None` → preserves config value

**Anti-pattern:**

```python
# WRONG: This disables allow_dangerous when flag is absent
allow_dangerous_override=dangerous_flag  # False disables, should be None
```

## Integration Example

**From:** `src/erk/cli/commands/objective/next_plan_cmd.py`

See `next_plan()` in `src/erk/cli/commands/objective/next_plan_cmd.py:18` for the full implementation.

## Related Documentation

- [Objective Commands: Next-Plan](../cli/objective-commands.md#next-plan-command) - Usage of permission mode override
- [CLI Development Patterns](../cli/) - Command implementation patterns

## Testing Considerations

When testing commands that use `InteractiveClaudeConfig`:

**Create test config:**

```python
from erk_shared.context.types import InteractiveClaudeConfig, GlobalConfig

# Default test config
test_config = InteractiveClaudeConfig.default()

# Custom test config
test_config = InteractiveClaudeConfig(
    model="claude-opus-4-5",
    verbose=True,
    permission_mode="plan",
    dangerous=True,
    allow_dangerous=False,
)

# Embed in GlobalConfig
global_config = GlobalConfig.test(
    erk_root=Path("/tmp/test"),
    interactive_claude=test_config,
)
```
