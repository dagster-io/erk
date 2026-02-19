# Plan: Migrate Exec Scripts to PlanBackend (Objective #7419, Node 2.3)

## Context

Objective #7419 is migrating the plan system of record from GitHub issues to draft PRs. Phases 1 and 2.1-2.2 are complete, establishing the `PlanBackend` ABC and `DraftPRPlanBackend`. Node 2.3 migrates exec scripts that still use `GitHubIssues` directly or bypass the PlanBackend abstraction, so they work with both issue-based and draft-PR-based plans.

## Scope

Three exec scripts need migration. Two categories:
- **Direct GitHubIssues usage** (bypasses PlanBackend entirely): `close_issue_with_comment.py`, `plan_update_issue.py` (title update only)
- **Direct GitHubPlanStore instantiation** (bypasses context injection): `create_worker_impl_from_issue.py`

Scripts already using PlanBackend (`mark_impl_started.py`, `mark_impl_ended.py`, `handle_no_changes.py`, `setup_impl_from_issue.py`) are validated as compatible.

`post_workflow_started_comment.py` is deferred to node 2.4 (CI workflows) since its only caller is `plan-implement.yml`.

## Phase 1: Add `update_plan_title()` to PlanBackend ABC

**Why:** `plan_update_issue.py` calls `github_issues.update_issue_title()` directly. PlanBackend has no title-update method, so we need to add one.

### Files to modify:

1. **`packages/erk-shared/src/erk_shared/plan_store/backend.py`** — Add abstract method:
   ```python
   @abstractmethod
   def update_plan_title(self, repo_root: Path, plan_id: str, title: str) -> None:
   ```

2. **`packages/erk-shared/src/erk_shared/plan_store/github.py`** — Implement:
   ```python
   def update_plan_title(self, repo_root: Path, plan_id: str, title: str) -> None:
       number = self._parse_identifier(plan_id)
       self._github_issues.update_issue_title(repo_root, number, title)
   ```

3. **`packages/erk-shared/src/erk_shared/plan_store/draft_pr.py`** — Implement using GitHub gateway's PR title update. Check for existing `update_pr_title` or `update_pr_title_and_body` on the `GitHub` gateway. If only `update_pr_title_and_body` exists, either:
   - Add `update_pr_title()` to the GitHub gateway ABC (preferred)
   - Or use `update_pr_title_and_body()` preserving the existing body

4. **Tests** for the new method on both backends.

## Phase 2: Migrate `close_issue_with_comment.py`

**Current:** Uses `require_github_issues(ctx)` → `github.add_comment()` + `github.close_issue()`
**Target:** Uses `require_plan_backend(ctx)` → `backend.add_comment()` + `backend.close_plan()`

### File: `src/erk/cli/commands/exec/scripts/close_issue_with_comment.py`

Changes:
- Replace `require_github_issues` import with `require_plan_backend`
- Use `backend.add_comment(repo_root, str(issue_number), comment)`
- Use `backend.close_plan(repo_root, str(issue_number))`
- Note: `close_plan()` adds its own audit comment ("Plan completed via erk plan close"). The user's custom comment + system audit comment is acceptable (two comments).
- Keep `ISSUE_NUMBER` CLI argument name for backward compatibility with existing callers (renaming deferred)

### File: `tests/unit/cli/commands/exec/scripts/test_close_issue_with_comment.py`

Update tests to verify PlanBackend calls instead of direct GitHubIssues calls. Tests already use `ErkContext.for_test(github_issues=fake)` which auto-wires PlanBackend.

## Phase 3: Complete `plan_update_issue.py` Migration

**Current:** Uses PlanBackend for content update but `require_issues(ctx)` + `github.update_issue_title()` for title.
**Target:** Uses PlanBackend for both content and title.

### File: `src/erk/cli/commands/exec/scripts/plan_update_issue.py`

Changes:
- Remove `require_issues` import (line 33)
- Remove `github = require_issues(ctx)` (line 87)
- Replace `github.update_issue_title(repo_root, issue_number, full_title)` (line 125) with `backend.update_plan_title(repo_root, plan_id, full_title)`

### File: `tests/unit/cli/commands/exec/scripts/test_plan_update_issue.py`

Update tests to verify `update_plan_title` via PlanBackend instead of direct `update_issue_title`.

## Phase 4: Migrate `create_worker_impl_from_issue.py`

**Current:** Directly instantiates `RealGitHubIssues` and `GitHubPlanStore` (violates exec script standards in AGENTS.md). No `@click.pass_context`.
**Target:** Uses `@click.pass_context` + `require_plan_backend(ctx)`.

### File: `src/erk/cli/commands/exec/scripts/create_worker_impl_from_issue.py`

Changes:
- Remove direct imports of `RealGitHubIssues`, `RealTime`, `GitHubPlanStore`
- Add `@click.pass_context` decorator
- Add `ctx: click.Context` as first parameter
- Use `require_plan_backend(ctx)` and `require_repo_root(ctx)` (with `require_cwd` fallback for `--repo-root`)
- Replace `plan_store.get_plan()` with `backend.get_plan()`

### File: `tests/unit/cli/commands/exec/scripts/test_create_worker_impl_from_issue.py`

Create or update tests using standard `ErkContext.for_test()` pattern with `CliRunner`.

## Phase 5: Audit Already-Migrated Scripts

Validate these scripts work correctly with DraftPRPlanBackend (read-only audit, fix only if broken):

- `mark_impl_started.py` — Uses `backend.update_metadata()`. The `int(plan_ref.plan_id)` on line 163 may fail for non-numeric plan IDs. Check if draft PR plan IDs are always numeric (they should be — PR numbers).
- `mark_impl_ended.py` — Same pattern as above.
- `handle_no_changes.py` — Uses `backend.add_comment()`. Already compatible.
- `setup_impl_from_issue.py` — Uses `backend.get_plan()`. Already compatible.

## Verification

1. Run existing tests for modified scripts:
   ```
   pytest tests/unit/cli/commands/exec/scripts/test_close_issue_with_comment.py
   pytest tests/unit/cli/commands/exec/scripts/test_plan_update_issue.py
   ```

2. Run type checker:
   ```
   ty check packages/erk-shared/src/erk_shared/plan_store/
   ty check src/erk/cli/commands/exec/scripts/
   ```

3. Run full test suite:
   ```
   make fast-ci
   ```