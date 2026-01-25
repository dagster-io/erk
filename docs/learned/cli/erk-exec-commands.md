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
