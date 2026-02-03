---
title: SandboxMode Abstraction
last_audited: "2026-02-03 03:56 PT"
audit_result: edited
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

> **Status: Design Document** — The `SandboxMode` enum and `_sandbox_to_permission_mode()` functions described here are a planned abstraction. Check the codebase for current implementation state before relying on specific types or function names.

## Overview

`SandboxMode` is an erk-level abstraction that maps to backend-specific permission systems for both Claude Code CLI and Codex. This allows erk to specify a single permission model that translates correctly to each backend's flags.

## Backend Mappings

This is the core high-value content — the cross-backend mapping not visible in any single file:

| Erk SandboxMode | Claude Code CLI                  | Codex exec            | Codex TUI                                 |
| --------------- | -------------------------------- | --------------------- | ----------------------------------------- |
| `safe`          | `--permission-mode default`      | `--sandbox read-only` | `--sandbox read-only -a untrusted`        |
| `edits`         | `--permission-mode acceptEdits`  | `--full-auto`         | `--sandbox workspace-write -a on-request` |
| `plan`          | `--permission-mode plan`         | `--sandbox read-only` | `--sandbox read-only -a never`            |
| `dangerous`     | `--dangerously-skip-permissions` | `--yolo`              | `--yolo`                                  |

For `dangerous` mode, erk must pass both `--permission-mode bypassPermissions` AND `--dangerously-skip-permissions` for Claude.

## Two Functions That Must Stay in Sync

There are (or will be) two `_sandbox_to_permission_mode()` functions:

1. **Claude backend** (`src/erk/core/interactive_claude.py`): Maps `SandboxMode` to Claude CLI flags
2. **Codex backend**: Maps `SandboxMode` to Codex CLI flags

**CRITICAL**: These functions must maintain identical enum-to-backend mappings. If one is updated, both must be updated.

## Verification Checklist

When modifying sandbox mode mappings:

- [ ] Both `_sandbox_to_permission_mode()` functions updated
- [ ] Mapping table in this doc updated to match code
- [ ] Test coverage for each mode on both backends
- [ ] Config file examples updated if field names change

## Related Documentation

- [Interactive Agent Config](interactive-agent-config.md) - Configuration format for interactive agents
