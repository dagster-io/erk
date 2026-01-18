---
title: Prompt Hooks Guide
read_when:
  - "creating prompt hooks"
  - "customizing post-init setup"
  - "customizing CI workflow"
  - "understanding prompt hooks vs claude hooks"
---

# Prompt Hooks Guide

Prompt hooks are markdown files that provide AI-readable instructions at specific workflow points. They are **different from Claude Code hooks** (which execute shell commands).

## What Are Prompt Hooks?

| Aspect   | Claude Code Hooks            | Prompt Hooks             |
| -------- | ---------------------------- | ------------------------ |
| Location | `.claude/settings.json`      | `.erk/prompt-hooks/*.md` |
| Format   | JSON config + shell commands | Markdown instructions    |
| Executor | Shell/Python scripts         | Claude AI agent          |
| Purpose  | Automation, validation       | AI-guided workflows      |

## Available Prompt Hooks

### `post-init.md` — New Developer Setup

**When:** After `erk init` completes (auto-executed by Claude via the [auto-execution pattern](../cli/auto-execution-pattern.md))

**Purpose:** Project-specific setup for developers joining the project.

**Example use cases:**

- Create symlinks to related repositories
- Install project-specific tools
- Configure local environment variables
- Set up database or service connections

**Example:**

```markdown
# Post-Init Setup

## Symlink OSS Dagster

Create symlink to local dagster checkout for development:

1. Check if ~/code/dagster exists
2. If yes, create symlink: ln -s ~/code/dagster .dagster-oss
3. If no, skip (optional dependency)

## Install Pre-commit Hooks

Run: pre-commit install
```

### `post-plan-implement-ci.md` — CI Workflow After Implementation

**When:** After `/erk:system:impl-execute` completes implementation

**Purpose:** Define CI validation and iteration strategy.

**Example:**

```markdown
# Post-Implementation CI

Run CI validation using `make fast-ci`.

Load the `ci-iteration` skill for the iterative fix workflow.

## Iteration Process

1. Run `make fast-ci` via devrun agent
2. If checks fail: apply targeted fixes
3. Re-run CI (max 5 iterations)
4. On success: proceed to PR creation
```

## Creating a Prompt Hook

1. Create `.erk/prompt-hooks/<hook-name>.md`
2. Write instructions in imperative mood for the AI agent
3. Include specific commands, expected outcomes
4. Reference skills to load if needed

## Best Practices

- **Be specific:** Exact commands, not vague instructions
- **Define success:** Clear exit criteria
- **Reference skills:** Load relevant skills for specialized workflows
- **Version control:** Commit hooks with your project
- **Keep focused:** One workflow per hook

## Checking Hook Status

Run `erk doctor` to see which prompt hooks are configured:

```
✓ Post-init hook configured (.erk/prompt-hooks/post-init.md)
ℹ No CI instructions hook (.erk/prompt-hooks/post-plan-implement-ci.md)
```
