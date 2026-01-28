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

### Plan Review Operations

- `plan-create-review-branch` - Create branch with plan file for review
- `plan-create-review-pr` - Create draft PR and update plan metadata
- `plan-submit-for-review` - Orchestrate full review submission workflow

#### plan-create-review-pr

Creates a draft PR for asynchronous plan review:

1. Validates plan issue exists
2. Creates draft PR with plan file as content
3. Updates plan issue metadata with `review_pr` field

**Arguments:**

| Option    | Required | Description       |
| --------- | -------- | ----------------- |
| `--issue` | Yes      | Plan issue number |

**Output (JSON):**

```json
{
  "success": true,
  "pr_number": 123,
  "pr_url": "https://github.com/owner/repo/pull/123"
}
```

**Error codes:**

| Code                     | Description                           |
| ------------------------ | ------------------------------------- |
| `issue_not_found`        | Plan issue does not exist             |
| `metadata_update_failed` | PR created but metadata update failed |

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

## Adding New Exec Commands

When adding new exec commands:

1. Create script in `src/erk/cli/commands/exec/scripts/`
2. Import in `group.py` and call `exec_group.add_command()`
3. **Regenerate reference docs:** `erk-dev gen-exec-reference-docs`

The third step is often forgotten, causing the reference docs to become stale.
