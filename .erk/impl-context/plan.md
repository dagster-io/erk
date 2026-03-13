# Remove Dead PR-to-Issue Linkage Code

## Context

Plans migrated from GitHub issues to draft PRs (`github-draft-pr` provider). The old PR-to-issue linkage infrastructure — which queried GitHub's timeline API for `CrossReferencedEvent` to find which PRs referenced a plan issue — is now dead code. These queries always return empty results because draft plan PRs don't create cross-reference relationships in GitHub's data model. The `will_close_target` field on `PullRequestInfo` is similarly vestigial since "Closes #N" keywords were removed from PR bodies in Feb 2026.

**Scope:** Remove linkage query infrastructure and simplify callers. Leave objective-to-plan linkage untouched. Keep `erk pr close` but remove linked-PR discovery.

---

## Step 1: Delete Gateway Methods

### `get_prs_referencing_issue()` — delete from 3 gateways + fakes
- `packages/erk-shared/src/erk_shared/gateway/github/issues/abc.py` — remove abstract method (lines 268-288)
- `packages/erk-shared/src/erk_shared/gateway/github/issues/real.py` — remove implementation
- `packages/erk-shared/src/erk_shared/gateway/github/issues/dry_run.py` — remove implementation
- `packages/erk-shared/src/erk_shared/gateway/remote_github/abc.py` — remove abstract method
- `packages/erk-shared/src/erk_shared/gateway/remote_github/real.py` — remove implementation (line 301+)
- `tests/fakes/gateway/github_issues.py` — remove fake implementation
- `tests/fakes/gateway/remote_github.py` — remove fake implementation

### `get_prs_linked_to_issues()` — delete from GitHub gateway + fakes
- `packages/erk-shared/src/erk_shared/gateway/github/abc.py` — remove abstract method
- `packages/erk-shared/src/erk_shared/gateway/github/real.py` — remove implementation (lines 755-942) including helpers `_build_issue_pr_linkage_query()`, `_parse_issue_pr_linkages()`
- `packages/erk-shared/src/erk_shared/gateway/github/dry_run.py` — remove implementation
- `tests/fakes/gateway/github.py` — remove fake implementation

### `_close_linked_prs_http()` — delete from pr_service
- `packages/erk-shared/src/erk_shared/gateway/pr_service/real.py` — remove method (lines 95-127)

---

## Step 2: Delete Types

### `PRReference` dataclass — delete entirely
- `packages/erk-shared/src/erk_shared/gateway/github/issues/types.py` — delete class (lines 80-95)
- Remove from imports in `issues/abc.py`, `remote_github/abc.py`, and anywhere else it's imported

### `PullRequestInfo.will_close_target` field — remove
- `packages/erk-shared/src/erk_shared/gateway/github/types.py` — remove field (line 225) and its comment (line 224)

### GraphQL query constants — delete
- `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py` — remove `ISSUE_PR_LINKAGE_FRAGMENT` and `GET_ISSUES_WITH_PR_LINKAGES_QUERY`

---

## Step 3: Delete Orphaned Files

### `get_issue_timeline_prs.py` exec script — delete entirely
- `src/erk/cli/commands/exec/scripts/get_issue_timeline_prs.py` — delete file
- `tests/unit/cli/commands/exec/scripts/test_get_issue_timeline_prs.py` — delete file
- Unregister from exec command group (check `src/erk/cli/commands/exec/` for registration)

### `select_display_pr` utility — delete entirely (all callers being removed)
- `src/erk/core/pr_utils.py` — delete file
- `tests/unit/core/test_pr_utils.py` — delete file

---

## Step 4: Simplify Callers

### `erk pr close` (`src/erk/cli/commands/pr/close_cmd.py`)
- Remove lines 38-46 (the `get_prs_referencing_issue()` call and linked-PR closure loop)
- Remove `closed_prs` variable and lines 69-71 (output about closed linked PRs)
- Remove unused imports (`PRReference` if imported)
- Keep: plan existence check, plan closure, objective update

### `erk pr checkout` (`src/erk/cli/commands/pr/checkout_cmd.py`)
- Remove `_checkout_plan()` function (lines 343-392) — always fails for draft PRs
- Remove `_checkout_plan_pr()` function (lines 395-459) — unreachable
- Remove `_display_multiple_prs()` function (lines 462-481) — unreachable
- Remove `_PlanRef` class (lines 45-49) — no longer needed
- Simplify the main command: when a P-prefixed identifier is provided, error with a helpful message like "Plan checkout is not supported. Use `erk pr checkout <pr-number>` with the implementation PR number."
- Remove unused imports

### `run/list_cmd.py` (`src/erk/cli/commands/run/list_cmd.py`)
- Remove the plan linkage block (lines 89-108): `get_prs_linked_to_issues()` call, `select_display_pr()` usage, `plan_to_run_ids` building
- Remove `plan_numbers` list and `extract_plan_number` calls (lines 77-79, 91-97)
- Remove imports: `select_display_pr`, `extract_plan_number`
- Keep: direct PR number extraction from display_title

### `tui/data/real_provider.py`
- In runs tab method: remove `_fetch_plan_linkages()` closure and its ThreadPoolExecutor usage. Just fetch direct PRs.
- In PR table method: remove `pr_linkages` usage and `will_close_target` emoji (line 616-617)
- Remove imports: `select_display_pr`

### `ci_generate_summaries.py`
- Delete `_find_plan_issue_for_pr()` function (lines 122-157) — always returns None
- In `_post_or_update_comment()`: remove the `plan_issue` lookup and the entire block conditioned on `plan_issue is not None` (lines 180-215). Simplify to just post/update the comment on the PR directly.

### `pr/list/cli.py` (`src/erk/cli/commands/pr/list/cli.py`)
- Remove `will_close_target` display (lines 56-57, the 🔗 emoji)

---

## Step 5: Update Tests

### Delete test files
- `tests/unit/cli/commands/exec/scripts/test_get_issue_timeline_prs.py`
- `tests/unit/core/test_pr_utils.py`
- `tests/integration/real_github_issues/test_get_prs_referencing.py`

### Update test files
- `tests/commands/pr/test_close.py` — remove assertions about linked PRs being closed
- `tests/commands/pr/test_checkout_plan.py` — update for new plan checkout behavior (error message)
- `tests/commands/pr/test_remote_paths.py` — remove PRReference usage
- `tests/fakes/gateway/github_issues.py` — remove `get_prs_referencing_issue` fake method
- `tests/fakes/gateway/github.py` — remove `get_prs_linked_to_issues` fake method
- `tests/fakes/gateway/remote_github.py` — remove `get_prs_referencing_issue` fake method
- `tests/unit/fakes/test_fake_github_issues.py` — remove linkage tests
- `tests/unit/gateways/remote_github/test_real_remote_github.py` — remove linkage tests
- `tests/unit/gateways/github/test_real.py` — remove linkage tests
- `tests/core/operations/test_github.py` — remove `will_close_target` assertions
- `tests/tui/test_plan_table.py` — remove `will_close_target` assertions
- `tests/test_utils/builders.py` — remove `will_close_target` from builder helpers

---

## Step 6: Delete Documentation

- `docs/learned/erk/issue-pr-linkage-storage.md` — delete
- `docs/learned/architecture/github-pr-linkage-api.md` — delete
- `docs/learned/architecture/issue-reference-flow.md` — check if exists, delete if so
- `docs/learned/integrations/issue-pr-closing-integration.md` — check if exists, delete if so
- `docs/learned/planning/pr-discovery.md` — update to remove linkage references
- `docs/learned/architecture/remote-github-gateway.md` — update to remove `get_prs_referencing_issue`
- `docs/learned/cli/ambiguity-resolution.md` — update if referencing linkage
- `docs/learned/cli/pr-submission.md` — update stale "Closes #N" references
- Update `docs/learned/index.md` if any deleted docs are referenced

---

## Verification

1. Run `make fast-ci` — unit tests + lint + type checking
2. Run `make all-ci` — integration tests
3. Grep for residual references: `get_prs_referencing_issue`, `get_prs_linked_to_issues`, `will_close_target`, `PRReference`, `select_display_pr`, `_find_plan_issue_for_pr`
4. Verify `erk pr close <number>` still works (closes the PR, no linked-PR search)
5. Verify `erk pr checkout P123` gives a helpful error message
