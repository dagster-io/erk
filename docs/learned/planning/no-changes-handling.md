---
title: No-Code-Changes Handling
read_when:
  - "plan implementation produces no code changes"
  - "understanding the no-changes label"
  - "debugging why a plan PR has no changes"
  - "resolving duplicate plan scenarios"
---

# No-Code-Changes Handling

When the erk-impl workflow detects that a plan implementation resulted in zero code changes, it handles this gracefully by creating diagnostics and notifying the user rather than failing the workflow.

## When This Occurs

**Duplicate Plans**

The same work was already implemented by another plan or manual commit. This commonly happens when multiple agents work on related issues simultaneously or when an implementation addresses a problem that was already solved.

**Refactoring-Only Implementations**

Changes were structural (file reorganization, renaming) without net code differences. The git diff shows no new code added or removed.

**Already-Merged Work**

The target branch (usually `master`) already contains the intended changes, either from a previous plan or external contribution.

## How the Workflow Responds

### Detection Phase

After implementation completes, the workflow analyzes the commit tree:

1. Compares the implementation branch against the base branch (master)
2. Checks for actual code changes (not just metadata or formatting)
3. Analyzes recent commits to identify potentially duplicate work

### Response Flow

When zero changes are detected:

```
┌─────────────────────┐
│  Detect No Changes  │
└──────────┬──────────┘
           │
           ├─→ Create/update PR with diagnostics
           │
           ├─→ Apply no-changes label (orange)
           │
           ├─→ Post notification to plan issue
           │
           └─→ Exit gracefully (code 1)
```

**Diagnostic PR Creation**

- PR body includes timestamp and detection reason
- Lists recent commits that may represent the duplicate work
- Provides links to the originating plan issue
- Includes user guidance for verification

**Label Application**

The `no-changes` label (orange, #FFA500) marks the PR for easy filtering in the UI. Marks PRs that don't contain code changes.

**Issue Notification**

A comment is posted to the originating plan issue linking to the diagnostic PR and explaining the no-changes scenario.

**Graceful Exit**

The workflow exits with code 1 (distinct from blocking errors which use code 2). This prevents cascading failures while preserving the workflow state for user review.

### Step Gating

Subsequent workflow steps are conditional on detecting actual changes:

```yaml
- name: Submit implementation
  if: steps.handle_outcome.outputs.has_changes == 'true'
  run: erk pr submit ...

- name: Trigger learn workflow
  if: steps.handle_outcome.outputs.has_changes == 'true'
  run: ...
```

Steps like `submit`, `mark-ready`, `CI`, and `learn` only execute when `has_changes` is true.

## The `no-changes` Label

| Property     | Value                                   |
| ------------ | --------------------------------------- |
| Label Name   | `no-changes`                            |
| Color        | Orange (#FFA500)                        |
| Meaning      | Implementation produced no code changes |
| Applied By   | `erk exec handle-no-changes` command    |
| User Visible | Yes - appears in PR labels list         |
| Searchable   | Yes - can filter PRs by label           |

## Duplicate Plan Detection

The workflow uses heuristic analysis to identify likely duplicate implementations.

### Detection Logic

1. **Branch commit analysis**: Compares commits on the implementation branch vs. master
2. **Recent commits search**: Looks for commits in the past 7 days that may address the same problem
3. **Scope matching**: Identifies commits with similar scope to the plan's goals

### When Detection Triggers

The no-changes scenario is triggered when:

- Implementation branch has zero net changes after rebase against master
- The plan's intended changes already exist in the target branch
- Another plan or manual commit implemented equivalent changes

### Diagnostic Information Provided

The diagnostic PR includes:

- **Timestamp**: When detection occurred
- **Plan link**: Link to the originating plan issue
- **Recent commits**: Summary of commits that may represent duplicate work
- **Branch info**: Which commits are on current branch vs. master
- **User guidance**: Instructions for verifying and resolving

## User Workflow

### When You See No-Changes

1. **Review the diagnostic PR**: Examine the recent commits listed
2. **Verify the duplicate**: Check if the work was already completed
3. **Decide next steps**:
   - If duplicate confirmed: Close the plan issue as completed
   - If not duplicate: Investigate why implementation produced no changes (may indicate a tool issue)
4. **Cleanup**: Close the diagnostic PR once resolved

### Resolving Duplicate Plans

To confirm a duplicate:

1. Check the commit messages listed in the diagnostic PR
2. Review the changes in those commits against your plan's goals
3. If goals are fully addressed, the plan's work is complete
4. Close the plan issue with a comment linking to the resolving commit(s)

### If Not Actually a Duplicate

If the recent commits don't explain the no-changes detection:

1. Verify the implementation branch was created correctly
2. Check that the `.impl/` folder contains expected changes
3. File an issue if the detection seems incorrect
4. The workflow can be retried with fixes

## Exit Code Semantics

The `handle-no-changes` command uses exit codes to distinguish scenarios:

| Exit Code | Meaning                                    |
| --------- | ------------------------------------------ |
| 0         | Successfully handled no-changes scenario   |
| 1         | Error during handling (API failures, etc.) |

The workflow itself uses different semantics:

| Exit Code | Meaning                                    |
| --------- | ------------------------------------------ |
| 0         | Implementation succeeded with code changes |
| 1         | No code changes detected (graceful)        |
| 2         | Blocking error (workflow failed)           |

## Exec Command Reference

See [erk exec handle-no-changes](../cli/erk-exec-commands.md) for detailed command documentation.

## Related Topics

- [Plan Lifecycle - Phase 4](lifecycle.md) — Understand implementation phases
- [erk exec Commands](../cli/erk-exec-commands.md) — Handle-no-changes command reference
- [Exec Command Patterns](../cli/exec-command-patterns.md) — Diagnostic messaging patterns
