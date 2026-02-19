---
title: Batch Objective Node Update Pattern
read_when:
  - "modifying objective node status in bulk"
  - "working with --all-unblocked dispatch"
  - "asserting on FakeGitHubIssues.updated_bodies in tests"
tripwires:
  - action: "asserting on FakeGitHubIssues.updated_bodies without filtering by issue number"
    warning: "updated_bodies is global across all issues. Filter to your target issue number to avoid false positives from plan issue creation side effects."
last_audited: "2026-02-19 00:00 PT"
audit_result: clean
---

# Batch Objective Node Update Pattern

When dispatching `--all-unblocked` nodes, multiple objective nodes need status updates. Rather than N separate GitHub API write cycles, the batch pattern uses fetch-once-accumulate-write-once.

## Problem

Dispatching N unblocked nodes individually causes N API write cycles for the objective issue body. Each write is a full-body update, so intermediate writes are wasted.

## Solution: `_batch_update_objective_nodes()`

<!-- Source: src/erk/cli/commands/objective/plan_cmd.py, _batch_update_objective_nodes -->

See `_batch_update_objective_nodes()` in `src/erk/cli/commands/objective/plan_cmd.py:342-404`.

The function implements a fetch-once-accumulate-write-once pattern:

1. Fetch the objective issue body once
2. Apply all node updates in memory using `_replace_node_refs_in_body()` (surgical replacement, not full-body rewrite)
3. Write the accumulated body back once
4. If v2 format (separate comment body), do the same fetch-accumulate-write for the comment

## Two-Phase Dispatch

The overall `--all-unblocked` dispatch is two-phase:

1. **O(N) API calls** for PR creation (one per unblocked node)
2. **O(1) API call** for objective body update (batch all node status changes)

## Partial Failure Handling

If some PR creations fail during phase 1:

- Successful nodes are marked `"planning"` in the batch update
- Failed nodes remain `"pending"` — no rollback is attempted
- The batch update only includes nodes with successful PR creations

## v2 Format Handling

Objectives can store node data in two places:

1. The issue body (always present)
2. A separate comment body (v2 format, identified by `objective_comment_id` in metadata)

`_batch_update_objective_nodes()` handles both: first the issue body, then the comment body if present. Both follow the same fetch-accumulate-write pattern.

## Testing: Filter `updated_bodies` by Issue Number

`FakeGitHubIssues.updated_bodies` is a **global** list across all issues. Tests that create plan issues as a side effect will see extra entries in `updated_bodies` from the plan issue creation.

**Anti-pattern:**

```python
# WRONG: Asserts on global list, breaks when plan creation adds entries
assert len(fake_issues.updated_bodies) == 1
```

**Correct pattern:**

```python
# RIGHT: Filter to your target issue number
objective_updates = [
    (num, body) for num, body in issues.updated_bodies if num == target_issue
]
assert len(objective_updates) == 1
```

<!-- Source: tests/commands/objective/test_plan_one_shot.py, test_plan_one_shot.py:171-173 -->

See `tests/commands/objective/test_plan_one_shot.py:171-173` for this filtering pattern in practice.

## Related Topics

- [Dependency Graph Architecture](dependency-graph.md) - How unblocked nodes are determined
- [Objective Lifecycle](objective-lifecycle.md) - Overall objective mutation flow
