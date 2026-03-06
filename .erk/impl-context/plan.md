# Plan: `erk reconcile` + Rename `reconcile-with-remote` → `diverge-fix`

## Context

`erk land` is the only way to trigger post-merge lifecycle operations (learn PR creation, objective updates, branch/worktree cleanup). If a PR is merged outside erk — via GitHub web UI, mobile, or API — these operations are skipped, leaving stale local branches, unupdated objectives, and lost session data.

**`erk reconcile`** detects locally which PRs were merged remotely and runs the same post-merge lifecycle. It's a first-class command, not optional maintenance.

To free up the "reconcile" name, the existing `erk pr reconcile-with-remote` (branch divergence fixer) is renamed to `erk pr diverge-fix`.

---

## Part 1: Rename `reconcile-with-remote` → `diverge-fix`

Mechanical rename across files. No behavioral changes.

### File renames (4 files)

| From | To |
|---|---|
| `.claude/commands/erk/reconcile-with-remote.md` | `.claude/commands/erk/diverge-fix.md` |
| `src/erk/cli/commands/pr/reconcile_with_remote_cmd.py` | `src/erk/cli/commands/pr/diverge_fix_cmd.py` |
| `tests/commands/pr/test_reconcile_with_remote.py` | `tests/commands/pr/test_diverge_fix.py` |
| `docs/learned/cli/commands/pr-reconcile-with-remote.md` | `docs/learned/cli/commands/pr-diverge-fix.md` |

### Content updates in renamed files

- **`diverge-fix.md`** (slash command): All `reconcile-with-remote` → `diverge-fix`, stash message updated
- **`diverge_fix_cmd.py`**: Function `pr_diverge_fix`, click name `"diverge-fix"`, import `stream_diverge_fix`
- **`test_diverge_fix.py`**: Test names, invoke args, command assertions all updated
- **`pr-diverge-fix.md`** (learned doc): Title, references updated

### Content-only updates (12 files)

| File | Change |
|---|---|
| `src/erk/cli/commands/pr/__init__.py` | Import `diverge_fix_cmd`, register as `"diverge-fix"` |
| `src/erk/cli/output.py` | Rename `ReconcileWithRemoteResult` → `DivergenceFixResult`, `stream_reconcile_with_remote` → `stream_diverge_fix`, update command strings |
| `src/erk/cli/ensure.py` | Comment update (line 126) |
| `src/erk/cli/commands/pr/submit_pipeline.py` | Error message (line 297) |
| `tests/commands/pr/test_submit.py` | Assertion (line 1790) |
| `.claude/commands/erk/pr-address.md` | Reference (line 373) |
| `docs/learned/cli/index.md` | Link update |
| `docs/learned/cli/commands/index.md` | Heading + link |
| `docs/learned/cli/command-organization.md` | Table row |
| `docs/learned/erk/graphite-divergence-detection.md` | CLI reference |
| `docs/learned/architecture/tripwires.md` | Tripwire reference |
| `docs/learned/architecture/git-graphite-quirks.md` | Warning reference |
| `docs/learned/pr-operations/draft-pr-handling.md` | Resolution reference |
| `docs/howto/conflict-resolution.md` | Table + code blocks |
| `docs/howto/pr-checkout-sync.md` | Multiple references |

**Leave CHANGELOG.md historical entries unchanged.**

---

## Part 2: Git Layer Extensions

### 2A: Add `gone` field to `BranchSyncInfo`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/abc.py`

Add `gone: bool = False` to the frozen dataclass. Default keeps backward compat.

### 2B: Parse `[gone]` in `get_all_branch_sync_info`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py` (line ~316)

After parsing the track string, add: `gone = "gone" in track`. Pass to `BranchSyncInfo` constructor.

### 2C: Add `fetch_prune` to remote ops

Add to all 5 implementations of `GitRemoteOps`:

| File | Implementation |
|---|---|
| `gateway/git/remote_ops/abc.py` | Abstract method |
| `gateway/git/remote_ops/real.py` | `run_subprocess_with_context(["git", "fetch", "--prune", remote], ...)` |
| `gateway/git/remote_ops/fake.py` | Record call, optionally raise |
| `gateway/git/remote_ops/dry_run.py` | Print dry-run message, delegate |
| `gateway/git/remote_ops/printing.py` | Print command, delegate |

---

## Part 3: `erk reconcile` Command

### 3A: Detection — `reconcile_pipeline.py` (new)

**File:** `src/erk/cli/commands/reconcile_pipeline.py`

**Data types:**

```python
@dataclass(frozen=True)
class ReconcileBranchInfo:
    branch: str
    pr_number: int
    pr_title: str | None
    worktree_path: Path | None
    plan_id: str | None
    objective_number: int | None

@dataclass(frozen=True)
class ReconcileResult:
    branch: str
    learn_created: bool
    objective_updated: bool
    cleaned_up: bool
    error: str | None  # None = success
```

**`detect_merged_branches(ctx, repo_root, main_repo_root) -> list[ReconcileBranchInfo]`**

1. `ctx.git.remote.fetch_prune(repo_root, "origin")`
2. `ctx.git.branch.get_all_branch_sync_info(repo_root)` → filter `gone=True`
3. Exclude trunk branch
4. For each candidate: `ctx.github.get_pr_for_branch(main_repo_root, branch)` → keep only `state == "MERGED"`
5. For each confirmed merged: resolve `plan_id` via `ctx.plan_backend.resolve_plan_id_for_branch()`, `objective_number` via `get_objective_for_branch()`, `worktree_path` via `ctx.git.worktree.find_worktree_for_branch()`

**`process_merged_branch(ctx, info, *, main_repo_root, cwd, dry_run) -> ReconcileResult`**

Per branch, in order (same as land execution pipeline):

1. **Learn PR** (fail-open): Call `create_learn_pr_for_reconcile()` — a new thin wrapper that calls `_create_learn_pr_impl` with the needed fields. This avoids constructing a full `LandState`.
2. **Objective update** (fail-open): Call `run_objective_update_after_land()` from `objective_helpers.py`
3. **Cleanup**: Extract and reuse cleanup logic from `land_cmd.py`:
   - `_ensure_branch_not_checked_out(ctx, repo_root, branch)`
   - Slot handling: `find_branch_assignment()` → `execute_unassign()` if assigned
   - `ctx.branch_manager.delete_branch(repo_root, branch, force=True)`
   - Worktree removal if non-slot linked worktree

Errors on one branch don't prevent processing others. Collect results and report at end.

### 3B: Learn PR extraction

**File:** `src/erk/cli/commands/land_learn.py`

Extract a new public function that doesn't require `LandState`:

```python
def create_learn_pr_for_merged_branch(
    ctx: ErkContext,
    *,
    plan_id: str,
    merged_pr_number: int,
    main_repo_root: Path,
    cwd: Path,
) -> None:
    """Create learn PR for a branch merged outside erk land. Fire-and-forget."""
```

This wraps the same `_create_learn_pr_impl` internals but constructs the needed state locally. The existing `_create_learn_pr_with_sessions` continues to work via `LandState` for the land pipeline.

### 3C: CLI command — `reconcile_cmd.py` (new)

**File:** `src/erk/cli/commands/reconcile_cmd.py`

```python
@click.command("reconcile")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@click.option("--dry-run", is_flag=True, help="Preview without making changes")
@click.option("--skip-learn", is_flag=True, help="Skip creating learn plans")
@click.pass_obj
def reconcile(ctx, *, force, dry_run, skip_learn) -> None:
```

Flow:
1. Discover repo context
2. `detect_merged_branches()` → list of candidates
3. If empty: "Nothing to reconcile." exit 0
4. Display table: branch, PR#, title, plan, objective, worktree
5. Confirm (unless `--force` or `--dry-run`)
6. Process each branch, collect results
7. Pull trunk
8. Display summary table with results

### 3D: Register command

**File:** `src/erk/cli/cli.py`

```python
from erk.cli.commands.reconcile_cmd import reconcile
cli.add_command(reconcile)  # after cli.add_command(land)
```

---

## Part 4: Tests

### Unit tests for git layer

**File:** Add to existing branch_ops tests or new file

- `BranchSyncInfo` with `gone=True` constructed correctly
- `get_all_branch_sync_info` parses `[gone]` from track string
- Normal `[ahead N, behind M]` still works alongside `gone`

### Integration tests for reconcile

**File:** `tests/commands/test_reconcile.py` (new)

| Test | What it verifies |
|---|---|
| `test_detects_merged_branches` | FakeGit `gone=True` + FakeGitHub `MERGED` → detected |
| `test_skips_closed_not_merged` | `gone=True` but PR state `CLOSED` → skipped |
| `test_skips_normal_branches` | Branches without `gone` → skipped |
| `test_skips_trunk` | Trunk with `gone=True` → skipped |
| `test_dry_run_no_mutations` | `--dry-run` shows plan, no deletions |
| `test_force_skips_confirmation` | `--force` processes without prompting |
| `test_cleans_up_branch` | Branch deleted after processing |
| `test_unassigns_slot` | Slot unassigned before branch deletion |
| `test_creates_learn_pr` | Learn PR created for branches with plans |
| `test_nothing_to_reconcile` | No `gone` branches → "Nothing to reconcile" |
| `test_learn_failure_continues` | Learn error doesn't block cleanup |
| `test_objective_failure_continues` | Objective error doesn't block cleanup |
| `test_pulls_trunk_after` | Trunk pulled after all branches processed |

### Rename verification

Run existing `test_diverge_fix.py` (renamed) and `test_submit.py` to verify the rename is clean.

---

## Implementation Order

1. **Part 2** — Git layer extensions (`gone` field, `fetch_prune`)
2. **Part 1** — Rename `reconcile-with-remote` → `diverge-fix` (mechanical)
3. **Part 3A-B** — Pipeline logic + learn extraction
4. **Part 3C-D** — CLI command + registration
5. **Part 4** — Tests
6. Run CI

---

## Verification

1. `erk pr diverge-fix --dangerous` works (renamed command)
2. `/erk:diverge-fix` slash command triggers correctly
3. `erk reconcile --dry-run` detects merged branches without mutating
4. `erk reconcile --force` processes branches end-to-end
5. All existing tests pass after rename
6. New tests pass for reconcile pipeline
