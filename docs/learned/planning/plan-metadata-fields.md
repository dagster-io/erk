---
title: Plan Metadata Fields
read_when:
  - "working with .impl/ folder structure"
  - "implementing get-pr-for-plan or learn workflows"
  - "debugging plan-to-PR associations"
tripwires:
  - score: 5
    action: "get-pr-for-plan failing to find PR"
    warning: "The branch_name field in .impl/metadata.json is required for get-pr-for-plan to look up the PR. If missing, the command cannot find the associated PR."
    context: "Learn workflows depend on branch_name to discover which PR implemented a plan. Without it, session-to-PR association breaks."
---

# Plan Metadata Fields

## Overview

Plans stored in `.impl/` folders contain metadata files that track implementation state and associate plans with git branches and GitHub PRs.

## .impl/metadata.json

The primary metadata file for a plan implementation.

**Required Fields:**

```json
{
  "branch_name": "feature-branch-name",
  "issue_number": 1234,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Field Descriptions:**

| Field          | Type               | Required | Purpose                                                       |
| -------------- | ------------------ | -------- | ------------------------------------------------------------- |
| `branch_name`  | string             | **YES**  | Git branch where plan is implemented. Required for PR lookup. |
| `issue_number` | integer            | YES      | GitHub issue number containing the plan                       |
| `created_at`   | ISO 8601 timestamp | YES      | When the implementation environment was created               |

## branch_name Field Requirement

The `branch_name` field is **critical** for plan-to-PR association workflows:

**Used By:**

- `erk exec get-pr-for-plan` - Looks up PR by branch name
- `erk learn` workflows - Associates sessions with PRs
- PR sync commands - Updates PR metadata from plan state

**Lookup Pattern:**

```python
metadata = read_metadata_json()
branch_name = metadata["branch_name"]  # REQUIRED

# Find PR via branch name
pr = gh_api.get_pr_for_branch(branch_name)
```

**If Missing:**

- `get-pr-for-plan` fails with "cannot find PR"
- Learn workflows cannot associate sessions with PRs
- PR metadata sync commands cannot determine which PR to update

## .impl/issue.json (Legacy)

Some plans may have `.impl/issue.json` instead of or in addition to `metadata.json`. This is a legacy format.

**Migration:** When encountering `issue.json`, prefer reading `metadata.json` if present. The `metadata.json` format is canonical.

## Example: Valid .impl/ Folder

```
.impl/
├── plan.md              # Plan content (immutable during implementation)
├── metadata.json        # Plan metadata with branch_name
└── notes.md            # Optional implementation notes
```

## Related Patterns

- [Plan Implement Customization](../cli/plan-implement-customization.md) - How .impl/ folders are created
- [Plan Save](../commands/plan-save.md) - Saving plans to GitHub issues
- [Learn Workflows](learn-workflows.md) - Session-to-PR association

## Attribution

Pattern documented from investigation of learn workflow requirements (Issue #6372).
