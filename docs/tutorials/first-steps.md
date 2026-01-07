# First Steps: Create Your First Plan

Create a plan with Claude in under 5 minutes.

**Prerequisites:** Complete [Installation](installation.md).

## What You'll Do

1. Start Claude Code in your project
2. Describe a feature you want to build
3. Watch Claude explore your codebase and create a plan
4. Save the plan to GitHub

By the end, you'll have a GitHub issue containing an implementation plan - ready for Claude to execute.

## Step 1: Start Claude Code

Open your terminal in your project directory:

```bash
cd /path/to/your-project
claude
```

You'll see the Claude Code prompt:

```
╭─────────────────────────────────────────────────────╮
│ Claude Code                                         │
│ Your project directory: /path/to/your-project       │
╰─────────────────────────────────────────────────────╯
>
```

**Verification:** You see the Claude Code prompt with your project path.

## Step 2: Describe Your Feature

Tell Claude what you want to build. Be specific:

```
> I want to add a "hello" command that prints "Hello, World!". Let's plan this.
```

When you mention planning, erk's hooks guide Claude into plan mode.

**What happens:**

- Claude reads your codebase structure
- Claude identifies where commands are defined
- Claude finds patterns to follow

You'll see Claude exploring files:

```
Claude is exploring your codebase...
Reading: src/cli/commands/__init__.py
Reading: src/cli/commands/version.py
...
```

**Verification:** Claude shows it's reading files from your project.

## Step 3: Review the Plan

Claude presents a plan. A good plan includes:

```
# Plan: Add hello command

## Goal
Add a "hello" CLI command that prints "Hello, World!"

## Implementation
1. Create src/cli/commands/hello.py
2. Register command in src/cli/commands/__init__.py
3. Add test in tests/cli/test_hello.py

## Files to Modify
- src/cli/commands/hello.py (create)
- src/cli/commands/__init__.py (modify)
- tests/cli/test_hello.py (create)
```

If you want changes, ask:

```
> Can we also add a --name flag to personalize the greeting?
```

Claude updates the plan.

**Verification:** You see a plan with clear steps and files.

## Step 4: Save to GitHub

When the plan looks good:

```
> The plan looks good. Let's save it.
```

Claude prompts you:

```
📋 Plan: Add hello command
What would you like to do with this plan?
> Save the plan (Recommended)
```

Select "Save the plan". Claude creates a GitHub issue:

```
Plan saved to GitHub issue #42
Title: Add hello command
URL: https://github.com/you/project/issues/42
```

**Verification:**

- You have a GitHub issue number
- Open the URL to see your plan

## What You've Accomplished

In about 5 minutes, you've:

| Step              | Result                            |
| ----------------- | --------------------------------- |
| Started Claude    | Claude connected to your project  |
| Described feature | Claude explored your codebase     |
| Reviewed plan     | Claude wrote implementation steps |
| Saved plan        | GitHub issue #42 created          |

The plan is now tracked in GitHub, separate from any code.

## Next Steps

Your plan is saved. Now implement it:

- [Implementing Your Plan](implementing.md) - Execute the plan in an isolated worktree

## Troubleshooting

**Claude doesn't enter plan mode:**

- Make sure `erk init` was run in your project
- Check `erk doctor` passes

**Plan save fails:**

- Verify GitHub CLI: `gh auth status`
- Check you have push access to the repo
