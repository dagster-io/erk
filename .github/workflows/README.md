# GitHub Workflows

This directory contains GitHub Actions workflows for the erk project.

## Required Secrets

### GitHub PAT: `ERK_QUEUE_GH_PAT`

A Personal Access Token (PAT) with the following permissions is required for workflows that push commits, dispatch other workflows, or upload workflow session artifacts:

**Required permissions:**

- `contents: write` - Push commits to branches
- `workflows` - Trigger workflow_dispatch events
- `gist` - Create gists for session log storage

**Why GITHUB_TOKEN isn't sufficient:**

The built-in `GITHUB_TOKEN` has two limitations that require using a PAT:

1. **Git push authentication**: When a workflow checks out code with `GITHUB_TOKEN`, git is not configured with credentials that allow pushing. Using a PAT at checkout time (`actions/checkout` with `token:`) configures git authentication so subsequent `git push` commands work.

2. **Cross-workflow triggers**: `GITHUB_TOKEN` cannot trigger other workflows via `workflow_dispatch`. This is a GitHub security feature to prevent infinite workflow loops. A PAT is required for the `gh workflow run` command.

**Used in:**

- `ci.yml` - `fix-formatting` checkout for auto-push
- `learn.yml` - Checkout, branch updates, dispatch to `plan-implement`
- `one-shot.yml` - Remote setup and PR submission
- `plan-implement.yml` - Remote setup, push, and session uploads
- `pr-address.yml` - Remote setup for Claude-driven PR updates
- `pr-rebase.yml` - Remote setup for rebase operations
- `pr-rewrite.yml` - Remote setup for rewrite operations

### Claude API Secrets

| Secret                    | Purpose                                 | Used in                                                                                              |
| ------------------------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code CLI authentication          | `code-reviews`, `learn`, `one-shot`, `plan-implement`, `pr-address`, `pr-rebase`, `pr-rewrite`       |
| `ANTHROPIC_API_KEY`       | Anthropic API authentication (fallback) | `ci`, `code-reviews`, `learn`, `one-shot`, `plan-implement`, `pr-address`, `pr-rebase`, `pr-rewrite` |

## Workflow Overview

| Workflow             | Trigger               | Purpose                                                     |
| -------------------- | --------------------- | ----------------------------------------------------------- |
| `ci.yml`             | push, PR, manual      | Repo-local formatting, validation, and CI failure summaries |
| `code-reviews.yml`   | PR                    | Convention-based shipped review capability entrypoint       |
| `docs-site.yml`      | manual                | Build and deploy the docs-site                              |
| `learn.yml`          | issue labeled, manual | Create a branch and dispatch learning work                  |
| `one-shot.yml`       | manual                | Plan and implement a task in one remote workflow            |
| `plan-implement.yml` | manual                | Execute Claude Code to implement a saved plan               |
| `pr-address.yml`     | manual                | Address PR feedback with Claude                             |
| `pr-rebase.yml`      | manual                | Rebase a PR with AI-assisted conflict handling              |
| `pr-rewrite.yml`     | manual                | Rewrite a PR branch with Claude                             |

## Repository Settings

The following repository settings are required:

**Settings > Actions > General > Workflow permissions:**

- Enable "Allow GitHub Actions to create and approve pull requests"

Without this setting, PR creation via `gh pr create` will fail with:
"GitHub Actions is not permitted to create or approve pull requests"
