# Plan: Add `get_plan_for_branch` to PlanBackend ABC

**Part of Objective #7419, Step 1.1**

## Context

The plan system currently resolves branch→plan via `extract_leading_issue_number(branch_name)` — a regex that parses `P{issue}-{slug}` branch names. This is called at 15+ sites across the codebase, each repeating the same two-step pattern: extract number → call plan_store. When we introduce `DraftPRPlanBackend` (step 1.2), branches won't encode plan IDs. We need an abstraction that encapsulates the branch→plan resolution strategy per backend.

## Approach

Add **two** new abstract methods to `PlanBackend`:

1. **`get_plan_for_branch`** — full plan lookup by branch name (returns `Plan | PlanNotFound`)
2. **`resolve_plan_id_for_branch`** — lightweight plan ID resolution (returns `str | None`)

The split avoids unnecessary API calls: 4 callers need the full Plan; 10+ callers only need the plan_id for downstream metadata operations. `resolve_plan_id_for_branch` is zero-cost for `GitHubPlanStore` (regex) but will require an API call in the future `DraftPRPlanBackend`.

## Phase 1: ABC + GitHubPlanStore Implementation

### `packages/erk-shared/src/erk_shared/plan_store/backend.py`

Add two abstract methods:

```python
@abstractmethod
def get_plan_for_branch(
    self, repo_root: Path, branch_name: str
) -> Plan | PlanNotFound:
    """Look up the plan associated with a branch.
    Returns PlanNotFound if branch is not a plan branch or plan doesn't exist.
    """

@abstractmethod
def resolve_plan_id_for_branch(
    self, repo_root: Path, branch_name: str
) -> str | None:
    """Resolve plan identifier for a branch without fetching the full plan.
    Returns None if branch is not associated with a plan.
    Does NOT verify the plan exists.
    """
```

### `packages/erk-shared/src/erk_shared/plan_store/github.py`

Implement both methods:

- `resolve_plan_id_for_branch`: calls `extract_leading_issue_number` → returns `str(number)` or None
- `get_plan_for_branch`: calls `resolve_plan_id_for_branch` → delegates to `self.get_plan`

### Tests

Add tests in `tests/integration/plan_store/test_github_plan_store.py`:
- `get_plan_for_branch` with plan branch (returns Plan)
- `get_plan_for_branch` with non-plan branch (returns PlanNotFound)
- `get_plan_for_branch` with plan branch but missing issue (returns PlanNotFound)
- `resolve_plan_id_for_branch` with P-prefix, legacy format, non-plan branch
- Both methods with `P123-O456-slug` objective format

## Phase 2: PlanContextProvider Migration

### `src/erk/core/plan_context_provider.py`

- Change `__init__` parameter from `plan_store: PlanStore` to `plan_backend: PlanBackend`
- Rename `PlanContext.issue_number: int` → `PlanContext.plan_id: str`
- Rewrite `get_plan_context` to use `self._plan_backend.get_plan_for_branch()` (one call replaces extract+get_plan)

### Callers of PlanContextProvider constructor

Update `plan_store=ctx.plan_store` → `plan_backend=ctx.plan_backend` in:
- `src/erk/cli/commands/pr/rewrite_cmd.py`
- `src/erk/cli/commands/pr/submit_pipeline.py`
- `src/erk/cli/commands/exec/scripts/update_pr_description.py`

### Callers of `PlanContext.issue_number`

Update `plan_context.issue_number` → `plan_context.plan_id` in:
- `src/erk/cli/commands/pr/shared.py` (assemble_pr_body references)
- `src/erk/core/commit_message_generator.py`

### Tests: `tests/core/test_plan_context_provider.py`

Update assertions: `issue_number` → `plan_id`, int values → str values.

## Phase 3: Direct Plan Lookup Callers (get_plan_for_branch)

These callers currently do `extract → get_plan` and need the full `Plan`:

### `src/erk/cli/commands/plan/view.py:251`

Replace `extract_leading_issue_number(branch) → get_plan(str(number))` with `get_plan_for_branch(repo_root, branch)`.

### `src/erk/cli/commands/objective_helpers.py:86,148`

Both functions: replace two-step pattern with `get_plan_for_branch`. Use `plan.plan_identifier` where plan_id is needed as string.

## Phase 4: Land Pipeline + Learn Functions

Largest blast radius. Rename `plan_issue_number: int` → `plan_id: str` throughout.

### `src/erk/cli/commands/land_pipeline.py`

- Rename `LandState.plan_issue_number: int | None` → `plan_id: str | None`
- Update `check_learn_status` step: use `resolve_plan_id_for_branch` instead of `extract_leading_issue_number`
- Update all `dataclasses.replace` calls and factory functions

### `src/erk/cli/commands/land_cmd.py`

- `_check_learn_status_and_prompt`: change `plan_issue_number: int` → `plan_id: str`
- Update all internal calls: `get_plan(str(plan_issue_number))` → `get_plan(plan_id)`
- Line 1071: replace `extract_leading_issue_number(target.branch)` with `resolve_plan_id_for_branch`
- Update display strings: `f"plan #{plan_issue_number}"` → `f"plan #{plan_id}"`
- `find_sessions_for_plan` call: adapt parameter type

### Tests: `tests/unit/cli/commands/land/pipeline/`

Update `make_execution_state` calls: `plan_issue_number=` → `plan_id=`, int → str.

## Phase 5: Remaining Lightweight Callers (resolve_plan_id_for_branch)

Each of these only needs the plan_id string, not the full Plan:

| File | Line | Change |
|------|------|--------|
| `src/erk/cli/commands/pr/metadata_helpers.py` | 82 | `extract_leading_issue_number` → `ctx.plan_backend.resolve_plan_id_for_branch` |
| `src/erk/cli/commands/implement_shared.py` | 468 | Same pattern; function returns `str \| None` unchanged |
| `src/erk/cli/commands/learn/learn_cmd.py` | 121 | Use resolve; change `issue_number: int \| None` → `plan_id: str \| None` downstream |
| `src/erk/cli/commands/exec/scripts/get_learn_sessions.py` | 241 | Use resolve; update downstream types |
| `src/erk/cli/commands/exec/scripts/track_learn_evaluation.py` | 175 | Use resolve; update downstream types |

## Out of Scope (Later Steps)

These callers are **not migrated** in step 1.1:

| File | Reason |
|------|--------|
| `gateway/plan_data_provider/real.py:434` | Bulk worktree mapping — step 2.1 |
| `impl_folder.py:261` | Cross-check with .impl plan_id — step 1.6 |
| `pr/shared.py:205` (discover_issue_for_footer) | Cross-check function, no backend access — step 1.6 |
| `plan/checkout_cmd.py:47` | Reverse lookup (issue→branch), different pattern — step 1.6 |
| `BranchOps.get_branch_issue` (abc/real/fake/dry_run/printing) | Gateway method — step 1.6 |
| `test_naming.py` | Test for `extract_leading_issue_number` itself — step 3.3 |

## Key Design Decisions

1. **Two methods, not one**: `get_plan_for_branch` (full Plan) + `resolve_plan_id_for_branch` (just ID) avoids unnecessary API calls for callers that only need the plan_id
2. **Methods on PlanBackend, not PlanStore**: PlanStore is deprecated; PlanContextProvider upgraded to accept PlanBackend
3. **`get_plan_for_branch` returns `Plan | PlanNotFound`** (not three-state): callers don't distinguish "not a plan branch" from "plan branch but missing plan" — both mean "no plan available"
4. **`resolve_plan_id_for_branch` returns `str | None`**: lightweight, no API call for GitHub backend; None means "not a plan branch"
5. **`extract_leading_issue_number` stays**: still called from out-of-scope sites; removed in step 3.3

## Verification

1. Run `ruff check` and `ty check` for type errors (via devrun agent)
2. Run unit tests: `pytest tests/integration/plan_store/ tests/core/test_plan_context_provider.py tests/unit/cli/commands/land/ tests/unit/cli/commands/test_implement_shared.py -x`
3. Run full test suite: `make fast-ci`
4. Grep for remaining `extract_leading_issue_number` calls — verify only out-of-scope callers remain