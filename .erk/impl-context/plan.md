# Plan: Objective #7911 Nodes 2.1 + 2.2 — Migrate plan test helpers to PlannedPRBackend

## Context

Part of Objective #7911, Nodes 2.1 and 2.2.

The issue-based plan backend (`GitHubPlanStore` + `FakeGitHubIssues`) is being removed in favor of the draft-PR backend (`PlannedPRBackend` + `FakeGitHub`). This plan covers:
- **Node 2.1**: Update the test helper functions in `plan_helpers.py` to return `(PlannedPRBackend, FakeGitHub)` instead of `(GitHubPlanStore, FakeGitHubIssues)`
- **Node 2.2**: Update the ~15 test files that call these helpers — migrate variable names, context wiring, and assertion trackers

## Phase 1: Update plan_helpers.py (Node 2.1)

**File**: `tests/test_utils/plan_helpers.py`

### 1a. Replace `create_plan_store_with_plans`

Current signature returns `tuple[GitHubPlanStore, FakeGitHubIssues]`. Change it to delegate to `create_planned_pr_store_with_plans` and return `tuple[PlannedPRBackend, FakeGitHub]`.

```python
def create_plan_store_with_plans(
    plans: dict[str, Plan],
) -> tuple[PlannedPRBackend, FakeGitHub]:
    """Create PlannedPRBackend backed by FakeGitHub."""
    return create_planned_pr_store_with_plans(plans)
```

Or just inline the body of `create_planned_pr_store_with_plans` directly into `create_plan_store_with_plans` and delete `create_planned_pr_store_with_plans`.

### 1b. Simplify `create_plan_store`

Remove the `backend` parameter. Always returns `(PlannedPRBackend, FakeGitHub)`:

```python
def create_plan_store(
    plans: dict[str, Plan],
) -> tuple[PlannedPRBackend, FakeGitHub]:
    return create_plan_store_with_plans(plans)
```

Keep `create_plan_store` as an alias for now (many callers use it). Callers that pass `backend=` will get a TypeError which makes migration easy to find.

### 1c. Delete dead code

- Delete `_plan_to_issue_info()` (only used by old `create_plan_store_with_plans`)
- Delete `create_planned_pr_store_with_plans()` (merged into `create_plan_store_with_plans`)
- Remove imports: `GitHubPlanStore`, `IssueInfo`, `FakeGitHubIssues`, `PlanStore`

## Phase 2: Update test files (Node 2.2)

### Tracker mapping reference

| FakeGitHubIssues tracker | FakeGitHub tracker | Tuple format change |
|---|---|---|
| `closed_issues` (list[int]) | `closed_prs` (list[int]) | Same |
| `added_comments` (list[tuple[int, str, int]]) | `pr_comments` (list[tuple[int, str]]) | 3-tuple → 2-tuple (no comment_id) |
| `updated_bodies` (list[tuple[int, str]]) | `updated_pr_bodies` (list[tuple[int, str]]) | Same format |

### Context wiring changes

Tests that pass `issues=fake_issues` to `context_for_test` or `build_workspace_test_context` need to be updated. Since PlannedPRBackend uses `FakeGitHub` (not `FakeGitHubIssues`), the returned `FakeGitHub` should NOT be passed as `issues=`. Instead:
- If the test only needs the plan store, just pass `plan_store=store`
- If the test needs an issues gateway too, pass `issues=fake_github.issues` (the nested FakeGitHubIssues inside FakeGitHub)

### Files with tracker assertions (need assertion migration)

**1. `tests/commands/pr/test_close.py`** (lines 50, 52)
- Rename: `fake_issues` → `fake_github`
- `fake_issues.closed_issues` → `fake_github.closed_prs`
- `any(num == 42 and "completed" in body for num, body, _ in fake_issues.added_comments)` → `any(num == 42 and "completed" in body for num, body in fake_github.pr_comments)`
- Context: `issues=fake_issues` → remove (or `issues=fake_github.issues` if needed)

**2. `tests/unit/cli/commands/pr/test_metadata_helpers.py`** (lines 41, 53, 67-68, 93, 110, 122, 136-137)
- Rename: `fake_issues` → `fake_github`
- `fake_issues.updated_bodies` → `fake_github.updated_pr_bodies`
- No context wiring changes (uses `context_for_test(plan_store=...)` directly)

**3. `tests/commands/test_top_level_commands.py`** (line 206)
- Rename: `fake_issues` → `fake_github`
- `fake_issues.closed_issues` → `fake_github.closed_prs`
- Context: `issues=fake_issues` → `issues=fake_github.issues`

**4. `tests/commands/workspace/test_delete.py`** (lines 469, 645)
- Rename: `fake_issues` → `fake_plan_github`
- `fake_issues.closed_issues` → `fake_plan_github.closed_prs`
- Context: `issues=fake_issues` likely not passed (uses `build_workspace_test_context`)
- Note: This file also has a separate `fake_github = FakeGitHub()` for PR closing — keep that separate

### Files with context wiring only (pass `issues=fake_issues` but no tracker assertions)

**5. `tests/commands/submit/test_rollback.py`** (line 30)
- `fake_github_issues` → `fake_plan_github`
- `issues=fake_github_issues` → remove or `issues=fake_plan_github.issues`

**6. `tests/commands/submit/test_workflow_config.py`** (line 160)
- Same pattern as test_rollback.py

**7. `tests/commands/submit/test_dispatch_metadata.py`** (line 54)
- Same pattern as test_rollback.py

**8. `tests/commands/submit/test_base_branch.py`** (lines 26-27, 139-140, 189-190)
- Currently creates TWO stores: `create_plan_store(..., backend="github")` for plan_store AND `create_plan_store_with_plans(...)` for fake_issues
- Simplify to single call: `fake_plan_store, fake_plan_github = create_plan_store_with_plans({...})`
- `issues=fake_github_issues` → `issues=fake_plan_github.issues`

**9. `tests/commands/submit/test_multiple_issues.py`** (lines 73-75)
- Same dual-store pattern as test_base_branch.py — simplify

**10. `tests/commands/submit/conftest.py`** (line 105)
- Remove `backend` parameter from `setup_submit_context`
- `create_plan_store(plans, backend=backend)` → `create_plan_store_with_plans(plans)`
- `isinstance(fake_backing, FakeGitHubIssues)` checks → update to `FakeGitHub`
- `fake_issues = fake_backing if isinstance(fake_backing, FakeGitHubIssues) else None` → `issues=fake_backing.issues`

### Files with `_` discard (only need type compatibility, minimal changes)

**11. `tests/commands/pr/test_view.py`** — Uses `store, _ = create_plan_store(...)` with `backend=plan_backend_type` fixture. Remove `backend=` param. Remove `plan_backend_type` fixture.

**12. `tests/commands/pr/test_log.py`** — `store, fake_issues = create_plan_store_with_plans({})`. Rename to `store, _fake_github`. No tracker assertions.

**13. `tests/commands/plan/test_duplicate_check.py`** — `_fake_issues` discarded. Rename to `_fake_github`.

**14. `tests/commands/implement/test_flags.py`** — `store, _ = create_plan_store(...)` with `backend=`. Remove `backend=` param, remove `plan_backend_type` fixture.

**15. `tests/commands/implement/test_issue_mode.py`** — Mix of `create_plan_store` and `create_plan_store_with_plans`. Remove `backend=` params, remove fixture.

**16. `tests/commands/implement/test_execution_modes.py`** — Same as test_flags.py.

**17. `tests/commands/implement/test_model_flag.py`** — Same as test_flags.py.

**18. `tests/commands/branch/test_checkout_cmd.py`** — `create_plan_store(...)` with explicit `backend=`. Remove `backend=` params.

### `plan_backend_type` fixture removal

Files 11, 14–18 use a `plan_backend_type` pytest fixture that parametrizes over `["github", "planned_pr"]`. Since there's now only one backend, remove this fixture and update all callers to use plain `create_plan_store_with_plans()` or the simplified `create_plan_store()`.

Fixture locations to check:
- `tests/commands/pr/test_view.py` (local fixture)
- `tests/commands/test_top_level_commands.py` (local fixture)
- `tests/commands/implement/` (likely shared conftest)
- `tests/commands/branch/test_checkout_cmd.py` (local or conftest)
- `tests/commands/submit/conftest.py` (`backend` param)

## Verification

1. Run affected test files individually to check for import/assertion errors:
   ```
   pytest tests/test_utils/ tests/commands/pr/ tests/commands/submit/ tests/commands/implement/ tests/commands/plan/ tests/commands/workspace/test_delete.py tests/commands/test_top_level_commands.py tests/unit/cli/commands/pr/test_metadata_helpers.py tests/commands/branch/test_checkout_cmd.py
   ```
2. Run ty for type checking on modified files
3. Run ruff for lint
4. Full CI via `/local:fast-ci`
