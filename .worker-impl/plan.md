# Plan: Consolidated Documentation for Learn Workflows

> **Consolidates:** #6080, #6070, #6069, #6068, #6060, #6057

## Source Plans

| # | Title | Items Merged |
| --- | --- | --- |
| 6080 | [erk-learn] Remove ai-generated label mentions | 2 items (cleanup references) |
| 6070 | [erk-learn] Workflow Refactor - Consolidation and Consistency | 5 items (composite action docs) |
| 6069 | [erk-learn] Rename workflow run to workflow launch | 6 items (workflow commands docs) |
| 6068 | [erk-learn] CLI API Alignment - Positional Arguments | 8 items (click patterns docs) |
| 6060 | [erk-learn] Fix erk br delete Not Force-Deleting | 3 items (BranchManager docs) |
| 6057 | [erk-learn] Fix erk br delete (duplicate of #6060) | 0 items (merged with #6060) |

## What Changed Since Original Plans

- Composite action `erk-remote-setup` fully implemented (commit eec5bfb1)
- `erk workflow launch` command fully implemented (commit 85b89496)
- `erk objective reconcile` command uses positional argument (already updated)
- BranchManager and FakeBranchManager fully implemented with force flag tracking
- Documentation exists on unmerged branch `origin/P6057-erk-learn-learn-plan-fix-01-26-0133` for #6057

## Investigation Findings

### Corrections to Original Plans

- **#6080**: Only 2 references remain to remove (not a pattern, just cleanup)
- **#6070**: Implementation complete, only docs missing
- **#6069**: Old commands removed from source, BUT TUI still references old syntax
- **#6068**: objective-commands.md already updated; only workflow bash syntax outdated
- **#6060/#6057**: Documentation was created but not merged to master

### Additional Details Discovered

- 7 composite actions exist in `.github/actions/`
- TUI references orphaned commands: `erk pr fix-conflicts-remote`, `erk pr address-remote`
- Test files exist for removed commands (orphaned)
- Three BranchManager tripwires already exist in tripwires.md

### Overlap Analysis

| Topic | Plans Involved | Resolution |
| --- | --- | --- |
| Workflow documentation | #6070, #6069 | Merge into single workflow-commands.md |
| Click patterns | #6068 | Create dedicated click-optional-arguments.md |
| BranchManager docs | #6060, #6057 | Merge PR branch or recreate docs |
| Cleanup tasks | #6080, TUI references | Simple file edits |

## Remaining Gaps

### Documentation to Create

1. **docs/learned/cli/workflow-commands.md** - Document `erk workflow launch` command _(from #6069, #6070)_
2. **docs/learned/ci/composite-action-patterns.md** - Document erk-remote-setup _(from #6070)_
3. **docs/learned/cli/click-optional-arguments.md** - Document Click positional argument patterns _(from #6068)_

### Documentation to Update

4. **docs/learned/ci/objective-reconciler-workflow.md** - Fix bash syntax: `${OBJECTIVE:+--objective $OBJECTIVE}` → `${OBJECTIVE}` _(from #6068)_

### Code Cleanup

5. **Remove ai-generated label references** _(from #6080)_:
   - `.claude/commands/erk/plan-implement.md:277`
   - `.claude/skills/fake-driven-testing/references/quick-reference.md:283`

### BranchManager Documentation (RESOLVED)

6. **BranchManager documentation** _(from #6060, #6057)_:
   - LANDED SEPARATELY by user - no action needed
   - `docs/learned/architecture/branch-manager-abstraction.md` and `docs/learned/testing/frozen-dataclass-test-doubles.md` now in master

### TUI Cleanup (discovered during investigation)

7. **Update TUI command references** - Update old command syntax to new:
   - `src/erk/tui/app.py` - Update `erk pr fix-conflicts-remote` → `erk workflow launch pr-fix-conflicts`
   - `src/erk/tui/screens/plan_detail_screen.py` - Update command references
   - `src/erk/tui/commands/registry.py` - Update command registry entries

## Implementation Steps

### Step 1: Create docs/learned/cli/workflow-commands.md _(from #6069, #6070)_

```markdown
---
title: Workflow Commands
read_when:
  - "triggering GitHub Actions workflows from CLI"
  - "using erk workflow launch"
  - "understanding WORKFLOW_COMMAND_MAP"
---

# Workflow Commands

## erk workflow launch

Unified interface for triggering GitHub Actions workflows.

### Available Workflows

| Subcommand | Workflow File | Description |
| --- | --- | --- |
| `pr-address` | `pr-address.yml` | Address PR review comments remotely |
| `pr-fix-conflicts` | `erk-rebase.yml` | Fix merge conflicts via rebase |
| `objective-reconcile` | `objective-reconcile.yml` | Reconcile objective after PR lands |
| `learn` | `learn-dispatch.yml` | Extract documentation from plan |

### Usage Examples

...
```

### Step 2: Create docs/learned/ci/composite-action-patterns.md _(from #6070)_

Document the 7 composite actions in `.github/actions/`, focusing on `erk-remote-setup`.

### Step 3: Create docs/learned/cli/click-optional-arguments.md _(from #6068)_

Document `@click.argument(required=False)` pattern with examples from reconcile_cmd.py.

### Step 4: Update objective-reconciler-workflow.md _(from #6068)_

Fix lines 106-110:
```bash
# OLD (incorrect)
erk objective reconcile ${DRY_RUN:+--dry-run} ${OBJECTIVE:+--objective $OBJECTIVE}

# NEW (correct)
erk objective reconcile ${DRY_RUN:+--dry-run} ${OBJECTIVE:+$OBJECTIVE}
```

### Step 5: Remove ai-generated label references _(from #6080)_

Edit 2 files to remove the non-existent label references.

### Step 6: BranchManager documentation _(from #6060, #6057)_ - ALREADY DONE

BranchManager docs landed separately - no action needed in this plan.

### Step 7: Update TUI command references _(discovered during investigation)_

Update TUI files to use new `erk workflow launch` syntax instead of removed commands.

## Attribution

Items by source:
- **#6080**: Step 5
- **#6070**: Steps 1, 2
- **#6069**: Steps 1, 7
- **#6068**: Steps 3, 4
- **#6060, #6057**: Already landed separately (no action in this plan)

## Verification

1. Run `make format` and `make lint` after all changes
2. Verify new docs appear in docs/learned/index.md (or add entries)
3. Check that tripwires in tripwires.md point to valid docs
4. Run `erk workflow launch --help` to confirm command works
5. Run `erk objective reconcile --help` to confirm positional argument documented