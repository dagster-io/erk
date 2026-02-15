# Run Remote Execution

Run implementations in GitHub Actions for sandboxed, parallel execution.

## Overview

Remote execution lets you submit plans to GitHub Actions for automated implementation. Use this approach when you want parallel execution across multiple plans, a sandboxed environment that mirrors CI, or hands-off operation while you work on other tasks. The trade-off is less direct control compared to the local workflow.

## Prerequisites

Before using remote execution:

- GitHub Actions must be enabled on your repository
- Required secrets configured: `ERK_QUEUE_GH_PAT`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY`
- Plan already saved to GitHub (see [Local Workflow](local-workflow.md) steps 1-3)

## Creating a Plan

The planning process is identical to the local workflow. Follow [Local Workflow](local-workflow.md) steps 1-3: start a Claude Code session, enter plan mode, and save the plan to GitHub when prompted. Stop after saving—do not choose "Implement now."

## Submitting for Remote Execution

Submit the saved plan for remote execution:

```bash
erk plan submit <issue-number>
```

This command:

1. Creates a feature branch from your current branch
2. Creates a draft PR linking to the plan issue
3. Triggers the `erk-impl` GitHub Actions workflow

You'll see the workflow URL in the output. The issue also receives a comment linking to the running workflow.

## Monitoring Execution

Watch the implementation progress in the GitHub Actions tab, or click the link in the issue comment. The workflow shows Claude implementing your plan step by step.

The issue receives status updates as implementation progresses. You can also check workflow status with:

```bash
gh run list --workflow=erk-impl.yml
```

## Reviewing the Result

When implementation completes, the draft PR is marked ready for review. The PR body contains:

- Summary of changes made
- Link back to the plan issue
- Checkout instructions for local iteration

Review the PR like any other: check the diff, run tests locally if needed, request changes or approve.

## Debugging Remote PRs

If the implementation needs fixes, check out the PR locally:

```bash
erk pr checkout <pr-number>
```

This creates a worktree with the PR branch. Make changes, push, and the PR updates. See [Checkout and Sync PRs](pr-checkout-sync.md) for detailed debugging workflows.

## When to Use Remote vs Local

| Aspect           | Remote Execution                  | Local Workflow                   |
| ---------------- | --------------------------------- | -------------------------------- |
| **Runs in**      | GitHub Actions                    | Your machine                     |
| **Best for**     | Parallel plans, CI-like sandboxes | Iterative development, debugging |
| **Control**      | Hands-off, monitor via web        | Direct interaction with Claude   |
| **Resource use** | GitHub Actions minutes            | Local compute                    |
| **Debugging**    | Checkout PR for local fixes       | Fix in place                     |

Use remote execution when you have multiple plans to implement or want a clean environment. Use local when you need direct control or expect iteration.

## See Also

- [Use the Local Workflow](local-workflow.md) - Alternative local approach
- [Checkout and Sync PRs](pr-checkout-sync.md) - Debug remote PRs locally
