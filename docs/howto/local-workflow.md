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

## Step 2: Enter Plan Mode

Press **Shift+Tab** or describe a task that requires planning. Claude enters plan mode and shows "plan" in the status line.

In plan mode, Claude researches your codebase and designs an implementation approach without making changes.

## Step 3: Develop Your Plan

Describe your goal and let Claude explore. Provide feedback to refine the approach:

- Point out constraints or preferences
- Ask about alternative approaches
- Request clarification on specific steps

The plan should cover what changes to make, why, and in what order.

## Step 4: Save the Plan

When the plan is ready, Claude presents options:

| Option             | Action                                              |
| ------------------ | --------------------------------------------------- |
| **Save to GitHub** | Creates a GitHub issue with the plan (for later)    |
| **Implement now**  | Saves to GitHub and immediately starts implementing |

Choose "Implement now" to continue in the same session. Choose "Save to GitHub" to defer implementation—useful when you want to review the plan, assign to a remote worker, or implement later.

## Step 5: Implement the Plan

If you chose "Implement now", implementation starts automatically. If you saved for later, start implementation with:

```bash
erk implement <issue-number>
```

This command:

1. Fetches the plan from the GitHub issue
2. Creates a worktree with a feature branch
3. Sets up the `.impl/` folder
4. Starts a Claude Code session to execute the plan

The agent follows the plan phases, writes code and tests, and runs CI checks.

## Step 6: Submit the PR

After implementation completes and CI passes, submit the PR:

```bash
erk pr submit
```

Or from within Claude Code:

```
/erk:pr-submit
```

This generates a commit message from the diff, pushes the branch, and creates or updates the PR with a summary linking to the plan issue.

## Step 7: Address Review Feedback

When reviewers leave comments, address them with:

```
/erk:pr-address
```

This fetches PR comments and unresolved review threads, then makes the requested changes. Run CI and submit again after addressing feedback.

## Step 8: Land the PR

Once approved and CI passes, merge the PR:

```bash
erk pr land
```

This merges via GitHub, closes the plan issue, and cleans up the worktree. Add `--up` to navigate to a stacked branch after landing.

## Quick Iteration

For small changes that don't need full planning:

```
/local:quick-submit
```

This commits all changes with an auto-generated message and submits immediately. Use for typo fixes, documentation updates, or iterative tweaks during review.

## See Also

- [Your First Plan](../tutorials/first-plan.md) - Tutorial walkthrough
- [The Workflow](../topics/the-workflow.md) - Conceptual overview
