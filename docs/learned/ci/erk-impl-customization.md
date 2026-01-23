---
title: Customizing erk-impl Workflow via Composite Actions
read_when:
  - customizing erk-impl workflow for a specific repository
  - installing system dependencies in erk-impl CI
  - overriding Python version in erk-impl workflow
---

# Customizing erk-impl Workflow via Composite Actions

## Overview

The `erk-impl.yml` workflow supports per-repository customization via local composite actions. This allows repos to install system dependencies, set environment variables, or specify Python versions without modifying the shared workflow.

## Extension Point

The workflow checks for a local composite action at `.github/actions/erk-impl-setup/action.yml` after checkout. If present, it runs before uv installation.

### Outputs

The composite action can provide outputs that the workflow consumes:

| Output           | Purpose                          | Default |
| ---------------- | -------------------------------- | ------- |
| `python-version` | Python version for uv to install | `3.13`  |

## Example: Repository with System Dependencies

Create `.github/actions/erk-impl-setup/action.yml`:

```yaml
name: "Erk CI Setup"
description: "Repo-specific setup for erk-impl workflow"

outputs:
  python-version:
    description: "Python version to use (default: 3.13)"
    value: ${{ steps.config.outputs.python-version }}

runs:
  using: "composite"
  steps:
    - name: Set configuration
      id: config
      shell: bash
      run: |
        echo "python-version=3.11" >> $GITHUB_OUTPUT

    - name: Install system dependencies
      shell: bash
      run: |
        sudo apt-get update
        sudo apt-get install -y libxml2-dev libxslt-dev libgit2-dev
```

## When to Use

Use a local composite action when your repository needs:

- **System dependencies**: Libraries not available in ubuntu-latest
- **Custom Python version**: Different from the default 3.13
- **Environment variables**: Set before uv/erk installation
- **Pre-installation setup**: Any arbitrary setup steps

## Workflow Behavior

1. **No action exists**: Workflow uses defaults (Python 3.13, no extra setup)
2. **Action exists**: Workflow runs it, then uses its outputs (if any)

The `hashFiles()` check ensures zero overhead for repos without customization.

## Conditional Step Gating

The erk-impl workflow uses step outputs to gate subsequent steps based on implementation results. This allows the workflow to handle error scenarios gracefully without failing.

### has_changes Output Pattern

After the handle-no-changes step, subsequent steps check the `has_changes` output:

```yaml
- name: Submit implementation
  if: steps.handle_outcome.outputs.has_changes == 'true'
  run: erk pr submit ...

- name: Mark PR ready
  if: steps.handle_outcome.outputs.has_changes == 'true'
  run: gh pr ready ...

- name: Run CI
  if: steps.handle_outcome.outputs.has_changes == 'true'
  run: make ci

- name: Trigger learn workflow
  if: steps.handle_outcome.outputs.has_changes == 'true'
  run: ...
```

### When to Add Conditional Gates

Add gating when a step:

- Should only run when actual code changes exist
- Depends on implementation having produced code
- Would fail or produce noise without real changes
- Should be skipped in error scenarios

### Common Gated Steps

The standard erk-impl workflow gates these steps:

| Step          | Reason                             | Condition               |
| ------------- | ---------------------------------- | ----------------------- |
| Submit PR     | Avoid submitting empty PRs         | `has_changes == 'true'` |
| Mark ready    | Only when implementation complete  | `has_changes == 'true'` |
| Run CI        | Unnecessary for empty changes      | `has_changes == 'true'` |
| Trigger learn | Documentation only for actual work | `has_changes == 'true'` |

When `has_changes` is false (no code changes detected), these steps are skipped and the user sees the diagnostic PR with guidance.

## Related Documentation

- [Container-less CI](containerless-ci.md) - General CI setup patterns
- [GitHub Actions Security](github-actions-security.md) - Security patterns for workflows
- [No-Code-Changes Handling](../planning/no-changes-handling.md) - Understanding and resolving no-changes scenarios
