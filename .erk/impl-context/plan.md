# Plan: Unify Local/Remote Codepaths in PR Read Commands

## Context

Six PR commands were recently converted to support remote operation (no local git repo) via `is_remote_mode()`. This created a pattern where each command has nearly-identical `_local()` and `_remote()` functions that differ only in how they fetch GitHub data. The duplication is significant (60-85% identical code per command).

The key insight: `resolve_owner_repo()` already handles both cases (local git context or `--repo` flag). We can always use `RemoteGitHub` (REST API via httpx) for data fetching, then conditionally add local enrichments (branch inference, activity sort, etc.) when a repo is available. This eliminates `is_remote_mode()` and the dual codepaths.

## Approach

**Single codepath per command**: resolve `owner/repo` via `resolve_owner_repo()`, fetch data via `get_remote_github()`, then optionally enrich with local-only capabilities gated on `not isinstance(ctx.repo, NoRepoSentinel)`.

## Implementation Order

### 1. `log_cmd.py` — Reference implementation (cleanest case)

**File**: `src/erk/cli/commands/pr/log_cmd.py`

Delete `_pr_log_local()` and `_pr_log_remote()`. Rewrite `pr_log()` as single path:

```python
owner, repo_name = resolve_owner_repo(ctx, target_repo=target_repo)
remote = get_remote_github(ctx)
plan_number = parse_issue_identifier(identifier)

issue = remote.get_issue(owner=owner, repo=repo_name, number=plan_number)
if isinstance(issue, IssueNotFound):
    ...

comment_bodies = remote.get_issue_comments(owner=owner, repo=repo_name, number=plan_number)
events = _extract_events_from_comments(comment_bodies)
# ... display (already shared)
```

Remove imports: `is_remote_mode`, `discover_repo_context`, `ensure_erk_metadata_dir`, `PlanNotFound`.

No local-only features to preserve.

### 2. `view_cmd.py` — Branch inference as optional enrichment

**File**: `src/erk/cli/commands/pr/view_cmd.py`

Delete `_pr_view_local()` and `_pr_view_remote()`. Single path:

1. If `identifier is None` and local repo available: infer from branch (existing logic), set `identifier`
2. If `identifier is None` and no local repo: error (existing behavior)
3. Resolve via `remote.get_issue()` + `github_issue_to_plan()`
4. Optional local enrichment: if local repo, try `ctx.plan_backend.get_all_metadata_fields()` for richer header info

### 3. `check_cmd.py` — Eliminate duplicate validation function

**File**: `src/erk/cli/commands/pr/check_cmd.py`

- Delete `validate_plan_format_remote()` entirely
- Rewrite `validate_plan_format()` signature to accept `RemoteGitHub` + `owner/repo` instead of `GitHubIssues` + `repo_root`:
  ```python
  def validate_plan_format(
      remote: RemoteGitHub, *, owner: str, repo: str, plan_number: int,
  ) -> PlanValidationResult:
  ```
- Delete `_check_plan_format()` and `_check_plan_format_remote()`, merge into single function
- `_check_pr_body()` stays as-is (genuinely local-only, requires current branch + PR context)
- Top-level `pr_check()`: when `identifier is None` and no local repo, error (existing behavior); when `identifier is None` and local repo, call `_check_pr_body()`; otherwise unified validation path

**Caller update**: `tests/commands/pr/test_check_plan.py` — 6 tests call `validate_plan_format(issues, tmp_path, number)`. Update to pass `FakeRemoteGitHub` + `owner/repo` instead.

Also check: `validate_plan_format` is called from `land_cmd.py` or elsewhere? Grep shows only `check_cmd.py` and `test_check_plan.py`.

### 4. `close_cmd.py` — Unified fetch, conditional close mechanism

**File**: `src/erk/cli/commands/pr/close_cmd.py`

- Delete `_close_linked_prs()` and `_close_linked_prs_remote()` — unify into single function using RemoteGitHub
- Delete `_pr_close_local()` and `_pr_close_remote()`
- Single path:
  1. `resolve_owner_repo()` + `get_remote_github()`
  2. Verify plan exists via `remote.get_issue()`
  3. Close linked PRs via single `_close_linked_prs(remote, owner, repo, plan_number)`
  4. Close the plan: if local repo → `ctx.plan_store.close_plan()` (adds audit comment); else → `remote.close_issue()`
  5. Objective update: if local repo and plan has `objective_id` → `run_objective_update_after_close()`. Get `objective_id` from `github_issue_to_plan(issue)` instead of `plan_store.get_plan()`.

### 5. `duplicate_check_cmd.py` — Mostly identical already

**File**: `src/erk/cli/commands/pr/duplicate_check_cmd.py`

- Delete `_duplicate_check_local()` and `_duplicate_check_remote()`
- Single path:
  1. `resolve_owner_repo()` for location
  2. When `--plan` provided: always use `remote.get_issue()` to fetch content
  3. `GitHubRepoLocation.root`: use `ctx.repo.root` if local, else temp dir
  4. Duplicate check logic is identical (already uses `PlanListService` + `PlanDuplicateChecker`)
  5. Trunk commit relevance: gate on `not isinstance(ctx.repo, NoRepoSentinel)`, show "skipped" note otherwise (existing behavior)

### 6. `list_cmd.py` — Most complex

**File**: `src/erk/cli/commands/pr/list_cmd.py`

- Delete `_pr_list_remote()`
- Merge into `_pr_list_impl()` (or rename to just the implementation):
  1. `resolve_owner_repo(ctx, target_repo=target_repo)` for owner/repo
  2. Root: `ctx.repo.root` if local, else temp dir
  3. Auth: use `remote.check_auth_status()` uniformly (instead of `ctx.github.check_auth_status()`)
  4. Activity sort: gate on local repo availability, silently fall back to plan ID sort otherwise
- `pr_list()` calls the single implementation directly, passing `target_repo`
- `dash` command stays local-only (unchanged, no `--repo` support)

### 7. `repo_resolution.py` — Delete `is_remote_mode`

**File**: `src/erk/cli/commands/pr/repo_resolution.py`

- Delete `is_remote_mode()` function
- Keep `resolve_owner_repo()`, `get_remote_github()`, `repo_option`

### 8. Tests

**`tests/commands/pr/test_remote_paths.py`**: Tests currently inject `FakeRemoteGitHub` + `NoRepoSentinel`. These should still work since the unified path uses `get_remote_github()` which returns `ctx.remote_github` when injected.

**`tests/commands/pr/test_check_plan.py`**: Update 6 `validate_plan_format()` calls to pass `FakeRemoteGitHub` + `owner/repo` instead of `FakeGitHubIssues` + `repo_root`.

**Existing local-path tests** (various test_*.py files): These currently use `FakeGitHubIssues`/`FakeLocalGitHub`. After unification, commands use `get_remote_github(ctx)`, so tests need `ctx.remote_github` populated with `FakeRemoteGitHub` configured with matching issue data. This is mechanical: add `FakeRemoteGitHub` construction alongside existing fake setup.

## Verification

1. Run `make fast-ci` after each command conversion to catch regressions
2. Verify each command works in 3 modes:
   - Inside a repo with no `--repo` flag (local enrichments active)
   - Inside a repo with `--repo` flag (explicit remote)
   - Outside a repo with `--repo` flag (pure remote)
3. Run `make all-ci` after all changes complete
