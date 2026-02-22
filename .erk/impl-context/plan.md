# Add `erk exec update-plan-objective` command

## Context

PR #7836 was saved without `--objective-issue=7823`, so its plan-header metadata has no `objective_issue` field. The TUI reads this field to display objective associations — without it, the PR shows "-" in the objective column despite the plan body referencing objective #7823 in prose.

There is no existing CLI command to retroactively set `objective_issue` on a plan. The infrastructure exists (`backend.update_metadata()`, the `OBJECTIVE_ISSUE` schema field), but no command exposes it.

Additionally, objective #7823's roadmap has nodes 1.1-1.3 pointing to plan `#7831` (the original plan issue) rather than `#7836` (the PR that actually implemented the work). This needs updating via the existing `erk exec update-objective-node` command.

## Plan

### Step 1: Create `update_plan_objective.py`

**File**: `src/erk/cli/commands/exec/scripts/update_plan_objective.py`

Minimal exec command following the exact pattern of `update_dispatch_info.py`:
- Takes two arguments: `plan_issue_number` (int) and `objective_issue_number` (int)
- LBYL check: reject non-positive `objective_issue_number` before calling backend
- Calls `backend.update_metadata(repo_root, str(plan_issue_number), metadata={"objective_issue": objective_issue_number})`
- Outputs JSON success/error (same `UpdateSuccess`/`UpdateError` dataclass pattern)
- Error output to stderr, success to stdout

### Step 2: Register in `group.py`

**File**: `src/erk/cli/commands/exec/group.py`

- Add import of `update_plan_objective` (alphabetically near `update_dispatch_info`)
- Add `exec_group.add_command(update_plan_objective, name="update-plan-objective")` (alphabetically near line 281)

### Step 3: Add tests

**File**: `tests/unit/cli/commands/exec/scripts/test_update_plan_objective.py`

Following the `test_update_dispatch_info.py` pattern:
1. `test_update_plan_objective_success` — happy path, verify metadata field set
2. `test_update_plan_objective_overwrites_existing` — plan already has an objective_issue, overwrite it
3. `test_update_plan_objective_issue_not_found` — exit 1, JSON error
4. `test_update_plan_objective_no_plan_header_block` — old format issue, exit 1
5. `test_update_plan_objective_negative_number` — LBYL rejects non-positive input

### Step 4: Fix PR #7836 and objective #7823

After the command is built and tests pass:

```bash
# Link PR #7836 to objective #7823
erk exec update-plan-objective 7836 7823

# Update objective roadmap nodes 1.1-1.3 to point to #7836
erk exec update-objective-node 7823 --node 1.1 --plan "#7836"
erk exec update-objective-node 7823 --node 1.2 --plan "#7836"
erk exec update-objective-node 7823 --node 1.3 --plan "#7836"
```

## Key Files

| File | Role |
|------|------|
| `src/erk/cli/commands/exec/scripts/update_dispatch_info.py` | Template to copy |
| `tests/unit/cli/commands/exec/scripts/test_update_dispatch_info.py` | Test template |
| `src/erk/cli/commands/exec/group.py` | Command registration |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py` | `OBJECTIVE_ISSUE` field definition |

## Verification

1. `uv run pytest tests/unit/cli/commands/exec/scripts/test_update_plan_objective.py`
2. `ruff check` and `ty` on new files
3. Run the Step 4 commands to fix the actual PR and objective
4. Confirm TUI shows "#7823" in objective column for PR #7836
