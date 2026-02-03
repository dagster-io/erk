---
title: Interactive Agent Configuration
tripwires:
  - action: "modifying InteractiveAgentConfig fields or config file format"
    warning: "Update both config loading (RealErkInstallation.load_config) and usage sites. Check backward compatibility with [interactive-claude] section."
  - action: "changing config section names ([interactive-claude] or [interactive-agent])"
    warning: "Maintain fallback from [interactive-agent] to [interactive-claude] for backward compatibility."
read_when:
  - "Working with global config loading (GlobalConfig)"
  - "Implementing interactive agent launch behavior"
  - "Adding new agent configuration options"
---

# Interactive Agent Configuration

## Overview

The `InteractiveAgentConfig` type stores configuration for launching interactive AI agents (currently Claude Code CLI, future support for Codex). Configuration is loaded from `~/.erk/config.toml` in the `[interactive-claude]` section (with planned migration to `[interactive-agent]` in future).

## Configuration Fields

| Field             | Type                   | Default       | Description                                        |
| ----------------- | ---------------------- | ------------- | -------------------------------------------------- |
| `model`           | `str \| None`          | `None`        | Model to use (e.g., "claude-opus-4-5")             |
| `verbose`         | `bool`                 | `False`       | Enable verbose output                              |
| `permission_mode` | `ClaudePermissionMode` | `acceptEdits` | Permission mode for agent operations               |
| `dangerous`       | `bool`                 | `False`       | Skip all permission prompts (dangerous!)           |
| `allow_dangerous` | `bool`                 | `False`       | Enable `--allow-dangerously-skip-permissions` flag |

### ClaudePermissionMode Values

- `"default"`: Default mode with permission prompts
- `"acceptEdits"`: Accept edits without prompts
- `"plan"`: Read-only plan mode
- `"bypassPermissions"`: Bypass all permissions (requires `dangerous=true`)

See [SandboxMode](sandbox-modes.md) for how these map to both Claude and Codex backends.

## Config File Format

### Current Format

Configuration lives in `~/.erk/config.toml` under `[interactive-claude]`:

```toml
[interactive-claude]
model = "claude-opus-4-5"
verbose = false
permission_mode = "acceptEdits"
dangerous = false
allow_dangerous = false
```

All fields are optional. Omitted fields use the defaults from `InteractiveClaudeConfig.default()`.

### Future Format (Planned)

Future versions will support `[interactive-agent]` section with backward compatibility:

```toml
[interactive-agent]
model = "claude-opus-4-5"
backend = "claude"  # New field: "claude" or "codex"
verbose = false
permission_mode = "acceptEdits"
dangerous = false
allow_dangerous = false
```

**Backward compatibility**: Config loading will check `[interactive-agent]` first, then fall back to `[interactive-claude]` if not found. This allows existing configs to continue working without migration.

## Loading Behavior

Configuration is loaded by `RealErkInstallation.load_config()`:

```python
# packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py:62-69
ic_data = data.get("interactive-claude", {})
interactive_claude = InteractiveClaudeConfig(
    model=ic_data.get("model"),
    verbose=bool(ic_data.get("verbose", False)),
    permission_mode=ic_data.get("permission_mode", "acceptEdits"),
    dangerous=bool(ic_data.get("dangerous", False)),
    allow_dangerous=bool(ic_data.get("allow_dangerous", False)),
)
```

**Key behaviors:**

- Missing section returns empty dict `{}`
- Missing fields use dataclass defaults
- Boolean coercion via `bool()` for safety
- String values (like `permission_mode`) are NOT validated at load time

## CLI Flag Override

CLI flags ALWAYS override config values. The config provides defaults when flags are omitted.

Example: `erk agent --model claude-sonnet-4-5` overrides the `model` field from config.

## Code References

- **Type definition**: `packages/erk-shared/src/erk_shared/context/types.py:72-93` (InteractiveClaudeConfig)
- **Config loading**: `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py:62-69`
- **Default values**: `packages/erk-shared/src/erk_shared/context/types.py:95-102` (InteractiveClaudeConfig.default())

## Related Documentation

- [SandboxMode](sandbox-modes.md) - Permission mode mappings to Claude/Codex
- [Global Config](../config/global-config.md) - Complete global config structure
