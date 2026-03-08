# Plan: Convert `pr dispatch` to @no_repo_required with --repo flag

**Part of Objective #8832, Node 3.2 (pr-dispatch-remote)**

## Context

The `erk pr dispatch` command dispatches plans for remote AI implementation via GitHub Actions. Currently it requires a local git repo for: syncing trunk, fetching/creating branches, committing impl-context files via git plumbing, pushing, and triggering workflows via `gh` CLI. However, the core dispatch operation is fundamentally remote — it validates a PR, commits context files to an existing branch, and triggers a workflow. All of these can be done via the GitHub REST API using RemoteGitHub, which already has `create_file_commit()`, `dispatch_workflow()`, `get_issue()`, `update_pull_request_body()`, and `add_issue_comment()`.

The one-shot remote dispatch (`src/erk/cli/commands/one_shot_remote_dispatch.py`) already demonstrates this full remote pattern.

## Approach

### 1. Create `_dispatch_planned_pr_plan_remote()` function

**File:** `src/erk/cli/commands/pr/dispatch_cmd.py`

New function alongside `_dispatch_planned_pr_plan()` that uses RemoteGitHub for the entire dispatch:

```python
def _dispatch_planned_pr_plan_remote(
    *,
    remote: RemoteGitHub,
    time: Time,
    owner: str,
    repo: str,
    validated: ValidatedPlannedPR,
    submitted_by: str,
    base_branch: str,
    ref: str | None,
) -> DispatchResult:
```

**Steps:**

1. **Fetch plan content** via `remote.get_issue(owner=, repo=, number=validated.number)` — extract plan body from the PR issue data. Parse plan content from PR body using existing `extract_plan_from_body()` or equivalent.
2. **Commit impl-context files** to branch via `remote.create_file_commit()` — call once per file from `build_impl_context_files()` (pure function, already works). Files: `plan.md`, `ref.json`, `status.json`.
3. **Dispatch workflow** via `remote.dispatch_workflow(owner=, repo=, workflow=DISPATCH_WORKFLOW_NAME, ref=dispatch_ref, inputs=...)`.
4. **Update PR body** with workflow URL via `remote.update_pull_request_body()`.
5. **Post queued event comment** via `remote.add_issue_comment()`.
6. Return `DispatchResult`.

**Skipped in remote mode** (vs local path):
- `ensure_trunk_synced()` — no local state to sync
- `fetch_branch()`, `create_branch()`, `update_local_ref()` — no local refs
- `push_to_remote()` — files committed directly via API
- `is_branch_checked_out()` / index sync — no local worktrees
- `write_dispatch_metadata()` — uses `get_workflow_run_node_id()` (LocalGitHub-only); skip node_id tracking in remote mode
- `load_workflow_config()` — reads local `.erk/config.toml`; use empty config in remote mode

**Reusable pure functions:**
- `build_impl_context_files()` from `erk_shared.impl_context` — builds file map
- `create_submission_queued_block()` / `render_erk_issue_event()` — builds comment body
- `construct_workflow_run_url()` — builds URL
- `_build_workflow_run_url()` / `_build_pr_url()` — existing helpers in dispatch_cmd.py

### 2. Create `_validate_planned_pr_for_dispatch_remote()` function

**File:** `src/erk/cli/commands/pr/dispatch_cmd.py`

Remote variant of `_validate_planned_pr_for_dispatch()` using RemoteGitHub:

```python
def _validate_planned_pr_for_dispatch_remote(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo: str,
    plan_number: int,
) -> ValidatedPlannedPR:
```

Uses `remote.get_issue()` instead of `ctx.github.get_pr()`. Checks labels and state the same way. Gets `head_ref_name` — need to verify if `IssueInfo` includes this or if we need to add it (PR head branch). If `IssueInfo` doesn't have `head_ref_name`, we may need to parse it from the plan metadata body (the `branch_name` field in the erk-header).

### 3. Modify `pr_dispatch` CLI command

**File:** `src/erk/cli/commands/pr/dispatch_cmd.py`

Changes:
- Add `@repo_option` decorator and `target_repo: str | None` parameter
- Import `resolve_owner_repo`, `get_remote_github`, `repo_option` from repo_resolution
- Import `NoRepoSentinel` from `erk_shared.context.types`
- Branch on repo availability after auth check:

```python
if isinstance(ctx.repo, NoRepoSentinel) or target_repo is not None:
    # Remote path
    owner, repo_name = resolve_owner_repo(ctx, target_repo=target_repo)
    remote = get_remote_github(ctx)

    # Require explicit plan numbers (no auto-detect in remote mode)
    if not plan_numbers:
        raise UserFacingCliError("Plan numbers required with --repo flag")

    # Get default branch as base (skip trunk sync)
    base_branch = base or remote.get_default_branch_name(owner=owner, repo=repo_name)

    # Validate and dispatch
    for plan_number in plan_numbers:
        validated = _validate_planned_pr_for_dispatch_remote(remote, owner=owner, repo=repo_name, plan_number=plan_number)
        result = _dispatch_planned_pr_plan_remote(remote=remote, time=ctx.time, owner=owner, repo=repo_name, validated=validated, ...)
else:
    # Existing local path (unchanged)
    ...
```

**Constraints in remote mode:**
- `--ref-current` rejected (can't determine current branch without local repo)
- Auto-detect from context disabled (requires local `.erk/impl-context/`)
- `load_workflow_config()` skipped (no local `.erk/config.toml`)

### 4. Handle `head_ref_name` for validated PRs

`ValidatedPlannedPR.branch_name` is needed for file commits and workflow inputs. Current local path gets it from `PRInfo.head_ref_name` via `ctx.github.get_pr()`.

Check if `IssueInfo` (returned by `RemoteGitHub.get_issue()`) includes `head_ref_name`. If not, parse `branch_name` from the plan metadata block in the PR body (the erk-header YAML contains `branch_name`).

### 5. Extract plan content from PR body

In remote mode, plan content must be extracted from the PR body (fetched via `remote.get_issue()`). The PR body has structure: `metadata_header + plan_content + footer`. Use existing parsing functions to extract the plan content portion.

Check for existing `extract_plan_from_body()` or equivalent in `erk_shared.plan_store.planned_pr_lifecycle`.

### 6. Add tests

**File:** `tests/commands/pr/test_remote_paths.py`

Add tests for remote dispatch:
- `test_dispatch_remote_dispatches_workflow()` — Happy path with `--repo` flag
- `test_dispatch_remote_requires_plan_numbers()` — Error without explicit plan numbers
- `test_dispatch_remote_rejects_ref_current()` — Error with `--ref-current` + `--repo`
- `test_dispatch_remote_validates_pr_labels()` — Rejects PRs without erk-plan label

**File:** `tests/commands/pr/test_dispatch.py` (existing)

Verify no regressions in existing local dispatch tests.

## Files to modify

| File | Action |
|------|--------|
| `src/erk/cli/commands/pr/dispatch_cmd.py` | Add `@repo_option`, `_validate_remote()`, `_dispatch_remote()`, branch on repo |
| `src/erk/cli/commands/pr/repo_resolution.py` | May need to verify `resolve_owner_repo` handles dispatch case |
| `tests/commands/pr/test_remote_paths.py` | Add remote dispatch tests |

## Open questions to resolve during implementation

1. Does `IssueInfo` have `head_ref_name`? If not, parse from plan metadata body.
2. Is there an existing `extract_plan_from_body()` function, or do we need to write one?
3. Should `write_dispatch_metadata()` be attempted in remote mode (skipping node_id), or skipped entirely?

## Verification

1. **Unit tests:** `uv run pytest tests/commands/pr/test_remote_paths.py -v`
2. **Existing tests:** `uv run pytest tests/commands/pr/test_dispatch.py -v`
3. **Type checking:** `uv run ty check src/erk/cli/commands/pr/dispatch_cmd.py`
4. **Lint:** `uv run ruff check src/erk/cli/commands/pr/dispatch_cmd.py`
