---
title: Branch Create --for-plan Option
read_when:
  - "creating a branch from a GitHub issue"
  - "using --for-plan flag with erk br create"
  - "understanding issue-to-worktree workflow"
tripwires:
  - action: "using ctx.plan_store.get_plan() in CLI code"
    warning: "Use try/except with RuntimeError (not custom exceptions). Plan store methods raise RuntimeError on not-found. Wrap with click.ClickException for user-friendly display."
---

# `erk br create --for-plan` Command Reference

## Purpose

Create a feature branch directly from a GitHub issue with the `erk-plan` label. The command automatically:

1. Fetches the plan content from the issue
2. Derives the branch name from the issue
3. Allocates a worktree slot
4. Creates `.impl/` folder with plan content and metadata
5. Generates activation script for the worktree

## Usage

```bash
# Using plain issue number
erk br create --for-plan 5037

# Using P-prefixed ID
erk br create --for-plan P5037

# Using full GitHub URL
erk br create --for-plan https://github.com/dagster-io/erk/issues/5037

# Suppress slot allocation (no worktree)
erk br create --for-plan 5037 --no-slot

# Force unassign oldest slot if pool is full
erk br create --for-plan 5037 --force
```

## Output

```
Created branch: P5037-phase-3-for-plan-on-branc-01-16-0536
Assigned P5037-phase-3-for-plan-on-branc-01-16-0536 to erk-slot-01
Created .impl/ folder from issue #5037

To activate the worktree environment:
  source /Users/user/.erk/repos/erk/worktrees/erk-slot-01/.erk/activate.sh
```

## Options

| Option             | Type   | Description                                                      |
| ------------------ | ------ | ---------------------------------------------------------------- |
| `--for-plan ISSUE` | string | GitHub issue number, P-prefixed ID, or URL with `erk-plan` label |
| `--no-slot`        | flag   | Create branch without allocating worktree slot                   |
| `-f, --force`      | flag   | Auto-unassign oldest branch if slot pool is full                 |

## Mutual Exclusivity

- **Cannot specify both** `BRANCH` argument and `--for-plan` option
- Must provide **either** `BRANCH` or `--for-plan`, not both
- If neither provided, command fails with clear error message

## Implementation Details

### Branch Name Derivation

Branch name is derived from issue metadata using the pattern: `P{issue_number}-{issue_title_slug}-{timestamp}`

Example: Issue #5037 titled "Phase 3 - `--for-plan` on Branch Create" becomes:

```
P5037-phase-3-for-plan-on-branc-01-16-0536
```

### Issue Validation

The command verifies:

1. Issue exists on GitHub
2. Issue has the `erk-plan` label (required)
3. Issue has plan content in the first comment

If validation fails, the command exits with a descriptive error message.

### `.impl/` Folder Creation

When `--for-plan` is used:

1. `.impl/plan.md` is created with the full plan content from the issue
2. `.impl/issue.json` is created with issue metadata (number, URL, title)
3. `.erk/activate.sh` script is generated in the worktree
4. Source command is printed for user copy-paste

### Activation Script

The `activate.sh` script sets up the worktree environment:

```bash
# Copy the printed source command
source /path/to/worktree/.erk/activate.sh
```

This ensures the environment is properly configured for implementation.

## Error Cases

| Condition                              | Error Message                                                                                                             |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Both BRANCH and --for-plan provided    | "Cannot specify both BRANCH and --for-plan. Use --for-plan to derive branch name from issue, or provide BRANCH directly." |
| Neither BRANCH nor --for-plan provided | "Must provide BRANCH argument or --for-plan option."                                                                      |
| Issue has no `erk-plan` label          | "Error: Plan #5037 does not have erk-plan label"                                                                          |
| Issue not found                        | "GitHub issue #5037 not found"                                                                                            |
| Branch already exists                  | "Error: Branch 'P5037-...' already exists. Use `erk br assign` to assign an existing branch to a slot."                   |

## Related Commands

- `erk br create BRANCH` - Traditional branch creation (manual branch name)
- `erk br assign` - Assign existing branch to slot
- `erk br list` - List all branches and their slot assignments
- `erk wt create` - Create worktree directly (without issue)

## Related Topics

- [Optional Arguments](optional-arguments.md) - Pattern for inferring CLI arguments from context
- [GitHub URL Parsing Architecture](../architecture/github-parsing.md) - Two-layer parsing architecture
