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

The standard erk workflow implements each plan in its own **worktree**.

### What's a Worktree?

Git worktrees let you have multiple branches checked out simultaneously in separate directories. Instead of switching branches in your main directory, erk creates a new directory with the feature branch—completely isolated.

### Prepare the Worktree

First, exit Claude Code:

```
/exit
```

Now prepare a worktree for your plan:

```bash
erk prepare 1
```

This creates a worktree with the plan's content. You'll see output like:

```
Created branch: P1-quit-command
✓ Assigned P1-quit-command to slot-1
Created .impl/ folder from issue #1

To activate and start implementation:
  source /Users/you/.erk/repos/say/worktrees/slot-1/.erk/bin/activate.sh && erk implement  (copied to clipboard)
```

### Activate and Implement

The activation command is automatically copied to your clipboard. Just paste and run it:

```bash
source /path/to/slot-1/.erk/bin/activate.sh && erk implement
```

This does two things:

1. **Activates** the worktree environment (changes directory, sets up venv, loads .env)
2. **Starts Claude Code** with the plan loaded

Your plan is now implementing.

### Work in Parallel

Open a **new terminal** and return to your main directory:

```bash
cd ~/say
```

From here, you can monitor progress with the erk dashboard:

```bash
erk dash
```

This launches an interactive TUI showing all your plans and their implementation status.

## Step 6: Submit the PR

When the implementation finishes, you're already in the worktree. Submit the PR:

```bash
erk pr submit
```

This creates a pull request linked to the original issue.

## Step 7: Land the PR

For this tutorial, merge your own PR:

```bash
erk land
```

This:

1. Merges the PR
2. Closes the linked issue
3. Deletes the feature branch
4. Frees the worktree for reuse

After landing, return to your main repo:

```bash
cd ~/say
```

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

| Task                 | Command                                        |
| -------------------- | ---------------------------------------------- |
| Start Claude         | `claude`                                       |
| Save plan            | `/erk:plan-save`                               |
| Exit Claude          | `/exit`                                        |
| Prepare worktree     | `erk prepare <issue>`                          |
| Activate + implement | `source .erk/bin/activate.sh && erk implement` |
| Monitor plans        | `erk dash`                                     |
| Submit PR            | `erk pr submit`                                |
| Land PR              | `erk land`                                     |

## Next Steps

- [The Workflow](../topics/the-workflow.md) - Conceptual understanding of plan-oriented development
- [CLI Command Reference](../ref/commands.md) - All available commands
