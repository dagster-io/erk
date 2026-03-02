# Skip impl-context cleanup for plan PRs in submit pipeline

## Context

`cleanup_impl_for_submit()` unconditionally removes `.erk/impl-context/` before pushing. For implementation PRs this is correct (scratch data), but for **plan PRs** (branches starting with `plnd/`), `.erk/impl-context/plan.md` IS the PR content — it enables inline review comments on the plan via GitHub's "Files Changed" tab. When `/erk:pr-submit` is used to re-push a plan PR after addressing review comments, the cleanup deletes the plan from the diff entirely.

## Changes

### 1. Add early return for plan branches

**File:** `src/erk/cli/commands/pr/submit_pipeline.py` (line ~200)

In `cleanup_impl_for_submit()`, add an early return when the branch is a plan branch:

```python
def cleanup_impl_for_submit(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Remove .erk/impl-context/ if present and git-tracked.

    Skipped for plan branches (plnd/*) where impl-context IS the PR content.
    """
    if state.branch_name.startswith(PLANNED_PR_TITLE_PREFIX):
        return state

    if not impl_context_exists(state.repo_root):
        return state
    # ... rest unchanged
```

`PLANNED_PR_TITLE_PREFIX` (`"plnd/"`) is already imported in this file (line 26).

### 2. Add test for plan branch skip

**File:** `tests/unit/cli/commands/pr/submit_pipeline/test_cleanup_impl_for_submit.py`

Add a test that verifies plan branches keep their `.erk/impl-context/`:

```python
def test_noop_for_plan_branch(tmp_path: Path) -> None:
    """Plan branches (plnd/*) keep .erk/impl-context/ — it IS their PR content."""
    impl_dir = tmp_path / ".erk" / "impl-context"
    impl_dir.mkdir(parents=True)
    (impl_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")

    fake_git = FakeGit(
        tracked_paths={".erk/impl-context/plan.md"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, branch_name="plnd/my-plan-branch")

    result = cleanup_impl_for_submit(ctx, state)

    assert isinstance(result, SubmitState)
    assert result is state
    assert impl_dir.exists()
    assert len(fake_git.commits) == 0
```

## Verification

1. Run `pytest tests/unit/cli/commands/pr/submit_pipeline/test_cleanup_impl_for_submit.py` — all tests pass including new one
2. Run `make fast-ci` — full fast CI green
