# Setting Up Your Project for Erk

This guide covers how to configure your repository to work with erk's planning and implementation workflows.

## Prerequisites

### Install Kits

Install the kits that provide erk's slash commands and agents:

```bash
# Install the erk kit (provides /erk:* commands and agents)
erk kit install erk

# Verify installation
erk kit list
```

The erk kit includes:

- **Commands**: `/erk:plan-implement`, `/erk:save-plan`, `/erk:replan`, etc.
- **Agents**: `issue-wt-creator`, `plan-extractor`
- **Workflows**: GitHub Actions templates for erk queue processing

### Optional: Install Related Kits

For the full erk experience, consider installing these complementary kits:

```bash
# Graphite integration for stacked PRs
erk kit install gt

# Development runner for CI iteration
erk kit install devrun

# Python coding standards (if your project uses Python)
erk kit install dignified-python
```

## Directory Structure

Erk uses specific directories in your repository:

```
your-repo/
├── .erk/
│   ├── post-implement.md    # Custom CI workflow (optional)
│   └── scratch/             # Session-specific temporary files
├── .impl/                   # Created per-worktree for implementation plans
│   ├── plan.md
│   ├── progress.md
│   └── issue.json
├── .github/
│   └── workflows/
│       └── erk/             # Installed erk GitHub Actions (from kit)
└── ...
```

## .gitignore Configuration

Add these entries to your `.gitignore` to exclude erk's temporary and session-specific files:

```gitignore
# Erk temporary files
.erk/scratch/
.impl/
```

**Why these are ignored:**

- **`.erk/scratch/`**: Session-specific scratch storage. Each Claude session creates temporary files here scoped by session ID. These are ephemeral and should not be committed.
- **`.impl/`**: Implementation plan files created per-worktree. These track in-progress work and are deleted after successful PR submission.

## Post-Implementation CI Configuration

After erk completes a plan implementation, it runs CI validation. You can customize this workflow by creating `.erk/post-implement.md`.

### How It Works

1. When `/erk:plan-implement` finishes implementing a plan, it checks for `.erk/post-implement.md`
2. If found, erk follows the instructions in that file for CI validation
3. If not found, erk skips automated CI and prompts you to run it manually

### Example: Python Project

For a Python project using a Makefile for CI, create `.erk/post-implement.md`:

```markdown
# Post-Implementation CI

Run CI validation after plan implementation using `make ci`.

@.claude/docs/ci-iteration.md
```

The `@` reference includes your CI iteration documentation, keeping the CI process in one place.

If you don't have a shared CI iteration doc, you can inline the instructions:

```markdown
# Post-Implementation CI

Run CI validation after plan implementation.

## CI Command

Use the Task tool with subagent_type `devrun` to run `make ci`:

    Task(
        subagent_type="devrun",
        description="Run make ci",
        prompt="Run make ci from the repository root. Report all failures."
    )

## Iteration Process (max 5 attempts)

1. Run `make ci` via devrun agent
2. If all checks pass: Done
3. If checks fail: Apply targeted fixes (e.g., `make fix`, `make format`)
4. Re-run CI
5. If max attempts reached without success: Exit with error

## Success Criteria

All checks pass: linting, formatting, type checking, tests.
```

## What's Next

More configuration options coming soon:

- Custom worktree naming conventions
- Project-specific planning templates
- Integration with project-specific tooling
