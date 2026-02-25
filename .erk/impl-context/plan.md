# Fix: `setup_impl` passes unsupported `branch_slug` to `setup_impl_from_issue`

## Context

`erk exec setup-impl --issue <N>` fails with `TypeError: setup_impl_from_issue() got an unexpected keyword argument 'branch_slug'`. This prevents the full setup pipeline from running, which means `cleanup_impl_context` (called at line 314) never executes — leaving `.erk/impl-context/` files committed on the implementation branch.

Root cause: `_handle_issue_setup` in `setup_impl.py:290-296` forwards `branch_slug=branch_slug` via `ctx.invoke`, but `setup_impl_from_issue` doesn't accept that parameter. It gets the branch name from GitHub's PR API (`pr_result.head_ref_name`), so a user-provided slug is irrelevant.

The `--branch-slug` option on `setup_impl` is dead code — it was added for plan-save (which has its own `--branch-slug`), not for setup-impl which reads existing branches.

## Changes

### 1. `src/erk/cli/commands/exec/scripts/setup_impl.py`

- **Line 295**: Remove `branch_slug=branch_slug` from `ctx.invoke(setup_impl_from_issue, ...)`
- **Line 272**: Remove `branch_slug: str | None` from `_handle_issue_setup` signature
- **Lines 161-165**: Remove the `--branch-slug` Click option from `setup_impl`
- **Line 168**: Remove `branch_slug` from `setup_impl` function signature
- **Lines 184, 212, 256**: Remove `branch_slug=` from all `_handle_issue_setup` calls

### 2. `tests/unit/cli/commands/exec/scripts/test_setup_impl.py` — Add regression test

Add `test_issue_setup_invokes_setup_impl_from_issue` that invokes `setup_impl --issue <N>` with a FakeGitHub containing a matching PR, and verifies it succeeds (no TypeError). This exercises the `_handle_issue_setup` → `setup_impl_from_issue` path that was broken.

### 3. Clean up PR #8125

After the bug fix, run `erk exec cleanup-impl-context` on the `add-erkbot-system-prompt` branch to remove the leaked `.erk/impl-context/` files.

## Verification

1. `uv run pytest tests/unit/cli/commands/exec/scripts/test_setup_impl.py -v` — new regression test passes
2. `uv run pytest tests/unit/cli/commands/exec/scripts/test_setup_impl_from_issue.py -v` — existing tests unaffected
3. `make fast-ci` — full lint/format/ty/unit pass
