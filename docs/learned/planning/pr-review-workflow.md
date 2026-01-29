---
title: PR-Based Plan Review Workflow
read_when:
  - "creating a PR for plan review"
  - "setting up asynchronous plan review"
  - "understanding review_pr metadata field"
tripwires:
  - action: "creating a review PR for a plan"
    warning: "Review PRs are draft and never merged. They exist only for inline comments. Use plan-create-review-pr command."
---

# PR-Based Plan Review Workflow

Enable asynchronous plan review by creating draft PRs that contain plan content for inline commenting.

## Overview

The review workflow creates a draft PR containing the plan file, enabling reviewers to leave inline comments on specific parts of the plan before implementation begins.

**Key distinction:** Review PRs are NEVER merged. They exist solely as a commenting surface. Implementation PRs are separate and created later.

## Workflow Steps

### 1. Create Review Branch

```bash
erk exec plan-create-review-branch --issue <plan-issue-number>
```

Creates a branch containing the plan file extracted from the GitHub issue.

### 2. Create Review PR

```bash
erk exec plan-create-review-pr --issue <plan-issue-number>
```

Creates a draft PR targeting master with:

- Plan file as the diff content
- PR body linking back to plan issue
- Warning that this PR is for review only

### 3. Review and Comment

Reviewers add inline comments on the plan PR. Comments appear on specific lines of the plan content.

### 4. Address Feedback

Plan author updates the plan issue based on feedback, then optionally recreates the review PR.

## Bidirectional Linkage Pattern

The workflow maintains bidirectional references:

| Direction   | Location       | Content                           |
| ----------- | -------------- | --------------------------------- |
| PR -> Issue | PR body        | `**Plan Issue:** #<issue_number>` |
| Issue -> PR | Metadata block | `review_pr: <pr_number>`          |

This enables:

- Navigating from PR to source plan
- Programmatic discovery of review PR from plan issue
- Status tracking (has plan been reviewed?)

## Multi-Step Operation Pattern

The `plan-create-review-pr` command performs a multi-step operation:

1. **Validate** - Check plan issue exists (LBYL)
2. **Create PR** - Call GitHub API to create draft PR
3. **Capture ID** - Store returned PR number
4. **Update Metadata** - Add `review_pr` field to plan issue

**Failure mode:** If step 4 fails, PR exists but metadata is not updated (orphaned PR).

**Recovery:** Re-running the command should detect the existing PR via branch lookup and update metadata.

## Why Draft PRs?

- Visual indicator that this isn't ready for merge
- Prevents accidental merging (GitHub blocks merge of drafts by default)
- Signals "for review only" to reviewers
- Distinguishes from implementation PRs

## Related Topics

- [Plan Lifecycle](lifecycle.md) - Overall plan state management
- [Metadata Field Workflow](metadata-field-workflow.md) - How review_pr field was added
- [PR Operations](../cli/pr-operations.md) - PR duplicate prevention patterns
