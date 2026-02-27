---
title: erk exec Commands
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
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

| Command             | `--format json` | Notes                        |
| ------------------- | --------------- | ---------------------------- |
| `impl-init`         | ✓               | Returns validation result    |
| `get-plan-metadata` | ✓               | Returns specific field value |
| `list-sessions`     | ✓               | Returns session list         |

### Commands Without Format Flag

| Command              | Output Format | Notes                       |
| -------------------- | ------------- | --------------------------- |
| `get-pr-body-footer` | Plain text    | Returns PR body footer text |
| `impl-signal`        | JSON always   | No format flag, always JSON |
| `setup-impl-from-pr` | Plain text    | Status messages only        |

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
- `resolve-review-threads` - Batch resolve multiple review threads via JSON stdin
- `reply-to-discussion-comment` - Reply to PR discussion
- `handle-no-changes` - Handle zero-change implementation outcomes (called by erk-impl workflow)

### Plan Operations

- `get-plan-metadata` - Read plan issue metadata
- `setup-impl-from-pr` - Prepare .erk/impl-context/ folder

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

### Objective Operations

- `objective-roadmap-check` - Parse and validate an objective's roadmap, returning structured JSON with phases, steps, summary, and next step
- `objective-roadmap-update` - Update a specific step's status or PR column in an objective's roadmap

#### objective-roadmap-check

```bash
erk exec objective-roadmap-check <OBJECTIVE_NUMBER>
```

Returns JSON with `phases`, `summary`, `next_step`, and `validation_errors`. See [Roadmap Parser](../objectives/roadmap-parser.md) for full output format.

#### objective-roadmap-update

```bash
erk exec objective-roadmap-update <OBJECTIVE_NUMBER> --step <STEP_ID> [--status <STATUS>] [--pr <PR_REF>]
```

Updates a step's status and/or PR reference. When `--pr` is provided without `--status`, the status cell is reset to allow inference. See [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) for inference rules.

### Implementation Setup Operations

- `setup-impl` - Consolidated implementation setup (orchestrator)
- `setup-impl-from-pr` - Prepare worktree from a plan issue (called by `setup-impl`)
- `cleanup-impl-context` - Remove `.erk/impl-context/` staging directory

#### setup-impl

Consolidated entry point for implementation setup. Handles all plan sources:

```bash
erk exec setup-impl --issue 2521              # From issue number
erk exec setup-impl --file ./my-plan.md       # From local file
erk exec setup-impl                           # Auto-detect from .erk/impl-context/, branch, or fail
```

**What it does:**

1. Detects plan source (issue, file, existing `.erk/impl-context/`, or branch name)
2. Delegates to `setup-impl-from-pr` for issue-based plans
3. Runs `impl-init` validation
4. Cleans up `.erk/impl-context/` staging directory (git rm + commit + push)

**Flags:**

- `--issue` - Issue number to fetch plan from
- `--file` - Local markdown file path
- `--no-impl` - Create branch only, skip `.erk/impl-context/` folder creation

**Output:** JSON with `success`, `source`, `plan_number`, `has_plan_tracking`, `valid`, `related_docs`

#### setup-impl-from-pr

Creates implementation environment from a plan issue:

1. Fetches plan from GitHub issue
2. Creates/checks out implementation branch (e.g., `P123-feature-01-15-1430`)
3. Creates `.erk/impl-context/` folder with plan content
4. Saves issue reference for PR linking

**Flags:**

- `--no-impl` - Create branch only, skip `.erk/impl-context/` folder creation

**Branch behavior:**

- If branch exists: Checks out existing branch
- If on trunk: Creates branch from trunk
- If on feature branch: Stacks new branch on current branch

**Important:** After `create_branch()`, explicit `checkout_branch()` is called because GraphiteBranchManager restores the original branch after tracking.

---

#### setup-impl

Consolidated entry point for implementation setup. Handles all plan sources:

```bash
erk exec setup-impl --issue 2521              # From issue number
erk exec setup-impl --file ./my-plan.md       # From local file
erk exec setup-impl                           # Auto-detect from .erk/impl-context/, branch, or fail
```

**What it does:**

1. Detects plan source (issue, file, existing `.erk/impl-context/`, or branch name)
2. Delegates to `setup-impl-from-pr` for issue-based plans
3. Runs `impl-init` validation
4. Cleans up `.erk/impl-context/` staging directory (git rm + commit + push)

#### cleanup-impl-context

Removes the `.erk/impl-context/` staging directory after implementation:

```bash
erk exec cleanup-impl-context
```

Performs `git rm -rf .erk/impl-context/` and commits the deletion.

### Batch Operations

Batch commands read JSON arrays from stdin and process items individually. They continue on individual failures and always exit with code 0.

- `add-plan-labels` — Add labels to multiple plans (stdin: `[{"plan_number": int, "label": str}]`)
- `close-prs` — Close multiple PRs with comments (stdin: `[{"plan_number": int, "comment": str}]`)

Both use frozen dataclass results with discriminated union error handling.

#### Command Renaming History

These commands were renamed from issue-oriented to PR-oriented terminology:

| Old Name                    | New Name                 |
| --------------------------- | ------------------------ |
| `close-issue-with-comment`  | `close-pr`               |
| `plan-update-issue`         | `plan-update`            |
| `setup-impl-from-issue`     | `setup-impl-from-pr`     |
| `issue-title-to-filename`   | `plan-title-to-filename` |
| `create-issue-from-session` | `create-pr-from-session` |

### PR Validation Operations

- `erk pr check` - Validate PR structural invariants

#### erk pr check --stage=impl

The `--stage=impl` flag adds implementation-specific validation:

```bash
erk pr check --stage=impl
```

**Additional check:** Verifies `.erk/impl-context/` has been cleaned up. This catches cases where the staging directory was not removed after implementation.

**Output format:** Each check returns a `PrCheck(passed: bool, description: str)` result. All checks are displayed with `[PASS]`/`[FAIL]` status.
