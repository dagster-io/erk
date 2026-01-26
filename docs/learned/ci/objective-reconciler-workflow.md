---
title: Objective Reconciler Workflow
read_when:
  - "understanding automated objective advancement"
  - "configuring objective reconciler GitHub Action"
  - "debugging objective auto-advance issues"
---

# Objective Reconciler Workflow

This document describes the planned GitHub Actions workflow for automatically advancing objectives.

## Overview

The objective reconciler workflow:

1. Runs on manual dispatch (initially)
2. Analyzes objectives with `auto-advance` label
3. Creates plans for pending steps
4. Reports results back to the objective issue

## Workflow Configuration

### Trigger

Manual dispatch only (for initial rollout):

```yaml
on:
  workflow_dispatch:
    inputs:
      dry_run:
        description: "Preview actions without executing"
        type: boolean
        default: false
      objective:
        description: "Specific objective number (optional)"
        type: string
        required: false
```

### Input Parameters

| Parameter   | Type    | Required | Description                         |
| ----------- | ------- | -------- | ----------------------------------- |
| `dry_run`   | boolean | No       | Preview mode - no mutations         |
| `objective` | string  | No       | Target specific objective by number |

When `objective` is not provided, the workflow processes all objectives with `auto-advance` label.

### Secret Requirements

| Secret              | Purpose                           |
| ------------------- | --------------------------------- |
| `ERK_QUEUE_GH_PAT`  | GitHub token for issue operations |
| `ANTHROPIC_API_KEY` | API key for plan generation       |

The `ERK_QUEUE_GH_PAT` needs permissions to:

- Read/write issues
- Create/update comments
- Add/remove labels

## Concurrency Control

```yaml
concurrency:
  group: objective-reconciler-${{ github.event.inputs.objective || 'all' }}
  cancel-in-progress: false
```

When targeting a specific objective, only one reconciler can run for that objective. When processing all objectives, a global lock prevents concurrent runs.

## Cost Model

Estimated cost per objective reconciliation:

| Operation         | Approximate Cost |
| ----------------- | ---------------- |
| Issue analysis    | ~$0.001          |
| Plan generation   | ~$0.002          |
| **Total per run** | ~$0.003          |

Costs scale linearly with number of objectives processed.

## Workflow Steps

1. **Checkout**: Get repository code
2. **Setup Python**: Install dependencies
3. **Fetch objectives**: Query for `auto-advance` objectives
4. **Analyze each objective**:
   - Determine current step
   - Check if step has associated plan/PR
   - Decide next action
5. **Execute actions** (if not dry-run):
   - Create plans for pending steps
   - Update objective comments with status
6. **Report results**: Output summary

## Integration Points

### CLI Command

The workflow invokes `erk objective reconcile`:

```bash
erk objective reconcile \
  ${DRY_RUN:+--dry-run} \
  ${OBJECTIVE:+$OBJECTIVE}
```

### Label Dependencies

| Label           | Meaning                          |
| --------------- | -------------------------------- |
| `erk-objective` | Identifies issue as an objective |
| `auto-advance`  | Enables automatic reconciliation |
| `erk-plan`      | Applied to generated plan issues |

## Future Enhancements

Planned improvements for later phases:

- **Scheduled runs**: Cron-based automatic reconciliation
- **Event triggers**: Reconcile on PR merge
- **Batch processing**: Parallel objective analysis
- **Cost controls**: Daily/weekly budget limits

## Related Documentation

- [Objective Commands](../cli/objective-commands.md) - CLI interface
- [Plan Lifecycle](../planning/lifecycle.md) - How plans are created
- [GitHub Actions Workflow Patterns](github-actions-workflow-patterns.md) - Workflow best practices
