---
last_audited: "2026-02-08 13:55 PT"
audit_result: edited
title: Interactive Agent Configuration
read_when:
  - "implementing erk commands that launch Claude or Codex interactively"
  - "understanding the two dangerous flags and when to use each"
  - "working with the with_overrides() None-preservation pattern"
  - "configuring agent permission modes across config and CLI layers"
category: reference
tripwires:
  - action: "confusing `dangerous` with `allow_dangerous`"
    warning: "`dangerous` forces skip all prompts (automation). `allow_dangerous` lets users opt in (productivity). See the decision table in this doc."
  - action: "passing a non-None value to with_overrides() when wanting to preserve config"
    warning: "None means 'keep config value'. Any non-None value (including False) is an active override. `allow_dangerous_override=dangerous_flag` when the flag is False will DISABLE the setting, not preserve it."
  - action: "using ClaudePermissionMode directly in new commands"
    warning: "New code should use PermissionMode ('safe', 'edits', 'plan', 'dangerous'). The Claude-specific modes are an internal mapping detail."
  - action: "referencing InteractiveClaudeConfig in new code"
    warning: "Renamed to InteractiveAgentConfig. The class is backend-agnostic (supports Claude and Codex). Config section also renamed: user-facing key is still 'interactive_claude' but attribute is 'interactive_agent'."
---

# Interactive Agent Configuration

## Why This Doc Exists

<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, InteractiveAgentConfig -->

`InteractiveAgentConfig` is the bridge between user configuration (`~/.erk/config.toml`) and agent CLI launches. It touches three layers — config loading, CLI flag parsing, and process execution — creating cross-cutting patterns that no single source file fully explains. This doc captures the design decisions and pitfalls across those layers.

## Configuration Fields

<!-- Third-party reference: Claude Code CLI configuration fields -->

See `InteractiveAgentConfig` in `packages/erk-shared/src/erk_shared/context/types.py` for the canonical dataclass definition.

| Field             | Type             | Default    | Description                                          |
| ----------------- | ---------------- | ---------- | ---------------------------------------------------- |
| `backend`         | `AgentBackend`   | `"claude"` | Which agent backend to use (`"claude"` or `"codex"`) |
| `model`           | `str \| None`    | `None`     | Model to use (e.g., `"claude-opus-4-5"`)             |
| `verbose`         | `bool`           | `False`    | Whether to show verbose output                       |
| `permission_mode` | `PermissionMode` | `"edits"`  | Permission mode for agent CLI                        |
| `dangerous`       | `bool`           | `False`    | Force skip all permission prompts                    |
| `allow_dangerous` | `bool`           | `False`    | Allow user to opt into skipping prompts              |

### Default Configuration

When no config file exists, erk uses `InteractiveAgentConfig.default()` which returns `backend="claude"`, `model=None`, `verbose=False`, `permission_mode="edits"`, and both dangerous flags `False`. See the `default()` staticmethod in `packages/erk-shared/src/erk_shared/context/types.py`.

### Config File Location

`~/.erk/config.toml`

**Section:** `[interactive-claude]`

```toml
[interactive-claude]
model = "claude-opus-4-5"
verbose = false
permission_mode = "edits"
dangerous = false
allow_dangerous = true
```

## Two-Layer Permission Model

<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, PermissionMode -->
<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, ClaudePermissionMode -->

Erk uses a **generic** `PermissionMode` that maps to **backend-specific** modes. This exists because erk supports multiple agent backends (Claude, Codex), each with different CLI flag vocabularies. New code should always use `PermissionMode`, never `ClaudePermissionMode` directly.

| Generic (`PermissionMode`) | Claude mapping        | Semantic meaning              |
| -------------------------- | --------------------- | ----------------------------- |
| `"safe"`                   | `"default"`           | Prompt for every permission   |
| `"edits"`                  | `"acceptEdits"`       | Auto-accept file edits        |
| `"plan"`                   | `"plan"`              | Exploration and planning only |
| `"dangerous"`              | `"bypassPermissions"` | Bypass all permissions        |

### Claude-Specific Permission Modes

<!-- Third-party reference: Claude Code CLI permission mode flags -->

These are the backend-specific modes as passed to the Claude CLI:

| Mode                | CLI Flag                              | Behavior                               |
| ------------------- | ------------------------------------- | -------------------------------------- |
| `default`           | (none)                                | Default mode with permission prompts   |
| `acceptEdits`       | `--permission-mode acceptEdits`       | Accept edits without prompts           |
| `plan`              | `--permission-mode plan`              | Plan mode for exploration and planning |
| `bypassPermissions` | `--permission-mode bypassPermissions` | Bypass all permissions                 |

See `PermissionMode` and `permission_mode_to_claude()` in `packages/erk-shared/src/erk_shared/context/types.py` for the mapping implementation.

## The Two Dangerous Flags

The most common mistake when working with this config is confusing `dangerous` and `allow_dangerous`. They map to different Claude CLI flags with fundamentally different trust models:

| Aspect             | `dangerous`                      | `allow_dangerous`                      |
| ------------------ | -------------------------------- | -------------------------------------- |
| Claude CLI flag    | `--dangerously-skip-permissions` | `--allow-dangerously-skip-permissions` |
| Who decides?       | The **config/script** decides    | The **user** decides at runtime        |
| Auto-skips prompts | Yes — all prompts suppressed     | No — prompts appear normally           |
| User can skip      | Yes                              | Yes                                    |
| Default behavior   | Skip all                         | Prompt normally                        |
| Use case           | CI/CD, automation, unattended    | Interactive dev — user opts in later   |

**Why two flags exist:** Automation needs unconditional permission bypass (prompts would hang). Interactive use needs the _option_ to bypass without _forcing_ it — the user might want prompts for some sessions but not others.

### `dangerous` Field

<!-- Third-party reference: Claude Code CLI dangerous flag -->

**Maps to:** `--dangerously-skip-permissions`

**Behavior:** Forces Claude to skip permission prompts for the entire session

**When to use:** Automated workflows where prompts would block, scripts that need unattended execution, CI/CD pipelines.

```toml
[interactive-claude]
dangerous = true
```

### `allow_dangerous` Field

<!-- Third-party reference: Claude Code CLI allow-dangerous flag -->

**Maps to:** `--allow-dangerously-skip-permissions`

**Behavior:** Allows the USER to opt into skipping prompts during a session, but doesn't force it

**When to use:** Interactive workflows where user might want to skip prompts later, commands that launch Claude for manual work, developer productivity.

```toml
[interactive-claude]
allow_dangerous = true
```

## The None-Preservation Override Pattern

<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, InteractiveAgentConfig.with_overrides -->

`with_overrides()` uses `None` as a sentinel meaning "keep the config file value." This is the critical design decision: **any non-None value is an active override**, including `False`.

| Override value passed | Effect                                   |
| --------------------- | ---------------------------------------- |
| `None`                | Config file value preserved              |
| `"plan"`              | Forces plan mode regardless of config    |
| `True`                | Forces enabled regardless of config      |
| `False`               | **Forces disabled** regardless of config |

### The Boolean Flag Trap

When mapping a CLI boolean flag to an override, you must use a ternary — not the flag value directly:

```python
# WRONG: When dangerous_flag is False, this disables allow_dangerous
# even if the config file has allow_dangerous = true
allow_dangerous_override=dangerous_flag
```

The correct pattern converts absent flags to `None`:

```python
# WRONG: Passes False when flag absent, overriding config
allow_dangerous_override=dangerous_flag

# RIGHT: Passes None when flag absent, preserving config
allow_dangerous_override=True if dangerous_flag else None
```

### Example: Force Plan Mode

**Use case:** `erk plan replan` always uses plan mode, regardless of config. It passes `permission_mode_override="plan"` and `None` for all other overrides. See `replan_plan()` in `src/erk/cli/commands/plan/replan_cmd.py` for the canonical example.

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

- `-d` present: `allow_dangerous_override=True` — enables it
- `-d` absent: `allow_dangerous_override=None` — preserves config value

<!-- Source: src/erk/cli/commands/objective/next_plan_cmd.py, next_plan -->

See `next_plan()` in `src/erk/cli/commands/objective/next_plan_cmd.py` for the canonical example of this pattern with a `-d` flag.

## Cross-Layer Naming: CLI Key vs Attribute

<!-- Source: src/erk/cli/commands/config.py, _CLI_KEY_TO_ATTR -->

The config system maintains **backward compatibility** for user-facing keys while the internal attribute name evolved:

- **User-facing config key:** `interactive_claude.*` (in `~/.erk/config.toml` and `erk config get/set`)
- **Internal attribute:** `GlobalConfig.interactive_agent` (an `InteractiveAgentConfig`)

The mapping lives in `_CLI_KEY_TO_ATTR` in `src/erk/cli/commands/config.py`. This means `erk config set interactive_claude.verbose true` writes to `GlobalConfig.interactive_agent.verbose` — the translation is invisible to users.

**Why the split:** The class was renamed from `InteractiveClaudeConfig` to `InteractiveAgentConfig` when Codex support was added, but existing user config files still use `[interactive-claude]`. Rather than force a migration, the CLI layer translates.

## Command Integration Pattern

<!-- Source: packages/erk-shared/src/erk_shared/gateway/agent_launcher/abc.py, AgentLauncher.launch_interactive -->

Every erk command that launches an interactive agent session follows the same three-step pattern:

1. **Load config** — from `ctx.global_config.interactive_agent` (or `InteractiveAgentConfig.default()` if no global config)
2. **Apply overrides** — via `with_overrides()` for command-specific requirements (e.g., plan commands always force `permission_mode_override="plan"`)
3. **Launch** — via `ctx.agent_launcher.launch_interactive(config, command=...)` which uses `os.execvp()` to replace the process

This pattern is implemented identically across `next_plan_cmd.py` and `replan_cmd.py`. The `AgentLauncher` ABC enables testing without actually exec'ing a process.

## Testing Considerations

When testing commands that use `InteractiveAgentConfig`:

- Use `InteractiveAgentConfig.default()` for a default test config
- Construct custom configs by passing all 6 fields (including `backend`) to the dataclass directly
- Embed in `GlobalConfig.test(erk_root=..., interactive_agent=test_config)` -- note the parameter is `interactive_agent`, not `interactive_claude`

See `GlobalConfig.test()` in `packages/erk-shared/src/erk_shared/context/types.py` for the full signature.

## Related Documentation

- [CLI Development Patterns](../cli/) — Command implementation patterns
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) — The ABC pattern used by `AgentLauncher`
