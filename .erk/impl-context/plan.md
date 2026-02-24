# Plan: Objective #7911 Nodes 1.3 + 1.4 — Delete Issue-Based Plan Backend (Phase 1 Completion)

Part of Objective #7911, Nodes 1.3+1.4

## Context

PRs #7971 (Node 1.1) and #7979 (Node 1.2) removed `get_plan_backend()`, `PlanBackendType`, and dead branches from CLI/exec/context layers. The plan backend is now always `PlannedPRBackend` (`get_provider_name()` always returns `"github-draft-pr"`), and `plan_backend` parameters always carry `"planned_pr"`.

This plan completes Phase 1 by removing the remaining dead code in two areas:
- **Node 1.3**: TUI `plan_backend` parameter and `_is_github_backend()` dead code
- **Node 1.4**: `get_provider_name() == "github-draft-pr"` conditionals across 10 production files

Both nodes are mechanical dead-code removal following the pattern established in PR #7979.

## Implementation

### Node 1.3: TUI plan_backend Removal (5 prod files, 4 test files, 1 doc)

**1. `src/erk/tui/commands/types.py`**
- Remove `plan_backend: Literal["planned_pr"]` field from `CommandContext` dataclass
- Remove `Literal` import if unused

**2. `src/erk/tui/commands/registry.py`**
- Delete `_is_github_backend()` function (lines 31-33)
- Delete entire `copy_prepare` command registration + its `_display_copy_prepare` helper — always hidden, dead code
- Delete entire `copy_prepare_activate` command registration + its `_display_copy_prepare_activate` helper — always hidden, dead code
- Simplify `copy_implement_local` predicate: remove `not _is_github_backend(ctx) and`

**3. `src/erk/tui/app.py`**
- Remove `plan_backend` parameter from `__init__()`, remove `self._plan_backend` field
- Line 167: collapse `if mode == ViewMode.PLANS and self._plan_backend == "planned_pr":` to `if mode == ViewMode.PLANS:`
- Remove `plan_backend=` from `PlanDataTable()`, `CommandContext()`, and `reconfigure()` calls

**4. `src/erk/tui/widgets/plan_table.py`**
- Remove `plan_backend` parameter from `__init__()` and `reconfigure()`; remove `self._plan_backend` field
- Line 161: hardcode `plan_col_header = "pr"` (delete github `else` branch)
- Lines 189-196: remove always-true `if self._plan_backend == "planned_pr":` wrapper
- Line 213: delete always-false `if self._plan_backend != "planned_pr":` block
- Lines 344-348: remove always-true conditional wrapper
- Line 358: delete always-false block

**5. `src/erk/tui/commands/provider.py`**
- Remove `plan_backend=self._app._plan_backend` from both `CommandContext()` calls (lines 97, 206)

**6. Tests**
- `tests/tui/commands/test_registry.py` (62 occurrences): Remove `plan_backend=` from all `CommandContext()` calls; delete tests for `copy_prepare`/`copy_prepare_activate` availability; update expected command lists
- `tests/tui/test_plan_table.py` (33 occurrences): Remove `plan_backend=` from all calls; delete github-only tests; update column index assertions to match always-planned_pr layout
- `tests/tui/test_app.py` (3 occurrences): Remove `plan_backend=` from `ErkDashApp()` calls; delete github display name test
- `tests/tui/screens/test_launch_screen.py` (4 occurrences): Remove `plan_backend=` from `CommandContext()` calls

**7. Documentation**
- Delete `docs/learned/tui/backend-aware-commands.md` (documents dead `_is_github_backend()` predicate)
- Update references in `docs/learned/tui/tripwires.md`, `view-aware-commands.md`, `adding-commands.md`

### Node 1.4: Provider Name Conditional Removal (10 prod files + tests)

For each file: keep the `"github-draft-pr"` (draft-PR) branch, delete the `"github"` (issue-based) branch, remove conditional wrapping.

**1. `src/erk/cli/commands/pr/submit_pipeline.py`** (line 701)
- Collapse to draft-PR path: always extract `metadata_prefix`, set `issue_number = None`
- Delete issue-based `_extract_closing_ref_from_pr` call

**2-4. Three identical PR body assembly files** (same pattern):
- `src/erk/cli/commands/exec/scripts/update_pr_description.py` (line 153)
- `src/erk/cli/commands/exec/scripts/set_pr_description.py` (line 89)
- `src/erk/cli/commands/pr/rewrite_cmd.py` (line 167)
- Always call `extract_metadata_prefix()`, remove `discover_issue_for_footer` call and its `else` branch
- After all 3 callers removed: delete `discover_issue_for_footer` from `pr/shared.py` (no remaining callers)

**5. `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py`** (line 77)
- Keep direct PR lookup, delete issue-metadata-to-branch-to-PR resolution path

**6. `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`** (line 422)
- Always call `_setup_planned_pr_plan()`; delete entire `_setup_issue_plan()` function (~125 lines)

**7. `src/erk/cli/commands/one_shot_dispatch.py`** — Most complex, 7 sites
- Delete skeleton issue creation block (lines 200-227)
- Keep only `generate_planned_pr_branch_name()` for branch naming
- Keep only planned-PR branch for PR creation with metadata block
- Hardcode `"plan_backend": "planned_pr"` in workflow inputs
- Delete issue-based PR body update block (lines 417-434)
- Remove `is_planned_pr` variable and `create_plan_issue`/`generate_branch_name` imports

**8. `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`** (lines 298, 666)
- Keep direct PR lookup, delete issue-based branch-lookup path
- Hardcode `"plan_backend": "planned_pr"` in workflow inputs

**9. `src/erk/cli/commands/exec/scripts/handle_no_changes.py`** (line 195)
- Remove `is_planned_pr` parameter from helpers; inline draft-PR messaging

**10. `src/erk/cli/commands/submit.py`** (line 1222)
- Keep planned-PR submission path; delete issue-based submission path
- Delete dead functions: `_setup_issue_plan`, `_submit_single_issue`, `_create_branch_and_pr`, `_validate_issue_for_submit`, `ValidatedIssue` (~500 lines)

**Tests for Node 1.4**: Update corresponding test files for each production change. Delete tests exercising issue-based code paths. Keep and simplify draft-PR tests.

### Out of Scope

3 files use `get_provider_name()` for output/storage only (no conditionals) — leave for later:
- `create_impl_context_from_plan.py`, `implement.py`, `get_plan_info.py`

## Verification

1. After Node 1.3: `pytest tests/tui/`
2. After Node 1.4 (incrementally per file group):
   - `pytest tests/commands/pr/` (submit_pipeline, rewrite)
   - `pytest tests/unit/cli/commands/exec/scripts/` (exec scripts)
   - `pytest tests/commands/one_shot/` (one_shot_dispatch)
   - `pytest tests/commands/plan/` (submit)
3. Full suite: `pytest`
4. Type check: `ty`
5. Grep verification: `rg "plan_backend" src/erk/tui/` returns 0 hits; `rg "get_provider_name.*github-draft-pr" src/erk/` returns 0 conditional hits
