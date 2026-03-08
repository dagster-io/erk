# Plan: Convert `erk launch` to @no_repo_required with --repo flag

Part of Objective #8832, Node 3.3 (launch-remote)

## Context

The `erk launch` command dispatches GitHub Actions workflows (pr-rebase, pr-address, pr-rewrite, learn, one-shot). It currently requires a local git repo for all operations, even though the actual work is done remotely via GitHub Actions. This prevents using `erk launch` from machines without a local clone (e.g., remote dispatch from a phone, CI, or a different project directory).

The goal is to add a `--repo owner/repo` flag so `erk launch` can work without a local git repository, following the same unified pattern established in node 3.2 (pr dispatch).

## Approach

### 1. Add `get_pr` to RemoteGitHub gateway

The launch command needs PR-specific fields (head_ref_name, base_ref_name, state) that `get_issue()` doesn't provide. Add a `get_pr` method to the RemoteGitHub ABC calling `GET /repos/{owner}/{repo}/pulls/{number}`.

**New file: `packages/erk-shared/src/erk_shared/gateway/remote_github/types.py`**
- `RemotePRInfo` frozen dataclass: number, title, state, url, head_ref_name, base_ref_name, owner, repo, labels
- `RemotePRNotFound` frozen dataclass: pr_number

**Modify: `packages/erk-shared/src/erk_shared/gateway/remote_github/abc.py`**
- Add abstract `get_pr(*, owner, repo, number) -> RemotePRInfo | RemotePRNotFound`

**Modify: `packages/erk-shared/src/erk_shared/gateway/remote_github/real.py`**
- Implement via `GET /repos/{owner}/{repo}/pulls/{number}`
- Map state: API returns lowercase "open"/"closed" + `merged` bool → "OPEN"/"CLOSED"/"MERGED"

**Modify: `packages/erk-shared/src/erk_shared/gateway/remote_github/fake.py`**
- Add `prs: dict[int, RemotePRInfo]` constructor parameter
- Implement `get_pr` returning from dict or `RemotePRNotFound`

### 2. Add --repo flag and is_remote routing to launch command

**Modify: `src/erk/cli/commands/launch_cmd.py`**

Add `@repo_option` decorator and `target_repo` parameter. Replace the `NoRepoSentinel` guard with routing:

```python
is_remote = target_repo is not None or isinstance(ctx.repo, NoRepoSentinel)
if is_remote:
    _launch_remote(ctx, workflow_name, target_repo=target_repo, ...)
else:
    _launch_local(ctx, workflow_name, ...)
```

- `_launch_local`: extract current body of `launch()` unchanged
- `_launch_remote`: resolve owner/repo via `resolve_owner_repo()`, get `RemoteGitHub` via `get_remote_github()`, route to per-workflow remote handlers

### 3. Create remote dispatch handlers

Each PR-based workflow gets a remote variant:
- `_dispatch_pr_rebase_remote` — requires `--pr` (no branch inference), calls `remote.get_pr()`, validates OPEN state, calls `_dispatch_workflow_remote()`
- `_dispatch_pr_address_remote` — same pattern
- `_dispatch_pr_rewrite_remote` — same pattern
- `_dispatch_one_shot_remote` — same pattern, uses `remote.get_authenticated_user()` for submitted_by
- `_dispatch_learn_remote` — simplest: just dispatch with plan_number input, no PR lookup
- `plan-implement` — remains blocked in both modes

### 4. Create `_dispatch_workflow_remote` helper

Remote counterpart to `_dispatch_workflow`:
- Calls `remote.dispatch_workflow(owner=, repo=, workflow=, ref=, inputs=)`
- Constructs run URL from owner/repo_name
- **Skips** `maybe_update_plan_dispatch_metadata` (local-only)

### 5. Handle ref resolution in remote mode

- `--ref-current` in remote mode → error ("--ref-current requires a local git repository")
- No `--ref` provided → call `remote.get_default_branch_name(owner=, repo=)` as fallback
- `--ref` provided → use it directly
- Skip `ctx.local_config.dispatch_ref` fallback in remote mode

### 6. Handle auth check in remote mode

- Remote mode: call `remote.check_auth_status()` directly instead of `Ensure.gh_authenticated(ctx)` which uses local `gh` CLI

## Key differences: remote vs local

| Aspect | Local | Remote |
|--------|-------|--------|
| PR lookup | `ctx.github.get_pr(repo.root, number)` | `remote.get_pr(owner=, repo=, number=)` |
| Workflow dispatch | `ctx.github.trigger_workflow(repo_root, ...)` | `remote.dispatch_workflow(owner=, repo=, ...)` |
| Plan metadata | `maybe_update_plan_dispatch_metadata(...)` | Skipped |
| Plan ID | `ctx.plan_backend.resolve_plan_id_for_branch(...)` | Empty string |
| PR inference from branch | Supported (pr-rebase only) | Not supported, --pr required |
| Ref fallback | `ctx.local_config.dispatch_ref` | `remote.get_default_branch_name()` |
| Auth check | `Ensure.gh_authenticated(ctx)` | `remote.check_auth_status()` |

## Files to modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/remote_github/types.py` | **NEW** — RemotePRInfo, RemotePRNotFound |
| `packages/erk-shared/src/erk_shared/gateway/remote_github/abc.py` | Add abstract `get_pr` |
| `packages/erk-shared/src/erk_shared/gateway/remote_github/real.py` | Implement `get_pr` via REST API |
| `packages/erk-shared/src/erk_shared/gateway/remote_github/fake.py` | Add prs dict, implement `get_pr` |
| `src/erk/cli/commands/launch_cmd.py` | Add --repo, is_remote routing, remote handlers |
| `tests/commands/launch/test_launch_remote.py` | **NEW** — Remote mode tests |

## Reuse

- `repo_option`, `resolve_owner_repo()`, `get_remote_github()` from `src/erk/cli/repo_resolution.py`
- `_get_workflow_file()` already exists in launch_cmd.py
- `WORKFLOW_COMMAND_MAP` from `src/erk/cli/constants.py`
- `context_for_test(repo=NoRepoSentinel(), remote_github=...)` from `src/erk/core/context.py`
- Pattern reference: `src/erk/cli/commands/pr/dispatch_cmd.py` (is_remote routing)
- Pattern reference: `tests/commands/pr/test_remote_paths.py` (remote test structure)

## Verification

1. Run existing launch tests: `uv run pytest tests/commands/launch/test_launch_cmd.py` — all pass (no regressions)
2. Run new remote tests: `uv run pytest tests/commands/launch/test_launch_remote.py`
3. Run type checker on modified files
4. Run linter on modified files
5. Manual smoke test: `erk launch pr-rebase --pr 123 --repo dagster-io/erk` (if possible)
