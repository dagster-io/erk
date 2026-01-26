---
title: Workflow Commands
read_when:
  - "triggering GitHub Actions workflows from CLI"
  - "using erk workflow launch"
  - "understanding WORKFLOW_COMMAND_MAP"
---

# Workflow Commands

The `erk workflow launch` command provides a unified interface for triggering GitHub Actions workflows that run Claude-powered operations remotely.

## Available Workflows

| Subcommand            | Workflow File            | Description                               |
| --------------------- | ------------------------ | ----------------------------------------- |
| `pr-fix-conflicts`    | `erk-rebase.yml`         | Rebase PR with AI-powered conflict resolution |
| `pr-address`          | `pr-address.yml`         | Address PR review comments remotely       |
| `objective-reconcile` | `objective-reconcile.yml`| Reconcile auto-advance objectives         |
| `learn`               | `learn-dispatch.yml`     | Extract documentation from plan session   |

## Command Syntax

```bash
erk workflow launch <workflow-name> [options]
```

### Options by Workflow

| Workflow              | Required Options                  | Optional Options              |
| --------------------- | --------------------------------- | ----------------------------- |
| `pr-fix-conflicts`    | None (infers from current branch) | `--pr`, `--no-squash`, `--model` |
| `pr-address`          | `--pr`                            | `--model`                     |
| `objective-reconcile` | `--objective`                     | `--dry-run`                   |
| `learn`               | `--issue`                         | None                          |

## Usage Examples

### Fix Conflicts on PR

```bash
# Fix conflicts on current branch's PR
erk workflow launch pr-fix-conflicts

# Fix conflicts on specific PR
erk workflow launch pr-fix-conflicts --pr 123

# Skip commit squashing
erk workflow launch pr-fix-conflicts --pr 123 --no-squash

# Use specific Claude model
erk workflow launch pr-fix-conflicts --model claude-sonnet-4-5
```

### Address PR Review Comments

```bash
# Address comments on specific PR
erk workflow launch pr-address --pr 456

# With specific model
erk workflow launch pr-address --pr 456 --model claude-opus-4
```

### Reconcile Objectives

```bash
# Reconcile specific objective
erk workflow launch objective-reconcile --objective 789

# Preview mode (no mutations)
erk workflow launch objective-reconcile --objective 789 --dry-run
```

### Trigger Learn Workflow

```bash
# Extract docs from plan issue session
erk workflow launch learn --issue 123
```

## Architecture

### WORKFLOW_COMMAND_MAP

The mapping from command names to workflow files is defined in `src/erk/cli/constants.py`:

```python
WORKFLOW_COMMAND_MAP: dict[str, str] = {
    "plan-implement": "erk-impl.yml",
    "pr-fix-conflicts": "erk-rebase.yml",
    "pr-address": "pr-address.yml",
    "objective-reconcile": "objective-reconcile.yml",
    "learn": "learn-dispatch.yml",
}
```

### Workflow Input Building

Each workflow has a dedicated handler function that:

1. Validates required options
2. Fetches PR/issue context from GitHub
3. Builds workflow-specific inputs dict
4. Triggers the workflow via GitHub API

## Prerequisites

- GitHub CLI (`gh`) must be authenticated
- Required GitHub Actions secrets must be configured:
  - `ERK_QUEUE_GH_PAT`
  - `ANTHROPIC_API_KEY`
  - `CLAUDE_CODE_OAUTH_TOKEN`

## Migration from Old Commands

The `erk workflow launch` command replaces the previous pattern of separate remote commands:

| Old Command                   | New Command                                     |
| ----------------------------- | ----------------------------------------------- |
| `erk pr fix-conflicts-remote` | `erk workflow launch pr-fix-conflicts`          |
| `erk pr address-remote`       | `erk workflow launch pr-address --pr <number>`  |

## Error Handling

The command validates:

- GitHub authentication status
- Workflow name validity
- Required options for each workflow
- PR/issue existence and state (for PR workflows)

Example error messages:

```
Error: Unknown workflow 'invalid'. Available workflows: learn, objective-reconcile, plan-implement, pr-address, pr-fix-conflicts
Error: --pr is required for pr-address workflow
Error: Cannot rebase MERGED PR - only OPEN PRs can be rebased
```

## Related Documentation

- [Remote Workflow Template](../erk/remote-workflow-template.md) - Workflow YAML patterns
- [GitHub Actions Workflow Patterns](../ci/github-actions-workflow-patterns.md) - CI best practices
- [Command Organization](command-organization.md) - CLI structure decisions
