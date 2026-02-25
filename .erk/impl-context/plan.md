# Plan: Update tests for impl_* scripts (Objective #7724, Node 3.2)

## Context

Part of **Objective #7724 — Rename issue_number to plan_number in plan-related code**, Node 3.2.

Node 3.1 (PR #7908) renamed `issue_number` to `plan_number` in the source impl_* exec scripts. The test files were included in that PR's file list but still contain legacy `issue.json` format references that should be migrated to `plan-ref.json` format.

## Changes

### 1. `tests/unit/cli/commands/exec/scripts/test_impl_init.py`

**`test_impl_init_with_issue_tracking` (line 85-108):**
- Update docstring: `"returns issue_number"` → `"returns plan_number"`
- Replace legacy `issue.json` file creation with `plan-ref.json` format:
  - Old: writes `issue.json` with `{"issue_number": 123, "issue_url": "...", "created_at": "...", "synced_at": "..."}`
  - New: writes `plan-ref.json` with `{"provider": "github", "plan_id": "123", "url": "...", "created_at": "...", "synced_at": "...", "labels": [], "objective_id": null}`
- Assertion `data["plan_number"] == 123` already correct (updated in 3.1)

### 2. `tests/integration/cli/commands/exec/scripts/test_check_impl_integration.py`

**`test_check_impl_validates_complete_issue_json` (line 40-63):**
- Rename test function → `test_check_impl_validates_complete_plan_ref`
- Update docstring to reference `plan-ref.json`
- Replace `issue.json` creation with `plan-ref.json` format (same schema as above)

**`test_check_impl_handles_incomplete_issue_json` (line 66-86):**
- Rename test function → `test_check_impl_handles_incomplete_plan_ref`
- Update docstring
- Replace `issue.json` with a `plan-ref.json` that has missing required fields (e.g. only `{"provider": "github"}` — missing `plan_id`, `url`, etc.)
- This tests that incomplete format disables tracking

**`test_check_impl_normal_mode_with_tracking` (line 157-181):**
- Replace `issue.json` creation with `plan-ref.json` format (plan_id "456")
- Update string assertion `"GitHub tracking: ENABLED (issue #456)"` if the source output changed (verify)

### 3. Files NOT changed (confirmed no action needed)

- **`test_impl_signal.py`**: Local variable names (`comment_issue_number`, `updated_issue_number`) follow the convention from prior PRs (#7849, #7896) of not renaming internal test variables. `plan-ref.json` format already used throughout.
- **`test_mark_impl_started_ended.py`**: Already fully using `plan-ref.json` and `plan_number`. No `issue_number` references.
- **`test_setup_impl_from_issue.py`**: Already fully using `plan-ref.json` and `plan_number`. No `issue_number` references.

## Key Reference: plan-ref.json Format

From `packages/erk-shared/src/erk_shared/impl_folder.py:93-103`:

```python
@dataclass(frozen=True)
class PlanRef:
    provider: PlanProviderType  # "github" | "github-draft-pr"
    plan_id: str                # e.g. "123"
    url: str                    # e.g. "https://github.com/org/repo/issues/123"
    created_at: str             # ISO 8601
    synced_at: str              # ISO 8601
    labels: tuple[str, ...]     # e.g. ("erk-plan",)
    objective_id: int | None    # Parent objective or None
```

## Verification

1. Run scoped tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_impl_init.py tests/integration/cli/commands/exec/scripts/test_check_impl_integration.py -v`
2. Grep for remaining `issue_number` in the modified files to confirm none left
3. Grep for remaining `issue.json` references in the modified files to confirm migration complete
