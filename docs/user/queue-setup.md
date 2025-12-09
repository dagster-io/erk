# Setting Up Erk Queue

This guide covers enabling GitHub Actions workflows to create pull requests for the erk implementation queue.

## Overview

The erk queue system allows GitHub Actions workflows to automatically create and manage pull requests. This requires enabling specific permissions in your GitHub repository.

## Prerequisites

- Repository admin access
- `gh` CLI installed and authenticated

## Quick Setup

### 1. Check Current Permissions

```bash
erk admin github-pr-setting
```

This displays the current state of the GitHub Actions PR creation permission.

### 2. Enable PR Creation

```bash
erk admin github-pr-setting --enable
```

This enables GitHub Actions workflows in your repository to create and update pull requests.

### 3. Verify Setup

Run the check command again to verify:

```bash
erk admin github-pr-setting
```

You should see "Current status: Enabled"

## What This Does

When you enable queue permissions, your repository's GitHub Actions workflows gain the ability to:

- Create pull requests
- Update existing pull requests
- Approve pull requests (if configured)

This is required for automated implementation workflows that create PRs from queued issues.

## Security Note

This permission applies to **all** GitHub Actions workflows in your repository. Review your workflows before enabling.

## Disabling Queue Permissions

If you need to disable PR creation for workflows:

```bash
erk admin github-pr-setting --disable
```

## Workflow Configuration

Customize workflow parameters by creating `.erk/workflows/dispatch-erk-queue.toml` in your repository:

```toml
# Kits to install (comma-separated)
kit_names = "erk,gt,devrun"

# Claude model to use
model_name = "claude-sonnet-4-5-20250929"

# Optional: Custom package installation script
package_install_script = "pip install -e ."
```

These values are passed as inputs to the GitHub Actions workflow at dispatch time when running `erk submit`.

### How It Works

1. When you run `erk submit <issue>`, erk looks for a config file at `.erk/workflows/<workflow-name>.toml`
2. The filename matches the workflow file (without the `.yml` extension)
3. Config values are merged with required inputs (issue_number, branch_name, etc.)
4. If no config file exists, the workflow uses its built-in defaults

### Available Parameters

| Parameter                | Description                             | Example                        |
| ------------------------ | --------------------------------------- | ------------------------------ |
| `kit_names`              | Comma-separated list of kits to install | `"erk,gt,devrun"`              |
| `model_name`             | Claude model ID to use                  | `"claude-sonnet-4-5-20250929"` |
| `package_install_script` | Shell commands for package installation | `"pip install -e ."`           |

Note: All values are converted to strings before being passed to the workflow.

## Troubleshooting

**"Resource not accessible by integration"**

- Ensure you have admin access to the repository
- Re-authenticate gh CLI: `gh auth refresh -s admin:repo_hook`

**Permissions not updating**

- Wait a few seconds and try again (GitHub API may have delay)
- Verify you're authenticated: `gh auth status`

## TODO

- [ ] Add workflow configuration guide
- [ ] Document label-based queue triggering
- [ ] Add security best practices
- [ ] Document integration with existing workflows

## See Also

- [GitHub Actions Permissions](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#permissions-for-the-github_token)
- TODO: Link to erk queue architecture docs
