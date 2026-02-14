---
title: Incomplete Command/Workflow Removal
read_when:
  - removing CLI command functions or workflow triggers
  - deleting command infrastructure
  - refactoring command dispatch systems
tripwires:
  - action: "Before removing CLI command functions, workflow triggers, or command infrastructure"
    warning: "When removing command infrastructure: (1) Search for command name in WORKFLOW_COMMAND_MAP and similar dispatch maps in src/erk/cli/constants.py, (2) Remove or update map entries that reference the deleted function, (3) Verify no dead references remain using grep -r \"command_name\" src/erk/cli/, (4) Check for related test files that should be removed"
    score: 6
last_audited: "2026-02-14"
audit_result: clean
---

# Incomplete Command/Workflow Removal

When removing CLI command infrastructure, workflow triggers, or command functions, dispatch maps and configuration dictionaries must also be cleaned up. Dead map entries pass code review but cause runtime failures.

## Why This Matters

Dead map entries look valid in isolation:

```python
WORKFLOW_COMMAND_MAP: dict[str, str] = {
    "plan-implement": DISPATCH_WORKFLOW_NAME,
    "objective-reconcile": "objective-reconcile.yml",  # Dead reference!
}
```

This code passes type checking and static analysis. The error only manifests at runtime when a user runs `erk launch objective-reconcile`, potentially weeks or months after the PR lands.

## The Pattern

When removing command infrastructure:

1. **Search dispatch maps**: Check `WORKFLOW_COMMAND_MAP` and similar maps in `src/erk/cli/constants.py`
2. **Remove map entries**: Delete or update entries that reference the deleted function
3. **Grep for references**: Run `grep -r "command_name" src/erk/cli/` to verify no dead references remain
4. **Check test files**: Remove related test files that tested the deleted command

## Example

PR #6882 removed `_trigger_objective_reconcile()` from `launch_cmd.py` but initially left the `objective-reconcile` entry in `WORKFLOW_COMMAND_MAP` at `constants.py:28`. This created a dead reference that would fail at runtime with `AttributeError`.

## Why Static Analysis Fails

String-based command routing bypasses type checking:

```python
# The map entry uses a string key
workflow_file = WORKFLOW_COMMAND_MAP["objective-reconcile"]  # Type-checks fine

# The actual function lookup happens via string dispatch
func = getattr(module, f"_trigger_{command_name}")  # Runtime AttributeError
```

Type checkers can't verify that string keys in dispatch maps correspond to actual function names.

## Related Context

- Command dispatch systems: `src/erk/cli/constants.py`
- Workflow triggers: `src/erk/cli/commands/launch_cmd.py`
- Command infrastructure: Various `*_cmd.py` files in `src/erk/cli/commands/`
