# Plan: Encode objective ID into branch names

## Goal

When a plan is associated with an objective, encode the objective ID into the branch name:
- Without objective: `P{plan}-{slug}-{timestamp}` (unchanged)
- With objective: `P{plan}-O{objective}-{slug}-{timestamp}`

Example: `P123-O456-fix-auth-bug-01-15-1430`

## Changes

### 1. `packages/erk-shared/src/erk_shared/naming.py`

**`generate_issue_branch_name`** - Add optional `objective_id` parameter:

```python
def generate_issue_branch_name(
    issue_number: int | str,
    title: str,
    timestamp: datetime,
    *,
    objective_id: int | None = None,  # NEW - but see note below
) -> str:
```

Per erk convention (no default parameter values), `objective_id` is a required keyword-only `int | None` parameter:

```python
def generate_issue_branch_name(
    issue_number: int | str,
    title: str,
    timestamp: datetime,
    *,
    objective_id: int | None,
) -> str:
```

Logic change: if `objective_id is not None`, insert `O{objective_id}-` after the `P{issue_number}-` prefix.

The prefix becomes `P{issue_number}-O{objective_id}-` or `P{issue_number}-` depending on presence. The 31-char truncation applies to `prefix + sanitized_title` before the timestamp suffix.

**`extract_leading_issue_number`** - Must still work with new format. Current regex `^[Pp]?(\d+)-` already extracts the plan number correctly from `P123-O456-...` since `P123-` matches. No change needed.

**New function: `extract_objective_number`** - Extract objective ID from branch name:

```python
def extract_objective_number(branch_name: str) -> int | None:
    """Extract objective number from branch name.

    Format: P{plan}-O{objective}-{slug}-{timestamp}
    """
    match = re.match(r"^[Pp]?\d+-[Oo](\d+)-", branch_name)
    if match:
        return int(match.group(1))
    return None
```

### 2. `packages/erk-shared/src/erk_shared/issue_workflow.py`

**`prepare_plan_for_worktree`** - Pass `objective_id` to `generate_issue_branch_name`:

```python
branch_name = generate_issue_branch_name(
    issue_number,
    plan.title,
    timestamp,
    objective_id=plan.objective_id,
)
```

### 3. `tests/core/utils/test_naming.py`

- Update existing `test_generate_issue_branch_name_format` parametrized cases to pass `objective_id=None`
- Add new test cases with `objective_id` set (e.g., `objective_id=456`)
- Add tests for `extract_objective_number`
- Add test that `extract_leading_issue_number` still works with new format

### 4. Other callers of `generate_issue_branch_name`

Search shows it's only called from `issue_workflow.py:prepare_plan_for_worktree`, so only one call site to update.

## Files to modify

1. `packages/erk-shared/src/erk_shared/naming.py` - Modify `generate_issue_branch_name`, add `extract_objective_number`
2. `packages/erk-shared/src/erk_shared/issue_workflow.py` - Pass `objective_id` through
3. `tests/core/utils/test_naming.py` - Update and add tests

## Verification

1. Run `uv run pytest tests/core/utils/test_naming.py` to validate naming changes
2. Run `uv run ty check packages/erk-shared/src/erk_shared/naming.py packages/erk-shared/src/erk_shared/issue_workflow.py` for type checking