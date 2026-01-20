# Setting Up Your Project for Erk

> **Audience**: This guide is for **project maintainers** setting up erk in a repository for the first time. If you're a developer joining a repo that already has erk configured, see [Developer Onboarding](developer-onboarding.md) instead.

This guide covers how to configure your repository to work with erk's planning and implementation workflows.

## Step 1: Initialize Erk

First, initialize erk in your repository:

```bash
erk init
```

This creates the `erk.toml` configuration file in your repository root.

## Step 2: Directory Structure

Erk uses specific directories in your repository:

```
your-repo/
├── .erk/
│   ├── prompt-hooks/        # Customizable prompt overrides (optional)
│   │   ├── post-plan-implement-ci.md  # Custom CI workflow
│   │   └── commit-message-prompt.md   # Custom commit message format
│   └── scratch/             # Session-specific temporary files
├── .impl/                   # Created per-worktree for implementation plans
│   ├── plan.md
│   ├── progress.md
│   └── issue.json
├── .github/
│   └── workflows/
│       └── erk/             # Erk GitHub Actions
└── ...
```

## Step 3: Configure .gitignore

Add these entries to your `.gitignore` to exclude erk's temporary and session-specific files:

```gitignore
# Erk temporary files
.erk/scratch/
.impl/
```

**Why these are ignored:**

- **`.erk/scratch/`**: Session-specific scratch storage. Each Claude session creates temporary files here scoped by session ID. These are ephemeral and should not be committed.
- **`.impl/`**: Implementation plan files created per-worktree. These track in-progress work and are deleted after successful PR submission.

## Step 4: Commit Your Setup

After completing the setup, commit the following files to git:

- **`erk.toml`** - Project configuration (created by `erk init`)
- **`.claude/`** - Claude Code artifacts (commands, skills, hooks)
- **`.gitignore`** - Updated exclusions for erk temporary files

This makes the erk configuration available to all team members who clone the repository.

## Prompt Hooks

Prompt hooks let you customize how erk's AI-powered features behave. They live in `.erk/prompt-hooks/` and are markdown files that override or extend default prompts.

### Available Prompt Hooks

| Hook File                   | Purpose                                        |
| --------------------------- | ---------------------------------------------- |
| `post-plan-implement-ci.md` | Custom CI workflow after plan implementation   |
| `commit-message-prompt.md`  | Custom prompt for PR/commit message generation |

---

### Post-Implementation CI (`post-plan-implement-ci.md`)

After erk completes a plan implementation, it runs CI validation. You can customize this workflow by creating `.erk/prompt-hooks/post-plan-implement-ci.md`.

**How It Works:**

1. When `/erk:plan-implement` finishes implementing a plan, it checks for this file
2. If found, erk follows the instructions in that file for CI validation
3. If not found, erk skips automated CI and prompts you to run it manually

**Example: Python Project**

For a Python project using a Makefile for CI:

```markdown
# Post-Implementation CI

Run CI validation after plan implementation using `make ci`.

Load the `ci-iteration` skill for the iterative fix workflow.
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

---

### Commit Message Prompt (`commit-message-prompt.md`)

Customize how erk generates PR titles and commit messages. This hook completely replaces the default prompt used when running `erk pr submit`, `/erk:pr-submit`, and related commands.

**How It Works:**

1. When erk generates a commit message or PR description, it checks for `.erk/prompt-hooks/commit-message-prompt.md`
2. If found, it uses this prompt instead of the built-in default
3. If not found, it uses the built-in prompt

**Use Cases:**

- Enforce your team's commit message conventions (Conventional Commits, etc.)
- Add project-specific context or terminology
- Include custom formatting requirements
- Reference internal documentation or style guides

**Example: Conventional Commits**

```markdown
# Commit Message Generator

Generate a commit message following Conventional Commits format.

## Format
```

<type>(<scope>): <description>

[optional body]

[optional footer(s)]

```

## Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, missing semi-colons, etc.)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding or correcting tests
- `chore`: Build process, tooling, or dependencies

## Rules

1. First line must be 50 characters or less
2. Use imperative mood ("add feature" not "added feature")
3. Body should explain WHY, not WHAT (the diff shows what)
4. Reference issue numbers in footer if applicable

## Output

Analyze the diff and generate ONLY the commit message. No explanations.
```

**Example: Simple Format**

```markdown
# Commit Message Generator

Generate a concise commit message for the provided diff.

## Format

- Title: One line, max 72 characters, imperative mood
- Body: Brief explanation of the change (2-3 sentences max)

Focus on what changed and why. Be concise.

## Output

Generate ONLY the commit message text. No markdown code fences or explanations.
```

## What's Next

More configuration options coming soon:

- Custom worktree naming conventions
- Project-specific planning templates
- Integration with project-specific tooling
