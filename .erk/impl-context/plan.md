# Plan: Make RemoteGitHub the Canonical One-Shot Dispatch Path

Part of Objective #8832, Node 1.5 (canonical-remote-one-shot)

## Context

The one-shot command currently has two parallel dispatch paths:
- **Local path** (`dispatch_one_shot` in `one_shot_dispatch.py`): Uses subprocess-based git + gh CLI to create branches, push, create PRs, dispatch workflows
- **Remote path** (`dispatch_one_shot_remote` in `one_shot_remote_dispatch.py`): Uses RemoteGitHub REST API gateway — no local git needed

The local path exists because the remote path was added later (node 1.3, `--repo` flag). Now that RemoteGitHub is proven, we unify onto it and delete the local dispatch code. This eliminates ~200 lines of parallel logic and makes the one-shot command work without a local git clone when `--repo` is provided.

**Dependency**: Node 1.4 (#8880) must land first — provides `@no_repo_required` decorator.

## Implementation

### Phase 1: Move shared types from `one_shot_dispatch.py` to `one_shot_remote_dispatch.py`

The remote dispatch module already imports these from the local module. Move them so we can delete the local module.

**Symbols to move:**
- `OneShotDispatchParams` (dataclass)
- `OneShotDispatchResult` (dataclass)
- `ONE_SHOT_WORKFLOW` (constant)
- `generate_branch_name` (function)

**File**: `src/erk/cli/commands/one_shot_remote_dispatch.py`
- Move the 4 symbols into this file
- Remove the import from `one_shot_dispatch`

### Phase 2: Update all callers to import from `one_shot_remote_dispatch`

Update imports in:
- `src/erk/cli/commands/one_shot.py` (imports `OneShotDispatchParams`, `dispatch_one_shot`)
- `src/erk/cli/commands/objective/plan_cmd.py` (imports `OneShotDispatchParams`, `dispatch_one_shot`)
- `src/erk/core/workflow_smoke_test.py` (imports `OneShotDispatchParams`, `dispatch_one_shot`)

### Phase 3: Convert `one_shot.py` to always use RemoteGitHub

**File**: `src/erk/cli/commands/one_shot.py`

Current logic (lines 147-158):
```python
if target_repo is not None:
    _dispatch_remote(ctx, target_repo=target_repo, ...)
else:
    ref = resolve_dispatch_ref(ctx, ...)
    dispatch_one_shot(ctx, params=params, ...)
```

New logic:
```python
# Resolve owner/repo: from --repo flag or from local git remote
if target_repo is not None:
    if "/" not in target_repo or target_repo.count("/") != 1:
        raise UserFacingCliError(...)
    owner, repo_name = target_repo.split("/")
else:
    # Extract from local repo's git remote
    if isinstance(ctx.repo, NoRepoSentinel) or ctx.repo.github is None:
        raise UserFacingCliError(
            "Cannot determine target repository.\n"
            "Use --repo owner/repo or run from inside a git repository."
        )
    owner, repo_name = ctx.repo.github.owner, ctx.repo.github.repo

# Construct RemoteGitHub
if ctx.http_client is None:
    raise UserFacingCliError("GitHub authentication required.\nRun 'gh auth login'.")

remote = RealRemoteGitHub(http_client=ctx.http_client, time=ctx.time)

# Resolve dispatch ref
if target_repo is not None and ref_current:
    raise click.UsageError("--repo and --ref-current are mutually exclusive")
if target_repo is not None:
    ref = dispatch_ref  # no local branch resolution for remote
else:
    ref = resolve_dispatch_ref(ctx, dispatch_ref=dispatch_ref, ref_current=ref_current)

dispatch_one_shot_remote(
    remote=remote, owner=owner, repo=repo_name,
    params=params, dry_run=dry_run, ref=ref,
    time_gateway=ctx.time, llm_caller=ctx.llm_caller,
)
```

- Apply `@no_repo_required` decorator (from node 1.4)
- Delete `_dispatch_remote` helper (logic absorbed into main function)

### Phase 4: Convert `objective/plan_cmd.py` callers

**File**: `src/erk/cli/commands/objective/plan_cmd.py`

Functions `_handle_one_shot` (line 683) and `_handle_all_unblocked` (line 245) call `dispatch_one_shot(ctx, ...)`. Convert both to:
1. Extract `owner/repo` from `ctx.repo.github`
2. Construct `RealRemoteGitHub(http_client=ctx.http_client, time=ctx.time)`
3. Call `dispatch_one_shot_remote(remote=..., owner=..., repo=..., ...)`

These functions already validate `ctx.repo` is not `NoRepoSentinel`, so `ctx.repo.github` access is safe. Just need to also validate `ctx.repo.github is not None` and `ctx.http_client is not None`.

### Phase 5: Convert `workflow_smoke_test.py`

**File**: `src/erk/core/workflow_smoke_test.py`

`run_smoke_test` (line 53) calls `dispatch_one_shot(ctx, ...)`. Same conversion pattern as Phase 4.

### Phase 6: Handle dispatch metadata gap

The local `dispatch_one_shot` writes dispatch metadata via `write_dispatch_metadata()` (plan backend + gh CLI). The remote path doesn't. Two options:

**Option A (Recommended)**: Accept the gap. The metadata writing is best-effort (wrapped in try/except), and the queued comment already tracks the dispatch. The plan-header metadata can be updated later when we add `update_plan_header` to RemoteGitHub.

**Option B**: Add a `write_dispatch_metadata_remote` that uses RemoteGitHub to update the PR body. This is extra scope.

Go with Option A — the metadata gap is acceptable and can be addressed in a follow-up.

### Phase 7: Delete `one_shot_dispatch.py`

Delete `src/erk/cli/commands/one_shot_dispatch.py` entirely. All its symbols are either moved to `one_shot_remote_dispatch.py` or deleted.

### Phase 8: Update tests

**Test files to update:**
- `tests/commands/one_shot/test_one_shot.py` — update imports, ensure tests use FakeRemoteGitHub
- `tests/commands/objective/test_plan_one_shot.py` — update imports and dispatch mocks
- `tests/unit/core/test_workflow_smoke_test.py` — update imports and dispatch mocks

Key pattern: Tests that previously mocked `dispatch_one_shot` should now mock `dispatch_one_shot_remote` or use `FakeRemoteGitHub`.

## Files Modified

| File | Action |
|------|--------|
| `src/erk/cli/commands/one_shot_remote_dispatch.py` | Add shared types, remove old import |
| `src/erk/cli/commands/one_shot.py` | Unify onto RemoteGitHub, add @no_repo_required |
| `src/erk/cli/commands/objective/plan_cmd.py` | Switch to dispatch_one_shot_remote |
| `src/erk/core/workflow_smoke_test.py` | Switch to dispatch_one_shot_remote |
| `src/erk/cli/commands/one_shot_dispatch.py` | **DELETE** |
| `tests/commands/one_shot/test_one_shot.py` | Update imports and mocks |
| `tests/commands/objective/test_plan_one_shot.py` | Update imports and mocks |
| `tests/unit/core/test_workflow_smoke_test.py` | Update imports and mocks |

## Key References

- `RemoteGitHub` ABC: `packages/erk-shared/src/erk_shared/gateway/remote_github/abc.py`
- `FakeRemoteGitHub`: `packages/erk-shared/src/erk_shared/gateway/remote_github/fake.py`
- `RealRemoteGitHub`: `packages/erk-shared/src/erk_shared/gateway/remote_github/real.py`
- `RepoContext.github`: `packages/erk-shared/src/erk_shared/context/types.py:117` — `GitHubRepoId` with `.owner`/`.repo`
- `resolve_dispatch_ref`: `src/erk/cli/commands/ref_resolution.py` — uses `ctx.git` (needs local repo for `--ref-current`)

## Verification

1. Run unit tests: `make fast-ci`
2. Manual smoke test: `erk one-shot "test prompt" --dry-run` (from inside a repo, no --repo flag)
3. Manual smoke test: `erk one-shot "test prompt" --repo dagster-io/erk --dry-run` (with --repo flag)
4. Verify `erk objective plan 8832 --one-shot --dry-run --node 1.6` still works
