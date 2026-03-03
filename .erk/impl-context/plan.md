# Plan: Consolidate Documentation from 18 erk-learn Plans

> **Consolidates:** #8698, #8692, #8691, #8690, #8685, #8679, #8677, #8672, #8669, #8666, #8665, #8663, #8656, #8650, #8649, #8648, #8647, #8645

## Context

18 erk-learn plans accumulated on 2026-03-03 from various implementation PRs. All source PRs are fully merged. This plan consolidates all documentation work into a single implementation effort. Plan #8650 is superseded by #8669 (a plnd/ skip was added then removed).

## Source Plans

| # | Title | Items Merged |
| --- | --- | --- |
| 8698 | Move uv sync outside VIRTUAL_ENV guard | 2 items |
| 8692 | Rename "In plan br" to "In current wt" | 1 item |
| 8691 | Fix slot reuse to ignore untracked files | 1 item |
| 8690 | Hide plan PR option when on trunk branch | 1 item |
| 8685 | Add impl-context cleanup to plan-implement | 1 item |
| 8679 | Eliminate issue-based plan refs / consolidate next-steps | 3 items |
| 8677 | Sync CHANGELOG Unreleased section | 1 item |
| 8672 | Add progress indicator during PR description generation | 2 items |
| 8669 | Remove incorrect plnd/ skip in cleanup_impl_for_submit | 1 item |
| 8666 | Add CI step for erk-mcp tests | 1 item |
| 8665 | Create erk-mcp server via MCP protocol | 2 items |
| 8663 | Support objectives without a roadmap | 1 item |
| 8656 | Add GitHub API fallback to dispatch auto-detection | 1 item |
| 8650 | Skip impl-context cleanup for plan PRs (SUPERSEDED by #8669) | 0 items |
| 8649 | Improve "Using existing branch" message | 1 item |
| 8648 | Auto-execute activation script in stack-in-place | 1 item |
| 8647 | Add plan-only PR detection / Plan File Mode | 1 item |
| 8645 | Add "Implement on current branch" option | 1 item |

## Overlap Analysis

- **#8650 + #8669**: Both cover impl-context cleanup for plan branches. #8650 added a skip, #8669 removed it. Merged into single documentation item about why cleanup always runs.
- **#8698 + #8648**: Both affect activation scripts. Merged into single activation-scripts.md update.
- **#8645 + #8690 + #8692**: All affect exit plan mode / plan-save output. Merged into single workflow.md update.
- **#8685 + #8669 + #8650**: All relate to impl-context lifecycle. Merged into single impl-context.md update.
- **#8665 + #8666**: Both cover erk-mcp. Merged into single MCP documentation effort.

## Implementation Steps

### Step 1: Update activation-scripts.md _(from #8698, #8648)_

**File:** `docs/learned/cli/activation-scripts.md`

**Changes:**
1. Update "VIRTUAL_ENV Idempotency Guard" section (lines 75-106):
   - Clarify that `uv sync` and `uv pip install` now run OUTSIDE the guard (always execute)
   - Guard only protects: venv activation, .env loading, shell completion
   - Add rationale: reused slots need dependency sync on branch switch
2. Update tripwire (lines 10-11): Distinguish "removing guard entirely" (dangerous) from "moving sync outside guard" (correct)
3. Add section on `force_script_activation` parameter:
   - Stack-in-place checkout forces script output (`force_script_activation=True`)
   - Normal checkout respects `--script` flag (`force_script_activation=False`)
   - Source: `src/erk/cli/commands/branch/checkout_cmd.py:164`
4. Update code example to match current `render_activation_script()` output

**Verification:** Read `src/erk/cli/activation.py:193-228` to confirm script structure matches docs

### Step 2: Update planning workflow.md _(from #8645, #8690, #8692)_

**File:** `docs/learned/planning/workflow.md`

**Changes:**
1. Update exit plan mode options (lines 61-110) to reflect 4 options:
   - Option A: "Create a plan PR on new branch"
   - Option B: "Create a plan PR on the current branch" (hidden on trunk)
   - Option C: "Just implement on the current branch without creating a PR" (NEW from #8645)
   - Option D: "View/Edit the Plan"
2. Add note: Option B hidden on trunk branches (master/main) with warning (#8690)
3. Note "In current wt" label in plan-save output (#8692)
4. Source: `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py:336-357`

**Verification:** Read exit_plan_mode_hook.py to confirm option list matches

### Step 3: Update impl-context.md _(from #8669, #8650, #8685)_

**File:** `docs/learned/planning/impl-context.md`

**Changes:**
1. Add note that `cleanup_impl_for_submit()` runs for ALL branches including `plnd/*`
   - A skip guard was added (PR #8636) then correctly removed (PR #8667)
   - Reason: plan-save uses `git.remote.push_to_remote()` directly, never the submit pipeline
   - So the skip was unnecessary and caused impl-context to leak into implementation PRs
2. Reference plan-implement.md Step 11 cleanup (`erk exec cleanup-impl-context`) added by #8682
3. Source: `src/erk/cli/commands/pr/submit_pipeline.py:194-211`

**Verification:** Confirm no `PLANNED_PR_TITLE_PREFIX` check in `cleanup_impl_for_submit()`

### Step 4: Update CI job-ordering-strategy.md _(from #8666)_

**File:** `docs/learned/ci/job-ordering-strategy.md`

**Changes:**
1. Update three-tier architecture diagram (lines 23-30): Add `erk-mcp-tests` to Tier 3
2. Update validation jobs table (lines 42-54): Add 7th job entry for erk-mcp-tests
3. Update any job count mentions (e.g., "6 parallel validation jobs" -> "7")
4. Source: `.github/workflows/ci.yml` erk-mcp-tests job

**Verification:** Count CI jobs in ci.yml and confirm table matches

### Step 5: Create MCP integration doc _(from #8665, #8666)_

**File:** `docs/learned/integrations/mcp-integration.md` (NEW)

**Content:**
1. Frontmatter with read-when: "working with erk-mcp server, MCP protocol, .mcp.json configuration"
2. Package structure: `packages/erk-mcp/`
3. Three MCP tools: `plan_list()`, `plan_view()`, `one_shot()`
4. `_run_erk()` subprocess wrapper pattern
5. Configuration: `.mcp.json` at repo root, `uv run --package erk-mcp erk-mcp`
6. Makefile targets: `mcp`, `mcp-dev`, `test-erk-mcp`
7. CI: erk-mcp-tests job in ci.yml
8. Source: `packages/erk-mcp/src/erk_mcp/server.py`

**Verification:** Run `uv run --package erk-mcp python -c "from erk_mcp.server import mcp; print(mcp)"` to confirm import

### Step 6: Create threading-patterns.md _(from #8672)_

**File:** `docs/learned/architecture/threading-patterns.md` (NEW)

**Content:**
1. Frontmatter with read-when: "adding background threading, progress indicators, long-running operations"
2. Daemon thread pattern with holder lists (from `commit_message_generator.py:142-197`)
3. Thread-safe communication via holder lists + LBYL checks
4. Time abstraction injection for testability
5. Integration with ProgressEvent generator pattern
6. Comparison: `threading.Thread` vs `ThreadPoolExecutor` (statusline) vs Textual `run_worker()`
7. Cross-reference: `docs/learned/architecture/claude-cli-progress.md`
8. Source: `src/erk/core/commit_message_generator.py:142-197`

**Verification:** Read `commit_message_generator.py` to confirm pattern descriptions are accurate

### Step 7: Update dispatch-ref-config.md _(from #8656)_

**File:** `docs/learned/erk/dispatch-ref-config.md`

**Changes:**
1. Add section "Plan Auto-Detection Strategy" documenting two-stage detection:
   - Stage 1: Local `.erk/impl-context/` via `resolve_impl_dir()` (no API call)
   - Stage 2: GitHub API via `resolve_plan_id_for_branch()` (fallback)
2. Note this aligns dispatch with implement_shared.py and land_cmd.py patterns
3. Source: `src/erk/cli/commands/pr/dispatch_cmd.py:356-386`

**Verification:** Confirm `_detect_plan_number_from_context()` has both stages

### Step 8: Create next-steps-output.md _(from #8679)_

**File:** `docs/learned/planning/next-steps-output.md` (NEW)

**Content:**
1. Frontmatter with read-when: "working with plan next-steps output, PlanNextSteps type, format_plan_next_steps_plain"
2. Unified `PlanNextSteps` type (replaced `IssueNextSteps` and `PlannedPRNextSteps`)
3. `PlanNumberEvent` (replaced `IssueNumberEvent`)
4. `format_plan_next_steps_plain()` function
5. Source: `packages/erk-shared/src/erk_shared/output/next_steps.py`

**Verification:** Confirm `PlanNextSteps` exists and `IssueNextSteps` does not

### Step 9: Fix dead link and stale references _(from #8679)_

**File:** `docs/topics/worktrees.md`

**Changes:**
1. Remove dead link to `why-github-issues.md` (line 10) - file was deleted

**Verification:** Confirm `docs/topics/why-github-issues.md` does not exist

### Step 10: Update objective documentation _(from #8663)_

**File:** `docs/learned/objectives/` (find appropriate file or create new)

**Changes:**
1. Document that objectives can exist without a roadmap block
2. `parse_roadmap()` returns `([], [])` when no `objective-roadmap` block exists
3. `validate_objective()` skips roadmap-dependent checks 3-7 when no roadmap
4. `view_objective()` displays "No roadmap data found" for roadmap-free objectives
5. Source: `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py:467-469`

**Verification:** Run `erk objective check` on an objective without roadmap to confirm pass

### Step 11: Document slot reuse untracked file handling _(from #8691)_

**File:** `docs/learned/erk/` (find appropriate file or add to worktree docs)

**Changes:**
1. Document that `find_inactive_slot()` now ignores untracked files
2. Uses `git.status.get_file_status()` checking only `staged` and `modified` (not `untracked`)
3. Rationale: git leaves untracked files untouched during branch switching
4. Source: `src/erk/cli/commands/slot/common.py:179-184`

**Verification:** Read `find_inactive_slot()` to confirm only staged/modified checked

### Step 12: Update workspace-activation.md cross-reference _(from #8698)_

**File:** `docs/learned/erk/workspace-activation.md`

**Changes:**
1. Replace duplicate activation structure section (lines 41-54) with cross-reference to `docs/learned/cli/activation-scripts.md`
2. Keep package refresh focus as primary topic

**Verification:** Confirm no content duplication between the two files

### Step 13: Update claude-cli-progress.md cross-reference _(from #8672)_

**File:** `docs/learned/architecture/claude-cli-progress.md`

**Changes:**
1. Expand CommitMessageGenerator reference (lines 124-133) to mention threading implementation
2. Add cross-reference to new threading-patterns.md

**Verification:** Confirm cross-reference links work

### Step 14: Run docs sync

**Command:** `erk docs sync`

Regenerates auto-generated index files to include new documents.

**Verification:** Check that `docs/learned/index.md` includes new files

## Attribution

Items by source:
- **#8698**: Steps 1, 12
- **#8692**: Step 2
- **#8691**: Step 11
- **#8690**: Step 2
- **#8685**: Step 3
- **#8679**: Steps 8, 9
- **#8677**: (no doc changes needed - changelog already synced)
- **#8672**: Steps 6, 13
- **#8669**: Step 3
- **#8666**: Steps 4, 5
- **#8665**: Step 5
- **#8663**: Step 10
- **#8656**: Step 7
- **#8650**: Step 3 (superseded by #8669)
- **#8649**: (no doc changes - message improvement already shipped)
- **#8648**: Step 1
- **#8647**: (no doc changes - already documented in phase-zero-detection-pattern.md and pr-address-workflows.md)
- **#8645**: Step 2
