# Fix: Bidirectional Objective-Plan Linkage

## Context

PR #9033 was merged but its associated objective #9009 was never updated (node 1.5 stayed `in_progress`). Root cause: the plan PR had no `objective_issue` in its plan-header metadata, so `erk land`/`erk reconcile` couldn't trace the PR back to its objective. The roadmap referenced `pr: '#9033'` on node 1.5 (one-way link), but the plan didn't reference the objective back (missing backlink).

This happens when a plan is created outside `/erk:objective-plan` and later linked to an objective via `erk exec update-objective-node --pr "#9033"`.

## Part A: Prevention — `update_objective_node` writes the backlink

When `update_objective_node` sets `--pr "#NNN"` on a node, it should also ensure the referenced plan PR has `objective_issue` in its plan-header metadata pointing back to this objective.

### 1. Add `update_plan_header_objective_issue()` helper

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py`

Follow the exact pattern of `update_plan_header_comment_id()` (line 474):
- Extract plan-header block via `find_metadata_block()`
- Copy data dict, set `objective_issue` field
- Validate via `PlanHeaderSchema().validate()`
- Render and replace block in body

### 2. Add backlink logic to `update_objective_node`

**File:** `src/erk/cli/commands/exec/scripts/update_objective_node.py`

After successfully writing the objective roadmap update (line 389), if `--pr` was provided with a non-empty value:

1. Parse PR number from `pr_ref` (strip `#` prefix)
2. Fetch the PR body via `github.get_issue(repo_root, pr_number)` (PRs are issues)
3. Check if plan-header already has `objective_issue` via `extract_plan_header_objective_issue()`
4. If not set (None), update the PR body with `update_plan_header_objective_issue()` and write back via `github.update_issue_body()`
5. If already set to a *different* objective, log a warning in the JSON output but don't overwrite (a plan shouldn't be silently re-parented)
6. This is **fail-open**: backlink failure doesn't prevent the node update from succeeding. Add a `backlink_set` field to JSON output.

### 3. Tests

**File:** `tests/unit/cli/commands/exec/scripts/test_update_objective_node.py` (existing)

Add test cases:
- Setting `--pr "#123"` on a node also sets `objective_issue` on the plan PR
- If plan PR already has matching `objective_issue`, no extra write
- If plan PR has no plan-header block, backlink is skipped (not all PRs are erk plans)
- If plan PR has a different `objective_issue`, warning emitted, no overwrite

**File:** `packages/erk-shared/tests/unit/gateway/github/metadata/test_plan_header.py` (existing)

Add test for `update_plan_header_objective_issue()`.

## Part B: Detection — `erk objective check` validates backlinks

### 4. Add Check 9 to `validate_objective()`

**File:** `src/erk/cli/commands/objective/check_cmd.py`

After existing checks (line 247), add a new check: "PR backlink consistency". For each node with a `pr: "#NNN"` field:

1. Fetch the PR via `remote.get_issue()` (using `owner`, `repo`, PR number parsed from `#NNN`)
2. Extract `objective_issue` from plan-header via `extract_plan_header_objective_issue()`
3. Verify it matches the current objective's issue number

Report:
- Pass: "All PR references have matching objective_issue backlinks"
- Fail: "Step 1.5 PR #9033 missing objective_issue backlink" (or "has mismatched objective_issue: 1234")

This requires the `RemoteGitHub` gateway — need to check it has `get_issue()`. If not, use the existing `remote.get_issue()` from `erk_shared.gateway.remote_github.abc`.

### 5. Tests

**File:** `tests/unit/cli/commands/objective/test_check_cmd.py` (existing or new)

Test the new validation check with fake issues that have/lack backlinks.

## Critical Files

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py` | Add `update_plan_header_objective_issue()` |
| `src/erk/cli/commands/exec/scripts/update_objective_node.py` | Add backlink write after node update |
| `src/erk/cli/commands/objective/check_cmd.py` | Add Check 9: backlink validation |
| Tests for all three |

## Verification

```bash
# Unit tests for the new helper
uv run pytest packages/erk-shared/tests/unit/gateway/github/metadata/test_plan_header.py -v -k objective_issue

# Unit tests for update-objective-node backlink
uv run pytest tests/unit/cli/commands/exec/scripts/test_update_objective_node.py -v

# Unit tests for objective check
uv run pytest tests/unit/cli/commands/objective/ -v

# Integration: manually test against real objective
erk objective check 9009 --json-output

# Full CI
make fast-ci
```
