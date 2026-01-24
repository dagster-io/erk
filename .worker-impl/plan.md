# Consolidated Plan: erk-learn Documentation Plans (Replan)

> **Consolidates:** #5865, #5864, #5859, #5855, #5849

## Source Plans

| #     | Title                                                | Status               | Items Merged |
| ----- | ---------------------------------------------------- | -------------------- | ------------ |
| 5865  | Phase 2B - Tripwire Candidate Detection              | Partially Implemented | 2 items      |
| 5864  | Consolidated Plan: erk-learn Documentation Plans     | COMPLETED (PR #5861)  | 0 items      |
| 5855  | Add pr-address-remote command                        | FULLY IMPLEMENTED     | 0 items      |
| 5859  | TUI Command Palette for Remote PR Addressing         | Substantially Impl    | 3 items      |
| 5849  | Improve Claude CLI Error Reporting in execute_prompt | Mostly Implemented    | 4 items      |

## What Changed Since Original Plans

PR #5861 (merged January 24, 2026) implemented the majority of documentation from these plans:
- Created `docs/learned/architecture/claude-cli-error-reporting.md`
- Created `docs/learned/claude-code/agent-commands.md`
- Updated `docs/learned/architecture/command-boundaries.md` with hybrid patterns
- Added tripwires for Claude CLI error reporting and agent commands
- Updated `docs/learned/tui/adding-commands.md` with remote workflow patterns

Commit `d4b4ea7c` added tripwire-worthiness scoring criteria to learn workflow.

## Investigation Findings

### Corrections to Original Plans

- **#5864**: Commit message claimed `docs/learned/claude-code/index.md` would be created, but it was NOT. The file is missing.
- **#5855**: ALL items fully implemented - no corrections needed
- **#5859**: Remote workflow pattern template mentioned but only specific implementation documented, not generalizable template
- **#5849**: RealPromptExecutor vs RealClaudeExecutor distinction was never clarified in docs

### Additional Details Discovered

- Two separate executor implementations exist with different error handling:
  - `RealClaudeExecutor` at `src/erk/core/claude_executor.py:49` - Full streaming with stderr thread
  - `RealPromptExecutor` at `packages/erk-shared/src/erk_shared/prompt_executor/real.py:15` - Lightweight with retry
- Plan metadata dispatch helper `_maybe_update_plan_dispatch_metadata()` is inline in address_remote_cmd.py, not extracted
- The `docs/learned/claude-code/` directory exists but lacks an index.md (other directories have auto-generated indexes)

### Overlap Analysis

- #5864 was a consolidation plan that said it was complete - but investigation found the missing index.md
- #5859 and #5855 have significant overlap on pr-address-remote documentation - both largely implemented
- #5849 overlaps with #5864 on Claude CLI error reporting - mostly complete

## Remaining Gaps

After investigation, these items from the original plans still need implementation:

### HIGH Priority

1. **Missing `docs/learned/claude-code/index.md`** _(from #5864)_
   - Auto-generated index file that lists documents in claude-code directory
   - Fix: Run `erk docs sync` to generate

### MEDIUM Priority

2. **RealPromptExecutor vs RealClaudeExecutor Comparison** _(from #5849)_
   - Document differences between the two executor implementations
   - Location: `docs/learned/architecture/claude-executor-patterns.md` (UPDATE)
   - Content: When to use each, error handling differences, scope

3. **Subprocess Error Accumulation Pattern** _(from #5849)_
   - Document stderr background thread pattern in RealClaudeExecutor
   - Location: `docs/learned/architecture/subprocess-wrappers.md` (UPDATE) or new file
   - Content: Why stderr needs thread, how parts are accumulated

4. **Plan Metadata Dispatch Helpers Extraction** _(from #5859)_
   - Extract `_maybe_update_plan_dispatch_metadata()` to reusable module
   - Location: `src/erk/cli/commands/pr/metadata_helpers.py` (CREATE)
   - Content: Reusable dispatch metadata update logic

### LOW Priority

5. **Remote Workflow Command Pattern Template** _(from #5859)_
   - Generalizable template for creating remote workflow commands
   - Location: `docs/learned/erk/remote-workflow-template.md` (CREATE)
   - Content: Step-by-step template based on address_remote pattern

6. **Subprocess Mocking Test Patterns** _(from #5849)_
   - Document testing patterns for subprocess-heavy code
   - Location: `docs/learned/testing/subprocess-testing.md` (CREATE)
   - Content: How to test code with subprocess calls using fakes

## Implementation Steps

1. Run `erk docs sync` to generate missing `docs/learned/claude-code/index.md` _(from #5864)_

2. Update `docs/learned/architecture/claude-executor-patterns.md` _(from #5849)_
   - Add "Executor Comparison" section
   - Table comparing RealClaudeExecutor vs RealPromptExecutor
   - When to use each implementation

3. Update `docs/learned/architecture/subprocess-wrappers.md` _(from #5849)_
   - Add "Error Accumulation Pattern" section
   - Document stderr background thread pattern
   - Reference implementation in claude_executor.py

4. Create `src/erk/cli/commands/pr/metadata_helpers.py` _(from #5859)_
   - Extract `_maybe_update_plan_dispatch_metadata()` from address_remote_cmd.py
   - Make reusable for fix_conflicts_remote and future commands

5. Create `docs/learned/erk/remote-workflow-template.md` _(from #5859)_
   - Document generalizable pattern from address_remote implementation
   - Include CLI command, workflow dispatch, metadata tracking steps

6. Create `docs/learned/testing/subprocess-testing.md` _(from #5849)_
   - Document testing patterns for subprocess-heavy code
   - Reference FakeClaudeExecutor as example

## Attribution

Items by source:
- **#5864**: Step 1
- **#5849**: Steps 2, 3, 6
- **#5859**: Steps 4, 5

## Verification

After implementation:
1. Run `erk docs sync` - should not create additional files
2. Verify `docs/learned/claude-code/index.md` exists and lists agent-commands.md
3. Run `make fast-ci` to ensure documentation passes linting
4. Verify tripwires.md is regenerated correctly