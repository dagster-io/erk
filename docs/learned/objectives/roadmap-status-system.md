---
title: Roadmap Status System
read_when:
  - "understanding how objective roadmap status is determined"
  - "working with roadmap step status values"
  - "implementing objective roadmap parsing logic"
tripwires:
  - action: "inferring status from PR column when explicit status is set"
    warning: "Explicit status values (done, in-progress, pending, blocked, skipped) always take priority over PR-based inference. Only '-' or empty values trigger PR-based inference."
  - action: "treating status as a single-source value"
    warning: "Status resolution uses a two-tier system: explicit values first, then PR-based inference. Always check both the Status and PR columns."
---

# Roadmap Status System

Objective roadmap tables use a **two-tier status resolution system** that combines explicit status values with PR-based inference to determine each step's current status.

## Two-Tier Resolution System

### Tier 1: Explicit Status Values (Highest Priority)

When the Status column contains one of these explicit values, it takes priority over any PR-based inference:

| Status Value                 | Result      | Meaning                                |
| ---------------------------- | ----------- | -------------------------------------- |
| `done`                       | done        | Step is complete                       |
| `in-progress`, `in_progress` | in_progress | Step is actively being worked on       |
| `pending`                    | pending     | Step is waiting to be started          |
| `blocked`                    | blocked     | Step cannot proceed (dependency issue) |
| `skipped`                    | skipped     | Step will not be implemented           |

**Key insight:** Both `in-progress` (hyphenated) and `in_progress` (underscore) are accepted and normalized to `in_progress` internally.

### Tier 2: PR-Based Inference (for `-` or empty)

When the Status column is `-` or empty, the parser infers status from the PR column:

| PR Column Value | Inferred Status | Logic                             |
| --------------- | --------------- | --------------------------------- |
| `#123`          | done            | PR exists → work is complete      |
| `plan #456`     | in_progress     | Plan exists → work is in progress |
| `-` or empty    | pending         | No PR → work hasn't started       |

## Priority Ordering

The resolution logic prioritizes explicit values over inference:

```python
# Tier 1: Explicit status values take priority
if status_col in ("done", "blocked", "skipped"):
    status = status_col
elif status_col in ("in-progress", "in_progress"):
    status = "in_progress"
elif status_col == "pending":
    status = "pending"
# Tier 2: Fall back to PR-column inference
elif pr_col and pr_col != "-" and pr_col.startswith("#"):
    status = "done"
elif pr_col and pr_col.startswith("plan #"):
    status = "in_progress"
else:
    status = "pending"
```

This means:

1. **Explicit beats inference:** If Status is `blocked`, it stays `blocked` even if PR is `#123`
2. **Dash enables inference:** Status `-` with PR `#123` infers `done`
3. **Empty defaults to pending:** Both columns `-` or empty → `pending`

## Example Resolutions

| Status Column | PR Column  | Final Status | Reasoning                          |
| ------------- | ---------- | ------------ | ---------------------------------- |
| `done`        | `-`        | done         | Explicit value takes priority      |
| `-`           | `#123`     | done         | Inference from PR                  |
| `blocked`     | `#123`     | blocked      | Explicit overrides PR              |
| `-`           | `plan #45` | in_progress  | Inference from plan PR             |
| `pending`     | `#123`     | pending      | Explicit overrides PR (manual set) |
| `-`           | `-`        | pending      | Default when both empty            |

## When to Use Each Tier

### Use Explicit Status (Tier 1) When:

- Marking a step as `blocked` due to external dependencies
- Marking a step as `skipped` because it's no longer needed
- Manually overriding status for special cases (e.g., `pending` even though PR exists)

### Use Inference (Tier 2) When:

- Normal workflow: PR created → status becomes `done`
- Plan saved → status becomes `in_progress`
- Most common case: let the PR column drive status

## Implementation Reference

- **Parser logic:** `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py:102-115`
- **Fix commit:** `4090e6df` (PR #6552)
- **Mutation commands:** `objective-roadmap-update`, `update-roadmap-step`

## Related Documentation

- [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) — How mutation commands interact with the two-tier system
- [Roadmap Parser](roadmap-parser.md) — Full parsing rules and validation
