---
title: Customizing erk-impl Workflow via Composite Actions
last_audited: "2026-03-02 15:00 PT"
audit_result: clean
read_when:
  - customizing erk-impl workflow for a specific repository
  - installing system dependencies in erk-impl CI
  - configuring Python version for erk remote workflows
---

# Customizing erk-impl Workflow via Composite Actions

## Overview

The `plan-implement.yml` workflow supports per-repository customization via local composite actions. This allows repos to install system dependencies or set environment variables without modifying the shared workflow.

## Python Version

Python version is auto-discovered by uv from standard repo config — no erk-specific configuration needed. uv checks (in order):

1. `.python-version` file in the repo root
2. `requires-python` in `pyproject.toml`
3. System Python / auto-download

To control which Python version erk remote workflows use, add a `.python-version` file to your repo root (e.g., `3.11`).

## Extension Point

The workflow checks for a local composite action at `.github/actions/erk-impl-setup/action.yml` after checkout. If present, it runs before uv installation.

## Example: Repository with System Dependencies

Create `.github/actions/erk-impl-setup/action.yml`:

```yaml
name: "Erk CI Setup"
description: "Repo-specific setup for erk-impl workflow"

runs:
  using: "composite"
  steps:
    - name: Install system dependencies
      shell: bash
      run: |
        sudo apt-get update
        sudo apt-get install -y libxml2-dev libxslt-dev libgit2-dev
```

## When to Use

Use a local composite action when your repository needs:

- **System dependencies**: Libraries not available in ubuntu-latest
- **Environment variables**: Set before uv/erk installation
- **Pre-installation setup**: Any arbitrary setup steps

## Workflow Behavior

1. **No action exists**: Workflow uses defaults (no extra setup)
2. **Action exists**: Workflow runs it, then uses its outputs (if any)

The `hashFiles()` check ensures zero overhead for repos without customization.

## Step Output Gating Pattern

The erk-impl workflow uses step outputs to conditionally execute downstream steps based on implementation results.

### `has_changes` Gating

After implementation, the workflow checks if any code changes were produced:

```yaml
- name: Check implementation outcome
  id: handle_outcome
  run: |
    CHANGES=$(git diff --name-only origin/$BASE_BRANCH)
    if [ -z "$CHANGES" ]; then
      echo "has_changes=false" >> $GITHUB_OUTPUT
    else
      echo "has_changes=true" >> $GITHUB_OUTPUT
    fi

- name: Submit branch
  if: steps.handle_outcome.outputs.has_changes == 'true'
  run: |
    # Only runs if there are actual changes
```

### When to Add Gating

Add output gating to custom steps when:

- Step should only run if implementation produced changes
- Step depends on prior step success
- Step is expensive and should be skipped when not needed

### Common Conditions

```yaml
# Only if changes exist
if: steps.handle_outcome.outputs.has_changes == 'true'

# Only if implementation succeeded AND changes exist
if: steps.implement.outputs.implementation_success == 'true' && steps.handle_outcome.outputs.has_changes == 'true'
```

See [No Code Changes Handling](../planning/no-changes-handling.md) for details on the no-changes scenario.

## Related Documentation

- [Container-less CI](containerless-ci.md) - General CI setup patterns
- [GitHub Actions Security](github-actions-security.md) - Security patterns for workflows
