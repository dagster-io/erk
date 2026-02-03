---
title: PermissionMode Abstraction
last_audited: "2026-02-03 03:56 PT"
audit_result: edited
tripwires:
  - action: "modifying PermissionMode enum or permission mode mappings"
    warning: "Two permission_mode_to_*() functions must stay in sync (Claude backend and Codex backend). Update both when changing mappings."
  - action: "changing permission_mode_to_*() implementations"
    warning: "Verify both Claude and Codex backend implementations maintain identical enum-to-mode mappings."
read_when:
  - "Working with interactive agent permissions"
  - "Implementing Codex or Claude backend integration"
  - "Modifying permission mode configuration"
---

# PermissionMode Abstraction

> **Status: Design Document** — The `PermissionMode` enum and `permission_mode_to_claude()` functions described here are a planned abstraction. Check the codebase for current implementation state before relying on specific types or function names.

## Overview

`PermissionMode` is an erk-level abstraction that maps to backend-specific permission systems for both Claude Code CLI and Codex. This allows erk to specify a single permission model that translates correctly to each backend's flags.

## Backend Mappings

This is the core high-value content — the cross-backend mapping not visible in any single file:

| Erk PermissionMode | Claude Code CLI                  | Codex exec            | Codex TUI                                 |
| ------------------ | -------------------------------- | --------------------- | ----------------------------------------- |
| `safe`             | `--permission-mode default`      | `--sandbox read-only` | `--sandbox read-only -a untrusted`        |
| `edits`            | `--permission-mode acceptEdits`  | `--full-auto`         | `--sandbox workspace-write -a on-request` |
| `plan`             | `--permission-mode plan`         | `--sandbox read-only` | `--sandbox read-only -a never`            |
| `dangerous`        | `--dangerously-skip-permissions` | `--yolo`              | `--yolo`                                  |

For `dangerous` mode, erk must pass both `--permission-mode bypassPermissions` AND `--dangerously-skip-permissions` for Claude.

## Two Functions That Must Stay in Sync

There are (or will be) two `permission_mode_to_*()` functions:

1. **Claude backend** (`packages/erk-shared/src/erk_shared/context/types.py`): `permission_mode_to_claude()` maps `PermissionMode` to Claude CLI flags
2. **Codex backend**: Maps `PermissionMode` to Codex CLI flags

**CRITICAL**: These functions must maintain identical enum-to-backend mappings. If one is updated, both must be updated.

## Verification Checklist

When modifying permission mode mappings:

- [ ] Both `permission_mode_to_*()` functions updated
- [ ] Mapping table in this doc updated to match code
- [ ] Test coverage for each mode on both backends
- [ ] Config file examples updated if field names change

## Related Documentation

- [Interactive Agent Config](interactive-agent-config.md) - Configuration format for interactive agents
