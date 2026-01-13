# Run Remote Execution

Run implementations in GitHub Actions for sandboxed, parallel execution.

## Overview

Remote execution lets you submit plans to GitHub Actions where a cloud-based Claude Code instance implements them automatically. Use this when you want to run implementations in parallel across multiple plans, need a sandboxed environment, or prefer hands-off operation while you focus on other work.

## Prerequisites

Before using remote execution, ensure:

- GitHub Actions is enabled on your repository
- Required secrets are configured: `ERK_QUEUE_GH_PAT`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY`
- The `erk-impl.yml` workflow exists in `.github/workflows/`

## Creating a Plan

Plan creation works the same as the local workflow. Follow Steps 1-3 from [Use the Local Workflow](local-workflow.md):

1. Start a Claude Code session
2. Enter plan mode and develop your plan
3. Save the plan to GitHub (choose "Save to GitHub", not "Implement now")

## Submitting for Remote Execution

Once your plan is saved as a GitHub issue, submit it for remote execution:

```bash
erk plan submit <issue-number>
```

This command:

1. Creates a feature branch from trunk
2. Sets up the `.worker-impl/` folder with the plan
3. Creates a draft PR linked to the issue
4. Dispatches the `erk-impl` workflow

You'll see output confirming the workflow was triggered and a link to monitor progress.

## Monitoring Execution

Track progress in the GitHub Actions tab. The workflow run is named with your issue number (e.g., `4123:a8b2c3`) making it easy to find.

You can also find the run link in the `workflow-started` comment posted to your plan issue. The workflow typically takes a few minutes, depending on plan complexity.

## Reviewing the Result

When execution completes:

- The draft PR is marked ready for review
- The PR body contains an implementation summary
- Standard code review process applies

Review the changes as you would any PR. The implementation follows the plan, so focus on verifying correctness and catching edge cases.

## Debugging Remote PRs

If the implementation needs adjustments, check out the branch locally:

```bash
erk pr checkout <pr-number>
```

This sets up a worktree with the remote branch. Make your changes, then sync back. See [Checkout and Sync PRs](pr-checkout-sync.md) for the full iteration workflow.

## When to Use Remote vs Local

| Aspect          | Local Workflow                   | Remote Execution                    |
| --------------- | -------------------------------- | ----------------------------------- |
| **Runs on**     | Your machine                     | GitHub Actions                      |
| **Use when**    | Single plan, want direct control | Multiple plans, hands-off preferred |
| **Environment** | Your local dev setup             | Fresh, sandboxed container          |
| **Parallelism** | One at a time (your terminal)    | Multiple concurrent runs            |
| **Iteration**   | Immediate fixes in same session  | Checkout PR branch to iterate       |

Choose remote when you want to queue up work and step away. Choose local when you want tight iteration loops or need specific local dependencies.

## See Also

- [Use the Local Workflow](local-workflow.md) - Alternative local approach
- [Checkout and Sync PRs](pr-checkout-sync.md) - Debug remote PRs locally
