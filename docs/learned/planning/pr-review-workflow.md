---
title: PR-Based Plan Review Workflow
read_when:
  - "creating a PR for plan review"
  - "understanding the plan review lifecycle"
  - "working with review_pr metadata field"
  - "coordinating plan feedback with reviewers"
tripwires:
  - action: "creating a review PR for a plan"
    warning: "Review PRs are draft PRs that are never merged. Use erk exec plan-create-review-pr."
  - action: "manually creating plan review branches"
    warning: "Use plan-create-review-branch to ensure proper naming (plan-review-{issue}-{timestamp})."
---

# PR-Based Plan Review Workflow

PR-based plan review enables inline comments on saved plans through temporary draft PRs. This workflow creates a GitHub PR containing only the plan markdown file, allowing reviewers to add line-specific feedback before implementation begins.

## Overview

**Purpose**: Enable reviewers to add inline comments on plan content without implementing the plan.

**Key characteristics**:

- Review PRs are **draft PRs** - they signal they are not ready for merge
- Review PRs are **never merged** - they exist only for gathering feedback
- Branch and PR are **ephemeral** - deleted after review completes
- Metadata provides **bidirectional linkage** - PR ↔ issue tracking via `review_pr` field

**When to use**: When a plan needs detailed review with inline comments before implementation.

## Full Workflow

### 1. Parse Issue → Check Existing Review

**Command**: `/erk:review-plan <issue-number>`

**Checks performed**:

1. Validate issue exists and has `erk-plan` label
2. Check for active review via `review_pr` metadata field
3. Check for previous completed review via `last_review_pr` field

**Early exit scenarios**:

- Active review exists: Display existing PR, exit
- Previous review completed: Prompt user to confirm new review

### 2. Create Review Branch

**Exec command**: `erk exec plan-create-review-branch <issue-number>`

**Operations**:

1. Fetch plan content from issue (validates `plan_comment_id` in metadata)
2. Create timestamped branch: `plan-review-{issue}-{MM-DD-HHMM}`
3. Write plan to `PLAN-REVIEW-{issue}.md` at repo root
4. Commit and push to origin

**Source**: `src/erk/cli/commands/exec/scripts/plan_create_review_branch.py` (217 lines)

**LBYL pattern**: Checks issue existence, label, plan content availability before creating branch.

### 3. Create Draft PR

**Exec command**: `erk exec plan-create-review-pr <issue> <branch> <title>`

**Operations**:

1. Validate issue exists and has `plan-header` metadata block
2. Check no PR exists for this branch (duplicate prevention via `get_pr_for_branch()`)
3. Create draft PR targeting master with formatted body linking to issue
4. Add `plan-review` label to PR
5. Update issue `plan-header` metadata with `review_pr` field

**Source**: `src/erk/cli/commands/exec/scripts/plan_create_review_pr.py` (206 lines)

**PR body format**:

```markdown
# Plan Review: {plan_title}

This PR is for reviewing the plan in issue #{issue_number}.

**Plan Issue:** #{issue_number}

## Important

**This PR will not be merged.** It exists solely to enable inline review comments on the plan.

Once review is complete, the plan will be implemented directly and this PR will be closed.
```

### 4. Review Phase

Reviewers add inline comments directly on the plan file in the PR. Comments can reference specific lines, sections, or implementation details.

**Future enhancement**: `plan-update-from-feedback` command to sync feedback back to issue.

### 5. Complete Review

**Exec command**: `erk exec plan-review-complete <issue-number>`

**Operations**:

1. Extract `review_pr` from plan-header metadata
2. Fetch PR details (need branch name)
3. Close PR (without merging)
4. Delete remote branch
5. If currently checked out on review branch: switch to master
6. Delete local branch if it exists
7. Archive metadata: `review_pr` → `last_review_pr`, clear `review_pr`

**Source**: `src/erk/cli/commands/exec/scripts/plan_review_complete.py` (166 lines)

**Re-review guard**: Clearing `review_pr` and archiving to `last_review_pr` allows future reviews. The `/erk:review-plan` command checks `last_review_pr` and prompts user to confirm if creating a second review.

## Bidirectional Linkage Pattern

Review PRs maintain two-way linkage between PR and issue:

**PR → Issue**: PR body contains `**Plan Issue:** #{issue_number}` link

**Issue → PR**: `plan-header` metadata contains `review_pr: {pr_number}` field

**After completion**: Metadata archives to `last_review_pr: {pr_number}`, clearing `review_pr`

This linkage enables:

- Quick navigation from PR to plan details
- Discovery of active/past review PRs from issue
- State tracking via metadata (active vs. archived)

## Metadata-Driven State

The review lifecycle is tracked via metadata fields:

| State            | `review_pr`   | `last_review_pr`     | Meaning                      |
| ---------------- | ------------- | -------------------- | ---------------------------- |
| No review        | `null`        | `null`               | Plan has never been reviewed |
| Active review    | `{pr_number}` | `null` or `{old_pr}` | Review PR open and active    |
| Review completed | `null`        | `{pr_number}`        | Previous review archived     |

**State transitions**:

1. `plan-create-review-pr` sets `review_pr` to new PR number
2. `plan-review-complete` moves `review_pr` → `last_review_pr`, clears `review_pr`
3. Creating a second review: sets new `review_pr`, keeps `last_review_pr` from first review

## Why Draft PRs?

Review PRs are created as draft PRs for several reasons:

1. **Signal intent**: Draft status indicates "not ready for merge" in GitHub UI
2. **Prevent accidental merge**: GitHub prevents merging draft PRs
3. **Distinguish from implementation PRs**: Clear visual distinction in PR lists

## Multi-Step Operation Failure Modes

The workflow involves 5 exec commands that must execute sequentially. Each command validates preconditions via LBYL patterns.

**Failure recovery**:

- **Step 2 fails** (branch creation): No side effects, safe to retry
- **Step 3 fails** (PR creation): Branch exists but no PR. Can delete branch manually or retry PR creation
- **Step 5 fails** (completion): PR closed but branch/metadata may remain. Can run completion again (idempotent for branch deletion)

**Idempotency**: Commands check current state before mutation:

- `plan-create-review-pr` checks if PR exists via `get_pr_for_branch()`
- `plan-review-complete` checks if branch exists before deleting

## Exec Commands Involved

| Command                     | Purpose                                   | Args                       | Updates                                                                 |
| --------------------------- | ----------------------------------------- | -------------------------- | ----------------------------------------------------------------------- |
| `plan-submit-for-review`    | Fetch plan content from issue             | `<issue>`                  | None (read-only)                                                        |
| `plan-create-review-branch` | Create timestamped branch with plan file  | `<issue>`                  | Git: new branch + commit                                                |
| `plan-create-review-pr`     | Create draft PR and update metadata       | `<issue> <branch> <title>` | GitHub: PR + label, Issue: `review_pr` field                            |
| `plan-review-complete`      | Close PR, delete branch, archive metadata | `<issue>`                  | GitHub: close PR + delete branch, Issue: `review_pr` → `last_review_pr` |
| `plan-update-from-feedback` | Update plan issue with review feedback    | `<issue>`                  | Issue body (not yet implemented)                                        |

See [erk exec Commands Reference](../cli/erk-exec-commands.md) for detailed command documentation.

## Orchestration Pattern

The workflow is orchestrated by the `/erk:review-plan` slash command, which chains exec commands via JSON IPC. See [Skill-Exec Decomposition](../architecture/skill-exec-decomposition.md) for the pattern details.

**Skill responsibility**: Parse arguments, handle user interaction, chain commands, format output

**Exec command responsibility**: Atomic operations with typed errors, no user interaction

## Related Topics

- [Plan Metadata Fields](learn-plan-metadata-fields.md) - `review_pr` and `last_review_pr` schema
- [Metadata Field Workflow](metadata-field-workflow.md) - How to add new metadata fields
- [Plan Schema Reference](plan-schema.md) - Complete plan metadata schema
- [PR Operations](../cli/pr-operations.md) - Review PR creation patterns
- [Skill-Exec Decomposition](../architecture/skill-exec-decomposition.md) - Command orchestration pattern
