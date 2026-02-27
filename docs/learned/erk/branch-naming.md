---
title: Branch Naming Conventions
read_when:
  - "creating or modifying branch name generation"
  - "extracting issue or objective numbers from branch names"
  - "working with generate_planned_pr_branch_name(), or extract functions"
tripwires:
  - action: "constructing branch names manually"
    warning: "Use generate_planned_pr_branch_name() for consistent objective ID encoding."
  - action: "trying to extract plan issue number from branch name"
    warning: "Plan issue numbers are NOT encoded in branch names. Use plan-ref.json as the sole source of truth."
last_audited: "2026-02-24 00:00 PT"
audit_result: clean
---

# Branch Naming Conventions

All erk-managed plan branches use the `plnd/` prefix. Plan issue numbers are **not** encoded in branch names — `.erk/impl-context/plan-ref.json` is the sole source of truth for plan-to-branch mapping.

## Canonical Function

<!-- Source: packages/erk-shared/src/erk_shared/naming.py, generate_planned_pr_branch_name -->

See `generate_planned_pr_branch_name()` in `packages/erk-shared/src/erk_shared/naming.py`. Accepts `title`, `timestamp`, and optional `objective_id` keyword argument.

## Branch Format

**Without objective:**

```
plnd/{slug}-{MM-DD-HHMM}
```

**With objective:**

```
plnd/O{objective}-{slug}-{MM-DD-HHMM}
```

**Examples:**

- `plnd/fix-auth-bug-01-15-1430`
- `plnd/O456-fix-auth-bug-01-15-1430`

**Constraints:**

- Prefix (`plnd/` or `plnd/O{obj}-`) + sanitized title must not exceed 31 characters
- Title is sanitized via `sanitize_worktree_name()` (lowercased, special chars replaced with hyphens)
- Timestamp suffix: `-MM-DD-HHMM` format
- Trailing hyphens stripped before timestamp

## Plan-to-Branch Mapping

Since branch names do not encode plan issue numbers, `plan-ref.json` is the sole mechanism for mapping plans to branches:

- **`.erk/impl-context/plan-ref.json`** in each worktree contains `provider`, `plan_id`, `url`, etc.
- **`PlannedPRBackend.get_plan_for_branch()`** resolves plans by looking up the PR associated with the branch

## Extraction Functions

### extract_objective_number()

<!-- Source: packages/erk-shared/src/erk_shared/naming.py, extract_objective_number -->

Extracts the optional objective ID from a `plnd/` branch name. See `extract_objective_number()` in `packages/erk-shared/src/erk_shared/naming.py`.

- `"plnd/O456-fix-auth-01-15-1430"` -> `456`
- `"plnd/fix-auth-bug-01-15-1430"` -> `None`

## Usage Sites

All branch creation codepaths use `generate_planned_pr_branch_name()`:

| Codepath               | File                                             |
| ---------------------- | ------------------------------------------------ |
| Plan save (planned-PR) | `src/erk/cli/commands/exec/scripts/plan_save.py` |
| One-shot dispatch      | `src/erk/cli/commands/one_shot_dispatch.py`      |

The one-shot dispatch also has a fallback for non-plan tasks: `oneshot-{slug}-{MM-DD-HHMM}`.

## Related Topics

- [Plan Lifecycle](../planning/lifecycle.md) - Plan states and transitions
