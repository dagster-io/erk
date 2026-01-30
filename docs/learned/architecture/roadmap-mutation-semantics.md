---
title: Roadmap Mutation Semantics
read_when:
  - "modifying objective roadmap update logic"
  - "understanding status inference when updating roadmap steps"
  - "working with objective-roadmap-update command"
tripwires:
  - action: "setting status explicitly when --pr is provided without --status"
    warning: "When --pr is set without --status, reset status cell to '-' to allow inference. Do not preserve the existing status — it may be stale (e.g., 'blocked' after a PR is added)."
---

# Roadmap Mutation Semantics

The `objective-roadmap-update` command uses inference-driven status updates. Understanding the interaction between the Status and PR columns is essential for correct roadmap mutations.

## Inference Rules

When updating a roadmap step, the status column interacts with the PR column:

| Scenario                       | Status Column    | PR Column     | Behavior                     |
| ------------------------------ | ---------------- | ------------- | ---------------------------- |
| `--status done --pr #123`      | Set to `done`    | Set to `#123` | Explicit override            |
| `--pr #123` (no `--status`)    | Reset to `-`     | Set to `#123` | Parser infers `done` from PR |
| `--status blocked` (no `--pr`) | Set to `blocked` | Unchanged     | Explicit override            |
| `--status done` (no `--pr`)    | Set to `done`    | Unchanged     | Explicit override            |

## Why Reset Status on `--pr` Without `--status`

The key insight is in `_replace_row_cells()` (lines 76–84 of `objective_roadmap_update.py`):

When `--pr` is provided without `--status`, the Status cell is reset to `"-"` rather than preserved. This prevents stale status values:

- A step might have been `blocked`, then a PR was added → status should now be `done`
- A step might have been `pending`, then a plan PR was added → status should now be `in_progress`

By resetting to `"-"`, the parser's inference logic (`parse_roadmap()`) determines the correct status from the PR column value.

## Parser Inference Logic

The shared parser in `objective_roadmap_shared.py` (lines 107–115) applies these inference rules:

| Status Column Value    | PR Column Value      | Inferred Status                |
| ---------------------- | -------------------- | ------------------------------ |
| `blocked` or `skipped` | (any)                | Keep as-is (explicit override) |
| (any other value)      | Starts with `#`      | `done`                         |
| (any other value)      | Starts with `plan #` | `in_progress`                  |
| (any other value)      | Empty or `-`         | `pending`                      |

## LBYL Pattern in Update Command

The update command uses LBYL throughout:

```python
# Validate before processing
if new_status is None and new_pr is None:
    # Error: must provide at least one of --status or --pr

# Check result type before accessing fields
if isinstance(issue, IssueNotFound):
    # Handle missing issue

# Check parse result before using
if not phases:
    # Handle empty roadmap
```

## Reference Implementation

- Mutation logic: `src/erk/cli/commands/exec/scripts/objective_roadmap_update.py:53-86`
- Parser inference: `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py:107-115`

## Related Documentation

- [Roadmap Parser](../objectives/roadmap-parser.md) — Parsing rules and CLI usage
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — The isinstance() checking pattern
