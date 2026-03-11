# Plan: Push business logic from dispatch cli.py down to operation.py

## Context

`cli.py` (662 lines) contains substantial business logic that should live in `operation.py` (245 lines). Currently `operation.py` only handles the remote dispatch path via `run_pr_dispatch()`, while the local dispatch path (validation, branch sync, impl-context commit, workflow trigger, metadata/comments) lives entirely in `cli.py` mixed with `user_output()`/`click.style()`/`SystemExit` calls.

The established pattern (seen in `pr/view`, `pr/list`, `one-shot`) is: operation.py owns all business logic returning `Result | MachineCommandError`, cli.py marshals Click flags and renders results.

## Files to Modify

- `src/erk/cli/commands/pr/dispatch/operation.py` — receives all moved business logic
- `src/erk/cli/commands/pr/dispatch/cli.py` — stripped to thin CLI adapter
- `src/erk/cli/commands/exec/scripts/incremental_dispatch.py` — import path update
- `tests/commands/dispatch/test_workflow_config.py` — import path update
- `tests/unit/cli/commands/pr/test_dispatch_cmd.py` — import path update

## Step 1: Move pure functions to operation.py

These have zero CLI concerns — move as-is:

- `ValidatedPlannedPR` dataclass (cli.py:122-129)
- `load_workflow_config()` (cli.py:52-85)
- `_build_workflow_run_url()` (cli.py:88-102)
- `_build_pr_url()` (cli.py:105-119)
- `_detect_pr_number_from_context()` (cli.py:371-401) — drop leading underscore since it becomes part of the operation module's API

Add required imports to operation.py: `tomllib`, `Path`, `RepoContext`, `resolve_impl_dir`, `read_plan_ref`, etc.

## Step 2: Create `validate_planned_pr()` in operation.py

Replace `_validate_planned_pr_for_dispatch()` which uses `click.style`/`user_output`/`SystemExit`:

```python
def validate_planned_pr(
    ctx: ErkContext, repo: RepoContext, pr_number: int,
) -> ValidatedPlannedPR | MachineCommandError:
```

Same logic, but returns `MachineCommandError` instead of raising `SystemExit`:
- PR not found → `error_type="not_found"`
- Missing `[erk-pr]` prefix → `error_type="invalid_pr"`
- Not OPEN → `error_type="pr_not_open"`

Follows the exact pattern already used by `run_pr_dispatch()` (operation.py:94-117).

## Step 3: Create `dispatch_planned_pr()` in operation.py

Extract the core of `_dispatch_planned_pr_plan()` (cli.py:179-368, ~190 lines). Same signature/logic but:

- Remove all `user_output()` and `click.style()` calls → use `logger.info()` for progress
- Replace `SystemExit`/`UserFacingCliError` → return `MachineCommandError`
  - Plan not found → `error_type="plan_not_found"`
  - Push failure → `error_type="push_failed"`
- Keep best-effort `try/except` blocks for metadata write, PR body update, comment posting (use `logger.warning()`)
- Return `PrDispatchResult` on success

```python
def dispatch_planned_pr(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    validated: ValidatedPlannedPR,
    submitted_by: str,
    base_branch: str,
    ref: str | None,
) -> PrDispatchResult | MachineCommandError:
```

## Step 4: Create `run_local_pr_dispatch()` in operation.py

Orchestrates the validate-then-dispatch loop for the local path (analogous to `run_pr_dispatch()` for remote):

```python
@dataclass(frozen=True)
class LocalPrDispatchRequest:
    pr_numbers: tuple[int, ...]
    base_branch: str | None
    ref: str | None

def run_local_pr_dispatch(
    ctx: ErkContext,
    repo: RepoContext,
    request: LocalPrDispatchRequest,
) -> list[PrDispatchResult] | MachineCommandError:
```

This function handles:
- Auto-detecting PR numbers from context if none provided
- Resolving base branch (placeholder branch check, remote existence, trunk fallback)
- Getting GitHub username via `ctx.github.check_auth_status()`
- Validating all PRs upfront via `validate_planned_pr()`
- Dispatching each via `dispatch_planned_pr()`
- Returning list of results or first error

## Step 5: Rewrite cli.py as thin adapter (~120 lines)

Keep in cli.py:
- `_print_dispatch_summary()` — pure display
- `pr_dispatch()` Click command — simplified to:
  1. Determine remote vs local mode
  2. For remote: `resolve_owner_repo()`, build `PrDispatchRequest`, call `run_pr_dispatch()`, handle error, display summary
  3. For local: `Ensure.gh_authenticated()`, discover repo, `ensure_trunk_synced()`, build `LocalPrDispatchRequest`, call `run_local_pr_dispatch()`, handle error, display summary

CLI-layer preconditions (`Ensure.gh_authenticated`, `ensure_trunk_synced`) stay in cli.py since they have side effects and raise `SystemExit` — consistent with how the remote path already works (operation assumes deps are available).

## Step 6: Update external imports

- `incremental_dispatch.py`: `from erk.cli.commands.pr.dispatch.operation import load_workflow_config`
- `test_workflow_config.py`: same
- `test_dispatch_cmd.py`: `from erk.cli.commands.pr.dispatch.operation import detect_pr_number_from_context`

## Verification

1. Run dispatch tests: `uv run pytest tests/commands/dispatch/ tests/unit/cli/commands/pr/test_dispatch_cmd.py -x`
2. Run type checker on modified files
3. Run full fast-ci
