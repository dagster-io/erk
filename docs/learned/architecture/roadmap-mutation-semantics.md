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

## Objective-Level vs Step-Level Commands

Erk provides two commands for mutating objective roadmap tables:

### `objective-roadmap-update` (Objective-Level)

**Purpose:** Update multiple cells in a single step row with flexible overrides.

**Usage:**

```bash
erk exec objective-roadmap-update 6423 --step 1.3 --status done --pr "#6500"
```

**Capabilities:**

- Can set status explicitly with `--status`
- Can set PR reference with `--pr`
- Can update either field independently or both together
- Preserves status when `--pr` not provided
- Resets status to "-" when `--pr` provided without `--status` (for inference)

**Use When:** You need precise control over both status and PR columns, especially when overriding status (e.g., marking as "blocked" or "skipped").

### `update-roadmap-step` (Step-Level)

**Purpose:** Atomically update a step's PR cell with automatic status inference.

**Usage:**

```bash
erk exec update-roadmap-step 6423 --step 1.3 --pr "plan #6464"
```

**Capabilities:**

- Updates only the PR cell
- Always resets status to "-" for parser inference
- Simpler mental model: "set step X's PR to Y"
- Designed for plan-save workflow integration

**Use When:** You're updating PR references and want automatic status inference (most common case).

### PR Cell Mutation Pattern

Both commands use the same underlying regex pattern for PR cell replacement:

```python
# Find the step row pattern:
r'\|\s*{step_id}\s*\|.*?\|.*?\|(.*?)\|'

# The fourth column (PR cell) is captured and replaced
```

This pattern works across all phases in the roadmap table.

### Shared Parser

Both commands use `objective_roadmap_shared.py` for:

- Parsing the markdown roadmap table
- Extracting phases and steps
- Applying status inference rules
- Validating step IDs

## Reference Implementation

- Objective-level mutation: `src/erk/cli/commands/exec/scripts/objective_roadmap_update.py:53-86`
- Step-level mutation: `src/erk/cli/commands/exec/scripts/update_roadmap_step.py:48-87`
- Parser inference: `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py:107-115`

## Related Documentation

- [Update Roadmap Step Command](../cli/commands/update-roadmap-step.md) — Step-level PR updates
- [Roadmap Parser](../objectives/roadmap-parser.md) — Parsing rules and CLI usage
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — The isinstance() checking pattern
