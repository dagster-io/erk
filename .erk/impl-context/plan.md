# Plan: Improved `erk land --stack` for bottom-up Graphite stack landing

## Context

PR #8948 implements `erk land --stack` to land an entire Graphite stack bottom-up. The core algorithm is sound (resolve stack, validate all PRs, then iterate: rebase → re-parent → merge → cleanup), but the implementation has several bugs, missing features, and design issues. This plan replans the implementation to produce a better PR.

## Issues in PR #8948 to fix

### Critical bugs
1. **`--dry-run --stack` is broken** — In `land()`, the `dry_run` context recreation happens at line 1560-1561 (`ctx = create_context(dry_run=True)`), but the PR's `--stack` dispatch is placed AFTER `discover_repo_context` without forwarding `dry_run`. The `execute_land_stack()` checks `ctx.dry_run` which is always False.
2. **No confirmation prompt** — Plan says "confirm (unless --force)" but the code lands without asking.

### Missing features
3. **No learn PR creation** — Plan says "Create learn PR per branch" but code doesn't implement it.
4. **Poor partial failure reporting** — On failure mid-stack, no indication of which PRs already landed.

### Design issues
5. **`raise SystemExit(0)` for success** — Makes every test use `pytest.raises(SystemExit)`. The `land()` function already returns after calling `execute_land_stack()`, so returning normally works.
6. **O(N²) re-parenting API calls** — `_reparent_upstack()` re-parents ALL remaining entries each iteration. Only the next entry needs re-parenting.

### Test gaps
7. No dry-run test (and dry-run is broken anyway)
8. No confirmation prompt test
9. No learn PR creation test
10. No operation ordering verification

## Files to modify

### 1. `src/erk/cli/commands/land_cmd.py` — MODIFY

Add `--stack` flag and dispatch. Key fix: place dispatch AFTER dry-run context recreation.

```python
# At line ~1508, add --stack option (same as PR)
@click.option("--stack", "stack_flag", is_flag=True, help="Land the entire Graphite stack bottom-up.")

# Add stack_flag parameter to land() signature

# Add mutual exclusion checks (same as PR):
Ensure.invariant(not (stack_flag and (up_flag or down_flag)), ...)
Ensure.invariant(not (stack_flag and target is not None), ...)

# CRITICAL FIX: Dispatch AFTER dry-run context recreation (move after line 1561)
if stack_flag:
    from erk.cli.commands.land_stack import execute_land_stack
    execute_land_stack(ctx, repo=repo, force=force, pull_flag=pull_flag,
                       no_delete=no_delete, skip_learn=skip_learn)
    return
```

The dispatch must happen after `ctx = create_context(dry_run=True)` so `ctx.dry_run` is correct.

### 2. `src/erk/cli/commands/land_stack.py` — NEW

Core stack landing logic. ~350 lines.

**Data types:**
```python
@dataclass(frozen=True)
class StackLandEntry:
    branch: str
    pr_number: int
    pr_details: PRDetails
    worktree_path: Path | None
    plan_id: str | None
    objective_number: int | None
```

**Functions:**

| Function | Purpose |
|----------|---------|
| `execute_land_stack(ctx, *, repo, force, pull_flag, no_delete, skip_learn)` | Main orchestrator. Returns normally on success. |
| `_resolve_stack(ctx, *, main_repo_root) -> list[str]` | Get stack branches (excluding trunk). |
| `_validate_stack_prs(ctx, *, main_repo_root, branches, trunk, force) -> list[StackLandEntry]` | Pre-validate all PRs. |
| `_display_stack_summary(entries)` | Show numbered PR list. |
| `_confirm_stack_land(ctx, *, entries, force)` | Prompt user; `raise SystemExit(0)` on decline. Skip if `force` or `ctx.dry_run`. |
| `_rebase_and_push(ctx, *, main_repo_root, branch, trunk)` | Fetch, rebase, force-push. Abort + error on conflict. |
| `_reparent_entry(ctx, *, main_repo_root, entry, trunk)` | Re-parent ONE entry's PR base + Graphite tracking. O(N) total. |
| `_merge_and_cleanup_branch(ctx, *, main_repo_root, entry)` | Squash-merge + delete remote branch. |
| `_try_create_learn_pr(ctx, *, main_repo_root, entry)` | Fire-and-forget learn PR creation if plan_id set. |
| `_cleanup_after_stack_land(ctx, *, repo, entries, main_repo_root)` | Delete local branches/worktrees. |
| `_pull_trunk(ctx, *, main_repo_root, trunk)` | Pull latest trunk. |

**Main loop in `execute_land_stack` (key changes from PR):**

```python
def execute_land_stack(ctx, *, repo, force, pull_flag, no_delete, skip_learn):
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    # 1. Resolve stack
    branches_to_land = _resolve_stack(ctx, main_repo_root=main_repo_root)

    # 2. Pre-validate all PRs
    trunk = ctx.git.branch.detect_trunk_branch(main_repo_root)
    entries = _validate_stack_prs(ctx, main_repo_root=main_repo_root,
                                   branches=branches_to_land, trunk=trunk, force=force)

    # 3. Display summary
    _display_stack_summary(entries)

    # 4. Dry-run early exit (ctx.dry_run is correct because dispatch is after context recreation)
    if ctx.dry_run:
        user_output(click.style("[DRY RUN] No changes made", fg="yellow", bold=True))
        return  # Return normally, not SystemExit

    # 5. Confirm unless --force
    _confirm_stack_land(ctx, entries=entries, force=force)

    # 6. Land each branch bottom-up with partial failure tracking
    landed: list[StackLandEntry] = []
    total = len(entries)

    for i, entry in enumerate(entries):
        try:
            if i > 0:
                _rebase_and_push(ctx, main_repo_root=main_repo_root,
                                 branch=entry.branch, trunk=trunk)

            # Re-parent ONLY the next entry (O(N) total)
            if i + 1 < total:
                _reparent_entry(ctx, main_repo_root=main_repo_root,
                                entry=entries[i + 1], trunk=trunk)

            _merge_and_cleanup_branch(ctx, main_repo_root=main_repo_root, entry=entry)
        except UserFacingCliError:
            _report_partial_failure(landed=landed, failed=entry,
                                    remaining=entries[i + 1:], total=total)
            raise

        landed.append(entry)
        user_output(click.style("✓", fg="green")
                    + f" Merged PR #{entry.pr_number} [{entry.branch}] ({i + 1}/{total})")

        # Learn PR (fire-and-forget, per branch)
        if not skip_learn and entry.plan_id is not None:
            _try_create_learn_pr(ctx, main_repo_root=main_repo_root, entry=entry)

    # 7-9. Cleanup, pull, objectives (same as PR but no SystemExit)
    ...
    user_output(click.style("✓", fg="green", bold=True)
                + f" Stack landed: {total} PR(s) merged successfully")
```

**Partial failure reporting:**
```python
def _report_partial_failure(*, landed, failed, remaining, total):
    lines = []
    for prev in landed:
        lines.append(click.style("  ✓ ", fg="green") + f"PR #{prev.pr_number} [{prev.branch}]")
    lines.append(click.style("  ✗ ", fg="red") + f"PR #{failed.pr_number} [{failed.branch}]")
    for rem in remaining:
        lines.append(click.style("  - ", dim=True) + f"PR #{rem.pr_number} [{rem.branch}]")
    user_output(f"\nStack progress ({len(landed)}/{total} landed):\n" + "\n".join(lines))
```

**Learn PR creation (fire-and-forget):**
```python
def _try_create_learn_pr(ctx, *, main_repo_root, entry):
    if entry.plan_id is None:
        return
    try:
        _create_learn_pr_core(ctx, repo_root=main_repo_root, plan_id=entry.plan_id,
                              merged_pr_number=entry.pr_number, cwd=main_repo_root)
    except Exception:
        user_output(click.style("Warning: ", fg="yellow")
                    + f"Learn plan creation failed for PR #{entry.pr_number}")
```

### 3. `tests/unit/cli/commands/land/test_land_stack.py` — NEW

**Key test improvements over PR:**

| Test | What it verifies | PR gap addressed |
|------|-----------------|------------------|
| `test_happy_path_three_branch_stack` | All 3 merged, rebases for B/C, re-parents before merges | No `pytest.raises(SystemExit)` needed |
| `test_dry_run_no_mutations` | Summary shown, no merges/rebases/re-parents | Bug #1: dry-run works |
| `test_confirmation_shown_without_force` | `ctx.console.confirm()` called | Bug #2: confirmation |
| `test_confirmation_declined_aborts` | `SystemExit(0)` on decline, no merges | Bug #2 |
| `test_force_skips_confirmation` | No confirm call with `force=True` | Bug #2 |
| `test_learn_pr_per_branch` | Learn PR created for entries with plan_id | Missing feature #3 |
| `test_skip_learn_no_learn_prs` | No learn PR with `skip_learn=True` | Missing feature #3 |
| `test_partial_failure_reports_progress` | Error output shows landed/failed/remaining | Missing feature #4 |
| `test_reparent_is_O_N` | Each PR base updated exactly once | Design issue #6 |
| `test_operation_ordering` | `operation_log` verifies re-parent before merge per iteration | Test gap #10 |
| `test_single_branch_stack` | No rebase, works like regular land | Same as PR |
| `test_rebase_conflict_bails_cleanly` | Rebase aborted, partial progress reported | Enhanced |
| `test_merge_failure` | Error raised, progress shown | Enhanced |
| `test_no_delete_preserves_branches` | Local branches preserved | Same as PR |
| `test_requires_graphite` | Error when Graphite disabled | Same as PR |
| `test_stack_not_found` | Error when branch not in stack | Same as PR |
| `test_pr_not_open_fails_fast` | Pre-validation catches non-open PR | Same as PR |

**Test infrastructure:**
- Use `context_for_test(console=FakeConsole(..., confirm_responses=[True]))` for confirmation tests
- Use `fake_github.operation_log` (exists at `fake.py:1072`) to verify operation ordering
- No `pytest.raises(SystemExit)` needed for happy paths since `execute_land_stack` returns normally
- For confirmation-declined test: `pytest.raises(SystemExit)` with code 0

## Verification

1. `uv run pytest tests/unit/cli/commands/land/test_land_stack.py -v`
2. `uv run ty check src/erk/cli/commands/land_stack.py`
3. `uv run ruff check src/erk/cli/commands/land_stack.py tests/unit/cli/commands/land/test_land_stack.py`
4. Existing land tests still pass: `uv run pytest tests/unit/cli/commands/land/ -v`
