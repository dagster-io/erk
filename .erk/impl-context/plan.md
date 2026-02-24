# Plan: Objective #7911 Nodes 1.3 + 1.4 — Delete Issue-Based Plan Backend (Phase 1 Completion)

Part of Objective #7911, Nodes 1.3+1.4

## Context

PRs #7971 (Node 1.1) and #7979 (Node 1.2) removed `get_plan_backend()`, `PlanBackendType`, and dead branches from CLI/exec/context layers. The plan backend is now always `PlannedPRBackend` (`get_provider_name()` always returns `"github-draft-pr"`), and `plan_backend` parameters always carry `"planned_pr"`.

This plan completes Phase 1 by removing the remaining dead code in two areas:
- **Node 1.3**: TUI `plan_backend` parameter and `_is_github_backend()` dead code
- **Node 1.4**: `get_provider_name() == "github-draft-pr"` conditionals across 10 production files

Both nodes are mechanical dead-code removal. Every change removes an always-true or always-false conditional.

## Implementation

### Batch 1: TUI Core — Types + Registry (Node 1.3)

**`src/erk/tui/commands/types.py`**
- Remove `plan_backend: Literal["planned_pr"]` field from `CommandContext`
- Remove `Literal` import if unused

**`src/erk/tui/commands/registry.py`**
- Delete `_is_github_backend()` function (lines 31-33)
- Delete `_display_copy_prepare()` and `_display_copy_prepare_activate()` helpers
- Delete `copy_prepare` and `copy_prepare_activate` `CommandDefinition` blocks (always hidden)
- Simplify `copy_implement_local` predicate: remove `not _is_github_backend(ctx) and`

### Batch 2: TUI Production — App, Table, Provider (Node 1.3)

**`src/erk/tui/widgets/plan_table.py`**
- Remove `plan_backend` param from `__init__()` and `reconfigure()`; remove `self._plan_backend`
- Hardcode `plan_col_header = "pr"` (delete `else: plan_col_header = "plan"` branch)
- Remove always-true `if self._plan_backend == "planned_pr":` guards in `_setup_columns()` and `_row_to_values()`
- Delete always-false `if self._plan_backend != "planned_pr":` blocks

**`src/erk/tui/app.py`**
- Remove `plan_backend` param from `__init__()`, remove `self._plan_backend`
- Simplify `_display_name_for_view()`: `if mode == ViewMode.PLANS:` hardcode `"Planned PRs"`
- Remove `plan_backend=` from `PlanDataTable()`, `CommandContext()`, and `reconfigure()` calls

**`src/erk/tui/commands/provider.py`**
- Remove `plan_backend=self._app._plan_backend` from both `CommandContext()` calls

### Batch 3: TUI Tests (Node 1.3)

**`tests/tui/commands/test_registry.py`** (~55 occurrences)
- Remove `plan_backend=` from all `CommandContext()` calls
- Collapse `for plan_backend in ("github", "planned_pr"):` loop to single check
- Delete tests for `copy_prepare`/`copy_prepare_activate` availability
- Update expected command lists

**`tests/tui/test_plan_table.py`** (~20 occurrences)
- Remove `plan_backend=` from all `PlanDataTable()` calls
- Delete github-only tests (github column layout, `_plan_backend` field assertions)

**`tests/tui/test_app.py`**
- Remove `plan_backend=` from `ErkDashApp()` calls
- Delete `test_display_name_github_plans_view()` test

**`tests/tui/screens/test_launch_screen.py`**
- Remove `plan_backend=` from 4 `CommandContext()` calls

**Documentation:**
- Delete `docs/learned/tui/backend-aware-commands.md` (documents dead `_is_github_backend()`)
- Update references in TUI tripwires/docs

**Verify:** `pytest tests/tui/` + `ty check src/erk/tui/`

### Batch 4: CLI PR Description + Shared (Node 1.4, group A)

These four files share the same pattern: always-true `get_provider_name() == "github-draft-pr"` → collapse to `extract_metadata_prefix()` unconditional, delete `discover_issue_for_footer()` else-branch.

**`src/erk/cli/commands/exec/scripts/update_pr_description.py`** (line ~153)
- Collapse to: `metadata_prefix = extract_metadata_prefix(existing_body)` + `issue_number = None` / `effective_plans_repo = None` / `header = ""`
- Remove dead imports: `IssueLinkageMismatch`, `discover_issue_for_footer`, `extract_header_from_body`

**`src/erk/cli/commands/exec/scripts/set_pr_description.py`** (line ~89)
- Same pattern as above

**`src/erk/cli/commands/pr/rewrite_cmd.py`** (line ~167)
- Same pattern as above

**`src/erk/cli/commands/pr/submit_pipeline.py`** (line ~701)
- Collapse to draft-PR path: keep `state.pr_number is not None` guard, delete else-branch
- Delete `_extract_closing_ref_from_pr()` function (~15 lines)
- Remove dead imports: `extract_closing_reference`, `extract_footer_from_body`

**After all 4 callers cleaned:** Delete from `src/erk/cli/commands/pr/shared.py`:
- `discover_issue_for_footer()` function
- `IssueLinkageMismatch` dataclass
- Related dead imports

**Verify:** `pytest tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py tests/commands/pr/`

### Batch 5: CLI Remaining Files (Node 1.4, group B)

**`src/erk/cli/commands/exec/scripts/get_pr_for_plan.py`** (line ~77)
- Keep direct PR lookup, delete issue-based fallback (~50 lines after `return`)
- Remove `require_github_issues` and related dead imports

**`src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`** (line ~422)
- Call `_setup_planned_pr_plan()` unconditionally, delete `else` branch
- Delete entire `_setup_issue_plan()` function (~125 lines)
- Delete `--branch-slug` CLI option and parameter
- Remove dead imports: `require_time`, `generate_issue_branch_name`, `sanitize_worktree_name`, etc.

**`src/erk/cli/commands/one_shot_dispatch.py`** — 7 `is_planned_pr` sites:
- Delete skeleton issue creation block (`if not is_planned_pr:`)
- Keep only `generate_planned_pr_branch_name()` for branch naming
- Keep only planned-PR PR creation path
- Hardcode `"plan_backend": "planned_pr"` in workflow inputs
- Delete issue-based PR body update block
- Remove `is_planned_pr` variable and dead imports (`create_plan_issue`, `generate_issue_branch_name`)

**`src/erk/cli/commands/exec/scripts/trigger_async_learn.py`** (lines ~298, ~666)
- Keep direct PR lookup in `_get_pr_for_plan_direct()`, delete issue-based fallback
- Hardcode `"plan_backend": "planned_pr"` in workflow inputs

**`src/erk/cli/commands/exec/scripts/handle_no_changes.py`** (line ~195)
- Remove `is_planned_pr` parameter from `_build_pr_body()` and `_build_issue_comment()`
- Inline `is_planned_pr=True` behavior, delete `else` branches
- Delete `is_planned_pr=False` tests

**`src/erk/cli/commands/submit.py`** (line ~1222) — Largest change:
- Keep planned-PR submission path, delete issue-based path
- Delete dead functions (~500 lines): `_validate_issue_for_submit`, `_submit_single_issue`, `_create_branch_and_pr`, `_find_existing_branches_for_issue`, `_prompt_existing_branch_action`, `ValidatedIssue`
- Keep `_build_pr_url()` and `_build_workflow_run_url()` (still used by `_submit_planned_pr_plan`)
- Clean up dead imports

**Verify:** `pytest tests/unit/cli/commands/exec/scripts/ tests/commands/one_shot/ tests/commands/submit/ tests/commands/plan/test_submit.py`

### Out of Scope

3 files use `get_provider_name()` for output/storage only (no conditionals) — leave for later nodes:
- `create_impl_context_from_plan.py`, `implement.py`, `get_plan_info.py`

## Verification

After each batch, run the relevant test subset. Final verification:

1. `pytest tests/tui/` — TUI tests (Batches 1-3)
2. `pytest tests/unit/cli/ tests/commands/` — CLI tests (Batches 4-5)
3. `pytest` — Full test suite
4. `ty` — Type check
5. Grep verification: `rg "plan_backend" src/erk/tui/` returns 0 hits; `rg "_is_github_backend" src/erk/` returns 0 hits
