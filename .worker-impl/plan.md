# Canonicalize Branch Naming: Encode Objective ID in All Codepaths

## Context

Branch names like `P7268-erk-plan-migrate-steps-4-02-17-0424` are missing the objective encoding (`O7161`). The canonical function `generate_issue_branch_name()` in `naming.py` already supports `O{objective_id}` encoding, but two codepaths bypass it and manually construct branch names without objective IDs.

## Bug Summary

| Codepath | File | Issue |
|----------|------|-------|
| Plan Submit | `src/erk/cli/commands/submit.py:370-378` | Manual branch construction, no objective |
| One-Shot Dispatch | `src/erk/cli/commands/one_shot_dispatch.py:45-74` | Separate `generate_branch_name()`, no objective |

Working codepaths (for reference): `branch/create_cmd.py`, `setup_impl_from_issue.py`, `issue_workflow.py` all correctly call `generate_issue_branch_name()` with `objective_id`.

## Fix 1: `submit.py` — Replace manual construction with `generate_issue_branch_name`

**File:** `src/erk/cli/commands/submit.py`

The `_validate_issue_for_submit()` function (lines 373-378) manually builds the branch name:
```python
prefix = f"P{issue_number}-"
sanitized_title = sanitize_worktree_name(issue.title)
base_branch_name = (prefix + sanitized_title)[:31].rstrip("-")
timestamp_suffix = format_branch_timestamp_suffix(ctx.time.now())
new_branch_name = base_branch_name + timestamp_suffix
```

**Changes:**
1. Add imports: `generate_issue_branch_name` from `erk_shared.naming`, `extract_plan_header_objective_issue` from `erk_shared.gateway.github.metadata.plan_header`
2. Remove now-unused imports: `format_branch_timestamp_suffix`, `sanitize_worktree_name` (verify no other usage in file first)
3. Replace lines 373-378 with:
```python
objective_id = extract_plan_header_objective_issue(issue.body)
new_branch_name = generate_issue_branch_name(
    issue_number, issue.title, ctx.time.now(), objective_id=objective_id
)
```

## Fix 2: `one_shot_dispatch.py` — Delegate to `generate_issue_branch_name` when plan issue exists

**File:** `src/erk/cli/commands/one_shot_dispatch.py`

The `generate_branch_name()` function (lines 45-74) has its own naming logic and doesn't accept `objective_id`. When `plan_issue_number` is provided, this duplicates `generate_issue_branch_name()` behavior.

**Changes:**
1. Add `objective_id: int | None` parameter to `generate_branch_name()`
2. When `plan_issue_number is not None`, delegate to `generate_issue_branch_name()` instead of manually constructing
3. Keep the `oneshot-` prefix path for when `plan_issue_number is None`
4. At the call site (line 168), pass `objective_id=objective_id` (already available at line 146)

Updated function:
```python
def generate_branch_name(
    instruction: str,
    *,
    time: Time,
    plan_issue_number: int | None,
    objective_id: int | None,
) -> str:
    if plan_issue_number is not None:
        return generate_issue_branch_name(
            plan_issue_number, instruction, time.now(), objective_id=objective_id
        )
    slug = sanitize_worktree_name(instruction)
    prefix = "oneshot-"
    max_slug_len = 31 - len(prefix)
    if len(slug) > max_slug_len:
        slug = slug[:max_slug_len].rstrip("-")
    timestamp = format_branch_timestamp_suffix(time.now())
    return f"{prefix}{slug}{timestamp}"
```

At call site (line 168):
```python
branch_name = generate_branch_name(
    params.instruction,
    time=ctx.time,
    plan_issue_number=plan_issue_number,
    objective_id=objective_id,
)
```

## Fix 3: Update tests

**File:** `tests/commands/one_shot/test_branch_name.py`

- Update existing test `test_generate_branch_name_with_plan_issue_number` to also pass `objective_id=None`
- Add new test `test_generate_branch_name_with_objective_id` that verifies `O{N}` encoding when both plan_issue_number and objective_id are provided
- Update all calls to `generate_branch_name()` to include `objective_id=None` for backward compat

## Verification

1. Run tests: `pytest tests/commands/one_shot/test_branch_name.py`
2. Run tests: `pytest tests/core/utils/test_naming.py`
3. Run broader submit tests: `pytest tests/commands/` (scoped to commands)
4. Run ty/ruff for type checking and lint