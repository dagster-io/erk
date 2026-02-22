# Plan: Consolidated Documentation for erk-learn PRs #5688 and #5679

> **Consolidates:** #5689, #5687

## Source Plans

| #    | Title                                                              | Items Merged |
| ---- | ------------------------------------------------------------------ | ------------ |
| 5689 | Documentation Plan: Handle "No Code Changes" Gracefully            | 8 items      |
| 5687 | Documentation Plan: Detect and Reuse Existing Local Branches       | 5 items      |

## What Changed Since Original Plans

- Both PRs have been merged to master
- All implementation code and tests exist
- No documentation items have been created yet
- Both plans propose updates to the same files (`lifecycle.md`, `tripwires.md`, `testing.md`)

## Investigation Findings

### Verification: All Implementation Code Exists

**No-Changes Handling (PR #5688):**
- `src/erk/cli/commands/exec/scripts/handle_no_changes.py` (237 lines)
- `tests/unit/cli/commands/exec/scripts/test_handle_no_changes.py` (440 lines)
- `.github/workflows/erk-impl.yml` has `has_changes` gating (lines 257-296)

**Branch Reuse Detection (PR #5679):**
- `src/erk/cli/commands/submit.py` - `_find_existing_branches_for_issue()`, `_prompt_existing_branch_action()`
- `tests/commands/submit/test_existing_branch_detection.py` (8 tests)
- `FakeConsole` with `confirm_responses` parameter in `packages/erk-shared/src/erk_shared/gateway/console/fake.py`

### Overlap Analysis

Both plans propose updates to:
1. `docs/learned/planning/lifecycle.md` - Phase 2 (branch reuse) and Phase 4 (no-changes)
2. `docs/learned/tripwires.md` - Different tripwires, can be combined
3. `docs/learned/testing/testing.md` - FakeConsole section needed

## Remaining Documentation Gaps

All 13 documentation items need to be created.

## Implementation Steps

### Step 1: Create `docs/learned/planning/submit-branch-reuse.md` _(from #5687)_

New file documenting the branch reuse feature in `erk plan submit`. Include:
- Problem statement (duplicate branches on resubmission)
- User workflow with three decision paths
- Detection and selection logic (`_find_existing_branches_for_issue`)
- Graphite integration (LBYL pattern for tracking)
- Why detection happens before computing new name

**Frontmatter:**
```yaml
---
title: Branch Reuse in Plan Submit
read_when:
  - "implementing erk plan submit"
  - "handling duplicate branches"
  - "resubmitting a plan issue"
---
```

### Step 2: Create `docs/learned/planning/no-changes-handling.md` _(from #5689)_

New file documenting graceful handling of no-code-changes scenarios. Include:
- When this occurs (duplicate plans, already-merged work)
- Workflow response (detection, diagnostic PR, label, issue comment, graceful exit)
- Label definition (`no-changes`)
- User resolution steps

**Frontmatter:**
```yaml
---
title: No Code Changes Handling
read_when:
  - "implementing erk-impl workflow"
  - "debugging no-changes scenarios"
  - "understanding erk-impl error handling"
---
```

### Step 3: Update `docs/learned/planning/lifecycle.md` _(from #5687, #5689)_

**Phase 2 addition** (after Branch Creation subsection):
Add "Branch Reuse Detection" subsection explaining the detection flow and user prompts.

**Phase 4 addition** (new subsection):
Add "No-Changes Error Scenario" subsection covering exit code semantics and graceful degradation pattern.

### Step 4: Create `docs/learned/cli/exec-command-patterns.md` _(from #5689)_

New file establishing patterns for diagnostic messaging in exec scripts. Include:
- Pattern for diagnostic PR body generation (`_build_pr_body`)
- Pattern for issue notification comments (`_build_issue_comment`)
- Key principles (structured templates, actionable guidance, cross-linking)

**Frontmatter:**
```yaml
---
title: Exec Command Patterns
read_when:
  - "writing exec scripts with PR/issue output"
  - "building diagnostic messages"
  - "standardizing exec command output"
---
```

### Step 5: Update `docs/learned/cli/erk-exec-commands.md` _(from #5689)_

Add entry for `handle-no-changes` command in the PR Operations category:
- Purpose: Handle zero-change implementation outcomes
- Usage: Called by erk-impl workflow when no code changes detected
- Exit codes: 0 (success), 1 (GitHub API failure)

### Step 6: Update `docs/learned/testing/testing.md` _(from #5687)_

Add new section "FakeConsole for Interactive Prompts" covering:
- Constructor parameters (`is_interactive`, `confirm_responses`)
- Testing pattern for `ctx.console.confirm()` calls
- Example showing sequence of responses
- Reference to `test_existing_branch_detection.py` for examples

### Step 7: Update `docs/learned/erk/graphite-branch-setup.md` _(from #5687)_

Add section "Automatic Tracking on Branch Reuse" after "Typical Workflow":
- LBYL check pattern (`is_branch_tracked()` before `track_branch()`)
- When this occurs (reusing existing branch in submit)
- Code pattern example

### Step 8: Update `docs/learned/ci/erk-impl-customization.md` _(from #5689)_

Add section on `has_changes` step gating pattern:
- How the workflow uses step outputs to gate downstream steps
- YAML example of conditional step execution
- When to add gating to custom steps

### Step 9: Add tripwires to source docs _(from #5687, #5689)_

Add to appropriate source document frontmatter (NOT directly to tripwires.md):

**In `exec-command-patterns.md` frontmatter:**
```yaml
tripwires:
  - action: "writing PR/issue body generation in exec scripts"
    warning: "Use `_build_pr_body` and `_build_issue_comment` patterns from handle_no_changes.py for consistency and testability."
```

**In `testing/testing.md` frontmatter:**
```yaml
tripwires:
  - action: "implementing interactive prompts with ctx.console.confirm()"
    warning: "Ensure FakeConsole in test fixture is configured with `confirm_responses` parameter. See tests/commands/submit/test_existing_branch_detection.py for examples."
```

### Step 10: Run `erk docs sync` to regenerate indexes

This will update:
- `docs/learned/index.md`
- `docs/learned/tripwires.md`
- Category index files

## Verification

1. Run `make fast-ci` to validate:
   - YAML frontmatter syntax
   - Markdown formatting (prettier)
   - No broken links

2. Verify tripwires appear in `docs/learned/tripwires.md` after sync

3. Verify new docs appear in `docs/learned/index.md`

## Files to Modify

| File | Action |
|------|--------|
| `docs/learned/planning/submit-branch-reuse.md` | CREATE |
| `docs/learned/planning/no-changes-handling.md` | CREATE |
| `docs/learned/planning/lifecycle.md` | UPDATE |
| `docs/learned/cli/exec-command-patterns.md` | CREATE |
| `docs/learned/cli/erk-exec-commands.md` | UPDATE |
| `docs/learned/testing/testing.md` | UPDATE |
| `docs/learned/erk/graphite-branch-setup.md` | UPDATE |
| `docs/learned/ci/erk-impl-customization.md` | UPDATE |

## Related Documentation

**Skills to load:** `learned-docs` (for frontmatter patterns)

**Docs to reference:**
- `docs/learned/planning/lifecycle.md` - existing Phase 2 and Phase 4 content
- `docs/learned/testing/testing.md` - existing fake documentation patterns

## Attribution

| Step | Source Plans |
|------|--------------|
| 1 | #5687 |
| 2 | #5689 |
| 3 | #5687, #5689 |
| 4 | #5689 |
| 5 | #5689 |
| 6 | #5687 |
| 7 | #5687 |
| 8 | #5689 |
| 9 | #5687, #5689 |
| 10 | (both) |