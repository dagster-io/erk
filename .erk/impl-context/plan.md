# Plan: Eliminate dual code paths in `erk launch` — single path via RemoteGitHub

## Context

PR #9019 introduced `--repo` support for `erk launch` by adding a separate "remote mode" code path. This duplicated every workflow handler (5 local + 5 remote = 10 functions) and a separate dispatch function, resulting in ~900 lines with significant duplication. The user wants a single code path where the only difference with a local repo is that owner/repo can be inferred.

## Design

**Always use `RemoteGitHub`** for PR lookup and workflow dispatch. Local repo presence only provides enrichments:
- Infer owner/repo from git remote (skip `--repo`)
- Infer PR from current branch for pr-rebase (skip `--pr`)
- Resolve `--ref-current` and config-based dispatch ref
- Plan ID resolution and plan metadata updates post-dispatch

## Implementation

### Step 1: Rewrite `_dispatch_workflow` to use RemoteGitHub

Replace the two dispatch functions (local + remote) with one:

```python
def _dispatch_workflow(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo_name: str,
    workflow_name: str,
    inputs: dict[str, str],
    ref: str,  # Always resolved before calling
) -> str:  # Returns run_id
```

- `ref` is `str` not `str | None` — always resolved before this point
- Returns `run_id` so caller can do post-dispatch plan metadata updates
- No longer calls `maybe_update_plan_dispatch_metadata` internally

### Step 2: Rewrite per-workflow handlers — delete all `_*_remote` variants

Replace 10 functions with 5 unified ones. Each uses `RemoteGitHub` + explicit `owner`/`repo_name`:

- `_dispatch_pr_rebase(remote, *, owner, repo_name, pr_number: int, ...)` — `pr_number` is always resolved
- `_dispatch_pr_address(remote, *, owner, repo_name, pr_number, ...)`
- `_dispatch_pr_rewrite(remote, *, owner, repo_name, pr_number, ...)`
- `_dispatch_learn(remote, *, owner, repo_name, issue, ...)`
- `_dispatch_one_shot(remote, *, owner, repo_name, pr_number, prompt, ...)`

Each handler: looks up PR via `remote.get_pr()` (returns `RemotePRInfo`), validates state, builds inputs, calls `_dispatch_workflow`, returns `(branch_name, run_id)` tuple for post-dispatch enrichment.

Plan ID is passed in as a parameter (resolved by entry point), not resolved inside handler.

### Step 3: Restructure `launch()` entry point — remove `is_remote` branching

Single flow:
1. `resolve_owner_repo(ctx, target_repo=target_repo)` — already handles both `--repo` and local inference
2. `get_remote_github(ctx)` — get RemoteGitHub instance
3. Auth check via remote (replace `Ensure.gh_authenticated` which needs `gh` CLI)
4. Resolve dispatch ref — local enrichments when available, fallback to `remote.get_default_branch_name()`
5. Local enrichment: pr-rebase branch inference when no `--pr` (uses `ctx.github.get_pr_for_branch`)
6. Local enrichment: plan ID resolution via `ctx.plan_backend.resolve_plan_id_for_branch`
7. Dispatch to unified handler
8. Post-dispatch: `maybe_update_plan_dispatch_metadata` when local repo available

### Step 4: Update ref resolution

Keep `resolve_dispatch_ref()` for local-repo cases. Add a wrapper/fallback:
- When local repo: use existing `resolve_dispatch_ref()` which may return `None`
- When result is `None`: fall back to `remote.get_default_branch_name(owner, repo_name)`
- When no local repo and no `--ref`: use `remote.get_default_branch_name(owner, repo_name)`
- `--ref-current` errors if no local repo

### Step 5: Update tests

**`test_launch_cmd.py`**: Migrate from `FakeLocalGitHub` to `FakeRemoteGitHub` for PR lookup and dispatch verification:
- Replace `FakeLocalGitHub(prs=..., pr_details=...)` with `FakeRemoteGitHub(prs=...)` using `RemotePRInfo`
- Replace `github.triggered_workflows` assertions with `fake_remote.dispatched_workflows`
- Pass `remote_github=fake_remote` via kwargs to `build_workspace_test_context`
- Keep `FakeGit` for branch inference tests (pr-rebase without `--pr`)
- Still need `FakeLocalGitHub` (can be empty default) since `build_workspace_test_context` creates one

**`test_launch_remote_paths.py`**: Minimal changes — already uses `FakeRemoteGitHub`. Update test names/descriptions to remove "remote mode" terminology.

### Step 6: Clean up imports

Remove from `launch_cmd.py`: `PRNotFound`, `PRDetails`, `RepoContext` (only needed for type narrowing at entry point, use `NoRepoSentinel` check instead).

## Files to modify

- `src/erk/cli/commands/launch_cmd.py` — core refactoring (from ~917 lines to ~450-500)
- `tests/commands/launch/test_launch_cmd.py` — migrate to FakeRemoteGitHub
- `tests/commands/launch/test_launch_remote_paths.py` — minor updates

## Verification

1. Run `uv run pytest tests/commands/launch/` — all tests pass
2. Run `uv run ruff check src/erk/cli/commands/launch_cmd.py` — no lint errors
3. Run `uv run ty check src/erk/cli/commands/launch_cmd.py` — no type errors
4. Manual smoke test: `erk launch pr-rebase --pr 123` (from local repo) and `erk launch pr-rebase --pr 123 --repo owner/repo` (without local repo) should follow the same code path
