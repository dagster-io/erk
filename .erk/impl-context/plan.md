# Detect remote divergence before `gt submit` in Graphite-first flow

## Context

When `erk pr submit` uses the Graphite-first flow (`_graphite_first_flow`), it calls `gt submit` directly without checking if the local branch has diverged from the remote. If the remote branch was updated (e.g., by CI or another session), `gt submit` fails with a raw error:

```
ERROR: Branch X has been updated remotely. Use gt get or gt sync...
```

This surfaces as a generic "Graphite submit failed" message with no actionable guidance. Meanwhile, the core submit flow (`_core_submit_flow`) already has clean divergence detection at lines 296-339 of `submit_pipeline.py` with fetch, auto-rebase, and helpful error messages.

**Goal**: Detect remote divergence _before_ calling `gt submit` in the Graphite-first flow and return a clean `SubmitError` with actionable instructions.

## Implementation

### Step 1: Add pre-check in `_graphite_first_flow`

**File**: `src/erk/cli/commands/pr/submit_pipeline.py` (lines 200-266)

Insert divergence detection between the "Phase 1" echo (line 202) and the `submit_stack` call (line 204). Pattern from `sync_divergence_cmd.py` lines 59-67:

```python
# After line 202 (Phase 1 echo), before line 203 (Running gt submit echo):

# Pre-check: detect remote divergence before gt submit
if ctx.git.branch.branch_exists_on_remote(state.repo_root, "origin", state.branch_name):
    ctx.git.remote.fetch_branch(state.repo_root, "origin", state.branch_name)
    divergence = ctx.git.branch.is_branch_diverged_from_remote(
        state.cwd, state.branch_name, "origin"
    )
    if divergence.behind > 0 and not state.force:
        return SubmitError(
            phase="push_and_create_pr",
            error_type="remote_diverged",
            message=(
                f"Branch '{state.branch_name}' is behind remote by "
                f"{divergence.behind} commit(s)"
                + (f" and ahead by {divergence.ahead} commit(s)" if divergence.ahead > 0 else "")
                + ".\n\n"
                "The remote branch has been updated (e.g., by CI or another session).\n\n"
                "To fix:\n"
                "  erk pr sync-divergence --dangerous   # Fetch, rebase, and resolve conflicts\n"
                "  erk pr submit -f                     # Force push (overrides remote changes)"
            ),
            details={
                "branch": state.branch_name,
                "ahead": str(divergence.ahead),
                "behind": str(divergence.behind),
            },
        )
```

Key design decisions:

- **Guard on `branch_exists_on_remote`**: New branches have no remote tracking — skip the check
- **Fetch first**: Local remote refs can be stale; `fetch_branch` gets current state
- **Check `behind > 0`** not just `is_diverged`: A branch only behind (ahead=0) still needs sync
- **`--force` bypasses**: Consistent with how `gt submit --force` works

### Step 2: Tests

**File**: `tests/commands/pr/test_submit.py`

Add test functions using the existing patterns in the file:

1. **`test_pr_submit_graphite_flow_detects_remote_divergence`** — Configure `FakeGit` with `remote_branches` containing the branch and `branch_divergence` showing behind > 0. Assert clean error output with "behind remote" and both fix suggestions. Assert `gt submit` was never called.

2. **`test_pr_submit_graphite_flow_force_bypasses_divergence`** — Same setup but invoke with `--force`. Assert `gt submit` was called (no divergence error).

3. **`test_pr_submit_graphite_flow_skips_check_for_new_branch`** — No `remote_branches` configured (branch doesn't exist remotely). Assert submission proceeds past divergence check.

FakeGit configuration for divergence test:

```python
git = FakeGit(
    remote_branches={env.cwd: ["origin/feature"]},  # Branch exists on remote
    branch_divergence={
        (env.cwd, "feature", "origin"): BranchDivergence(
            is_diverged=True, ahead=1, behind=2
        )
    },
    # ... other standard config
)
```

## Files to modify

| File                                         | Change                                             |
| -------------------------------------------- | -------------------------------------------------- |
| `src/erk/cli/commands/pr/submit_pipeline.py` | Add divergence pre-check in `_graphite_first_flow` |
| `tests/commands/pr/test_submit.py`           | Add 3 test functions                               |

## Existing utilities reused

- `ctx.git.branch.branch_exists_on_remote()` — `packages/erk-shared/.../git/branch_ops/abc.py:177`
- `ctx.git.remote.fetch_branch()` — `packages/erk-shared/.../git/remote_ops/abc.py:28`
- `ctx.git.branch.is_branch_diverged_from_remote()` — `packages/erk-shared/.../git/branch_ops/abc.py` (returns `BranchDivergence`)
- `FakeGitBranchOps` supports `remote_branches` and `branch_divergence` constructor args

## Verification

1. Run existing submit tests: `uv run pytest tests/commands/pr/test_submit.py`
2. Run new tests specifically
3. Run ty on the modified file: `uv run ty check src/erk/cli/commands/pr/submit_pipeline.py`
