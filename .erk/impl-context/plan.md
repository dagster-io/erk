# Plan: Convert `objective plan --one-shot` to `@no_repo_required` with `--repo` flag

Part of Objective #8832, Node 3.4

## Context

This is the final node of the "Decouple CLI Commands from Git Repo Requirement" objective. The `erk objective plan` command currently requires a local git repo for all modes (interactive, `--one-shot`, `--all-unblocked`). The one-shot and all-unblocked modes already dispatch via `RemoteGitHub` (`dispatch_one_shot_remote()`), so the only blocker is owner/repo resolution and ref resolution still depending on local git context.

The pattern is well-established from 11 completed nodes (PR #9019 for `launch` being the most recent reference).

## Files to Modify

1. **`src/erk/cli/commands/objective/plan_cmd.py`** - Main conversion target
2. **`tests/commands/objective/test_plan_remote_paths.py`** - New test file for remote paths

## Implementation

### Phase 1: Add `--repo` flag to `plan_objective` command

- Add `@repo_option` decorator (from `erk.cli.repo_resolution`) to `plan_objective`
- Add `target_repo: str | None` parameter
- Validate: `--repo` is incompatible with interactive mode (no `--one-shot` or `--all-unblocked`)
  - Error: `"--repo requires --one-shot or --all-unblocked"`
- Pass `target_repo` through to `_handle_one_shot()` and `_handle_all_unblocked()`
- Switch import from `_get_remote_github` (one_shot.py) to `get_remote_github` (repo_resolution.py)

### Phase 2: Refactor `_resolve_next()` for remote support

Add `target_repo: str | None` parameter. When `target_repo is not None` or repo is NoRepoSentinel:
- Require `issue_ref` (can't infer from branch without local repo)
- Use `resolve_owner_repo(ctx, target_repo=target_repo)` instead of `ctx.repo.github`
- Use `get_remote_github(ctx)` for `validate_objective()` (already does)

### Phase 3: Refactor `_resolve_all_unblocked()` for remote support

Same pattern as `_resolve_next()` above.

### Phase 4: Refactor `_handle_one_shot()` for remote support

Add `target_repo: str | None` parameter. Changes:
- Replace `ctx.repo.github.owner/repo` (line 798-803) with `resolve_owner_repo(ctx, target_repo=target_repo)`
- Gate `--ref-current` on having a local repo: `if ref_current and not has_local_repo: raise UsageError`
- Ref resolution: use `resolve_dispatch_ref()` when local repo available, else use `dispatch_ref` directly
- Fallback: if `ref is None`, call `remote.get_default_branch_name(owner, repo_name)` (matches launch pattern)

### Phase 5: Refactor `_handle_all_unblocked()` for remote support

Same ref resolution pattern as `_handle_one_shot()`. Replace inline `ctx.repo.github` (line 270-275) with `resolve_owner_repo()`.

### Phase 6: Tests

New file `tests/commands/objective/test_plan_remote_paths.py` following the pattern from `tests/commands/launch/test_launch_remote_paths.py`:

Tests using `context_for_test(repo=NoRepoSentinel(), remote_github=fake_remote)`:

1. `test_one_shot_remote_dispatches_workflow` - Happy path: `--repo owner/repo --one-shot 42`
2. `test_one_shot_remote_with_node` - `--repo --one-shot --node 2.1`
3. `test_one_shot_remote_no_pending_nodes` - All-done objective returns cleanly
4. `test_one_shot_remote_default_ref` - Uses default branch when no `--ref`
5. `test_one_shot_remote_explicit_ref` - `--ref custom-ref` threaded through
6. `test_all_unblocked_remote_dispatches_all` - `--repo --all-unblocked`
7. `test_repo_without_one_shot_fails` - `--repo` without `--one-shot` errors
8. `test_ref_current_without_local_repo_fails` - `--ref-current --repo` errors
9. `test_next_without_issue_ref_remote_fails` - `--next` without ISSUE_REF in remote mode errors

## Key Patterns to Reuse

- `resolve_owner_repo(ctx, target_repo=target_repo)` from `src/erk/cli/repo_resolution.py:18`
- `get_remote_github(ctx)` from `src/erk/cli/repo_resolution.py:52`
- `repo_option` from `src/erk/cli/repo_resolution.py:78`
- Ref resolution pattern from `launch_cmd.py:429-442` (gate ref-current, fallback to default branch)
- Remote test context: `context_for_test(repo=NoRepoSentinel(), remote_github=fake_remote)`

## Verification

1. Run existing objective plan tests: `pytest tests/commands/objective/test_plan_one_shot.py tests/unit/cli/commands/objective/test_plan_cmd.py`
2. Run new remote path tests: `pytest tests/commands/objective/test_plan_remote_paths.py`
3. Run type checker on modified files
4. Run linter
