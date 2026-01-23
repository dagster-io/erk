---
title: erk exec Commands
read_when:
  - "running erk exec subcommands"
  - "looking up erk exec syntax"
tripwires:
  - action: "running any erk exec subcommand"
    warning: "Check syntax with `erk exec <command> -h` first, or load erk-exec skill for workflow guidance."
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

### Plan Operations

- `plan-save-to-issue` - Save plan to GitHub
- `get-plan-metadata` - Read plan issue metadata
- `setup-impl-from-issue` - Prepare .impl/ folder

### Session Operations

- `list-sessions` - List Claude Code sessions
- `preprocess-session` - Compress session for analysis

### Workflow Error Handling

- `handle-no-changes` - Handle plan implementations with no code changes

#### handle-no-changes

Detects when a plan implementation resulted in zero code changes and creates appropriate diagnostics.

**Purpose:** When the erk-impl workflow completes but no actual code changes are present, this command generates a diagnostic PR explaining why (e.g., duplicate plan, refactoring-only, already-merged work) and applies the `no-changes` label for tracking.

**Usage:**

```bash
erk exec handle-no-changes \
  --branch <branch-name> \
  --plan-id <plan-issue-number> \
  --pr-number <pr-number> \
  --run-id <workflow-run-id>
```

**Behavior:**

1. Creates or updates PR with diagnostic information explaining why no changes occurred
2. Applies `no-changes` label (orange, #FFA500) to the PR
3. Posts notification comment to the plan issue linking to the diagnostic PR
4. Sets `has_changes` output to `false` for workflow step gating
5. Exits gracefully (exit code 0) rather than failing

**Outputs:**

- `has_changes=false` - Used to gate subsequent workflow steps

**Exit Codes:**

- `0`: Successfully handled no-changes scenario
- `1`: Error during handling (GitHub API failures, missing parameters, etc.)

**User Experience:**

Users will see:
- A PR with the `no-changes` label explaining the scenario
- A comment on the plan issue notifying them of the diagnostic PR
- Recent commits listed that may represent duplicate work
- Clear guidance for determining if this was a true duplicate or unexpected behavior

**Related Documentation:**

- [No-Code-Changes Handling](../planning/no-changes-handling.md) - User guide for understanding and resolving no-changes scenarios
- [Exec Command Patterns](exec-command-patterns.md) - Helper functions used for diagnostic messaging
