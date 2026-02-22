# Plan: Prefer `erk br co <name>` over `--for-plan` in Draft PR Copy

## Context

The previous PR ("Unify plan checkout into `erk br co`") introduced `--for-plan` guidance throughout the codebase. For the **draft PR backend**, the branch already exists at plan-save time, so `erk br co <branch-name>` is simpler, shorter, and more natural than `erk br co --for-plan <num>`. The `--for-plan` flag remains necessary for the **issue backend** where the branch doesn't exist yet.

## Changes

### 1. `DraftPRNextSteps` properties — use branch name instead of `--for-plan`

**File:** `packages/erk-shared/src/erk_shared/output/next_steps.py`

Change these properties to use `self.branch_name`:
- `prepare` → `erk br co {self.branch_name}` (was `--for-plan {self.pr_number}`)
- `prepare_and_implement` → `source "$(erk br co {self.branch_name} --script)" && erk implement --dangerous`
- `prepare_new_slot` → `erk br co --new-slot {self.branch_name}`
- `prepare_new_slot_and_implement` → similar

Note: `DraftPRNextSteps` already has `branch_name: str` field (line 48).

### 2. TUI prepare commands — use branch name when available

For plans with a known branch name (`pr_head_branch` or `worktree_branch`), show `erk br co <name>`. Fall back to `--for-plan <plan_id>` only when no branch name is available.

Add a helper to resolve branch name from `PlanRowData`:
```python
def _resolve_branch_name(row: PlanRowData) -> str | None:
    return row.pr_head_branch or row.worktree_branch
```

**Files to update:**
- `src/erk/tui/app.py` (lines 870-881): `copy_prepare` and `copy_prepare_activate` commands
- `src/erk/tui/commands/registry.py` (lines 102-111): `_display_copy_prepare` and `_display_copy_prepare_activate`
- `src/erk/tui/screens/plan_detail_screen.py` (lines 341, 347, 635, 641, 841): all prepare command locations

### 3. CLI error message in `plan/checkout_cmd.py`

**File:** `src/erk/cli/commands/plan/checkout_cmd.py` (line 135)

Keep `--for-plan` here — this error fires when no branch exists yet, so `--for-plan` is the correct guidance.

### 4. CLI `plan create` output

**File:** `src/erk/cli/commands/plan/create_cmd.py` (line 120)

Keep `--for-plan` — `plan create` is issue-backend and doesn't know branch name yet.

### 5. `implement.py` error message

**File:** `src/erk/cli/commands/implement.py` (line 402)

Keep `--for-plan` — this is a fallback suggestion when auto-detect fails.

### 6. Skill/command specs

**File:** `.claude/commands/erk/plan-save.md`
- Lines 147-168: Update slot options blocks to show `erk br co <branch>` for draft PR sections
- Lines 185-186: Already uses old `erk br create --for-plan` — update to `erk br co <branch>`

**File:** `.claude/commands/erk/migrate-plan-to-draft-pr.md` (line 66)
- Update to use branch name form

### 7. `plan_create_review_pr.py` — issue body

**File:** `src/erk/cli/commands/exec/scripts/plan_create_review_pr.py` (lines 81, 86)

Keep `--for-plan` — review PRs reference plan issues (issue backend).

### 8. `format_next_steps_markdown` — issue body

**File:** `packages/erk-shared/src/erk_shared/output/next_steps.py` (line 122)

Keep as-is — this is issue-backend only.

### 9. Documentation updates

- `docs/learned/planning/next-steps-output.md` — update draft PR examples
- `docs/learned/planning/branch-name-inference.md` — minor rewording
- `docs/learned/planning/plan-execution-patterns.md` — update step 1 if draft PR
- `docs/tutorials/first-plan.md` — update draft PR examples

### 10. Test updates

Update expected strings in:
- `packages/erk-shared/tests/unit/output/test_next_steps.py` — DraftPRNextSteps assertions
- `tests/unit/shared/test_next_steps.py` — DraftPRNextSteps assertions
- `tests/tui/test_app.py` — `copy_prepare` clipboard assertions
- `tests/tui/commands/test_registry.py` — display name assertions
- `tests/tui/commands/test_execute_command.py` — execute command assertions
- `packages/erk-shared/tests/unit/github/test_plan_issues.py` — issue body assertions for draft PR

## Not Changed (Issue Backend)

These stay as `--for-plan` because the branch doesn't exist yet:
- `IssueNextSteps` properties
- `format_next_steps_plain` / `format_next_steps_markdown`
- `plan/create_cmd.py`
- `plan/checkout_cmd.py` error message
- `plan_create_review_pr.py`
- `implement.py` error message

## Verification

1. Run unit tests: `pytest tests/unit/shared/test_next_steps.py tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py packages/erk-shared/tests/unit/output/test_next_steps.py -x`
2. Run TUI tests: `pytest tests/tui/ -x`
3. Run shared tests: `pytest packages/erk-shared/tests/unit/github/test_plan_issues.py -x`
4. `ty` and `ruff` checks
