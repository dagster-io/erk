# GitHub Workflows

This directory contains GitHub Actions workflows for the erk project.

## Required Secrets

### GitHub PAT: `ERK_QUEUE_GH_PAT`

A Personal Access Token (PAT) with the following permissions is required for workflows that push commits or trigger other workflows:

**Required permissions:**

- `contents: write` - Push commits to branches
- `workflows` - Trigger workflow_dispatch events

**Why GITHUB_TOKEN isn't sufficient:**

The built-in `GITHUB_TOKEN` has two limitations that require using a PAT:

1. **Git push authentication**: When a workflow checks out code with `GITHUB_TOKEN`, git is not configured with credentials that allow pushing. Using a PAT at checkout time (`actions/checkout` with `token:`) configures git authentication so subsequent `git push` commands work.

2. **Cross-workflow triggers**: `GITHUB_TOKEN` cannot trigger other workflows via `workflow_dispatch`. This is a GitHub security feature to prevent infinite workflow loops. A PAT is required for the `gh workflow run` command.

**Used in:**

- `learn-dispatch.yml` - Checkout (for push), dispatch to erk-impl
- `erk-impl.yml` - Checkout (for push)

### Claude API Secrets

| Secret                    | Purpose                                 | Used in                                                 |
| ------------------------- | --------------------------------------- | ------------------------------------------------------- |
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code CLI authentication          | erk-impl, dignified-python-review, tripwires-review     |
| `ANTHROPIC_API_KEY`       | Anthropic API authentication (fallback) | erk-impl, dignified-python-review, tripwires-review, ci |

## Workflow Overview

| Workflow                      | Trigger               | Purpose                                               |
| ----------------------------- | --------------------- | ----------------------------------------------------- |
| `ci.yml`                      | push, PR              | Run tests, linting, type checking                     |
| `learn-dispatch.yml`          | issue labeled, manual | Create branch and dispatch to erk-impl for extraction |
| `erk-impl.yml`                | workflow_dispatch     | Execute Claude Code to implement plans                |
| `dignified-python-review.yml` | PR                    | Automated Python code review                          |
| `tripwires-review.yml`        | PR                    | Automated tripwire violation detection                |
| `docs.yml`                    | push to master        | Build and deploy documentation                        |
| `build-ci-image.yml`          | manual                | Build Docker image for CI                             |

## Repository Settings

The following repository settings are required:

**Settings > Actions > General > Workflow permissions:**

- Enable "Allow GitHub Actions to create and approve pull requests"

Without this setting, PR creation via `gh pr create` will fail with:
"GitHub Actions is not permitted to create or approve pull requests"
