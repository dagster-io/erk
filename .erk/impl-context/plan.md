# Plan: `erk land --stack` — Land entire Graphite stack

## Context

Currently `erk land` only lands a single PR. When working with Graphite stacks (main → A → B → C), the user must manually land each PR bottom-up, rebasing between each. This is tedious and error-prone. `erk land --stack` automates the full cycle: validate all PRs, then land each bottom-up with rebase between iterations.

## Why Rebase Is Required Between Each Land

After squash-merging PR A → trunk, trunk has a new squash commit (different SHA from A's original commits). PR B still has A's original commits. GitHub would see duplicate changes and produce conflicts. We must rebase B onto updated trunk to remove A's commits from B's history before merging B.

## Algorithm

```
1. Resolve stack: get_branch_stack → ["main", "A", "B", "C"]
   branches_to_land = ["A", "B", "C"]

2. Pre-validate ALL PRs (open, no unresolved comments unless --force)
   Fail fast before any mutations.

3. Display summary, confirm (unless --force)

4. For each branch [A, B, C] (bottom-up):
   a. If not first iteration:
      - Fetch updated trunk
      - Find cwd (worktree or checkout in root)
      - Rebase onto origin/trunk → BAIL if conflicts
      - Force-push rebased branch
   b. Re-parent remaining upstack PRs to trunk (GitHub API)
   c. Re-parent remaining upstack Graphite tracking to trunk
   d. Squash-merge via GitHub API
   e. Delete remote branch
   f. Create learn PR (if plan_id exists and not --skip-learn)
   g. Output: "✓ Merged PR #N [branch] (i/total)"

5. Post-land cleanup: delete local branches/worktrees, navigate to trunk
6. Objective updates (fail-open) for any linked objectives
```

## Files to Modify/Create

### 1. `src/erk/cli/commands/land_stack.py` — NEW

Core stack landing logic. Keeps `land_cmd.py` at manageable size.

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

- `execute_land_stack(ctx, repo, force, pull_flag, no_delete, skip_learn)` — main orchestrator
- `_resolve_stack(ctx, main_repo_root)` — get stack, strip trunk, validate Graphite mode
- `_validate_stack_prs(ctx, main_repo_root, branches, trunk, force)` → `list[StackLandEntry]` — pre-validate all PRs
- `_display_stack_summary(entries)` — show numbered list of PRs to land
- `_rebase_and_push(ctx, main_repo_root, branch, trunk)` — fetch, rebase, push; bail on conflict
- `_reparent_upstack(ctx, main_repo_root, remaining_entries, trunk)` — update PR bases + Graphite tracking
- `_merge_and_cleanup_branch(ctx, main_repo_root, entry)` — squash merge + delete remote
- `_resolve_rebase_cwd(ctx, main_repo_root, branch)` → `Path` — find worktree or checkout in root
- `_cleanup_after_stack_land(ctx, repo, entries, main_repo_root)` — delete local branches/worktrees

**Gateway operations used (all testable via fakes):**

| Operation | Gateway call |
|-----------|-------------|
| Get stack | `ctx.branch_manager.get_branch_stack(repo_root, branch)` |
| Fetch trunk | `ctx.git.remote.fetch_branch(repo_root, "origin", trunk)` |
| Find worktree | `ctx.git.worktree.find_worktree_for_branch(repo_root, branch)` |
| Checkout branch | `ctx.branch_manager.checkout_branch(repo_root, branch)` |
| Rebase | `ctx.git.rebase.rebase_onto(cwd, f"origin/{trunk}")` → `RebaseResult` |
| Abort rebase | `ctx.git.rebase.rebase_abort(cwd)` |
| Force push | `ctx.git.remote.push_to_remote(cwd, "origin", branch, set_upstream=False, force=True)` |
| Update PR base | `ctx.github.update_pr_base_branch(repo_root, pr_number, trunk)` |
| Track branch | `ctx.branch_manager.track_branch(repo_root, branch, trunk)` |
| Merge PR | `ctx.github.merge_pr(repo_root, pr_number, squash=True, ...)` |
| Delete remote | `ctx.github.delete_remote_branch(repo_root, branch)` |
| Get PR details | `ctx.github.get_pr_for_branch(repo_root, branch)` |
| Delete local branch | `ctx.branch_manager.delete_branch(repo_root, branch, force=True)` |

### 2. `src/erk/cli/commands/land_cmd.py` — MODIFY

Add `--stack` flag and routing.

**Changes:**
- Add `--stack` Click option (is_flag=True)
- Add `stack_flag` parameter to `land()` function
- Add mutual exclusion: `--stack` vs `--up`/`--down`/`target`
- Add dispatch: when `stack_flag` is True, call `execute_land_stack()` from `land_stack.py`

```python
# New option (between --no-delete and --skip-learn)
@click.option(
    "--stack",
    "stack_flag",
    is_flag=True,
    help="Land the entire Graphite stack bottom-up.",
)

# Mutual exclusion in land()
Ensure.invariant(
    not (stack_flag and (up_flag or down_flag)),
    "--stack is mutually exclusive with --up and --down.",
)
Ensure.invariant(
    not (stack_flag and target is not None),
    "--stack cannot be combined with a target argument.",
)

# Dispatch
if stack_flag:
    execute_land_stack(ctx, repo=repo, force=force, ...)
    return
```

### 3. `tests/unit/cli/commands/land/test_land_stack.py` — NEW

Unit tests for `execute_land_stack` and helpers.

**Test cases:**

1. **Happy path: 3-branch stack** — All 3 PRs merge in order. Assert: merge calls in order, rebase for B and C (not A), re-parent calls before each merge, remote branches deleted.

2. **Single-branch stack** — Stack is `["main", "A"]`. No rebase needed. Works like regular land.

3. **Requires Graphite** — Error when `is_graphite_managed()` returns False.

4. **Stack returns None** — Error when branch not in any Graphite stack.

5. **Pre-validation: PR not open** — One PR is MERGED. No mutations happen.

6. **Pre-validation: unresolved comments** — Without `--force`, aborts before any mutations.

7. **Rebase conflict bails cleanly** — FakeGit `rebase_onto_result=RebaseResult(success=False, ...)`. First PR merged, rebase aborted, error with partial progress.

8. **Merge failure mid-stack** — FakeGitHub `merge_should_succeed=False` for second PR. First landed, error for second.

9. **Re-parenting order** — Assert `update_pr_base_branch` calls happen before `merge_pr` for each iteration.

10. **Learn PRs created per-branch** — Entries with plan_ids get learn PR creation.

11. **Dry-run shows summary** — No mutations, output shows what would be landed.

12. **Worktree fallback** — Branch without worktree falls back to root worktree checkout.

**Fake setup pattern** (matches existing land tests):
```python
FakeBranchManager(
    graphite_mode=True,
    stacks={"A": ["main", "A", "B", "C"]},  # All branches return same stack
    parent_branches={"A": "main", "B": "A", "C": "B"},
)
FakeLocalGitHub(
    pr_details={101: PRDetails(..., branch="A"), 102: ..., 103: ...},
    merge_should_succeed=True,
)
FakeGit(rebase_onto_result=RebaseResult(success=True, conflict_files=()))
```

### 4. `tests/commands/land/test_stack_flag.py` — NEW

CLI-level tests for flag validation via CliRunner.

- `--stack --up` → error
- `--stack --down` → error
- `--stack 123` → error (target + stack)
- `--stack --force` → works (compatible)

## Error Handling

**Partial failure:** If PR #2 of 3 fails (rebase conflict, merge failure), report:
```
✓ Merged PR #101 [A] (1/3)
✗ Failed to land PR #102 [B]: Rebase conflicts on 'B'

Resolve conflicts: cd <worktree> && erk pr rebase
Then retry: erk land --stack
```

The remaining upstack PRs are already re-parented to trunk (step 4b/4c happens before merge), so the user can fix and retry.

**Bail on rebase conflict:** Call `ctx.git.rebase.rebase_abort(cwd)` to clean up, then exit with error message.

## Key Design Decisions

1. **Separate file (`land_stack.py`)** — The stack loop is fundamentally different from the single-PR pipeline pattern. Forcing it into `LandStep` functions would be awkward.

2. **GitHub API merge (not `execute_land_pr`)** — We know the full stack upfront and handle re-parenting ourselves. `execute_land_pr` discovers children dynamically which adds unnecessary complexity.

3. **Gateway rebase (not `gt restack` subprocess)** — `ctx.git.rebase.rebase_onto()` is fully testable via `FakeGitRebaseOps`. Raw `subprocess.run(["gt", "restack"])` isn't.

4. **No deferred script mode** — Stack landing always ends at trunk. No shell navigation needed.

5. **Bail on conflicts (V1)** — No auto-resolution. User fixes with `erk pr rebase`, then retries.

## Verification

1. **Unit tests:** `uv run pytest tests/unit/cli/commands/land/test_land_stack.py`
2. **CLI tests:** `uv run pytest tests/commands/land/test_stack_flag.py`
3. **Type check:** `uv run ty check src/erk/cli/commands/land_stack.py`
4. **Lint:** `uv run ruff check src/erk/cli/commands/land_stack.py`
5. **Manual test (dry-run):** From a Graphite stack, run `erk land --stack --dry-run` to verify stack resolution and summary output
