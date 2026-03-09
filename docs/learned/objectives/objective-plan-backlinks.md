---
title: "Objective-Plan Backlinks"
read_when:
  - "linking plans to objectives"
  - "understanding objective_issue metadata"
  - "debugging objective-plan linkage"
  - "working with plan-header metadata"
tripwires:
  - action: "manually setting objective_issue in plan header without using update_plan_header_objective_issue()"
    warning: "Use update_plan_header_objective_issue() to set the backlink. It handles metadata block detection and formatting."
  - action: "overwriting an existing objective_issue backlink with a different value"
    warning: "_set_plan_backlink() refuses to overwrite existing backlinks to prevent accidental plan reuse across objectives. It warns and skips instead."
---

# Objective-Plan Backlinks

Bidirectional linkage between objectives and their implementation plans.

## Overview

Two references establish the link:

- **Forward**: Objective roadmap step references a plan PR via `pr: "#1234"`
- **Backward**: Plan PR's metadata block contains `objective_issue: 42`

## objective_issue Field

**Source**: `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py`

The `objective_issue` field in the plan-header metadata block stores the parent objective number:

```python
# Set the backlink
updated_body = update_plan_header_objective_issue(issue_body, objective_issue_number)

# Read the backlink
objective_number = extract_plan_header_objective_issue(issue_body)
```

## \_set_plan_backlink()

**Source**: `src/erk/cli/commands/exec/scripts/update_objective_node.py`

Fail-open function that establishes the forward link when updating an objective node:

1. Only acts when `--pr` is provided with a `#`-prefixed value
2. Fetches the plan PR's issue body
3. Checks for existing `objective_issue` value

Three outcomes:

- **Already correct**: Existing backlink matches — no action needed
- **Conflict**: Different objective already linked — warns and skips (never overwrites)
- **No backlink**: Sets the backlink via `update_plan_header_objective_issue()`

Plans without a plan-header metadata block are silently skipped (they aren't erk plans).

## Check 9: \_check_pr_backlinks

**Source**: `src/erk/cli/commands/objective/check_cmd.py`

Validation that confirms backlink consistency for all PR-referencing nodes:

- Only validates erk plans (those with plan-header metadata blocks)
- Non-erk PRs are silently accepted
- Missing backlink on an erk plan: reports as failure
- Mismatched backlink (different objective number): reports as hard error

Run validation:

```bash
erk objective check <number>
```

## Fail-Open Design

Backlink operations never block the primary workflow:

- `_set_plan_backlink()` returns status results, never raises
- Validation via Check 9 reports issues but doesn't prevent other checks
- Conflict detection prevents accidental plan reuse without blocking updates
