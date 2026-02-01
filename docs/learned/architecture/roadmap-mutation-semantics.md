---
title: Roadmap Mutation Semantics
read_when:
  - "modifying objective roadmap update logic"
  - "understanding status inference when updating roadmap steps"
  - "working with objective-roadmap-update command"
tripwires:
  - action: "setting status explicitly when --pr is provided without --status"
    warning: "When --pr is set without --status, reset status cell to '-' to allow inference. Do not preserve the existing status — it may be stale (e.g., 'blocked' after a PR is added)."
  - action: "inferring status from PR column when status is explicitly set"
    warning: "Explicit status values (done, in-progress, pending, blocked, skipped) always override PR-based inference. Only '-' allows inference."
---

# Roadmap Mutation Semantics

The `objective-roadmap-update` command uses inference-driven status updates. Understanding the interaction between the Status and PR columns is essential for correct roadmap mutations.

## Two-Tier Status Resolution

The roadmap parser uses a two-tier system to determine step status:

**Tier 1: Explicit Status Values (highest priority)**

When the Status column contains explicit values, they override PR-based inference:

| Status Column Value            | Result Status | Notes                                   |
| ------------------------------ | ------------- | --------------------------------------- |
| `done`                         | `done`        | Explicit override                       |
| `in-progress` or `in_progress` | `in_progress` | Explicit override (both forms accepted) |
| `pending`                      | `pending`     | Explicit override                       |
| `blocked`                      | `blocked`     | Explicit override                       |
| `skipped`                      | `skipped`     | Explicit override                       |

**Tier 2: PR-Based Inference (for `-` or empty values)**

When the Status column is `-` or empty, status is inferred from the PR column:

| PR Column Value | Inferred Status |
| --------------- | --------------- |
| `#123`          | `done`          |
| `plan #456`     | `in_progress`   |
| `-` or empty    | `pending`       |

## Mutation Command Behavior

When updating a roadmap step, the status column interacts with the PR column:

| Scenario                       | Status Column    | PR Column     | Behavior                     |
| ------------------------------ | ---------------- | ------------- | ---------------------------- |
| `--status done --pr #123`      | Set to `done`    | Set to `#123` | Explicit value, no inference |
| `--pr #123` (no `--status`)    | Reset to `-`     | Set to `#123` | Parser infers `done` from PR |
| `--status blocked` (no `--pr`) | Set to `blocked` | Unchanged     | Explicit value, no inference |
| `--status done` (no `--pr`)    | Set to `done`    | Unchanged     | Explicit value, no inference |

## Why Reset Status on `--pr` Without `--status`

The key insight is in `_replace_row_cells()` (lines 76–84 of `objective_roadmap_update.py`):

When `--pr` is provided without `--status`, the Status cell is reset to `"-"` rather than preserved. This prevents stale explicit status values:

- A step might have explicit status `blocked`, then a PR was added → should infer `done` from `#123`
- A step might have explicit status `pending`, then a plan PR was added → should infer `in_progress` from `plan #456`

By resetting to `"-"`, the parser's Tier 2 inference logic (`parse_roadmap()`) determines the correct status from the PR column value. Without the reset, the explicit status would take priority (Tier 1) and prevent inference.

## Parser Resolution Logic

The shared parser in `objective_roadmap_shared.py` (lines 102–115) applies a two-tier resolution system:

```python
# Tier 1: Explicit status values take priority
if status_col in ("done", "blocked", "skipped"):
    status = status_col
elif status_col in ("in-progress", "in_progress"):
    status = "in_progress"
elif status_col == "pending":
    status = "pending"
# Tier 2: Fall back to PR-column inference for "-" or legacy values
elif pr_col and pr_col != "-" and pr_col.startswith("#"):
    status = "done"
elif pr_col and pr_col.startswith("plan #"):
    status = "in_progress"
else:
    status = "pending"
```

This means:

1. If Status column has an explicit value (`done`, `in-progress`, `pending`, `blocked`, `skipped`), use it
2. Otherwise (Status is `-` or empty), infer from PR column
3. If both are empty or `-`, default to `pending`

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
- Two-tier status resolution: `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py:102-115`
- Fix commit: `4090e6df` (merged PR #6552)

## Related Documentation

- [Update Roadmap Step Command](../cli/commands/update-roadmap-step.md) — Step-level PR updates
- [Roadmap Parser](../objectives/roadmap-parser.md) — Parsing rules and CLI usage
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — The isinstance() checking pattern
