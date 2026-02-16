---
title: PermissionMode Abstraction
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
tripwires:
  - action: "modifying PermissionMode enum or permission mode mappings"
    warning: "permission_mode_to_claude() (and future permission_mode_to_codex()) must stay in sync. Update both when changing mappings."
  - action: "changing permission_mode_to_claude() (or future permission_mode_to_codex()) implementations"
    warning: "Verify both Claude and Codex backend implementations maintain identical enum-to-mode mappings."
read_when:
  - "Working with interactive agent permissions"
  - "Implementing Codex or Claude backend integration"
  - "Modifying permission mode configuration"
---

# PermissionMode Abstraction

## Cross-Cutting Pattern

`PermissionMode` is erk's abstraction layer that separates **what permission level we want** from **how each agent backend implements it**. This allows erk to specify permissions once while supporting multiple agent backends (Claude, Codex) with different CLI flags and semantics.

**Why this exists:** Claude uses `--permission-mode acceptEdits`, Codex uses `--full-auto`, but both mean "let the agent edit files without prompting." Without abstraction, every launch site would need backend-specific conditionals. The enum centralizes the decision.

## The Dangerous Mode Anomaly

Most modes map one-to-one: `PermissionMode.edits` → `--permission-mode acceptEdits`. But `dangerous` requires **two flags** for Claude:

```bash
claude --permission-mode bypassPermissions --dangerously-skip-permissions
```

**Why both flags are required:** Claude's permission system has two layers. `bypassPermissions` mode alone allows dangerous operations but still prompts. Only when combined with `--dangerously-skip-permissions` does it fully bypass confirmation dialogs.

This dual-flag requirement is hardcoded into the mapping layer, not exposed to callers. Code using `PermissionMode.dangerous` doesn't need to know about Claude's two-flag implementation.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/agent_launcher/real.py, build_claude_args -->

See `build_claude_args()` in `packages/erk-shared/src/erk_shared/gateway/agent_launcher/real.py` for the `if config.dangerous: args.append("--dangerously-skip-permissions")` pattern that supplements the permission mode mapping.

## Backend Mapping Synchronization Problem

When Codex backend support is added, there will be two mapping functions:

1. `permission_mode_to_claude()` — already exists
2. `permission_mode_to_codex()` — future

**Critical invariant:** Both functions must map the same `PermissionMode` enum to equivalent backend semantics:

| PermissionMode | Claude                             | Codex (future)        |
| -------------- | ---------------------------------- | --------------------- |
| `safe`         | `default`                          | `--sandbox read-only` |
| `edits`        | `acceptEdits`                      | `--full-auto`         |
| `plan`         | `plan`                             | `--sandbox read-only` |
| `dangerous`    | + `--dangerously-skip-permissions` | `--yolo`              |

<!-- Source: docs/learned/integrations/codex/codex-cli-reference.md, Permission/Sandbox Mapping table -->

The complete cross-backend mapping table (including Codex TUI mode differences) is maintained in [Codex CLI Reference](../integrations/codex/codex-cli-reference.md#permissionsandbox-mapping-for-erk).

**Why synchronization matters:** If one backend updates its mode mappings but the other doesn't, the same `PermissionMode` value will produce different security postures across backends. A config that's safe in Claude could become dangerous in Codex, or vice versa.

## Decision: Why a Mapping Function Instead of Method

The implementation uses a standalone function `permission_mode_to_claude()` rather than a method on `InteractiveAgentConfig`:

```python
# Actual pattern
permission_mode = permission_mode_to_claude(config.permission_mode)

# NOT this
permission_mode = config.to_claude_permission_mode()
```

**Why:** The `PermissionMode` enum is defined in `context/types.py` alongside the mapping dictionary. The mapping function lives next to the data it transforms. This makes the single-backend → multi-backend migration mechanical: copy the pattern for `permission_mode_to_codex()` and maintain the parallel structure.

If the mapping were a method, it would tie backend-specific knowledge to the config type, requiring the config to know about every backend's flag syntax.

<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, permission_mode_to_claude and _PERMISSION_MODE_TO_CLAUDE -->

See `permission_mode_to_claude()` and `_PERMISSION_MODE_TO_CLAUDE` dict in `packages/erk-shared/src/erk_shared/context/types.py` for the current mapping implementation.

## Verification Checklist

When modifying permission mode mappings:

- [ ] Update `permission_mode_to_claude()` mapping dictionary
- [ ] Update `permission_mode_to_codex()` mapping dictionary (when it exists)
- [ ] Verify both backends produce equivalent security postures for each mode
- [ ] Update cross-backend table in [Codex CLI Reference](../integrations/codex/codex-cli-reference.md)
- [ ] Check test coverage for each mode in both backends

## Related Documentation

- [Interactive Agent Config](interactive-agent-config.md) — Config-level defaults and CLI override semantics
- [Codex CLI Reference](../integrations/codex/codex-cli-reference.md) — Complete cross-backend mapping table
