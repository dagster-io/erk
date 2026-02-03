---
title: SandboxMode Abstraction
tripwires:
  - action: "modifying SandboxMode enum or permission mode mappings"
    warning: "Two _sandbox_to_permission_mode() functions must stay in sync (Claude backend and Codex backend). Update both when changing mappings."
  - action: "changing _sandbox_to_permission_mode() implementations"
    warning: "Verify both Claude and Codex backend implementations maintain identical enum-to-mode mappings."
read_when:
  - "Working with interactive agent permissions"
  - "Implementing Codex or Claude backend integration"
  - "Modifying permission mode configuration"
---

# SandboxMode Abstraction

## Overview

`SandboxMode` is an erk-level abstraction that maps to backend-specific permission systems for both Claude Code CLI and Codex. This allows erk to specify a single permission model that translates correctly to each backend's flags.

## SandboxMode Enum

The `SandboxMode` enum defines four permission levels:

| Mode        | Description                                                  |
| ----------- | ------------------------------------------------------------ |
| `safe`      | Read-only operations with permission prompts                 |
| `edits`     | Can write to workspace, with approval based on backend model |
| `plan`      | Read-only exploration for planning (no permission prompts)   |
| `dangerous` | Bypass all permission checks                                 |

## Backend Mappings

### Complete Mapping Table

| Erk SandboxMode | Claude Code CLI                  | Codex exec            | Codex TUI                                 |
| --------------- | -------------------------------- | --------------------- | ----------------------------------------- |
| `safe`          | `--permission-mode default`      | `--sandbox read-only` | `--sandbox read-only -a untrusted`        |
| `edits`         | `--permission-mode acceptEdits`  | `--full-auto`         | `--sandbox workspace-write -a on-request` |
| `plan`          | `--permission-mode plan`         | `--sandbox read-only` | `--sandbox read-only -a never`            |
| `dangerous`     | `--dangerously-skip-permissions` | `--yolo`              | `--yolo`                                  |

### Claude Code CLI Mapping

Claude Code uses `--permission-mode` with four standard values:

- **default**: Default behavior with permission prompts
- **acceptEdits**: Accepts edit operations without prompts
- **plan**: Read-only mode for exploration and planning
- **bypassPermissions**: Bypass all permissions (requires additional `--dangerously-skip-permissions` flag)

For `dangerous` mode, erk must pass both `--permission-mode bypassPermissions` AND `--dangerously-skip-permissions`.

### Codex Mapping

Codex has two operational modes with different flag sets:

#### Codex exec (non-interactive)

- **`--sandbox read-only`**: Read-only operations (maps to `safe` and `plan`)
- **`--full-auto`**: Workspace write + auto-approve (maps to `edits`)
- **`--yolo`**: Bypass all permissions (maps to `dangerous`)

#### Codex TUI (interactive)

Combines sandbox level with approval mode (`-a` / `--ask-for-approval`):

- **`--sandbox read-only -a untrusted`**: Prompt for untrusted commands (maps to `safe`)
- **`--sandbox workspace-write -a on-request`**: Model decides when to ask (maps to `edits`)
- **`--sandbox read-only -a never`**: Never prompt, read-only (maps to `plan`)
- **`--yolo`**: Bypass everything (maps to `dangerous`)

## Implementation Pattern

### Two Functions That Must Stay in Sync

There are two `_sandbox_to_permission_mode()` functions that perform this mapping:

1. **Claude backend** (`src/erk/core/interactive_claude.py`): Maps `SandboxMode` → Claude CLI flags
2. **Codex backend** (`src/erk/core/prompt_executor.py` or similar): Maps `SandboxMode` → Codex CLI flags

**CRITICAL**: These functions must maintain identical enum-to-backend mappings. If one is updated, both must be updated to preserve consistent behavior across backends.

### Verification Checklist

When modifying sandbox mode mappings:

- [ ] Both `_sandbox_to_permission_mode()` functions updated
- [ ] Mapping table in this doc updated to match code
- [ ] Test coverage for each mode on both backends
- [ ] Config file examples updated if field names change

## Related Documentation

- [Codex CLI Reference](../integrations/codex/codex-cli-reference.md) - Complete Codex flag documentation
- [Interactive Agent Config](interactive-agent-config.md) - Configuration format for interactive agents
