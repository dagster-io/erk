# erk

`erk` is a CLI tool for plan-oriented agentic engineering: create implementation plans with AI, save them to GitHub, execute them in isolated worktrees, and ship code via automated PR workflows.

**[Read the Documentation](https://dagster-io.github.io/erk/)** for complete guides, tutorials, and reference. ([source](docs/))

For the philosophy and design principles behind erk, see [The TAO of erk](docs/TAO.md).

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

Then follow [Your First Plan](docs/tutorials/first-plan.md) to learn the workflow.

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

See [The Workflow](docs/topics/the-workflow.md) for the complete guide.

## Documentation

| Section                      | Description                              |
| ---------------------------- | ---------------------------------------- |
| [Tutorials](docs/tutorials/) | Setup, installation, first plan tutorial |
| [Topics](docs/topics/)       | Worktrees, stacked PRs, plan mode        |
| [How-to Guides](docs/howto/) | Workflows for common tasks               |
| [Reference](docs/ref/)       | Commands, configuration, file locations  |
| [FAQ](docs/faq/)             | Common questions and troubleshooting     |
