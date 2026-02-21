# Run Remote Execution

Run implementations in GitHub Actions for sandboxed, parallel execution.

## Overview

Remote execution runs your plan implementations on a GitHub Actions runner instead of your local machine. You write and save the plan locally, then `erk plan submit` sends it to a GitHub Actions workflow that executes it with Claude.

Why use remote execution:

- **Sandboxed environment** - runs on a clean Ubuntu runner, no local state interference
- **Parallel execution** - run multiple plans simultaneously (one per issue)
- **Keep working** - your machine stays free while plans execute in the background
- **Batch work** - submit plans overnight or in bulk

The mental model: `erk plan submit` creates a branch, commits your plan, opens a draft PR, and dispatches a GitHub Actions workflow. The workflow runs Claude against the plan, pushes the implementation, and marks the PR ready for review.

## Prerequisites

Before you can submit plans for remote execution:

1. **The `plan-implement.yml` workflow** must exist in your repository's `.github/workflows/` directory.

2. **Three repository secrets** must be configured:

   | Secret                    | Scope           | Purpose                                             |
   | ------------------------- | --------------- | --------------------------------------------------- |
   | `ERK_QUEUE_GH_PAT`        | `repo` + `gist` | Branch creation, PR management, session gist upload |
   | `ANTHROPIC_API_KEY`       | N/A             | Claude API access                                   |
   | `CLAUDE_CODE_OAUTH_TOKEN` | N/A             | Claude Code authentication                          |

   `ERK_QUEUE_GH_PAT` is validated at workflow startup with a clear error message if missing or lacking the required scopes.

3. **A saved erk-plan issue** - your plan must be saved to a GitHub issue (from `/erk:plan-save` or `erk plan create --file <path>`) before you can submit it.

## Creating a Plan

Creating a plan for remote execution is the same as the local workflow:

1. Start a Claude Code session
2. Enter plan mode (Shift+Tab or describe a task)
3. Save the plan to GitHub

See [Use the Local Workflow](local-workflow.md) Steps 1-3 for details. The key difference is what happens next: instead of implementing locally, you submit the plan for remote execution.

## Submitting for Remote Execution

Submit a saved plan with:

```bash
erk plan submit <issue-number>
```

To submit multiple plans at once:

```bash
erk plan submit 123 456 789
```

This validates all issues first, then submits them sequentially.

### Flags

| Flag              | Description                                                                           |
| ----------------- | ------------------------------------------------------------------------------------- |
| `--base <branch>` | Base branch (defaults to current branch; falls back to trunk on placeholder branches) |
| `--force` / `-f`  | Skip confirmation prompts                                                             |

### What Happens Behind the Scenes

1. **Validates** the issue (has `erk-plan` label, is OPEN, working directory is clean)
2. **Creates a branch** with `P{issue}-` prefix (e.g., `P123-feature-01-15-1430`) or reuses an existing one
3. **Creates `.worker-impl/`** folder with plan files and commits it to the branch
4. **Creates a draft PR** locally (for correct commit attribution)
5. **Dispatches** the `plan-implement.yml` workflow
6. **Prints** the workflow run URL

### Branch Reuse

If existing branches for the same issue are found (matching `P{issue}-*`), you'll be prompted:

```
Found existing local branch(es) for this issue:
  - P123-feature-01-10-0900
  - P123-feature-01-12-1430

Use existing branch 'P123-feature-01-12-1430'? [Y/n]
```

You can use the existing branch, delete and create a new one, or abort.

## Monitoring Execution

The submit command prints the workflow run URL directly — click it to watch progress in GitHub Actions.

To find runs later:

```bash
gh run list --workflow=plan-implement.yml | grep "123:"
```

Run names use the format `{issue_number}:{distinct_id}` (where `distinct_id` is a 6-character base36 identifier).

### Concurrency

Only one run per issue at a time. Resubmitting a plan cancels the in-progress run and starts fresh.

### Observable States

| What You See                         | What It Means    |
| ------------------------------------ | ---------------- |
| `submission-queued` comment on issue | Plan submitted   |
| `workflow-started` comment on issue  | Workflow running |
| PR is in draft                       | Implementing     |
| PR is ready for review               | Complete         |

## Reviewing the Result

When implementation succeeds:

- The **draft PR is marked ready for review** automatically.
- The **PR body** contains an AI-generated implementation summary and checkout instructions.
- The **session log** is uploaded to a GitHub Gist, linked from the plan issue's `plan-header` metadata.

To review the code locally:

```bash
erk pr checkout <pr-number>
```

See [Checkout and Sync PRs](pr-checkout-sync.md) for details on working with checked-out PRs.

If the `no-changes` label is applied to the PR, the implementation found nothing to change. Review the diagnostic PR to determine whether the work is already done or the plan needs revision.

## Debugging Remote PRs

Check out the PR locally to debug or iterate:

```bash
erk pr checkout <pr-number>
```

Sync with remote updates if the branch has changed:

```bash
erk pr sync --dangerous
```

Address review comments:

```
/erk:pr-address
```

To start over, resubmit the plan — this cancels the current run and dispatches a fresh one:

```bash
erk plan submit <issue-number>
```

See [Checkout and Sync PRs](pr-checkout-sync.md) for the complete checkout and sync workflow.

## When to Use Remote vs Local

| Factor             | Remote                                   | Local                               |
| ------------------ | ---------------------------------------- | ----------------------------------- |
| Runs on            | GitHub Actions (Ubuntu)                  | Your machine                        |
| Parallel execution | Yes (one per issue)                      | No (blocks your session)            |
| Session log        | Gist (automatic)                         | Local only                          |
| Debug access       | Via `erk pr checkout`                    | Immediate                           |
| Model              | Configurable (default `claude-opus-4-6`) | Your interactive session model      |
| Best for           | Parallel work, overnight, batch          | Iterative development, full control |

**Use remote when:** you have multiple plans to run, want to keep working on other things, or want to run plans overnight.

**Use local when:** you need interactive debugging, want immediate feedback, or are iterating on a tricky implementation.

## See Also

- [Use the Local Workflow](local-workflow.md) - Alternative local approach
- [Checkout and Sync PRs](pr-checkout-sync.md) - Debug remote PRs locally
