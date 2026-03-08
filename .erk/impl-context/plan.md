# Plan: Convert `pr create` to @no_repo_required with --repo flag

**Part of Objective #8832, Node 3.1 (pr-create-remote)**

## Context

The `erk pr create` command currently requires a local git repository for its entire workflow: detecting trunk branch, creating a branch, committing files via git plumbing, pushing, and creating a draft PR. As part of objective #8832 (Decouple CLI Commands from Git Repo Requirement), this command needs a remote path that works without a local clone, using RemoteGitHub REST API exclusively.

The remote plan creation pattern already exists in `dispatch_one_shot_remote()` (`src/erk/cli/commands/one_shot_remote_dispatch.py`), which creates branches, commits files, and creates PRs entirely via RemoteGitHub. This plan adapts that pattern for `pr create`.

## Approach

### 1. Create `create_plan_draft_pr_remote()` function

**File:** `packages/erk-shared/src/erk_shared/plan_store/create_plan_draft_pr.py`

Add a new function alongside the existing `create_plan_draft_pr()` that uses RemoteGitHub for the entire workflow:

```python
def create_plan_draft_pr_remote(
    *,
    remote: RemoteGitHub,
    time: Time,
    owner: str,
    repo: str,
    plan_content: str,
    branch_name: str,
    title: str | None,
    labels: list[str],
    source_repo: str | None,
    objective_id: int | None,
    created_from_session: str | None,
    created_from_workflow_run_url: str | None,
    learned_from_issue: int | None,
    summary: str,
    extra_files: dict[str, str] | None,
) -> CreatePlanDraftPRResult:
```

**Steps (mirroring `dispatch_one_shot_remote` pattern):**

1. Extract/validate title from plan H1 (reuse `extract_title_from_plan`)
2. Get default branch name via `remote.get_default_branch_name(owner=, repo=)`
3. Get trunk SHA via `remote.get_default_branch_sha(owner=, repo=)`
4. Create branch via `remote.create_ref(owner=, repo=, ref=f"refs/heads/{branch_name}", sha=trunk_sha)`
5. Build ref.json content (same logic as local path)
6. Commit each file via `remote.create_file_commit()`:
   - `.erk/impl-context/plan.md` with plan_content
   - `.erk/impl-context/ref.json` with ref data
   - Any `extra_files`
7. Get authenticated user via `remote.get_authenticated_user()`
8. Build metadata body via `format_plan_header_body()` (reuse existing pure function)
9. Build PR body via `build_plan_stage_body()` (reuse existing pure function)
10. Create draft PR via `remote.create_pull_request(owner=, repo=, head=branch_name, base=trunk, ...)`
11. Add footer via `remote.update_pull_request_body()`
12. Add labels via `remote.add_labels()`
13. Return `CreatePlanDraftPRResult`

**Key reusable functions** (all pure, no gateway dependency):
- `extract_title_from_plan` from `erk_shared.plan_utils`
- `format_plan_header_body` from `erk_shared.gateway.github.metadata.plan_header`
- `build_plan_stage_body` from `erk_shared.plan_store.planned_pr_lifecycle`
- `build_pr_body_footer` from `erk_shared.gateway.github.pr_footer`
- `get_title_tag_from_labels` from `erk_shared.plan_utils`

**New imports needed:** `RemoteGitHub` from `erk_shared.gateway.remote_github.abc`

### 2. Modify `create_cmd.py` CLI command

**File:** `src/erk/cli/commands/pr/create_cmd.py`

Changes:
- Add `@repo_option` decorator and `target_repo: str | None` parameter
- Import `resolve_owner_repo`, `get_remote_github`, `repo_option` from `erk.cli.commands.pr.repo_resolution`
- Import `NoRepoSentinel` from `erk_shared.context.types`
- Import `create_plan_draft_pr_remote` from the shared module
- Branch on repo availability after input reading:

```python
# After reading content and building labels...

if isinstance(ctx.repo, NoRepoSentinel):
    # Remote path: use RemoteGitHub for everything
    owner, repo_name = resolve_owner_repo(ctx, target_repo=target_repo)
    remote = get_remote_github(ctx)

    slug = generate_branch_slug(ctx.prompt_executor, title or extract_title_from_plan(content))
    branch_name = generate_planned_pr_branch_name(slug, ctx.time.now(), objective_id=None)

    result = create_plan_draft_pr_remote(
        remote=remote, time=ctx.time,
        owner=owner, repo=repo_name,
        plan_content=content, branch_name=branch_name,
        title=title, labels=labels, source_repo=None,
        objective_id=None, ...
    )
else:
    # Local path: existing workflow
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    # ... existing code ...
    result = create_plan_draft_pr(git=ctx.git, github=ctx.github, ...)
```

**Local-only features gated on repo availability:**
- `discover_repo_context()` / `ensure_erk_metadata_dir()` — local only
- `source_repo` from `ctx.local_config.plans_repo` — local only (set to None in remote)

### 3. Add tests

**File:** `tests/commands/pr/test_remote_paths.py`

Add tests for the remote `pr create` path:

- `test_create_remote_creates_plan_pr()` — Happy path: `--file` + `--repo` creates plan via RemoteGitHub
  - Verify FakeRemoteGitHub received: create_ref, create_file_commit (2+ calls), create_pull_request, add_labels
  - Verify exit code 0 and output contains plan number
- `test_create_remote_requires_repo_flag_when_no_local_repo()` — NoRepoSentinel without --repo flag errors
- `test_create_remote_with_stdin()` — Piped content works in remote mode

**Test setup pattern** (from existing tests):
```python
fake_remote = _make_fake_remote()  # existing helper
ctx = _build_remote_context(fake_remote)
runner = CliRunner()
# Use mix_stderr=False and input= for stdin tests
```

**Note:** Need to provide `FakePromptExecutor` in context for slug generation.

### 4. Add unit test for `create_plan_draft_pr_remote()`

**File:** `tests/shared/plan_store/test_create_plan_draft_pr_remote.py` (new file, or add to existing test file if one exists)

Test the business logic function directly:
- Verify correct sequence of RemoteGitHub calls
- Verify ref.json content
- Verify PR body structure (metadata header + plan content + footer)
- Verify label application

## Files to modify

| File | Action |
|------|--------|
| `packages/erk-shared/src/erk_shared/plan_store/create_plan_draft_pr.py` | Add `create_plan_draft_pr_remote()` |
| `src/erk/cli/commands/pr/create_cmd.py` | Add `@repo_option`, branch on repo availability |
| `tests/commands/pr/test_remote_paths.py` | Add remote pr create tests |
| `tests/shared/plan_store/` | Add unit test for remote function (check if dir exists first) |

## Verification

1. **Unit tests:** Run `uv run pytest tests/commands/pr/test_remote_paths.py` and the new unit test file
2. **Existing tests:** Run `uv run pytest tests/commands/pr/` to verify no regressions
3. **Type checking:** Run `uv run ty check src/erk/cli/commands/pr/create_cmd.py`
4. **Lint:** Run `uv run ruff check src/erk/cli/commands/pr/create_cmd.py packages/erk-shared/src/erk_shared/plan_store/create_plan_draft_pr.py`
