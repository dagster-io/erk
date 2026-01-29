---
title: Plan File Sync Pattern
read_when:
  - editing PLAN-REVIEW files locally
  - syncing local plan changes to GitHub issues
  - working with plan feedback workflows
tripwires:
  - action: "Call plan-update-from-feedback after editing local plan files"
    warning: "Sync is NOT automatic — GitHub issue will show stale content without explicit sync"
    score: 4
---

# Plan File Sync Pattern

Local plan file edits must be explicitly synced back to GitHub issues. This pattern ensures that plan changes made in response to review feedback are propagated to the GitHub issue where reviewers can see them.

## The Problem

Plan review PRs work with local markdown files (e.g., `PLAN-REVIEW-6252.md`). When addressing feedback, agents edit these files locally. However:

- **GitHub issue shows original plan**: The issue body still contains the old plan content
- **Reviewers see stale content**: Without sync, reviewers don't see the updated plan
- **Manual sync required**: Sync is NOT automatic — you must explicitly call the sync command

## The Solution: Explicit Sync Command

After editing the local plan file, call `plan-update-from-feedback` to sync changes back to the GitHub issue:

```bash
erk exec plan-update-issue --issue-number {issue} --plan-path PLAN-REVIEW-{issue}.md
```

This updates the plan-body comment on the GitHub issue with the new content from the local file.

## Workflow Integration

This pattern is part of the **Plan Review Mode** in `/erk:pr-address`. After editing the plan, Phase 3 syncs the changes:

### Step 1: Edit Local Plan File

Make changes to the local plan file (e.g., `PLAN-REVIEW-6252.md`) in response to review feedback.

### Step 2: Commit Changes

```bash
git add PLAN-REVIEW-{issue}.md
git commit -m "Address feedback: ..."
git push
```

### Step 3: Sync Plan to GitHub Issue

```bash
erk exec plan-update-issue --issue-number {issue} --plan-path PLAN-REVIEW-{issue}.md
```

**Source:** `.claude/commands/erk/pr-address.md:319-322`

This three-step sequence ensures both the PR and the issue are updated.

## Implementation Details

### plan_update_from_feedback Command

The sync command performs these operations:

1. **Validate issue exists**: Check that the issue number is valid
2. **Validate erk-plan label**: Ensure the issue is a plan issue
3. **Extract plan_comment_id**: Get the comment ID from plan-header metadata
4. **Find matching comment**: Locate the comment on the issue
5. **Format content**: Wrap the plan content in plan-body markers
6. **Update comment**: Replace the old comment with new content

**Source:** `src/erk/cli/commands/exec/scripts/plan_update_from_feedback.py:58-127`

### Metadata Preservation: plan-body Markers

The sync command preserves metadata by wrapping content in `plan-body` markers:

```markdown
<!-- plan-body -->

# Plan: Title

## Implementation Steps

...

<!-- /plan-body -->
```

This allows the issue to contain both plan content and metadata without conflicts.

### Error Cases

The sync command validates several conditions and raises errors if:

- **Issue not found**: The issue number doesn't exist
- **Missing erk-plan label**: The issue isn't a plan issue
- **Missing plan_comment_id**: The issue metadata doesn't track a plan comment
- **Comment not found**: The tracked comment ID doesn't exist on the issue

These validations ensure the sync only happens when the issue is in a valid state.

## Why Sync is Not Automatic

Sync is explicit rather than automatic because:

1. **Control**: Agents decide when to sync (after completing edits, not mid-edit)
2. **Atomicity**: Sync happens as a single operation, not piecemeal
3. **Visibility**: Explicit sync makes the operation visible in command flow
4. **Error handling**: Agents can handle sync failures without silent corruption

Automatic sync (e.g., on every file save) would create race conditions and partial updates.

## When to Sync

Sync the plan file in these scenarios:

- **After addressing review feedback**: Made changes based on reviewer comments
- **After regenerating sections**: Updated plan based on codebase changes
- **After clarification**: Added missing details or context
- **Before resolving threads**: Reviewers need to see changes before threads can be resolved

## When NOT to Sync

Skip syncing in these scenarios:

- **Mid-edit**: Still making changes, not ready for reviewers to see
- **Temporary edits**: Experimenting with ideas, will revert
- **Local-only plans**: Plan file not backed by a GitHub issue (file-based plans)
- **Read-only operations**: Just reading the plan, not modifying it

## Consumer Pattern

The typical consumer pattern for plan file sync:

```python
# 1. Edit the plan file
edit_plan_file(plan_path, changes)

# 2. Commit changes
git_commit(f"Address feedback: {summary}")

# 3. Sync to GitHub issue
result = plan_update_from_feedback(issue_number, plan_path)
if not result.success:
    # Handle sync failure
    ...
```

This ensures changes are persisted locally before syncing remotely.

## Testing Considerations

Tests should verify:

1. **Sync updates comment**: The comment body reflects the new plan content
2. **Markers preserved**: plan-body markers are correctly formatted
3. **Metadata unchanged**: plan-header metadata is not affected by sync
4. **Error handling**: Invalid states (missing comment ID, comment not found) raise errors

## Related Patterns

### Metadata Block Patterns

Plan file sync operates within the metadata block system:

- **plan-header**: Contains metadata (plan_comment_id)
- **plan-body markers**: Wrap the actual plan content
- **Comment updates**: Preserve markers during sync

### Two-Phase Commit

The edit → commit → sync workflow is a two-phase commit:

1. **Phase 1 (local)**: Edit file, commit to git
2. **Phase 2 (remote)**: Sync to GitHub issue

Both phases must complete for the update to be visible to reviewers.

## Comparison with Code PRs

Plan file sync differs from code PR workflows:

| Aspect              | Code PRs       | Plan PRs                         |
| ------------------- | -------------- | -------------------------------- |
| **Files modified**  | Source code    | Markdown plan files              |
| **Sync mechanism**  | Git push       | Git push + explicit sync command |
| **Review location** | PR diff        | GitHub issue + PR diff           |
| **Sync target**     | GitHub PR only | GitHub PR + issue comment        |

The extra sync step is necessary because plan content lives in both the PR (for version control) and the issue (for structured review).

## Related Documentation

- [PR-Based Plan Review Workflow](../planning/pr-review-workflow.md) - Complete plan review process
- [Plan Header Metadata](../planning/plan-header-metadata.md) - plan_comment_id field
- [PR Address Workflows](../erk/pr-address-workflows.md) - Plan review mode integration

## Attribution

Pattern implemented in plan review PR feedback workflow (PR #6237 implementation).
