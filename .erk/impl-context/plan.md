# Plan: Consolidate Documentation from 15 erk-learn Plans

> **Consolidates:** #8706, #8704, #8699, #8698, #8691, #8685, #8679, #8677, #8672, #8669, #8663, #8650, #8649, #8647, #8645

## Context

15 erk-learn plans accumulated from recent implementation sessions. All source PRs are merged and implementations are complete. These plans need to be consolidated into a single documentation plan that captures the remaining documentation gaps. Several plans have overlapping themes (impl-context cleanup, plan workflow enhancements) and some plans' documentation is already up-to-date, requiring no additional work.

## Source Plans

| # | Title | Items Merged | Doc Status |
| --- | --- | --- | --- |
| 8706 | Add "unexpected end of JSON input" as transient error | 1 item | Needs update |
| 8704 | Add /local:cmux-workspace-rename command | 1 item | Needs new doc |
| 8699 | Fix erk up/down navigation with branch mismatch | 2 items | Needs new doc |
| 8698 | Move uv sync outside VIRTUAL_ENV guard | 1 item | Needs fix |
| 8691 | Fix slot reuse to ignore untracked files | 1 item | Needs update |
| 8685 | Add impl-context cleanup to plan-implement | 1 item | Needs update |
| 8679 | Eliminate issue-based plan references | 1 item | Needs update |
| 8677 | Sync CHANGELOG unreleased section | 0 items | Already adequate |
| 8672 | Add progress indicator during PR description | 0 items | Already adequate |
| 8669 | Remove incorrect plnd/ skip in cleanup | 1 item | Merged with #8650 |
| 8663 | Support objectives without a roadmap | 1 item | Needs update |
| 8650 | Skip impl-context cleanup for plan PRs | 1 item | Merged with #8669 |
| 8649 | Improve "Using existing branch" message | 0 items | Already adequate |
| 8647 | Plan-only PR detection and Plan File Mode | 0 items | Already adequate |
| 8645 | Implement on current branch option | 0 items | Already adequate |

## Investigation Findings

### Plans with no remaining documentation gaps (5 plans)

These plans' source implementations are well-documented and need no further work:

- **#8677**: changelog-standards.md and categorization-rules.md are comprehensive
- **#8672**: claude-cli-progress.md covers the progress indicator pattern fully
- **#8649**: Trivial one-line message change, no doc needed
- **#8647**: pr-address-workflows.md already documents Plan File Mode
- **#8645**: workflow.md already documents 4 exit plan mode options

### Corrections to Original Plans

- **#8650**: Plan is OBSOLETE - the plnd/ skip it documented was incorrect and removed by #8669
- **#8698**: activation-scripts.md has INCORRECT info (lines 89-97 say uv sync is inside guard)

### Overlap Analysis

- **#8650 + #8669**: Same code path (cleanup_impl_for_submit plnd/ skip) - merged into single item
- **#8685 + #8650 + #8669**: All about impl-context cleanup lifecycle - grouped in Step 3

## Implementation Steps

### Step 1: Update github-api-retry-mechanism.md _(from #8706)_

**File:** `docs/learned/architecture/github-api-retry-mechanism.md`

- Add "unexpected end of json input" to the transient error pattern list (currently at lines 51-60)
- Add note: This error occurs when GitHub API returns truncated JSON responses
- Reference source: `packages/erk-shared/src/erk_shared/gateway/github/transient_errors.py` (line 15)
- **Verification:** Pattern list in doc matches `TRANSIENT_ERROR_PATTERNS` tuple in source

### Step 2: Fix activation-scripts.md _(from #8698)_

**File:** `docs/learned/cli/activation-scripts.md`

- Fix lines 89-97: Change "INSIDE guard (skipped on re-entry)" to "OUTSIDE guard (always runs)"
- Update line references: guard is at line 202 (not 198)
- Clarify: `uv sync` and `uv pip install` run unconditionally (lines 196-201), guard wraps venv activation/`.env` loading/completion (lines 202-225)
- Add rationale: ensures dependency sync after branch switches in reused slots
- **Source:** `src/erk/cli/activation.py` lines 196-225
- **Verification:** Doc's guard scope section matches actual code structure

### Step 3: Update impl-context.md _(from #8685, #8650, #8669)_

**File:** `docs/learned/planning/impl-context.md`

- Add note about cleanup at end of plan-implement workflow (Step 11 calls `erk exec cleanup-impl-context`)
- Document the plnd/ skip saga: skip was added (#8636/PR #8650) then removed (#8667/PR #8669) because plan-save uses `push_to_remote()` directly, never the submit pipeline
- Add note: `cleanup_impl_for_submit()` runs for ALL branches including plnd/* (no special casing)
- Reference the `cleanup_impl_context` exec script: `src/erk/cli/commands/exec/scripts/cleanup_impl_context.py`
- Add tripwire: "plan-save never goes through the submit pipeline"
- **Verification:** Notes match behavior in `src/erk/cli/commands/pr/submit_pipeline.py` (lines 194-211)

### Step 4: Update slot-pool-architecture.md _(from #8691)_

**File:** `docs/learned/erk/slot-pool-architecture.md`

- Add section about untracked file handling in `find_inactive_slot()`
- Document: untracked files (e.g., `.erk/bin/`) don't block slot reuse; only staged/modified tracked files do
- Code reference: `src/erk/cli/commands/slot/common.py` lines 179-181 uses `get_file_status()` to distinguish staged/modified from untracked
- Add tripwire: "Untracked files are safe for branch switching - don't use `has_uncommitted_changes()` for slot reuse"
- **Verification:** Description matches `find_inactive_slot()` behavior in source

### Step 5: Create worktree-branch-mismatch.md _(from #8699)_

**File:** `docs/learned/erk/worktree-branch-mismatch.md`

**Content outline:**
1. Problem: User manually runs `git checkout other-branch` in a worktree, then `erk up/down` can't find expected branch
2. Solution: Two-stage lookup with path-based fallback via `find_worktree_for_branch_or_path()`
3. Architecture: `WorktreeLookupResult` (path + needs_checkout flag), discriminated union pattern
4. When `needs_checkout=True`, activation script includes `git checkout <expected-branch>` command
5. Related: PR #8651 fixed same issue for root worktree; #8693 generalizes to non-root worktrees
- **Source:** `src/erk/cli/commands/navigation_helpers.py` lines 616-662, 501-603
- Add tripwire: "Always use find_worktree_for_branch_or_path() for stack navigation, not find_worktree_for_branch() alone"
- **Verification:** Document accurately describes `WorktreeLookupResult` and two-stage lookup in navigation_helpers.py

### Step 6: Document cmux workspace rename _(from #8704)_

**File:** `docs/learned/integrations/cmux-integration.md` (new or update existing)

**Content outline:**
1. `/local:cmux-workspace-rename` command: renames current CMUX workspace to match git branch name
2. Relationship to TUI `cmux_sync` command (launch key `m`)
3. When to use each: rename is standalone CLI, sync is TUI-integrated
- **Source:** `.claude/commands/local/cmux-workspace-rename.md`
- **Verification:** Command file exists and matches documentation

### Step 7: Update type naming documentation _(from #8679)_

**File:** `docs/learned/planning/planned-pr-lifecycle.md` or conventions doc

- Document consolidated type names: `IssueNextSteps` + `PlannedPRNextSteps` → `PlanNextSteps`
- Document: `IssueNumberEvent` → `PlanNumberEvent`
- Note: `format_planned_pr_next_steps_plain()` → `format_plan_next_steps_plain()` (no `branch_name` parameter)
- Historical references to "issue-based" in docs are intentional for migration context
- **Source:** `packages/erk-shared/src/erk_shared/output/next_steps.py`
- **Verification:** No references to old names exist in active code

### Step 8: Update objectives documentation _(from #8663)_

**File:** `docs/learned/objectives/` (existing docs)

- Document roadmap-free objectives: objectives can exist without an `objective-roadmap` metadata block
- Three-case distinction: (1) no block → valid roadmap-free, (2) block parses → normal, (3) block fails → legacy error
- `validate_objective()` skips roadmap checks 3-7 when no block present
- Display: "none (objective has no roadmap)" in check, "No roadmap data found" in view
- **Source:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` lines 467-481
- **Verification:** `erk objective check` passes for objectives without roadmap block

### Step 9: Update tripwires index _(all plans)_

**File:** `docs/learned/` (various tripwires.md files)

- Add new tripwires from Steps 3-5 to relevant category tripwires files
- Run `erk docs sync` to regenerate tripwires-index.md
- **Verification:** `erk docs sync` completes without errors

## Attribution

Items by source:
- **#8706**: Step 1
- **#8704**: Step 6
- **#8699**: Step 5
- **#8698**: Step 2
- **#8691**: Step 4
- **#8685**: Step 3
- **#8679**: Step 7
- **#8677**: No action needed (docs adequate)
- **#8672**: No action needed (docs adequate)
- **#8669**: Step 3 (merged with #8650)
- **#8663**: Step 8
- **#8650**: Step 3 (merged with #8669)
- **#8649**: No action needed (trivial change)
- **#8647**: No action needed (docs adequate)
- **#8645**: No action needed (docs adequate)

## Verification

After implementation:
1. All modified docs should have accurate file paths and line numbers matching current codebase
2. Run `erk docs sync` to verify index and tripwires are consistent
3. Grep for stale references: `IssueNextSteps`, `IssueNumberEvent`, `PlannedPRNextSteps` should have zero hits in active code
4. Verify activation-scripts.md no longer claims uv sync is inside the guard
