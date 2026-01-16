# erk

`erk` is a CLI tool for plan-oriented agentic engineering: create implementation plans with AI, save them to GitHub, execute them in isolated worktrees, and ship code via automated PR workflows.

**[Read the Documentation](https://dagster-io.github.io/erk/)** for complete guides, tutorials, and reference. ([source](docs/))

For the philosophy and design principles behind erk, see [The TAO of erk](TAO.md).

## Quick Start

```bash
# Install prerequisites: python 3.10+, claude, uv, gt, gh

# Install erk in your project
uv add erk && uv sync

# Initialize in your repo
erk init

# Verify setup
erk doctor
```

Then follow [Your First Plan](docs/getting-started/first-plan.md) to learn the workflow.

## The Workflow

The primary workflow: plan → save → implement → ship. **Often completes without touching an IDE.**

```bash
# 1. Plan (in Claude Code)
claude
# → develop plan → save to GitHub issue #42

# 2. Implement
erk implement 42

# 3. Submit PR
erk pr submit

# 4. Address feedback
/erk:pr-address

# 5. Land
erk land
```

See [The Workflow](docs/concepts/the-workflow.md) for the complete guide.

## Documentation

| Section                                  | Description                             |
| ---------------------------------------- | --------------------------------------- |
| [Getting Started](docs/getting-started/) | Setup, installation, first tutorial     |
| [Concepts](docs/concepts/)               | Worktrees, stacked PRs, plan mode       |
| [Guides](docs/guides/)                   | Workflows for common tasks              |
| [Reference](docs/reference/)             | Commands, configuration, file locations |
| [Troubleshooting](docs/troubleshooting/) | Common issues and solutions             |
