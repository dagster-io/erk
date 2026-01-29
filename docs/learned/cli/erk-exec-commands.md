---
title: erk exec Commands
read_when:
  - "running erk exec subcommands"
  - "looking up erk exec syntax"
tripwires:
  - action: "running any erk exec subcommand"
    warning: "Check syntax with `erk exec <command> -h` first, or load erk-exec skill for workflow guidance."
  - action: "using erk exec commands in scripts"
    warning: "Some erk exec subcommands don't support `--format json`. Always check with `erk exec <command> -h` first."
---

# erk exec Commands

The `erk exec` command group contains utility scripts for automation and agent workflows.

## Usage Pattern

All erk exec commands use named options (not positional arguments for most parameters):

```bash
# Correct
erk exec get-pr-review-comments --pr 123

# Wrong - positional arguments don't work
erk exec get-pr-review-comments 123
```

## Format Flag Support

Not all erk exec commands support the `--format` flag. Always check with `erk exec <command> -h` first.

### Commands with `--format json` Support

| Command              | `--format json` | Notes                           |
| -------------------- | --------------- | ------------------------------- |
| `plan-save-to-issue` | ✓               | Returns `{issue_number, title}` |
| `impl-init`          | ✓               | Returns validation result       |
| `get-plan-metadata`  | ✓               | Returns specific field value    |
| `list-sessions`      | ✓               | Returns session list            |

### Commands Without Format Flag

| Command                 | Output Format | Notes                         |
| ----------------------- | ------------- | ----------------------------- |
| `get-closing-text`      | Plain text    | Returns closing text or empty |
| `impl-signal`           | JSON always   | No format flag, always JSON   |
| `setup-impl-from-issue` | Plain text    | Status messages only          |

### Best Practice

Always check command help before assuming format support:

```bash
erk exec <command> -h
```

## Key Commands by Category

See the `erk-exec` skill for complete workflow guidance and the full command reference.

### PR Operations

- `get-pr-review-comments` - Fetch PR review threads
- `resolve-review-thread` - Resolve a review thread
- `reply-to-discussion-comment` - Reply to PR discussion
- `handle-no-changes` - Handle zero-change implementation outcomes (called by erk-impl workflow)

### Plan Operations

- `plan-save-to-issue` - Save plan to GitHub
- `get-plan-metadata` - Read plan issue metadata
- `setup-impl-from-issue` - Prepare .impl/ folder
- `plan-submit-for-review` - Fetch plan content from issue for PR-based review
- `plan-create-review-branch` - Create git branch for offline plan review

### Plan Review Operations

- `plan-submit-for-review` - Fetch plan content from issue for review
- `plan-create-review-branch` - Create branch with plan file from issue
- `plan-create-review-pr` - Create draft PR for plan review and update metadata
- `plan-review-complete` - Close review PR, delete branch, archive metadata
- `plan-update-from-feedback` - Update plan issue with review feedback

#### plan-submit-for-review

Fetches plan content from a GitHub issue to prepare for review.

**Arguments**: `<issue-number>`

**Output**: JSON with plan content and metadata

**Error codes**:

- `issue_not_found` - Issue does not exist
- `missing_erk_plan_label` - Issue is not an erk-plan
- `no_plan_content` - Issue has no plan_comment_id or plan content

#### plan-create-review-branch

Creates a timestamped branch with the plan file at repo root.

**Arguments**: `<issue-number>`

**Output**: JSON with branch name, file path, and plan title

**Branch naming**: `plan-review-{issue}-{MM-DD-HHMM}`

**File naming**: `PLAN-REVIEW-{issue}.md`

**Operations**:

1. Fetches plan content from issue
2. Creates branch from origin/master
3. Writes plan to file at repo root
4. Commits and pushes to origin

**Error codes**:

- `issue_not_found` - Issue does not exist
- `missing_erk_plan_label` - Issue is not an erk-plan
- `no_plan_content` - Issue has no plan_comment_id or plan content
- `branch_exists` - Branch already exists

#### plan-create-review-pr

Creates a draft PR for plan review and updates issue metadata.

**Arguments**: `<issue-number> <branch-name> <plan-title>`

**Output**: JSON with PR number and URL

**Operations**:

1. Validates issue exists and has plan-header block
2. Checks for duplicate PR via `get_pr_for_branch()`
3. Creates draft PR targeting master
4. Adds `plan-review` label
5. Updates issue `review_pr` field in plan-header metadata

**PR body format**: Links to plan issue, warns PR will not be merged

**Error codes**:

- `issue_not_found` - Issue does not exist
- `pr_already_exists` - PR already exists for this branch
- `invalid_issue` - Issue missing plan-header metadata

#### plan-review-complete

Closes a plan review PR and cleans up associated resources.

**Arguments**: `<issue-number>`

**Output**: JSON with PR number, branch name, deletion status

**Operations**:

1. Extracts `review_pr` from plan-header metadata
2. Closes the PR (without merging)
3. Deletes remote branch
4. Switches to master if currently on review branch
5. Deletes local branch if exists
6. Archives metadata: `review_pr` → `last_review_pr`, clears `review_pr`

**Error codes**:

- `issue_not_found` - Issue does not exist
- `no_plan_header` - Issue missing plan-header metadata
- `no_review_pr` - Issue has no active review PR
- `pr_not_found` - PR does not exist

#### plan-update-from-feedback

Updates the plan-body comment in a plan issue with revised content.

**Arguments**: `<issue-number>` with either `--plan-path PATH` or `--plan-content "..."`

**Output**: JSON with comment ID and URL

**Operations**:

1. Validates issue exists and has erk-plan label
2. Extracts plan_comment_id from plan-header
3. Updates the comment with new plan content
4. Preserves plan-body metadata markers

**Error codes**:

- `issue_not_found` - Issue does not exist
- `missing_erk_plan_label` - Issue is not an erk-plan
- `no_plan_comment` - Issue has no plan_comment_id
- `comment_not_found` - Comment does not exist

### Session Operations

- `list-sessions` - List Claude Code sessions
- `preprocess-session` - Compress session for analysis

### Learn Workflow Operations

- `track-learn-result` - Update parent plan's learn status

#### track-learn-result Status Values

| Status                | Description                            | When Used                     |
| --------------------- | -------------------------------------- | ----------------------------- |
| `not_started`         | Learn not yet run                      | Initial state                 |
| `pending`             | Learn scheduled                        | Waiting for execution         |
| `completed_no_plan`   | Learn found no documentation gaps      | No changes needed             |
| `completed_with_plan` | Learn created documentation plan issue | Gaps identified               |
| `pending_review`      | Learn plan awaiting review             | Plan created, not implemented |
| `plan_completed`      | Learn plan implemented and merged      | Documentation updated         |

### Implementation Setup Operations

- `setup-impl-from-issue` - Prepare worktree for plan implementation

#### setup-impl-from-issue

Creates implementation environment from a plan issue:

1. Fetches plan from GitHub issue
2. Creates/checks out implementation branch (e.g., `P123-feature-01-15-1430`)
3. Creates `.impl/` folder with plan content
4. Saves issue reference for PR linking

**Flags:**

- `--no-impl` - Create branch only, skip `.impl/` folder creation

**Branch behavior:**

- If branch exists: Checks out existing branch
- If on trunk: Creates branch from trunk
- If on feature branch: Stacks new branch on current branch

**Important:** After `create_branch()`, explicit `checkout_branch()` is called because GraphiteBranchManager restores the original branch after tracking.

#### plan-submit-for-review

Fetch plan content from a GitHub issue for PR-based review workflow.

**Usage:** `erk exec plan-submit-for-review <issue_number>`

**Output (JSON):**

- `success`, `issue_number`, `title`, `plan_content`, `plan_comment_id`, `plan_comment_url`

**Error Codes:** `issue_not_found`, `missing_erk_plan_label`, `no_plan_content`

#### plan-create-review-branch

Creates a git branch for offline plan review.

**Usage:** `erk exec plan-create-review-branch <issue_number>`

**Output (JSON):**

- `success`, `issue_number`, `branch`, `file_path`, `plan_title`

**Error Codes:** `issue_not_found`, `missing_erk_plan_label`, `no_plan_content`, `branch_already_exists`, `git_error`
