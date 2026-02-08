---
last_audited: "2026-02-08"
audit_result: regenerated
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

## Two-Layer Permission Model

<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, PermissionMode -->
<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, ClaudePermissionMode -->

Erk uses a **generic** `PermissionMode` that maps to **backend-specific** modes. This exists because erk supports multiple agent backends (Claude, Codex), each with different CLI flag vocabularies. New code should always use `PermissionMode`, never `ClaudePermissionMode` directly.

| Generic (`PermissionMode`) | Claude mapping        | Semantic meaning                     |
| -------------------------- | --------------------- | ------------------------------------ |
| `"safe"`                   | `"default"`           | Prompt for every permission          |
| `"edits"`                  | `"acceptEdits"`       | Auto-accept file edits               |
| `"plan"`                   | `"plan"`              | Exploration and planning only        |
| `"dangerous"`              | `"bypassPermissions"` | Bypass all permissions               |

See `PermissionMode` and `permission_mode_to_claude()` in `packages/erk-shared/src/erk_shared/context/types.py` for the mapping implementation.

## The Two Dangerous Flags

The most common mistake when working with this config is confusing `dangerous` and `allow_dangerous`. They map to different Claude CLI flags with fundamentally different trust models:

| Aspect             | `dangerous`                      | `allow_dangerous`                      |
| ------------------ | -------------------------------- | -------------------------------------- |
| Claude CLI flag    | `--dangerously-skip-permissions` | `--allow-dangerously-skip-permissions` |
| Who decides?       | The **config/script** decides    | The **user** decides at runtime        |
| Auto-skips prompts | Yes — all prompts suppressed     | No — prompts appear normally           |
| Use case           | CI/CD, automation, unattended    | Interactive dev — user opts in later   |

**Why two flags exist:** Automation needs unconditional permission bypass (prompts would hang). Interactive use needs the *option* to bypass without *forcing* it — the user might want prompts for some sessions but not others.

## The None-Preservation Override Pattern

<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, InteractiveAgentConfig.with_overrides -->

`with_overrides()` uses `None` as a sentinel meaning "keep the config file value." This is the critical design decision: **any non-None value is an active override**, including `False`.

| Override value passed | Effect                                       |
| --------------------- | -------------------------------------------- |
| `None`                | Config file value preserved                  |
| `"plan"`              | Forces plan mode regardless of config        |
| `True`                | Forces enabled regardless of config          |
| `False`               | **Forces disabled** regardless of config     |

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

This pattern is implemented identically across `next_plan_cmd.py`, `replan_cmd.py`, and `reconcile_cmd.py`. The `AgentLauncher` ABC enables testing without actually exec'ing a process.

## Related Documentation

- [CLI Development Patterns](../cli/) — Command implementation patterns
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) — The ABC pattern used by `AgentLauncher`
