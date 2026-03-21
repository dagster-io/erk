---
title: Action Plan Pattern
read_when:
  - "implementing a command with --dry-run capability"
  - "adding preview mode to a command that mutates state"
  - "replacing boolean parameter threading with typed plan objects"
tripwires:
  - action: "using a boolean flag to choose between preview and execute paths"
    warning: "Use the action plan pattern instead. Build a frozen dataclass describing what would happen, then display (dry-run) or execute. This avoids conditional logic scattered through the execution path."
  - action: "combining --script and --dry-run flags"
    warning: "--dry-run forces human-readable output and disables --script mode. See teleport_cmd.py:115-116 for the pattern: `if dry_run: script = False`."
---

# Action Plan Pattern

## Pattern

Build a frozen dataclass describing mutations, then either display (dry-run) or execute based on a flag. The plan object carries all state needed for both paths.

## Motivation

Commands that support preview/dry-run often devolve into conditional logic scattered through execution. The action plan pattern separates concerns:

1. **Gather state** — Read all inputs, fetch remote data, compute divergence
2. **Build plan** — Construct a frozen dataclass summarizing what would happen
3. **Decide** — Display the plan (dry-run) or execute it (normal mode)

This replaces boolean parameter threading with a typed, immutable plan object. The display and execution paths each receive the full plan and operate independently.

## Case Study: TeleportPlan

`TeleportPlan` in `packages/erk-slots/src/erk_slots/teleport_cmd.py:38-56`:

```python
@dataclass(frozen=True)
class TeleportPlan:
    """Describes what a teleport operation will do, without executing it."""
    pr_number: int
    branch_name: str
    base_ref_name: str
    ahead: int
    behind: int
    staged: list[str]
    modified: list[str]
    untracked: list[str]
    is_new_slot: bool
    branch_exists_locally: bool
    is_graphite_managed: bool
    trunk: str
    sync: bool
    has_slot: bool
```

Two-phase flow (see `slot_teleport()` at line 66):

1. **Build plan**: `_teleport_in_place()` or `_teleport_new_slot()` returns a `TeleportPlan`
2. **Decide**:
   - `dry_run=True` → `_display_dry_run_report(teleport_plan)` then exit
   - `dry_run=False` → `_execute_in_place_teleport()` or `_execute_new_slot_teleport()`

## When to Use

- Commands with `--dry-run` or preview capability
- Force-reset operations where showing "what would be lost" before executing is valuable
- Commands that need to display a summary before making irreversible changes

## Integration: --dry-run Disables --script

When `--dry-run` is active, disable `--script` mode — dry-run produces human-readable output, not shell activation scripts:

```python
# Dry-run forces human-readable output (no script mode)
if dry_run:
    script = False
```

Source: `packages/erk-slots/src/erk_slots/teleport_cmd.py:115-116`

## Related Documentation

- [Exec Script Patterns](../cli/exec-script-patterns.md) — General patterns for CLI commands
