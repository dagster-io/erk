# Auto-detect PR number in `erk pr dispatch` when no argument given

## Context & Problem

Currently, `erk pr dispatch` requires one or more `ISSUE_NUMBERS` arguments (`required=True`). When a user is on a plan branch (e.g., `plnd/O8036-add-webhook-server-02-25-1243`) and has just saved a plan, they have to manually type `erk pr dispatch <number>`. The error message when no argument is provided is not helpful:

```
Error: Missing argument 'ISSUE_NUMBERS...'.
```

The user wants the command to auto-detect the PR number from context (impl-context, `.impl/`, or branch) when no argument is given, similar to how `setup_impl.py` auto-detects the plan source.

## Changes

### 1. Modify `src/erk/cli/commands/pr/dispatch_cmd.py`

#### 1a. Change `ISSUE_NUMBERS` argument to optional

In the `pr_dispatch` Click command decorator, change `required=True` to `required=False` so the argument becomes optional:

```python
@click.argument("issue_numbers", type=int, nargs=-1, required=False)
```

This allows `nargs=-1` to accept zero arguments (empty tuple) instead of requiring at least one.

#### 1b. Add auto-detection function

Add a new function `_detect_plan_number_from_context()` that implements a fallback chain to find the PR number when no argument is given. The fallback chain mirrors the pattern in `setup_impl.py` (Path 3: Auto-detect):

```python
def _detect_plan_number_from_context(
    ctx: ErkContext,
    repo: RepoContext,
) -> int | None:
```

**Fallback chain (in order):**

1. **Check `.impl/` folder** — If `.impl/plan-ref.json` (or `ref.json` or legacy `issue.json`) exists, read the `plan_id` from it. Use `read_plan_ref()` from `erk_shared.impl_folder`. This handles the case where the user just saved a plan and has `.impl/` set up locally.

2. **Check `.erk/impl-context/ref.json`** — If `.erk/impl-context/ref.json` exists, parse it and extract `plan_id`. This handles the case where impl-context was committed to the branch but implementation hasn't started yet.

3. **PR lookup from current branch** — Call `ctx.github.get_pr_for_branch(repo.root, current_branch)` to find the PR associated with the current branch. This handles `plnd/` branches that have an associated PR but no local `.impl/` or `.erk/impl-context/`. This is the same approach used by `PlannedPRBackend.resolve_plan_id_for_branch()` and `detect_plan_from_branch.py`.

Each fallback step should return the detected plan number as `int | None`. If a number is found at any step, return it immediately without trying subsequent steps.

#### 1c. Wire auto-detection into `pr_dispatch()` command body

At the beginning of `pr_dispatch()`, after the `issue_numbers` parameter is received, add logic to handle the empty tuple case:

```python
# If no arguments given, try to auto-detect from context
if not issue_numbers:
    detected = _detect_plan_number_from_context(ctx, repo)
    if detected is None:
        user_output(
            click.style("Error: ", fg="red")
            + "No issue numbers provided and could not auto-detect from context.\n\n"
            "Provide issue numbers explicitly: erk pr dispatch <number>\n"
            "Or run from a plan branch with an associated PR."
        )
        raise SystemExit(1)
    user_output(
        f"Auto-detected PR #{detected} from context"
    )
    issue_numbers = (detected,)
```

This must be placed **after** `repo` is resolved (after the `discover_repo_context` call) but **before** the trunk sync and validation steps. Note that the existing code already determines `repo` early (lines 451-454), so the auto-detection can slot in right after that.

**Important ordering consideration:** The auto-detection needs to happen before `ensure_trunk_synced` is called, because the user may be on a plan branch and the detection logic needs the current branch. However, `ensure_trunk_synced` doesn't change the current branch (it only syncs trunk in the root worktree). So the detection can safely go after `ensure_trunk_synced` as well — but putting it right after `repo` resolution is cleaner.

Actually, looking more carefully at the code flow: `ensure_trunk_synced` is called at line 458, and `original_branch` is determined at line 461. The auto-detection needs `original_branch` (to do PR lookup from branch). So the correct placement is **after** `original_branch` is determined but **before** the validation loop at line 519.

The specific insertion point should be right after line 467 (after the detached HEAD check), replacing the hardcoded reliance on `issue_numbers`:

```python
# If no arguments given, try to auto-detect from context
if not issue_numbers:
    detected = _detect_plan_number_from_context(ctx, repo, original_branch)
    if detected is None:
        user_output(
            click.style("Error: ", fg="red")
            + "No issue numbers provided and could not auto-detect from context.\n\n"
            "Provide issue numbers explicitly: erk pr dispatch <number>\n"
            "Or run from a plan branch with an associated PR."
        )
        raise SystemExit(1)
    user_output(
        f"Auto-detected PR #{detected} from context"
    )
    issue_numbers = (detected,)
```

Update the `_detect_plan_number_from_context` signature to also accept `current_branch: str` so it can use it for the PR lookup step:

```python
def _detect_plan_number_from_context(
    ctx: ErkContext,
    repo: RepoContext,
    current_branch: str,
) -> int | None:
```

### 2. Add imports

Add to the imports in `dispatch_cmd.py`:

```python
from erk_shared.impl_folder import read_plan_ref
```

The `IMPL_CONTEXT_DIR` constant is already imported. `json` is already imported in the stdlib (though not currently used in this file — wait, `json` is NOT currently imported). We need `json` to parse `ref.json` from impl-context. Actually, we can use `read_plan_ref` for the impl-context `ref.json` too since it supports reading `ref.json` as a fallback filename. Let me verify: `read_plan_ref` checks `plan-ref.json` then `ref.json` in the given directory. So we can call `read_plan_ref(repo.root / ".erk" / "impl-context")` and it will find `ref.json`. No need to add `json` import.

### 3. Update command help text

Update the docstring of `pr_dispatch()` to document the auto-detection behavior:

```python
"""Dispatch plans for remote AI implementation via GitHub Actions.

Creates branch and draft PR locally (for correct commit attribution),
then triggers the plan-implement.yml GitHub Actions workflow.

Arguments:
    ISSUE_NUMBERS: One or more GitHub issue numbers to dispatch.
        If omitted, auto-detects from .impl/, .erk/impl-context/, or current branch.

\b
Example:
    erk pr dispatch 123
    erk pr dispatch 123 456 789
    erk pr dispatch 123 --base master
    erk pr dispatch                     # auto-detect from context

Requires:
    - All issues must have erk-plan label
    - All issues must be OPEN
    - Working directory must be clean (no uncommitted changes)
"""
```

## Implementation Details

### Auto-detection function

```python
def _detect_plan_number_from_context(
    ctx: ErkContext,
    repo: RepoContext,
    current_branch: str,
) -> int | None:
    """Detect plan PR number from local context when no argument given.

    Fallback chain:
    1. .impl/plan-ref.json (or ref.json, issue.json) — local impl folder
    2. .erk/impl-context/ref.json — committed staging directory
    3. PR lookup from current branch — GitHub API query

    Args:
        ctx: ErkContext with git/github operations
        repo: Repository context
        current_branch: Current git branch name

    Returns:
        Detected PR number, or None if nothing found.
    """
    # 1. Check .impl/ folder
    impl_dir = repo.root / ".impl"
    if impl_dir.exists():
        plan_ref = read_plan_ref(impl_dir)
        if plan_ref is not None and plan_ref.plan_id.isdigit():
            return int(plan_ref.plan_id)

    # 2. Check .erk/impl-context/
    impl_context_dir = repo.root / IMPL_CONTEXT_DIR
    if impl_context_dir.exists():
        plan_ref = read_plan_ref(impl_context_dir)
        if plan_ref is not None and plan_ref.plan_id.isdigit():
            return int(plan_ref.plan_id)

    # 3. PR lookup from branch
    pr_result = ctx.github.get_pr_for_branch(repo.root, current_branch)
    if not isinstance(pr_result, PRNotFound):
        return pr_result.number

    return None
```

Key design decisions:
- Uses `read_plan_ref()` which already handles the `plan-ref.json` → `ref.json` → `issue.json` fallback chain
- The `plan_id.isdigit()` check is consistent with the same pattern in `setup_impl.py` (line 200)
- `PRNotFound` is already imported in the file
- `IMPL_CONTEXT_DIR` constant (value: `.erk/impl-context`) is already imported
- Does NOT use `ctx.plan_store.resolve_plan_id_for_branch()` because that would add another API call; the direct `get_pr_for_branch` is clearer and matches the pattern in `detect_plan_from_branch.py`

### Edge cases

- **Multiple auto-detected numbers**: Only one number is auto-detected. If the user wants to dispatch multiple plans, they must provide arguments explicitly.
- **Detached HEAD with `.impl/`**: The `.impl/` and `.erk/impl-context/` checks don't require being on a branch. Only step 3 (branch lookup) is skipped if the branch is not available.
- **Non-plan PR**: The auto-detected PR goes through the same validation (`_validate_planned_pr_for_dispatch`) that catches missing `erk-plan` label or non-OPEN state.

## Files NOT Changing

- `.claude/commands/erk/pr-dispatch.md` — The slash command already searches conversation context for the issue number and passes it explicitly. The auto-detection in the CLI is a complementary feature for direct command-line usage.
- `src/erk/cli/commands/pr/dispatch_helpers.py` — No changes needed to trunk sync logic.
- `src/erk/cli/commands/exec/scripts/detect_plan_from_branch.py` — The auto-detection logic is inline in `dispatch_cmd.py` rather than calling this exec script, keeping the dependency chain simple.
- `packages/erk-shared/src/erk_shared/impl_context.py` — No API changes needed.
- `packages/erk-shared/src/erk_shared/impl_folder.py` — No changes; `read_plan_ref` already supports the needed fallback chain.

## Tests

### Add test in `tests/commands/pr/test_dispatch.py`

#### Test: `test_dispatch_auto_detects_from_impl_folder`

Set up a test with:
- No `ISSUE_NUMBERS` argument (empty invocation: `erk pr dispatch`)
- `.impl/plan-ref.json` present with a valid plan_id
- Verify the command auto-detects and dispatches that plan number

#### Test: `test_dispatch_auto_detects_from_impl_context`

Set up a test with:
- No `ISSUE_NUMBERS` argument
- `.erk/impl-context/ref.json` present with a valid plan_id
- No `.impl/` folder
- Verify the command auto-detects from impl-context

#### Test: `test_dispatch_auto_detects_from_branch_pr`

Set up a test with:
- No `ISSUE_NUMBERS` argument
- No `.impl/` or `.erk/impl-context/`
- Current branch has an associated PR (via `prs_by_branch` in FakeGitHub)
- Verify the command auto-detects from branch PR lookup

#### Test: `test_dispatch_no_args_no_context_fails`

Set up a test with:
- No `ISSUE_NUMBERS` argument
- No `.impl/`, no `.erk/impl-context/`, no associated PR
- Verify the command exits with error and helpful message

## Verification

1. Run the existing test suite to ensure no regressions: `pytest tests/commands/pr/test_dispatch.py`
2. Run the new tests to verify auto-detection works for each fallback step
3. Run type checking: `ty check src/erk/cli/commands/pr/dispatch_cmd.py`
4. Run linting: `ruff check src/erk/cli/commands/pr/dispatch_cmd.py`