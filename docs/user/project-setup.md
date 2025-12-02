# Setting Up Your Project for Erk

This guide covers how to configure your repository to work with erk's planning and implementation workflows.

## Directory Structure

Erk uses a `.erk/` directory in your repository root for project-specific configuration:

```
your-repo/
├── .erk/
│   └── post-implement.md    # Custom CI workflow (optional)
├── .impl/                   # Created per-worktree for implementation plans
│   ├── plan.md
│   └── progress.md
└── ...
```

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
