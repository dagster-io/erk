# Use the Local Workflow

Plan, implement, and ship code locally.

## Overview

The local workflow is the standard development cycle with erk: plan your changes in Claude Code, save the plan to GitHub, implement in a worktree, and ship via PR. Use this when you're developing on your own machine and want full control over the process.

## Step 1: Start a Claude Code Session

Open your terminal in any erk-initialized repository and run:

```bash
claude
```

This starts an interactive Claude Code session with access to erk's slash commands and skills.

## Step 2: Enter Plan Mode and Develop Your Plan

Press **Shift+Tab** or describe a task that requires planning. Claude enters plan mode and shows "plan" in the status line.

In plan mode, Claude researches your codebase and designs an implementation approach without making changes. The plan should cover what changes to make, why, and in what order.

## Step 3: Save the Plan

When the plan is ready, Claude presents options:

| Option             | Action                                              |
| ------------------ | --------------------------------------------------- |
| **Save to GitHub** | Creates a GitHub issue with the plan (for later)    |
| **Implement now**  | Saves to GitHub and immediately starts implementing |

_If you are familiar with Claude Code, you'll note that these options are different when you use `erk`. This is deliberate._

The standard workflow in `erk` is to save the plan to GitHub. There are cases where it makes sense to implement the plan immediately, but we will not be doing that in this guide.

Saving the plan in GitHub makes it easy to access from either a different worktree or a remote worker.

## Step 4: Implement the Plan

Copy and paste the implement command you see, and exit Claude. Then run it:

```bash
erk implement <issue-number>
```

This command:

1. Assigns or creates a worktree with a feature branch.
2. Switches working directory to that worktree.
3. Launches Claude Code, fetches the plan, begins implementation.

## Step 5: Submit the PR

Upon successful implementation, `/erk:pr-submit` will automatically run in the Claude session. This generates a commit message from the diff, pushes the branch, and creates or updates the PR with a summary linking to the plan issue.

If you need to run this manually later you can run it from the CLI (`erk pr submit`) or use `/erk:pr-submit` within a Claude session.

## Step 6: Address Review Feedback

`erk` is designed to incorporate PR review into the workflow, even if you are working alone. Think of the PR as a continuation of the Claude Code session. You (or agents or your collaborators) leave comments in the context of the relevant code. Then within a claude session in the relevant branch you can run:

```
/erk:pr-address
```

This fetches PR comments and unresolved review threads, then makes the requested changes. Run CI and submit again after addressing feedback.

## Step 7: Land the PR

Once approved and CI passes, merge the PR:

```bash
erk land
```

This merges via GitHub, closes the plan issue, deletes the branch, and cleans up the worktree. Add `--up` to navigate to a stacked branch after landing. It also plugs into other workflows, such as objectives and learning, which are covered in other guides.

## See Also

- [Your First Plan](../tutorials/first-plan.md) - Tutorial walkthrough
- [The Workflow](../topics/the-workflow.md) - Conceptual overview
