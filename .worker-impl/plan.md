# Plan: Consolidated Documentation Updates from 11 Learn Plans

> **Consolidates:** #7127, #7120, #7117, #7116, #7112, #7110, #7109, #7102, #7097, #7092, #7091

## Context

All 11 source implementations are fully merged to master. The remaining work is purely documentation: fixing stale references, creating missing docs, adding tripwires, and updating existing documents to reflect recent architectural changes.

## Source Plans

| #     | Title                                                    | Items Merged |
| ----- | -------------------------------------------------------- | ------------ |
| #7127 | Rich tables for objective view                           | 7 items      |
| #7120 | Address PR #7095 review comments (roadmap to erk_shared) | 17 items     |
| #7117 | Progress logging for docs sync                           | 6 items      |
| #7116 | last_audited format enforcement                          | 2 items      |
| #7112 | Workflow models to Opus                                  | 5 items      |
| #7110 | Objective v2 format                                      | 15 items     |
| #7109 | Author filtering in TUI                                  | 12 items     |
| #7102 | pr-address remote fix (context fork)                     | 11 items     |
| #7097 | View switching in TUI                                    | 4 items      |
| #7092 | Stub PR body with workflow run link                      | 4 items      |
| #7091 | Objective roadmap planning status                        | 14 items     |

## Investigation Findings

### Corrections to Original Plans

- **#7120**: Module paths moved from `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py` to `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`. 13+ docs still reference old path.
- **#7117**: Plan said `on_progress: Callable[[str], None] | None` (optional) but actual implementation is `on_progress: Callable[[str], None]` (required). No guard needed.
- **#7116**: `frontmatter-tripwire-format.md:39` still says "Free-form date string" despite validation enforcing `YYYY-MM-DD HH:MM PT`.
- **#7110**: Objective v2 format complete but only ~20% of docs created.
- **#7102**: `pr-preview-address.md` still uses old skill invocation pattern (not updated to Task tool like `pr-address.md`).
- **#7091**: `roadmap-status-system.md` does NOT mention "planning" status despite code using it since PR #7058.

### Overlap Analysis

- **Roadmap documentation** overlaps across #7120, #7110, #7091 (shared parser, dual storage, status system)
- **TUI documentation** overlaps across #7109, #7097 (author column + view switching)
- **Tripwire additions** span multiple plans (#7112, #7102, #7109, #7110, #7091)

## Implementation Steps

### Step 1: Fix stale `objective_roadmap_shared.py` references _(from #7120)_

**Files to update** (change old path to `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`):

1. `docs/learned/objectives/roadmap-parser.md` - Lines 28, 114
2. `docs/learned/objectives/roadmap-parser-api.md` - Lines 4, 24, 26, 49, 69, 71
3. `docs/learned/objectives/roadmap-mutation-patterns.md` - Line 45

**Also update** `docs/learned/architecture/erk-shared-package.md` (lines 19-29) to add `erk_shared.gateway.github.metadata.roadmap` and `erk_shared.core.frontmatter` to the package structure listing.

**Verification**: `grep -r "objective_roadmap_shared\|objective_roadmap_frontmatter" docs/learned/` returns zero results.

### Step 2: Fix outdated `last_audited` description _(from #7116)_

**File**: `docs/learned/documentation/frontmatter-tripwire-format.md`
- Line 39: Change `| Free-form date string |` to `| \`YYYY-MM-DD HH:MM PT\` format (validated by regex in \`operations.py:30\`) |`

**Verification**: Read line 39 and confirm it matches the `LAST_AUDITED_PATTERN` regex.

### Step 3: Add "planning" status to roadmap documentation _(from #7091, #7110)_

**File**: `docs/learned/objectives/roadmap-status-system.md`
- Add "planning" to the status values table
- Document transition: pending -> planning (when draft PR created) -> in_progress -> done
- Reference `next_plan_cmd.py:84,103` and `check_cmd.py:137,147`

**File**: `docs/learned/objectives/objective-lifecycle.md`
- Add "planning" state to the step lifecycle section
- Document the planning -> in_progress transition path

**Verification**: `grep "planning" docs/learned/objectives/roadmap-status-system.md` returns matches.

### Step 4: Add author field to TUI data contract _(from #7109)_

**File**: `docs/learned/tui/data-contract.md`
- Add `author: str` to the PlanRowData field reference table
- Note: sourced from `issue.author` via GitHub API, never nullable
- Reference: `src/erk/tui/data/types.py:100`

**Verification**: `grep "author" docs/learned/tui/data-contract.md` returns the field entry.

### Step 5: Merge documentation from unmerged branches _(from #7127, #7117)_

**PR #7128** (branch `P7127-erk-learn-fix-alignment-i-02-16-0208`):
- Contains updates to `docs/learned/cli/output-styling.md` (+87 lines: Rich tables, cell_len(), click.style() migration)
- Contains updates to `docs/learned/cli/tripwires.md` (emoji width tripwire)
- Contains updates to `docs/learned/cli/objective-commands.md` (view_objective() docs)
- **Action**: Cherry-pick or recreate these documentation additions on a new branch

**Branch `P7117`** (commit `5717f014a`):
- Contains `docs/learned/architecture/callback-progress-pattern.md` (NEW)
- Contains updates to progress-related docs
- **Action**: Cherry-pick or recreate on a new branch
- **Note**: Callback parameter is required (not optional). No `if on_progress is not None:` guard needed.

**Verification**: Files exist on master after merge.

### Step 6: Create workflow model policy doc _(from #7112)_

**Create**: `docs/learned/ci/workflow-model-policy.md`
- Document Opus standardization policy (all 6 workflows now use `claude-opus-4-6`)
- List affected workflows: ci.yml, learn.yml, one-shot.yml, plan-implement.yml, pr-address.yml, pr-fix-conflicts.yml
- Note: review models in `.erk/reviews/` are NOT standardized (intentionally use cost-optimized models)
- Document dual-default pattern in plan-implement.yml (workflow_dispatch + workflow_call)
- Add tripwire entry to `docs/learned/ci/tripwires.md` frontmatter

**Verification**: File exists; `grep "claude-opus-4-6" docs/learned/ci/workflow-model-policy.md` returns matches.

### Step 7: Create TUI view switching doc _(from #7097)_

**Create**: `docs/learned/tui/view-switching.md`
- Document ViewMode enum, ViewConfig dataclass, VIEW_CONFIGS tuple
- Document two-tier filtering: API labels for broad partitioning + client-side `is_learn_plan` for fine filtering
- Note GitHub GraphQL limitation: no negative label filtering
- Document cache strategy: cache by label tuple for instant same-label view switching
- Document reconfigure pattern: `PlanDataTable.reconfigure()` preserves widget state
- Document ViewBar naming: uses `_refresh_display()` not `_render()` (Textual LSP conflict)
- Reference: `src/erk/tui/views/types.py`, `src/erk/tui/app.py:340-390`, `tests/tui/test_app.py:1629-1788`

**Verification**: File exists with ViewMode, ViewConfig, and cache documentation.

### Step 8: Create objective v2 storage format doc _(from #7110)_

**Create**: `docs/learned/objectives/objective-storage-format.md`
- Document v2 format: metadata body (objective-header + objective-roadmap) + content comment (objective-body)
- Document 7-step creation flow in `create_objective_issue()` (`plan_issues.py:308-398`)
- Document metadata block naming convention: prefix matches entity type (plan-*, objective-*)
- Reference: `erk_shared/gateway/github/metadata/core.py`, `erk_shared/gateway/github/plan_issues.py`

**Verification**: File exists with v2 format description.

### Step 9: Create context fork execution modes doc _(from #7102)_

**Create**: `docs/learned/architecture/claude-cli-execution-modes.md`
- Document `context: fork` behavioral difference: interactive (isolation works) vs `--print` (loads inline, breaks isolation)
- Document Task tool as guaranteed isolation in all modes
- Document multi-phase workflow vulnerability: terminal instructions contaminate parent context
- Reference: `.claude/commands/erk/pr-address.md` (updated implementation)
- Note: `pr-preview-address.md` still uses old skill invocation pattern (should be updated separately)

**Also update**: `docs/learned/claude-code/context-fork-feature.md`
- Remove phantom references to non-existent commands at lines 89, 92

**Verification**: File exists; `grep "context: fork" docs/learned/architecture/claude-cli-execution-modes.md` returns matches.

### Step 10: Create stub PR workflow link doc _(from #7092)_

**Create**: `docs/learned/pr-operations/stub-pr-workflow-link.md`
- Document three-tier PR body lifecycle: stub creation -> workflow link -> AI summary
- Document implementation in `one_shot_dispatch.py:236-247` and `submit.py:785-792`
- Document best-effort pattern: try/except with `logger.warning()`, not silent pass
- Document `construct_workflow_run_url()` helper from `erk_shared.gateway.github.parsing`
- Document FakeGitHub assertion pattern: `github.updated_pr_bodies` tuple unpacking

**Also update**: `docs/learned/pr-operations/pr-submit-phases.md`
- Add workflow link step to Phase 6 documentation

**Verification**: File exists with lifecycle description.

### Step 11: Create creator filter preservation tripwire _(from #7109)_

**Update**: `docs/learned/tui/tripwires.md` (auto-generated from frontmatter)
- Add tripwire to source files' frontmatter: "constructing PlanFilters without copying all fields from existing filters" -> "All fields must be explicitly copied in _load_data() PlanFilters construction. Missing fields cause silent failures."
- Reference: `src/erk/tui/app.py:166-174` (the bug fix)

**Verification**: `grep "PlanFilters" docs/learned/tui/tripwires.md` returns the tripwire.

### Step 12: Create validation patterns doc _(from #7116)_

**Create**: `docs/learned/architecture/validation-patterns.md`
- Document module-level regex compilation pattern (compile once, name the constant)
- Use `LAST_AUDITED_PATTERN` as canonical example (`operations.py:30`)
- Document error message pattern: show both expected format AND actual value
- Add tripwire: "adding regex validation inline" -> "Compile at module level as named constants"

**Verification**: File exists with LAST_AUDITED_PATTERN reference.

### Step 13: Add remaining tripwires _(from #7112, #7102, #7110)_

**Tripwires to add** (via frontmatter updates to source docs):

1. **CI tripwire** (from #7112): "Creating workflows that invoke Claude without specifying model" -> "All workflows MUST default to claude-opus-4-6"
2. **Commands tripwire** (from #7102): "Writing multi-phase commands without testing in --print mode" -> "Test in both interactive and --print modes"
3. **Objectives tripwire** (from #7110): "Updating roadmap step in only one location (frontmatter or table)" -> "Must update both frontmatter AND markdown table"
4. **Objectives tripwire** (from #7091): "Using None/empty string interchangeably in update parameters" -> "None=preserve, empty=clear, value=set"

**Verification**: Run `erk docs sync` and verify tripwire counts increased.

### Step 14: Update remaining existing docs _(from #7120, #7092, #7109)_

1. **`docs/learned/architecture/erk-architecture.md`**: Add best-effort operation example (try/except with logging, from #7092)
2. **`docs/learned/testing/fake-github-testing.md`**: Add PR body update assertion pattern section (`updated_pr_bodies` tuple, from #7092)
3. **`docs/learned/tui/column-addition-pattern.md`**: Add cross-reference to author column as worked example (from #7109)
4. **`docs/learned/ci/github-actions-claude-integration.md`**: Update Model Selection section (line 37) to reference workflow-model-policy.md (from #7112)

**Verification**: Grep for added content in each file.

## Attribution

Items by source:
- **#7127**: Step 5 (merge doc branch)
- **#7120**: Steps 1, 5 (stale refs, erk-shared-package.md)
- **#7117**: Step 5 (merge doc branch)
- **#7116**: Steps 2, 12 (last_audited fix, validation-patterns.md)
- **#7112**: Steps 6, 13 (workflow-model-policy.md, CI tripwire)
- **#7110**: Steps 3, 8, 13 (planning status, objective-storage-format.md, dual-update tripwire)
- **#7109**: Steps 4, 11, 14 (author field, creator filter tripwire, column-addition cross-ref)
- **#7102**: Steps 9, 13 (execution-modes.md, multi-phase tripwire)
- **#7097**: Step 7 (view-switching.md)
- **#7092**: Steps 10, 14 (stub-pr-workflow-link.md, best-effort pattern)
- **#7091**: Steps 3, 13 (planning status, preservation semantics tripwire)

## Verification

After all steps complete:
1. Run `erk docs sync` to regenerate indexes and tripwires
2. Run `erk docs check` to validate all frontmatter
3. `grep -r "objective_roadmap_shared" docs/learned/` returns zero results
4. `grep -r "Free-form date string" docs/learned/` returns zero results
5. New docs exist: workflow-model-policy.md, view-switching.md, objective-storage-format.md, claude-cli-execution-modes.md, stub-pr-workflow-link.md, validation-patterns.md, callback-progress-pattern.md