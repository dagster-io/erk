---
title: Interactive Agent Configuration
last_audited: "2026-02-03 03:56 PT"
audit_result: edited
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

## Code References

- **Type definition**: `packages/erk-shared/src/erk_shared/context/types.py:72-93` (InteractiveClaudeConfig)
- **Config loading**: `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py:62-69`
- **Default values**: `packages/erk-shared/src/erk_shared/context/types.py:95-102` (InteractiveClaudeConfig.default())

## Key Behaviors

- **CLI flags ALWAYS override config values.** The config provides defaults when flags are omitted. Example: `erk agent --model claude-sonnet-4-5` overrides the `model` field from config.
- **Missing `[interactive-claude]` section** returns empty dict `{}`, so all fields use dataclass defaults.
- **Boolean coercion** via `bool()` for safety on verbose, dangerous, allow_dangerous fields.
- **String values** (like `permission_mode`) are NOT validated at load time.

## Backward Compatibility

Future versions will support `[interactive-agent]` section. Config loading will check `[interactive-agent]` first, then fall back to `[interactive-claude]` if not found. Existing configs continue working without migration.

See [PermissionMode](permission-modes.md) for how permission modes map to both Claude and Codex backends.

## Related Documentation

- [PermissionMode](permission-modes.md) - Permission mode mappings to Claude/Codex
- [Global Config](../config/global-config.md) - Complete global config structure
