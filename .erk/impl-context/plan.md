# Plan: Consolidated Documentation from 22 Erk-Learn Plans

> **Consolidates:** #9116, #9115, #9111, #9108, #9107, #9105, #9104, #9103, #9101, #9098, #9094, #9093, #9091, #9088, #9087, #9078, #9075, #9074, #9073, #9070, #9069, #9063

## Context

22 erk-learn plans accumulated from recent implementation sessions. Deep investigation of all plans against the current codebase reveals that 13 plans are already fully documented and 9 plans have documentation gaps requiring 7 new or updated doc files.

## Source Plans

| # | Title | Items Merged |
| --- | --- | --- |
| #9116 | Remove default MCP server configuration | 0 (already documented) |
| #9115 | Fix: Bidirectional Objective-Plan Linkage | 1 item |
| #9111 | Harden one-shot-plan to reject invalid prompts | 1 item |
| #9108 | Fix stale branch checkout in plan-implement workflow | 1 item |
| #9107 | Fix setup-claude-erk action | 0 (already documented) |
| #9105 | Fix Runs tab branch column | 1 item (merged with #9103, #9104) |
| #9104 | Enhance Runs tab | 1 item (merged with #9103, #9105) |
| #9103 | Add Runs tab to TUI | 1 item (merged with #9104, #9105) |
| #9101 | Add --json and MCP to pr list/view | 1 item |
| #9098 | Extract agentclick subpackage | 0 (already documented) |
| #9094 | anthropic_api_fast_path + GlobalConfigSchema | 0 (already documented) |
| #9093 | System folder convention | 0 (already documented) |
| #9091 | Git pre-push hook | 1 item |
| #9088 | Pretty-print JSON output | 1 item (merged with #9069) |
| #9087 | anthropic_api_fast_path setting | 0 (already documented) |
| #9078 | MCP one_shot upgrade | 0 (already documented) |
| #9075 | Node description reconciliation | 1 item |
| #9074 | output_types validation | 1 item (merged with #9069) |
| #9073 | Fix slot reuse in navigation | 1 item |
| #9070 | erk-dev audit-collect fix | 0 (bugfix, no docs needed) |
| #9069 | @json_command decorator | 1 item |
| #9063 | CHANGELOG update | 0 (no docs needed) |

## What Changed Since Original Plans

- All 22 source PRs have been merged to master
- 13 plans already have current documentation — no action needed
- 9 plans have documentation gaps requiring 7 documentation actions

## Investigation Findings

### Already Documented (No Action Needed)

- **#9116**: `docs/learned/integrations/mcp-integration.md` (lines 100-116) — user-managed MCP config
- **#9087 + #9094**: `docs/learned/architecture/globalconfig-field-addition.md` — GlobalConfigSchema step added
- **#9107**: `docs/learned/ci/composite-action-patterns.md` (lines 180-191) — package vs tool mode
- **#9098**: Covered by `docs/learned/architecture/monolith-to-subpackage-pattern.md` and MCP integration doc
- **#9078**: `docs/learned/integrations/mcp-integration.md` — auto-discovery mechanism
- **#9093**: `docs/learned/commands/system-folder-convention.md` — complete
- **#9070**: Bugfix (pass repo_info to RealLocalGitHub) — no docs needed
- **#9063**: CHANGELOG update — self-documenting

### Overlap Analysis

- **#9103 + #9104 + #9105**: All 3 TUI Runs tab plans → merged into single doc
- **#9069 + #9074 + #9088**: @json_command decorator + output_types + pretty-print → merged into single doc
- **#9087 + #9094**: Both anthropic_api_fast_path → already documented together

## Remaining Gaps

7 documentation actions needed across 9 plans:

## Implementation Steps

### Step 1: Create `docs/learned/cli/json-command-decorator.md` _(from #9069, #9074, #9088)_

**File:** `docs/learned/cli/json-command-decorator.md`

**Content outline:**
1. Overview: `@json_command` as universal CLI JSON infrastructure
2. Decorator parameters: `exclude_json_input`, `required_json_input`, `output_types`
3. `emit_json()` / `emit_json_result()` helper patterns
4. Error handling: `AgentCliError` with `error_type` classification
5. JSON input validation from stdin
6. `output_types` validation: `test_output_types_matches_return_annotation()` pattern
7. Pretty-printing: all `json.dumps()` calls use `indent=2`
8. Testing patterns for `@json_command` commands

**Source files:**
- `packages/erk-shared/src/erk_shared/agentclick/json_command.py` (lines 45-258)
- `packages/erk-shared/src/erk_shared/agentclick/errors.py` (lines 1-13)
- `tests/unit/cli/test_json_command.py` (lines 13-62 for output_types validation)

**Frontmatter read-when:** "adding @json_command decorator", "creating structured JSON CLI output", "understanding emit_json patterns"

**Verification:** All decorator parameters match actual implementation in json_command.py

### Step 2: Create `docs/learned/cli/adding-json-to-commands.md` _(from #9101)_

**File:** `docs/learned/cli/adding-json-to-commands.md`

**Content outline:**
1. Step-by-step guide to adding `--json` to existing Click commands
2. Decorator stacking order: `@mcp_exposed` above `@json_command` above `@click.command`
3. Result dataclasses: `to_json_dict()` protocol
4. `exclude_json_input` usage for parameters not accepted from JSON stdin
5. Worked example: `pr list` and `pr view` commands with `PrListResult` / `PrViewResult`

**Source files:**
- `src/erk/cli/commands/pr/list_cmd.py` (lines 43-51 for PrListResult, line 467 for decorators)
- `src/erk/cli/commands/pr/view_cmd.py` (lines 50-75 for PrViewResult, line 283 for decorators)
- `packages/erk-shared/src/erk_shared/agentclick/mcp_exposed.py` (lines 41-65)

**Frontmatter read-when:** "adding --json flag to a CLI command", "exposing a command via MCP", "creating result dataclasses for JSON output"

**Verification:** Decorator stacking matches actual commands in pr/list_cmd.py and pr/view_cmd.py

### Step 3: Create `docs/learned/tui/runs-tab-architecture.md` _(from #9103, #9104, #9105)_

**File:** `docs/learned/tui/runs-tab-architecture.md`

**Content outline:**
1. Overview: Runs tab as new ViewMode alongside Plans/Learn/Objectives
2. `RunRowData` frozen dataclass (7 columns: run-id, status, submitted, workflow, pr, branch, chks)
3. `RunDataTable` widget and column configuration
4. `fetch_runs()` data provider implementation
5. Branch resolution: PR `head_branch` > run.branch (filtered master/main) > "-"
6. `get_pr_head_branches()` gateway method (4-place pattern: ABC, Real, Fake, DryRun)
7. j/k navigation view-mode dispatch pattern in `navigation.py`
8. View switching via "4" key

**Source files:**
- `src/erk/tui/data/types.py` (lines 157-201 for RunRowData)
- `src/erk/tui/widgets/run_table.py` (RunDataTable widget)
- `src/erk/tui/data/real_provider.py` (lines 179-353 for fetch_runs)
- `src/erk/tui/actions/navigation.py` (lines 230-244 for j/k dispatch)
- `packages/erk-shared/src/erk_shared/gateway/github/abc.py` (line 249 for get_pr_head_branches)

**Frontmatter read-when:** "working with TUI Runs tab", "adding columns to RunDataTable", "understanding branch resolution in runs"

**Verification:** Column list matches RunDataTable implementation; branch resolution matches real_provider.py lines 317-350

### Step 4: Create `docs/learned/hooks/git-pre-push-validation.md` _(from #9091)_

**File:** `docs/learned/hooks/git-pre-push-validation.md`

**Content outline:**
1. Purpose: Local pre-push validation (ruff lint, ruff format, ty type check)
2. Setup: `make install-hooks` (sets `core.hooksPath = githooks`)
3. Hook file: `githooks/pre-push` (15-line shell script)
4. Manual run: `make pre-push-check`
5. Bypass: `git push --no-verify`
6. Relationship to CI checks (same checks, faster feedback)

**Source files:**
- `githooks/pre-push` (executable shell script)
- `Makefile` (lines ~112-123 for pre-push-check and install-hooks targets)

**Frontmatter read-when:** "setting up git hooks", "understanding pre-push validation", "bypassing local checks"

**Verification:** Hook file exists at githooks/pre-push; Makefile targets exist

### Step 5: Create `docs/learned/objectives/objective-plan-backlinks.md` _(from #9115)_

**File:** `docs/learned/objectives/objective-plan-backlinks.md`

**Content outline:**
1. `objective_issue` plan-header field: what it is, when it's set
2. `update_plan_header_objective_issue()` helper function
3. `_set_plan_backlink()` in update_objective_node.py (fail-open behavior)
4. Check 9 (`_check_pr_backlinks()`) validation in check_cmd.py
5. Bidirectional linkage: objective references plan, plan references objective

**Source files:**
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py` (line 55)
- `src/erk/cli/commands/exec/scripts/update_objective_node.py` (lines 311-352)
- `src/erk/cli/commands/objective/check_cmd.py` (line 108+)

**Frontmatter read-when:** "linking plans to objectives", "understanding objective_issue metadata", "debugging objective-plan linkage"

**Verification:** Check 9 exists in check_cmd.py; _set_plan_backlink exists in update_objective_node.py

### Step 6: Extend `docs/learned/planning/one-shot-workflow.md` _(from #9111)_

**File:** `docs/learned/planning/one-shot-workflow.md` (EXTEND existing)

**Content to add:** New "Prompt Validation and Rejection" section after existing content:
1. Step 1.5 validation: what makes a prompt invalid
2. Rejection output format: `plan-result.json` with `rejected: true` and `reason`
3. Workflow routing: plan issue closure on rejection, downstream step gating
4. `.claude/commands/erk/system/one-shot-plan.md` as source of truth

**Source files:**
- `.claude/commands/erk/system/one-shot-plan.md` (Step 1.5)
- `.github/workflows/one-shot.yml` (rejection detection and routing)

**Verification:** Step 1.5 exists in one-shot-plan.md; rejection handling in one-shot.yml

### Step 7: Extend `docs/learned/erk/slot-pool-architecture.md` _(from #9073)_

**File:** `docs/learned/erk/slot-pool-architecture.md` (EXTEND existing)

**Content to add:** New "Navigation Integration" section in Entry Points area:
1. `ensure_branch_has_worktree()` replaces `ensure_worktree_for_branch` for slot allocation
2. Navigation commands (`erk up`, `erk down`) use slot pool for worktree assignment
3. `_navigate_after_land()` in land_cmd.py also uses this pattern
4. User-facing message: "Assigned slot" (not "Created worktree")

**Source files:**
- `src/erk/cli/commands/navigation_helpers.py` (lines 546-548, 604-606)
- `src/erk/cli/commands/land_cmd.py` (line 1233)

**Verification:** `ensure_branch_has_worktree` import exists in navigation_helpers.py

### Step 8: Extend `docs/learned/objectives/objective-lifecycle.md` _(from #9075)_

**File:** `docs/learned/objectives/objective-lifecycle.md` (EXTEND existing)

**Content to add:** New "Node Description Reconciliation" subsection under Mutations:
1. "Naming divergence" contradiction type
2. Workflow: update node descriptions BEFORE prose updates (comment re-rendering)
3. `erk exec update-objective-node --description` command usage

**Source files:**
- `.claude/commands/erk/system/objective-update-with-landed-pr.md` (reconciliation guidance)

**Verification:** "naming divergence" pattern exists in objective-update-with-landed-pr.md

### Step 9: Extend `docs/learned/ci/plan-implement-workflow-patterns.md` _(from #9108)_

**File:** `docs/learned/ci/plan-implement-workflow-patterns.md` (EXTEND existing)

**Content to add:** New "Branch State Consistency" section:
1. Race condition: plan job pushes commits after implement job checks out branch
2. Fix: `git reset --hard "origin/$BRANCH_NAME"` after checkout
3. Safe because implement job has no local work to lose
4. Pattern: checkout → fetch → reset for workflow-dispatched branches

**Source files:**
- `.github/workflows/plan-implement.yml` (lines 157-158)

**Verification:** git reset --hard exists in plan-implement.yml implement job

## Tripwires and Frontmatter

Each new doc needs:
- `read_when` conditions in frontmatter
- At least one tripwire added to the appropriate category tripwires file
- Registration in docs/learned/ index via `erk docs sync`

## Attribution

Items by source:
- **#9069, #9074, #9088**: Step 1
- **#9101**: Step 2
- **#9103, #9104, #9105**: Step 3
- **#9091**: Step 4
- **#9115**: Step 5
- **#9111**: Step 6
- **#9073**: Step 7
- **#9075**: Step 8
- **#9108**: Step 9

## Verification

After implementation:
1. Run `erk docs sync` to regenerate index and tripwires
2. Verify each new file has proper frontmatter with `read_when` and `tripwires`
3. Spot-check file paths and line numbers referenced in docs against current codebase
4. Run `make fast-ci` to ensure no formatting issues
