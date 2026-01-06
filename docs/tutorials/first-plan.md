# Your First Plan

This tutorial walks you through erk's complete workflow: creating a plan, saving it to GitHub, implementing it, and landing the PR. By the end, you'll understand how plan-oriented engineering works in practice.

**Time to complete:** 15-20 minutes

**Prerequisites:** Complete [Installation](installation.md) and verify with `erk doctor`.

## The Scenario

We'll add a simple feature to an existing project. The specific change doesn't matter—what matters is learning the workflow. Pick any small feature you've been meaning to add, like:

- Adding a new CLI command
- Creating a utility function
- Adding a configuration option

For this tutorial, we'll use "add a greeting command" as our example.

## Step 1: Start a Claude Code Session

Open your terminal in your project directory and start Claude Code:

```bash
claude
```

You'll see the Claude Code prompt, ready to accept your request.

## Step 2: Enter Plan Mode

Ask Claude to help you plan the feature. When you mention planning, erk's hooks will guide Claude into plan mode:

```
I want to add a "greet" command that prints a welcome message. Let's plan this out.
```

Claude will enter plan mode and begin exploring your codebase to understand:

- Where CLI commands are defined
- What patterns existing commands follow
- What tests exist for commands

## Step 3: Develop Your Plan

Work with Claude to refine the plan. Good plans include:

- **What** you're building (the feature)
- **Where** the changes go (specific files)
- **How** it fits existing patterns (conventions to follow)
- **Tests** to verify it works

Claude will write the plan to a file. Review it and suggest changes:

```
Can we also add a --name flag to personalize the greeting?
```

Keep iterating until the plan covers everything needed.

## Step 4: Save the Plan to GitHub

When you're satisfied with the plan, tell Claude you're ready:

```
The plan looks good. Let's save it.
```

Erk prompts you to save the plan to GitHub as an issue. Choose "Save" when prompted.

Claude runs `/erk:plan-save`, which:

1. Creates a GitHub issue with your plan
2. Adds the `erk-plan` label
3. Returns the issue number

You'll see output like:

```
Plan saved as issue #42
```

**Note the issue number**—you'll use it next.

## Step 5: Exit Claude Code

Exit the Claude Code session:

```
/exit
```

You're back at your terminal. The plan is now tracked in GitHub, separate from any implementation.

## Step 6: Implement the Plan

Run `erk implement` with your issue number:

```bash
erk implement 42
```

This command:

1. **Creates a worktree** with a new feature branch
2. **Changes to that directory** (shell integration required)
3. **Starts Claude Code** with the plan loaded
4. **Claude implements** each step from the plan

Watch as Claude:

- Creates the command file
- Adds the `--name` flag
- Writes tests
- Runs the test suite

## Step 7: Review the Implementation

When Claude finishes, it reports what was done. Review the changes:

```bash
git diff
```

Check that:

- The command works: `your-cli greet --name "World"`
- Tests pass: `pytest`
- Code follows project conventions

If something needs adjustment, iterate with Claude:

```
The greeting should be more enthusiastic. Can you add an exclamation point?
```

## Step 8: Submit the PR

When you're satisfied with the implementation, submit the PR:

```bash
erk pr submit
```

Or from within Claude Code:

```
/erk:pr-submit
```

This creates a pull request linked to the original issue.

## Step 9: Address Review Feedback

After reviewers comment on your PR, address their feedback:

```
/erk:pr-address
```

Claude reads the PR comments and makes the requested changes. Repeat until approved.

## Step 10: Land the PR

Once approved, merge and clean up:

```bash
erk pr land
```

This:

1. Merges the PR
2. Deletes the feature branch
3. Removes the worktree
4. Returns you to the main worktree

## What You've Learned

You've completed the full erk workflow:

| Phase         | What Happened                                      |
| ------------- | -------------------------------------------------- |
| **Plan**      | Created a detailed implementation plan with Claude |
| **Save**      | Stored the plan as a GitHub issue for tracking     |
| **Implement** | Executed the plan in an isolated worktree          |
| **Submit**    | Created a PR linked to the original issue          |
| **Iterate**   | Addressed review feedback with AI assistance       |
| **Land**      | Merged and cleaned up automatically                |

The entire workflow—from planning to merged PR—happened without opening an IDE.

## Tips for Effective Planning

1. **Be specific about patterns**: "Follow the pattern in `existing_command.py`"
2. **Include test requirements**: "Add unit tests for the new function"
3. **Mention edge cases**: "Handle the case where name is empty"
4. **Reference existing code**: "Use the same error handling as `other_function`"

## Next Steps

- [Use the Local Workflow](../howto/local-workflow.md) - More details on daily usage
- [The Workflow](../topics/the-workflow.md) - Conceptual understanding
- [Work Without Plans](../howto/planless-workflow.md) - When you don't need a full plan
- [CLI Command Reference](../ref/commands.md) - All available commands

## Quick Reference

| Task             | Command                 |
| ---------------- | ----------------------- |
| Start Claude     | `claude`                |
| Save plan        | `/erk:plan-save`        |
| Exit Claude      | `/exit`                 |
| Implement plan   | `erk implement <issue>` |
| Submit PR        | `erk pr submit`         |
| Address feedback | `/erk:pr-address`       |
| Land PR          | `erk pr land`           |
