<<<<<<< HEAD
# Plan: Merge `plan`/`pr` into single `planned_pr` field in objective roadmap

## Context

In the draft-PR plan backend (now the only backend), a plan IS a draft PR — they share the same GitHub PR number. The current roadmap format has separate `plan` and `pr` fields on each node, plus separate "Plan" and "PR" columns in the markdown table. This is redundant: when both are set, they always contain the same value (e.g., `plan: "#7971", pr: "#7971"`). Merging into a single `planned_pr` field simplifies the data model, CLI interface, and display.

## Approach

Merge `plan: str | None` and `pr: str | None` into a single `planned_pr: str | None` across the data model, YAML schema, CLI, rendering, and tests. Bump schema version from "4" to "5". Support parsing v4 (auto-coalesce `pr` > `plan` > null) for existing objectives.

## Changes

### 1. Core data model (`packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`)

- **RoadmapNode**: Replace `plan: str | None` + `pr: str | None` with `planned_pr: str | None`
- **validate_roadmap_frontmatter()**:
  - Accept schema_version "5" (new) with `planned_pr` key
  - Accept schema_version "2"/"3"/"4" (existing) with separate `plan`/`pr` keys — coalesce: `pr or plan or None`
- **render_roadmap_block_inner()**: Emit `schema_version: "5"` with `planned_pr` key
- **update_node_in_frontmatter()**: Replace separate `plan`/`pr` params with single `planned_pr` param. Simplify status inference: `planned_pr` set → `in_progress`
- **render_roadmap_tables()**: Merge "Plan"/"PR" columns into single "Planned PR" column. Change `pr_count` to count done nodes instead of `step.pr is not None`
- **serialize_phases()**: Replace `plan`/`pr` keys with `planned_pr`

### 2. Dependency graph (`packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`)

- **ObjectiveNode**: Replace `plan: str | None` + `pr: str | None` with `planned_pr: str | None`
- Update `graph_from_phases()`, `graph_from_nodes()`, `nodes_from_graph()` to pass `planned_pr`

### 3. Render roadmap exec script (`src/erk/cli/commands/exec/scripts/objective_render_roadmap.py`)

- Update table header: `| Node | Description | Status | Planned PR |`
- Update table rows to emit single `planned_pr` column (always `-` for new roadmaps)

### 4. Update objective node CLI (`src/erk/cli/commands/exec/scripts/update_objective_node.py`)

- Replace `--plan`/`--pr` options with single `--planned-pr` option
- Remove the validation that `--plan` is required when `--pr` is set (no longer needed)
- Update `_replace_table_in_text()`: Match 4-column rows (was 5-column)
- Update `_find_node_refs()`: Return single `planned_pr` value
- Update `_replace_node_refs_in_body()`: Pass single `planned_pr`
- Update `_build_output()`: Replace `previous_plan`/`new_plan`/`previous_pr`/`new_pr` with `previous_planned_pr`/`new_planned_pr`

### 5. View command (`src/erk/cli/commands/objective/view_cmd.py`)

- **_format_node_status()**: Rename `plan` param → `planned_pr`
- Merge `max_plan_width`/`max_pr_width` into `max_planned_pr_width`
- Merge separate "plan"/"pr" table columns into single "planned_pr" column
- Update JSON output: replace `plan`/`pr` keys with `planned_pr`

### 6. Check command (`src/erk/cli/commands/objective/check_cmd.py`)

- Merge plan/pr consistency checks: single check for `planned_pr` reference format
- Update orphaned done check: `node.status == "done" and node.planned_pr is None`
- Merge plan/pr `#` prefix validation into single `planned_pr` check

### 7. Fetch context (`src/erk/cli/commands/exec/scripts/objective_fetch_context.py`)

- Update `step.plan == plan_ref` → `step.planned_pr == plan_ref` for step matching

### 8. Skill/command docs (update CLI examples)

- `.claude/commands/erk/objective-update-with-landed-pr.md` — `--planned-pr` instead of `--plan`/`--pr`
- `.claude/commands/erk/objective-update-with-closed-plan.md` — `--planned-pr ""`
- `.claude/commands/erk/plan-save.md` — `--planned-pr`
- `.claude/commands/local/objective-reevaluate.md` — `--planned-pr`
- `.claude/skills/erk-exec/reference.md` — update parameter docs
- `.claude/skills/objective/references/format.md` — update format docs

### 9. CI workflow (`.github/workflows/one-shot.yml`)

- Change `--plan "$PLAN_NUMBER"` → `--planned-pr "$PLAN_NUMBER"`

### 10. Tests

- `test_roadmap.py` — update `.pr`/`.plan` assertions → `.planned_pr`
- `test_roadmap_frontmatter.py` — update all plan/pr assertions and YAML fixtures
- `test_dependency_graph.py` — update ObjectiveNode assertions
- `test_update_objective_node.py` — update --plan/--pr to --planned-pr, update output keys
- `test_objective_render_roadmap.py` — update table format assertions

### 11. Docs (update roadmap-related learned docs)

- `docs/learned/architecture/roadmap-mutation-semantics.md` — if it references plan/pr separately
- `docs/learned/objectives/roadmap-status-system.md` — update two-tier status docs
- `docs/learned/reference/objective-summary-format.md` — update format reference

## Migration strategy

- **Parsing**: `validate_roadmap_frontmatter()` accepts v2/3/4 (coalesces `pr ?? plan` into `planned_pr`) and v5 (reads `planned_pr` directly)
- **Writing**: Always emits v5 with `planned_pr`
- **Existing objectives**: First read coalesces to v5 in memory; next write (via `update-objective-node` or any mutation) upgrades the on-disk YAML to v5
- **No explicit migration script needed**: objectives upgrade lazily on next mutation

## Verification

1. Run `make fast-ci` — all unit tests pass
2. `erk objective view 7911` — renders correctly with single "planned_pr" column (existing v4 YAML auto-coalesced)
3. `erk objective check 7911` — passes all validation checks
4. `erk exec update-objective-node 7911 --node 1.2 --planned-pr "#9999" --status in_progress` — sets single field, then revert
5. `erk exec objective-render-roadmap` with test JSON — produces 4-column table (Node | Description | Status | Planned PR)
=======
# Simplify `/erk:plan-implement` Command

## Context

`plan-implement.md` is 360 lines with 22 distinct actions across 15 numbered steps. Two problems:

1. **Too many steps** — the decision tree (Steps 0-2d) has 4 input paths with 8 sub-steps, all converging before actual implementation begins.
2. **Too much inline bash** — 3 blocks of shell logic (branch detection, impl-context cleanup, session upload) should be delegated to `erk exec` commands.

Additionally, Step 10b has a bug: it uses `--issue-number` but `upload-session` expects `--plan-id`.

## Approach

### Part A: Create 3 new `erk exec` commands for inline bash

#### 1. `detect-plan-from-branch`

Replaces the 6-line branch detection in Step 1b-branch.

- **File**: `src/erk/cli/commands/exec/scripts/detect_plan_from_branch.py`
- **Params**: None (reads current branch via git gateway)
- **Logic**: Call `extract_leading_issue_number()` from `erk_shared.naming` (already exists). If no match, fall back to `github.get_pr_for_branch()`.
- **Output**: `{"found": true, "plan_number": 2521, "detection_method": "branch_name"}` or `{"found": false}`
- **Test**: `tests/unit/cli/commands/exec/scripts/test_detect_plan_from_branch.py`

#### 2. `cleanup-impl-context`

Replaces the 4-line git rm + commit + push in Step 2d.

- **File**: `src/erk/cli/commands/exec/scripts/cleanup_impl_context.py`
- **Params**: None (operates on repo root)
- **Logic**: Check `impl_context_exists()` from `erk_shared.impl_context`. If exists: `remove_impl_context()`, then `git.commit.stage_files()` + `git.commit.commit()` + `git.remote.push_to_remote()`.
- **Output**: `{"cleaned": true}` or `{"cleaned": false, "reason": "not_found"}`
- **Test**: `tests/unit/cli/commands/exec/scripts/test_cleanup_impl_context.py`

Note: After `shutil.rmtree` (via `remove_impl_context()`), `git add .erk/impl-context/` stages the deletions. No need for `git rm`.

#### 3. `upload-impl-session`

Replaces the 8-line eval + jq + conditional upload in Step 10b. Fixes the `--issue-number` vs `--plan-id` bug.

- **File**: `src/erk/cli/commands/exec/scripts/upload_impl_session.py`
- **Params**: `--session-id` (required)
- **Logic**: Read plan ref from `.impl/` for `plan_id`. Use `capture_session_info` logic to find session file. Call `upload_session` internally. Exit 0 always (non-critical).
- **Output**: `{"uploaded": true, "plan_id": 2521}` or `{"uploaded": false, "reason": "no_plan_tracking"}`
- **Test**: `tests/unit/cli/commands/exec/scripts/test_upload_impl_session.py`

### Part B: Create consolidated `setup-impl` command

Replaces the entire decision tree (Steps 0 through 2d).

- **File**: `src/erk/cli/commands/exec/scripts/setup_impl.py`
- **Params**: `[SOURCE]` (optional positional: issue number, URL, or file path), `--session-id` (optional, for plan-save fallback)
- **Output**: JSON combining setup-impl-from-issue + impl-init output:

```json
{
  "success": true,
  "source_type": "issue",
  "plan_number": 2521,
  "has_plan_tracking": true,
  "branch": "P2521-feature-slug",
  "plan_path": "/path/.impl/plan.md",
  "phases": [...],
  "related_docs": {"skills": [...], "docs": [...]}
}
```

**Internal logic** (priority order):
1. Classify source arg (numeric → issue, URL → extract number, path → file, empty → continue)
2. If issue: call `_setup_draft_pr_plan` or `_setup_issue_plan` (reuse from `setup_impl_from_issue.py`)
3. If file: read file, generate branch via `BranchManager.create_branch()`, create `.impl/`
4. If `.impl/` exists and valid: sync if has tracking, use as-is if not
5. Try `detect-plan-from-branch` logic, then setup from detected issue
6. Fallback: `plan-save` with session-id, then setup from saved issue
7. **All paths**: call `cleanup-impl-context` + `impl-init` before returning

**Key reuse**:
- `_setup_draft_pr_plan()` and `_setup_issue_plan()` from `setup_impl_from_issue.py` — extract into importable functions or call directly
- `_validate_impl_folder()` and `_extract_related_docs()` from `impl_init.py`
- `extract_leading_issue_number()` from `erk_shared.naming`
- `BranchManager.create_branch()` for file-based path (no devrun needed — Graphite tracking is already abstracted)
- `impl_context_exists()` / `remove_impl_context()` from `erk_shared.impl_context`

**Test**: `tests/unit/cli/commands/exec/scripts/test_setup_impl.py`

### Part C: Simplify `plan-implement.md`

Rewrite the command from 15 steps to ~10, removing all inline bash:

```
Step 0: Parse Arguments (unchanged — trivial arg classification)
Step 1: Setup Implementation
  → single call: erk exec setup-impl $ARGUMENTS --session-id="${CLAUDE_SESSION_ID}"
  → parse JSON for phases, related_docs, plan_path, etc.
Step 2: Read Plan and Load Context
Step 3: Load Related Documentation (from setup-impl output)
Step 4: Create TodoWrite Entries (from setup-impl phases)
Step 5: Signal GitHub Started
  → erk exec impl-signal started --session-id="${CLAUDE_SESSION_ID}"
Step 6: Execute Each Phase Sequentially
Step 7: Final Verification
Step 8: Signal GitHub Ended + Upload Session
  → erk exec impl-signal ended --session-id="${CLAUDE_SESSION_ID}"
  → erk exec upload-impl-session --session-id="${CLAUDE_SESSION_ID}"
Step 9: Verify .impl/ Preserved
  → erk exec impl-verify
Step 10: Run CI Iteratively
Step 11: Submit PR
  → erk pr submit / erk exec impl-signal submitted / erk pr check
```

**Eliminated**: Steps 1a/1a-file/1b/1b-branch/1c/2/2b/2c/2d (all collapsed into Step 1), Step 10b (absorbed into Step 8).

## Implementation Sequence

1. **Phase 1**: Create `detect-plan-from-branch` exec command + tests
2. **Phase 2**: Create `cleanup-impl-context` exec command + tests
3. **Phase 3**: Create `upload-impl-session` exec command + tests
4. **Phase 4**: Create `setup-impl` consolidated command + tests (largest piece — composes phases 1-2 internally)
5. **Phase 5**: Rewrite `plan-implement.md` to use the new commands
6. **Phase 6**: Register all 4 commands in `group.py`

## Critical Files

- `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` — reuse `_setup_draft_pr_plan`, `_setup_issue_plan`
- `src/erk/cli/commands/exec/scripts/impl_init.py` — reuse `_validate_impl_folder`, `_extract_related_docs`
- `src/erk/cli/commands/exec/group.py` — register new commands
- `packages/erk-shared/src/erk_shared/naming.py` — `extract_leading_issue_number()`
- `packages/erk-shared/src/erk_shared/impl_context.py` — `remove_impl_context()`, `impl_context_exists()`
- `.claude/commands/erk/plan-implement.md` — rewrite

## Verification

1. Run `erk exec setup-impl --help` to confirm registration
2. Run `erk exec detect-plan-from-branch` on a P-prefixed branch to verify detection
3. Run unit tests for all 4 new commands
4. Test `/erk:plan-implement` end-to-end with an issue number argument
5. Run `local:fast-ci` to verify no regressions
>>>>>>> 1aba68119 (Add plan: Simplify `/erk:plan-implement` Command)
