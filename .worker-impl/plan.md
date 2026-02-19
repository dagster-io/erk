# Migrate Issue Plan to Draft PR Plan

## Context

Plans can be stored in two backends: GitHub Issues (the default `"github"` backend) and Draft PRs (`"draft_pr"` backend). As teams adopt the draft PR backend, they may need to migrate existing issue-based plans. This command automates that migration.

## What the Migration Does

1. Reads the issue plan (content + metadata) via `GitHubPlanStore`
2. Creates a `plan-{slug}-{timestamp}` branch from trunk, commits `.erk/plan/PLAN.md`, and pushes it
3. Creates a draft PR via `DraftPRPlanBackend.create_plan()`, preserving title, content, labels (including `erk-learn`), objective link, and `created_from_session`
4. Comments on the original issue with a migration notice and closes it
5. Outputs JSON: `{success, original_issue_number, pr_number, pr_url, branch_name}`

## Files

### Create

**`src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py`**

CLI command: `erk exec plan-migrate-to-draft-pr <issue_number> [--dry-run] [--format json|display]`

Pattern mirrors `_save_as_draft_pr` in `plan_save.py`:
- `require_repo_root`, `require_cwd`, `require_git`, `require_github`, `require_issues`, `require_time` from ctx
- Build `GitHubPlanStore(issues_gateway)` and call `.get_plan(repo_root, str(issue_number))`
- Return error JSON if `PlanNotFound`
- Check issue has `erk-plan` label; return error if not an erk-plan issue
- `generate_draft_pr_branch_name(plan.title, now, objective_id=plan.objective_id)` from `erk_shared.naming`
- `trunk = git.branch.detect_trunk_branch(cwd)` — use trunk (not current branch) as start point
- In `--dry-run` mode: output what would happen, skip all mutations
- Checkout dance: save current branch → create branch from trunk → checkout plan branch → write/stage/commit PLAN.md → push → restore current branch (in finally block)
- `DraftPRPlanBackend(github_gateway).create_plan(...)` with `metadata={"branch_name": branch_name, "trunk_branch": trunk, ...}`, preserving `objective_issue`, `created_from_session` from `plan.header_fields`
- Comment on original issue: `"Migrated to draft PR #<pr_number>: <pr_url>\n\nThis issue has been superseded by the draft PR above."`
- Close original issue via `issues_gateway.close_issue(repo_root, issue_number)`
- JSON output: `{"success": True, "original_issue_number": N, "pr_number": N, "pr_url": "...", "branch_name": "..."}`

Key imports:
- `GitHubPlanStore` from `erk_shared.plan_store.github`
- `DraftPRPlanBackend` from `erk_shared.plan_store.draft_pr`
- `PlanNotFound` from `erk_shared.plan_store.types`
- `generate_draft_pr_branch_name` from `erk_shared.naming`
- `require_cwd, require_repo_root, require_git, require_github, require_issues, require_time` from `erk_shared.context.helpers`

**`.claude/commands/erk/migrate-plan-to-draft-pr.md`**

Slash command that:
1. Parses issue number from `$ARGUMENTS` (or asks user if not provided)
2. Runs `erk exec plan-migrate-to-draft-pr <issue_number> --format json`
3. Displays the result: old issue closed, new draft PR URL, branch name
4. Suggests next steps: `erk prepare <pr_number>` or `gh pr view <pr_number> --web`

**`tests/unit/cli/commands/exec/scripts/test_plan_migrate_to_draft_pr.py`**

Pattern: `CliRunner` + `context_for_test(github=FakeGitHub(), git=FakeGit(...), issues=FakeGitHubIssues(...), ...)`.

Tests:
- `test_migrate_success_json` — happy path, issue exists with erk-plan label, returns JSON with pr_number
- `test_migrate_success_display` — display format shows human-readable output
- `test_migrate_dry_run` — `--dry-run` outputs intent but does not create PR or close issue
- `test_migrate_issue_not_found` — returns error JSON when issue doesn't exist
- `test_migrate_not_an_erk_plan` — returns error when issue lacks `erk-plan` label
- `test_migrate_preserves_objective_id` — objective_id flows through to draft PR metadata
- `test_migrate_preserves_erk_learn_label` — `erk-learn` label transferred to draft PR

### Modify

**`src/erk/cli/commands/exec/group.py`**

Add import and `exec_group.add_command(plan_migrate_to_draft_pr, name="plan-migrate-to-draft-pr")` in alphabetical order alongside other `plan_*` registrations.

## Key Reused Functions

| Function | File |
|---|---|
| `generate_draft_pr_branch_name` | `packages/erk-shared/src/erk_shared/naming.py` |
| `GitHubPlanStore` | `packages/erk-shared/src/erk_shared/plan_store/github.py` |
| `DraftPRPlanBackend` | `packages/erk-shared/src/erk_shared/plan_store/draft_pr.py` |
| `require_*` helpers | `packages/erk-shared/src/erk_shared/context/helpers.py` |
| `context_for_test` | `packages/erk-shared/src/erk_shared/context/testing.py` |
| Branch checkout dance | `src/erk/cli/commands/exec/scripts/plan_save.py:138-156` |

## Verification

```bash
# Test the exec script directly
erk exec plan-migrate-to-draft-pr <issue_number> --dry-run
erk exec plan-migrate-to-draft-pr <issue_number>

# Run unit tests
uv run pytest tests/unit/cli/commands/exec/scripts/test_plan_migrate_to_draft_pr.py

# Use the slash command in Claude Code
/erk:migrate-plan-to-draft-pr <issue_number>
```