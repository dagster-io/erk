---
title: Branch Name Inference
last_audited: "2026-02-03 03:56 PT"
audit_result: edited
tripwires:
  - action: "modifying plan-header metadata format"
    warning: "branch_name field is intentionally omitted at creation. Update recovery mechanism in get_pr_for_plan.py if changing pattern."
  - action: "changing branch naming convention (P{issue}- pattern)"
    warning: "Pattern matching in get_pr_for_plan.py depends on P{issue}- format. Update inference logic if pattern changes."
read_when:
  - "Working with plan metadata (plan-header block)"
  - "Debugging missing branch_name in plan issues"
  - "Implementing PR lookup from plan issues"
---

# Branch Name Inference

## Overview

The `branch_name` field in plan metadata is **intentionally omitted at creation time**. Instead, it's populated later via `impl-signal started` or recovered via pattern matching against the current git branch.

## Why Branch Name is Omitted at Creation

When a plan is saved to GitHub (via `erk exec plan-save-to-issue`), the **branch doesn't exist yet**. The typical workflow:

1. **Save plan** → Creates GitHub issue with metadata
2. **Create branch** → User runs `gt create P{issue}-{slug}`
3. **Signal started** → `erk exec impl-signal started` populates `branch_name` field

There's a time gap between steps 1 and 2 where the plan exists but the branch doesn't. Attempting to set `branch_name` during save would require either:

- **Predicting the branch name** - Fragile, assumes user follows naming convention
- **Creating the branch immediately** - Wrong, user hasn't started work yet

## Recovery Mechanism

When `branch_name` is missing, `get_pr_for_plan.py` attempts to infer it from the current git context:

See branch name inference logic in `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py:88-99`.

```python
# Pattern: if branch_name is missing from metadata, infer from current git branch
# matching P{issue_number}- prefix. Falls back to error if no match.
```

### Recovery Pattern

1. **Check metadata** - Look for `branch_name` field in `plan-header` block
2. **Get current branch** - Query git for the current branch name
3. **Pattern match** - Check if branch starts with `P{issue_number}-`
4. **Use or error** - If match, use it; otherwise, fail with error

This recovery mechanism handles two scenarios:

- **impl-signal never ran** - User created branch manually following convention
- **impl-signal failed** - Signal command errored but user continued work

## Branch Naming Convention

The inference relies on a strict naming pattern:

```
P{issue_number}-{slug}
```

Examples:

- `P1234-add-auth` - Issue #1234, slug "add-auth"
- `P5678-fix-typo` - Issue #5678, slug "fix-typo"

**CRITICAL:** If this pattern changes, update:

1. **Branch creation logic** - Where branches are created
2. **Pattern matching** - The `startswith(f"P{issue_number}-")` check
3. **This documentation** - Pattern examples

## When Recovery Fails

If the current branch doesn't match `P{issue_number}-`, the error message is:

```
Issue #1234 plan-header has no branch_name field
```

**Common causes:**

- Working from wrong branch (e.g., on `master` instead of feature branch)
- Branch name doesn't follow convention (e.g., `feature/1234` instead of `P1234-feature`)
- impl-signal never ran and user picked non-standard name

**Fix:** Ensure you're on a branch following the `P{issue}-{slug}` pattern, or manually update the plan-header metadata with the correct `branch_name`.

## Defense-in-Depth Design

This is an example of **fail-open pattern** (see [Fail-Open Patterns](../architecture/fail-open-patterns.md)):

1. **Primary mechanism**: impl-signal sets branch_name explicitly
2. **Fallback mechanism**: Pattern matching infers from git context
3. **Root cause prevention**: Fix impl-signal to succeed reliably

The fallback doesn't just mask errors - it enables manual workflows where impl-signal wasn't used (e.g., implementing a plan created by another developer).

## Related Documentation

- [Plan Metadata Fields](plan-metadata-fields.md) - Complete metadata format
- [Fail-Open Patterns](../architecture/fail-open-patterns.md) - Defense-in-depth design
- [PR Metadata Format](../pr-operations/pr-metadata-format.md) - How branch_name is used in PR footers
