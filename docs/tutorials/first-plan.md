# Your First Plan

This tutorial walks you through erk's complete workflow: creating a plan, saving it to GitHub, implementing it, and landing the PR. You'll build a simple CLI chatbot and add features to it.

**Prerequisites:** Complete [Installation](installation.md) and verify with `erk doctor`.

## Step 1: Clone the Starter Project

Clone the tutorial starter repo using the GitHub CLI. This front-loads authentication—if there are any issues, you'll discover them now:

```bash
gh repo create say --template dagster-io/erk-tutorial --public --clone
cd say
```

If prompted to authenticate, follow the instructions.

The starter is a Python project using modern tools: uv, ruff, ty, pytest, and, of course, erk.

Verify the setup:

```bash
uv run say
```

You should see a `>` prompt. Type something and press Enter—it echoes back. Press Ctrl+C to exit.

## Step 2: Plan Your First Feature

`erk` is built around a **plan → implement** cycle. We believe explicit planning is critical for agentic engineering: you get better outcomes, more precise control, and can perform larger units of work more confidently and autonomously.

We'll demonstrate this using Plan Mode in Claude Code to add a simple feature.

Start a new session:

```bash
claude
```

Ask Claude to plan adding a `/quit` command:

```
I want to add a /quit command that exits the loop gracefully with a "bye" message. Let's plan this.
```

Claude enters plan mode. You can also enter plan mode anytime by pressing **Shift+Tab** to cycle through modes (Auto → Plan → Auto).

You'll see Claude exploring the codebase—reading files, understanding the CLI structure, finding where the input loop lives, and identifying patterns to follow. When it finishes exploring, it presents a plan for your review.

## Step 3: Develop the Plan

This is a simple feature, so the plan should be straightforward: modify the input loop to check for `/quit`, print "bye", and exit. Review what Claude proposes and continue when you're satisfied.

## Step 4: Save the Plan to GitHub

When the plan is ready, Claude prompts you for next steps.

### `erk` Extends Plan Mode

Standard Claude Code plan mode shows this menu when you approve:

```
○ Start implementation
○ Edit the plan
```

`erk` extends this with additional options:

```
○ Save the plan          # Save as GitHub issue, stop here
○ Implement              # Save to GitHub, then implement
○ Incremental            # Implement directly (for quick iterations)
○ View/Edit the plan
```

Choose **Save the plan**. Claude runs `/erk:plan-save`, which:

1. Creates a GitHub issue with your plan
2. Adds the `erk-plan` label
3. Returns the issue number

You'll see output like:

```
Plan saved as issue #1
```

### Why Save to GitHub?

When you develop a plan in Claude Code, it normally lives only in the conversation—easy to lose when you close the session. By saving as a GitHub issue:

- **The plan persists** beyond your session
- **Anyone can implement it**—you, a teammate, or a CI agent
- **Progress is tracked effortlessly** through GitHub's issue system

## Step 5: Implement the Plan

The standard erk workflow implements each plan in its own **worktree**, which is ideal for organizing and parallelizing your work.

### What's a Worktree?

Git worktrees let you have multiple branches checked out simultaneously in separate directories. Instead of switching branches in your main directory, erk creates a new directory with the feature branch—completely isolated.

This isolation is powerful: an agent can implement your plan in one worktree while you continue working in another.

To switch to the new worktree, we first exit Claude Code:

```
/exit
```

Now run `erk implement`:

```bash
erk implement 1
```

This command:

1. **Creates a worktree** with a new feature branch
2. **Starts Claude Code** in that worktree with the plan loaded
3. **Claude implements** each step from the plan

Your plan is now implementing. While Claude works, let's see what else we can do.

### Work in Parallel

Open a **new terminal** and return to your main worktree:

```bash
cd ~/say
```

From here, you can monitor progress with the erk dashboard:

```bash
erk dash
```

This launches an interactive TUI showing all your plans and their implementation status. You can watch progress here, or start planning something else entirely—the implementation continues in its own worktree.

## Step 6: Submit the PR

When the implementation finishes, switch back to the worktree:

```bash
erk br co P1-quit-command
```

(Your branch name will match the issue title.)

Now submit the PR:

```bash
erk pr submit
```

This creates a pull request linked to the original issue.

## Step 7: Land the PR

For this tutorial, you can merge your own PR. Once ready:

```bash
erk land
```

This:

1. Merges the PR
2. Closes the linked issue
3. Deletes the feature branch
4. Frees the worktree for reuse
5. Returns you to the main worktree

## What You've Learned

You've completed the full erk workflow:

| Phase         | What Happened                                      |
| ------------- | -------------------------------------------------- |
| **Plan**      | Created a detailed implementation plan with Claude |
| **Save**      | Stored the plan as a GitHub issue for tracking     |
| **Implement** | Executed the plan in an isolated worktree          |
| **Submit**    | Created a PR linked to the original issue          |
| **Land**      | Merged and cleaned up automatically                |

## Quick Reference

| Task           | Command                 |
| -------------- | ----------------------- |
| Start Claude   | `claude`                |
| Save plan      | `/erk:plan-save`        |
| Exit Claude    | `/exit`                 |
| Implement plan | `erk implement <issue>` |
| Monitor plans  | `erk dash`              |
| Submit PR      | `erk pr submit`         |
| Land PR        | `erk land`           |

## Next Steps

- [The Workflow](../topics/the-workflow.md) - Conceptual understanding of plan-oriented development
- [CLI Command Reference](../ref/commands.md) - All available commands
