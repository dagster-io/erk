# Run Remote Execution

Run implementations in GitHub Actions for sandboxed, parallel execution.

## Overview

Remote execution allows you to submit implementation plans to GitHub Actions, where they are executed automatically by Claude Code in a clean, sandboxed environment. This is useful when you want to work on multiple plans in parallel, need a guaranteed-clean environment, or prefer hands-off automated implementation. The remote workflow creates a branch, opens a draft PR, and executes the plan—resulting in a PR ready for your review.

## Prerequisites

Before using remote execution, ensure:

- **GitHub Actions enabled** on your repository
- **Required secrets** configured in repository settings:
  - `ERK_QUEUE_GH_PAT` - GitHub personal access token with repo access
  - `CLAUDE_CODE_OAUTH_TOKEN` - Claude Code authentication token
  - `ANTHROPIC_API_KEY` - Anthropic API key for Claude
- **Plan already saved to GitHub** - Complete steps 1-3 from [local-workflow.md](local-workflow.md) (enter plan mode, create plan, save to GitHub)

## Creating a Plan

The planning phase is identical to the local workflow. Follow steps 1-3 in [Use the Local Workflow](local-workflow.md):

1. Start Claude Code session (`claude`)
2. Enter plan mode (Shift+Tab or automatic for complex tasks)
3. Choose "Save to GitHub" when plan is complete

Stop here—do not choose "Implement now" if using remote execution.

## Submitting for Remote Execution

Once your plan is saved as a GitHub issue, submit it for remote execution:

```bash
erk plan submit <issue-number>
```

You can submit multiple plans at once:

```bash
erk plan submit 123 456 789
```

### Submission Flags

| Flag              | Description                                |
| ----------------- | ------------------------------------------ |
| `--base <branch>` | Specify base branch (default: trunk)       |
| `-f, --force`     | Delete existing branches without prompting |

### What Happens During Submission

The `erk plan submit` command:

1. Creates a feature branch for the plan
2. Creates a draft PR linked to the plan issue
3. Commits the plan files to `.worker-impl/` folder
4. Triggers the `plan-implement.yml` GitHub Actions workflow
5. Posts a `submission-queued` comment to the issue

**Example output:**

```
✓ Created branch P123-feature-name-01-26-1430
✓ Created draft PR #456
✓ Triggered workflow run
→ Monitor: https://github.com/owner/repo/actions/runs/123456789
```

## Monitoring Execution

Track execution progress in several ways:

### GitHub Actions Tab

Visit your repository's Actions tab and look for the `plan-implement` workflow. Runs are named with the issue number and a unique identifier (e.g., `123:abc123`).

### Issue Comments

The workflow posts status comments to the plan issue:

- `workflow-started` - Links to the workflow run when execution begins
- `erk-implementation-status` - Progress updates during implementation
- Final comment with PR link when complete

### Workflow Run Discovery

The `distinct_id` generated during submission enables finding the specific run even when multiple implementations are running. The workflow's display title includes this identifier for easy matching.

## Reviewing the Result

When execution completes successfully:

1. **PR marked ready for review** - Draft status is removed automatically
2. **Implementation summary** added to PR body with changes made
3. **Session log uploaded** to gist for debugging (linked in PR)
4. **CI triggered** automatically via empty commit

Review the PR like any other:

- Check the implementation against the plan
- Review code quality and test coverage
- Run local tests if needed (see "Debugging Remote PRs" below)
- Leave review comments as usual

## Debugging Remote PRs

If you need to iterate on a remotely-created PR, check it out locally:

```bash
erk pr checkout <pr-number>
```

This creates a worktree for the PR, allowing you to make changes, run tests, and push updates. See [Checkout and Sync PRs](pr-checkout-sync.md) for the complete workflow.

## When to Use Remote vs Local

| Aspect          | Remote Execution                        | Local Workflow                      |
| --------------- | --------------------------------------- | ----------------------------------- |
| **Where runs**  | GitHub Actions (cloud)                  | Your local machine                  |
| **When to use** | Parallel execution, clean environment   | Immediate implementation, debugging |
| **Trade-offs**  | Slower feedback, requires secrets setup | Uses local resources, immediate     |

**Use remote when:**

- Working on multiple plans simultaneously
- You need a guaranteed-clean environment
- You want to implement plans overnight or while away
- Testing how implementations work in CI environment

**Use local when:**

- You want immediate feedback and control
- Iterating rapidly on a complex feature
- Debugging implementation issues
- Secrets are not configured for remote execution

## See Also

- [Use the Local Workflow](local-workflow.md) - Alternative local approach
- [Checkout and Sync PRs](pr-checkout-sync.md) - Debug remote PRs locally
